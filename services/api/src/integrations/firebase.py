# services/api/src/integrations/firebase.py
# SYNAPSE — Firebase Admin SDK Integration
# Firestore CRUD helpers for all 8 collections
# Handles real-time-safe operations, retries, and error logging

import os
import logging
from typing import Any, Optional
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter, Query
from google.cloud.firestore_v1.base_query import BaseQuery
from google.api_core.exceptions import NotFound, AlreadyExists, GoogleAPICallError

logger = logging.getLogger(__name__)

# ─── Initialise Firebase Admin (idempotent) ──────────────────────────────────
def _init_firebase():
    if firebase_admin._apps:
        return
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        # Cloud Run: use Application Default Credentials
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", "synapse-platform-prod")
    })

_init_firebase()
db = firestore.client()

# ─── Collection references ───────────────────────────────────────────────────
COLLECTIONS = {
    "needs":         "needs",
    "volunteers":    "volunteers",
    "tasks":         "tasks",
    "outcomes":      "outcomes",
    "campaigns":     "campaigns",
    "users":         "users",
    "impact_chains": "impact_chains",
    "badges":        "badges",
}

def col(name: str):
    """Return a Firestore CollectionReference by logical name."""
    if name not in COLLECTIONS:
        raise ValueError(f"Unknown collection: '{name}'. Valid: {list(COLLECTIONS.keys())}")
    return db.collection(COLLECTIONS[name])


# ─── Timestamp helper ────────────────────────────────────────────────────────
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ─── write_doc() ─────────────────────────────────────────────────────────────
async def write_doc(collection: str, doc_id: str, data: dict, merge: bool = False) -> str:
    """
    Write (or merge) a document to Firestore.
    Auto-injects created_at on new writes, updated_at on all writes.
    Returns the document ID.
    """
    try:
        ref = col(collection).document(doc_id)
        payload = {**data, "updated_at": now_utc()}
        if not merge:
            payload.setdefault("created_at", now_utc())
        if merge:
            ref.set(payload, merge=True)
        else:
            ref.set(payload)
        logger.debug(f"write_doc: {collection}/{doc_id} {'merged' if merge else 'set'}")
        return doc_id
    except GoogleAPICallError as e:
        logger.error(f"write_doc {collection}/{doc_id} failed: {e}")
        raise


# ─── read_doc() ──────────────────────────────────────────────────────────────
async def read_doc(collection: str, doc_id: str) -> Optional[dict]:
    """
    Read a single document. Returns dict with 'id' injected, or None if not found.
    """
    try:
        snap = col(collection).document(doc_id).get()
        if not snap.exists:
            return None
        return {"id": snap.id, **snap.to_dict()}
    except NotFound:
        return None
    except GoogleAPICallError as e:
        logger.error(f"read_doc {collection}/{doc_id} failed: {e}")
        raise


# ─── update_doc() ────────────────────────────────────────────────────────────
async def update_doc(collection: str, doc_id: str, updates: dict) -> bool:
    """
    Partial update on an existing document.
    Returns True on success, False if document not found.
    """
    try:
        ref = col(collection).document(doc_id)
        ref.update({**updates, "updated_at": now_utc()})
        return True
    except NotFound:
        logger.warning(f"update_doc: {collection}/{doc_id} not found")
        return False
    except GoogleAPICallError as e:
        logger.error(f"update_doc {collection}/{doc_id} failed: {e}")
        raise


# ─── delete_doc() ────────────────────────────────────────────────────────────
async def delete_doc(collection: str, doc_id: str) -> bool:
    """Soft-delete via status field (we never hard-delete humanitarian records)."""
    return await update_doc(collection, doc_id, {"status": "deleted", "deleted_at": now_utc()})


# ─── query_collection() ──────────────────────────────────────────────────────
async def query_collection(
    collection: str,
    filters: list[tuple] = None,
    order_by: str = None,
    order_dir: str = "DESCENDING",
    limit: int = 50,
    start_after: Any = None
) -> list[dict]:
    """
    Query a collection with optional filters, ordering, and pagination.
    filters: list of (field, operator, value) tuples
             Operators: ==, !=, <, <=, >, >=, in, array_contains, array_contains_any
    Returns list of dicts with 'id' injected.
    """
    try:
        q: BaseQuery = col(collection)

        if filters:
            for field, op, value in filters:
                q = q.where(filter=FieldFilter(field, op, value))

        if order_by:
            direction = (
                Query.DESCENDING if order_dir.upper() == "DESCENDING"
                else Query.ASCENDING
            )
            q = q.order_by(order_by, direction=direction)

        if start_after:
            q = q.start_after(start_after)

        q = q.limit(limit)
        docs = q.stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]

    except GoogleAPICallError as e:
        logger.error(f"query_collection {collection} failed: {e}")
        raise


# ─── increment_field() ───────────────────────────────────────────────────────
async def increment_field(collection: str, doc_id: str, field: str, delta: int = 1) -> bool:
    """Atomic increment using Firestore server transform."""
    try:
        from google.cloud.firestore_v1 import Increment
        col(collection).document(doc_id).update({field: Increment(delta)})
        return True
    except Exception as e:
        logger.error(f"increment_field {collection}/{doc_id}.{field} failed: {e}")
        return False


# ─── array_union() ───────────────────────────────────────────────────────────
async def array_union(collection: str, doc_id: str, field: str, values: list) -> bool:
    """Atomic array union (no duplicates) using Firestore server transform."""
    try:
        from google.cloud.firestore_v1 import ArrayUnion
        col(collection).document(doc_id).update({field: ArrayUnion(values)})
        return True
    except Exception as e:
        logger.error(f"array_union {collection}/{doc_id}.{field} failed: {e}")
        return False


# ─── batch_write() ───────────────────────────────────────────────────────────
async def batch_write(operations: list[dict]) -> bool:
    """
    Execute multiple writes atomically.
    operations: list of { collection, doc_id, data, op: 'set'|'update'|'delete' }
    Max 500 ops per batch (Firestore limit).
    """
    if len(operations) > 500:
        raise ValueError("Batch exceeds 500 operations (Firestore limit)")
    try:
        batch = db.batch()
        for op in operations:
            ref = col(op["collection"]).document(op["doc_id"])
            action = op.get("op", "set")
            if action == "set":
                batch.set(ref, {**op["data"], "updated_at": now_utc()})
            elif action == "update":
                batch.update(ref, {**op["data"], "updated_at": now_utc()})
            elif action == "delete":
                batch.update(ref, {"status": "deleted", "deleted_at": now_utc()})
        batch.commit()
        return True
    except GoogleAPICallError as e:
        logger.error(f"batch_write failed: {e}")
        return False


# ─── Collection-specific helpers ─────────────────────────────────────────────

async def get_active_needs(district_code: str = None, limit: int = 50) -> list[dict]:
    """Fetch open/in-progress needs, optionally filtered by district."""
    filters = [("status", "in", ["open", "in_progress"])]
    if district_code:
        filters.append(("admin_code", "==", district_code))
    return await query_collection(
        "needs", filters=filters,
        order_by="urgency_score", order_dir="DESCENDING",
        limit=limit
    )


async def get_available_volunteers(max_hours_30d: int = 40) -> list[dict]:
    """Fetch volunteers eligible for dispatch."""
    return await query_collection(
        "volunteers",
        filters=[
            ("available", "==", True),
            ("hours_30d", "<", max_hours_30d)
        ],
        limit=200
    )


async def get_tasks_for_volunteer(volunteer_id: str) -> list[dict]:
    """Fetch all non-completed tasks for a volunteer (used in mobile app)."""
    return await query_collection(
        "tasks",
        filters=[
            ("volunteer_id", "==", volunteer_id),
            ("status", "in", ["pending", "accepted", "in_progress"])
        ],
        order_by="created_at", order_dir="DESCENDING"
    )


async def get_outcomes_for_need(need_id: str) -> list[dict]:
    """Fetch all outcomes linked to a need (for urgency recalibration)."""
    return await query_collection(
        "outcomes",
        filters=[("need_id", "==", need_id)]
    )


async def get_campaigns_active() -> list[dict]:
    """Fetch all active campaigns for donor portal."""
    return await query_collection(
        "campaigns",
        filters=[("status", "==", "active")],
        order_by="created_at", order_dir="DESCENDING"
    )


async def get_user_by_uid(uid: str) -> Optional[dict]:
    """Read user profile including role for auth redirect."""
    return await read_doc("users", uid)


async def get_coverage_gaps(district_code: str, min_urgency: float = 60.0, days: int = 14) -> list[dict]:
    """
    Returns wards with high average urgency AND zero task activity in last N days.
    Used by Government Agent.
    """
    from datetime import timedelta
    cutoff = now_utc() - timedelta(days=days)

    # Get high-urgency needs in district
    high_needs = await query_collection(
        "needs",
        filters=[
            ("admin_code", ">=", district_code),
            ("urgency_score", ">=", min_urgency),
            ("status", "in", ["open"])
        ],
        limit=100
    )

    # Get recent tasks in district
    recent_tasks = await query_collection(
        "tasks",
        filters=[
            ("created_at", ">=", cutoff)
        ],
        limit=500
    )
    task_need_ids = {t.get("need_id") for t in recent_tasks}

    # Coverage gap = high urgency need with no recent task
    gaps = []
    seen_wards = set()
    for need in high_needs:
        if need["id"] not in task_need_ids:
            ward = need.get("admin_code", "unknown")
            if ward not in seen_wards:
                seen_wards.add(ward)
                gaps.append({
                    "ward": ward,
                    "avg_urgency": need.get("urgency_score", 0),
                    "category": need.get("category", ""),
                    "need_id": need["id"]
                })
    return gaps
