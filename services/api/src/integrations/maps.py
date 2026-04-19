# services/api/src/integrations/maps.py
# SYNAPSE — Google Maps Integration Layer
# Geocoding API v4 · Routes API · Places API (New) · Maps Datasets API
# Every call has fallback. No single point of failure.

import os
import logging
import httpx
from math import radians, sin, cos, sqrt, atan2
from typing import Optional

logger = logging.getLogger(__name__)

MAPS_KEY    = os.environ["GOOGLE_MAPS_API_KEY"]
TIMEOUT     = httpx.Timeout(20.0, connect=8.0)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
ROUTES_URL  = "https://routes.googleapis.com/directions/v2:computeRoutes"
PLACES_URL  = "https://places.googleapis.com/v1/places:searchNearby"

# Approximate travel speed fallbacks (km/h)
SPEED_WALK   = 5.0
SPEED_DRIVE  = 40.0   # urban average, traffic-adjusted
SPEED_TRANSIT = 20.0


# ─── Haversine (free, no quota) ──────────────────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Earth-surface great-circle distance in kilometres."""
    R = 6371
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (sin(d_lat / 2) ** 2
         + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2)
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def estimate_travel_minutes(km: float, mode: str = "driving") -> float:
    """Converts distance to approximate travel time. Used as Routes API fallback."""
    speed = {
        "walking":  SPEED_WALK,
        "driving":  SPEED_DRIVE,
        "transit":  SPEED_TRANSIT
    }.get(mode, SPEED_DRIVE)
    return (km / speed) * 60


# ─── geocode_address() ───────────────────────────────────────────────────────
async def geocode_address(address: str, region: str = "IN") -> dict:
    """
    Primary: Geocoding API v4 → lat, lng, admin boundary codes.
    Fallback: Returns None coords with requires_manual flag.
    """
    try:
        params = {
            "address": address,
            "region": region,
            "key": MAPS_KEY
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GEOCODE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            raise ValueError(f"Geocoding returned status: {data.get('status')}")

        result = data["results"][0]
        location = result["geometry"]["location"]

        # Extract admin boundary codes from address components
        admin_components = {}
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if "administrative_area_level_1" in types:
                admin_components["state"] = comp["short_name"]
            elif "administrative_area_level_2" in types:
                admin_components["district"] = comp["long_name"]
            elif "administrative_area_level_3" in types:
                admin_components["sub_district"] = comp["long_name"]
            elif "locality" in types:
                admin_components["city"] = comp["long_name"]
            elif "postal_code" in types:
                admin_components["pincode"] = comp["long_name"]

        admin_code = (
            f"{admin_components.get('state','XX')}-"
            f"{admin_components.get('district','00').replace(' ', '_').upper()}"
        )

        return {
            "lat": location["lat"],
            "lng": location["lng"],
            "formatted_address": result.get("formatted_address", address),
            "admin_code": admin_code,
            "admin_components": admin_components,
            "place_id": result.get("place_id"),
            "source": "geocoding_api"
        }

    except Exception as e:
        logger.warning(f"geocode_address failed for '{address}' ({e}), returning manual-entry fallback")
        return {
            "lat": None,
            "lng": None,
            "formatted_address": address,
            "admin_code": None,
            "admin_components": {},
            "place_id": None,
            "source": "geocoding_failed",
            "requires_manual_coordinates": True,
            "error": str(e)
        }


# ─── get_travel_time() ───────────────────────────────────────────────────────
async def get_travel_time(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
    mode: str = "DRIVE"
) -> dict:
    """
    Primary: Routes API → actual travel time with live traffic.
    Fallback: Haversine + speed estimate.
    Returns: { travel_time_mins, distance_km, source }
    """
    # Validate inputs
    for val, name in [(origin_lat, "origin_lat"), (origin_lng, "origin_lng"),
                      (dest_lat, "dest_lat"), (dest_lng, "dest_lng")]:
        if val is None:
            return _haversine_travel_result(origin_lat, origin_lng, dest_lat, dest_lng, mode, "missing_coords")

    try:
        payload = {
            "origin": {
                "location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}
            },
            "destination": {
                "location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}
            },
            "travelMode": mode,
            "routingPreference": "TRAFFIC_AWARE",
            "computeAlternativeRoutes": False,
            "languageCode": "en-US"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": MAPS_KEY,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.staticDuration"
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(ROUTES_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("routes"):
            raise ValueError("Routes API returned no routes")

        route = data["routes"][0]
        duration_secs = int(route["duration"].rstrip("s"))
        distance_m    = route["distanceMeters"]

        return {
            "travel_time_mins": round(duration_secs / 60, 1),
            "distance_km": round(distance_m / 1000, 2),
            "source": "routes_api",
            "source_label": "✅ Matched via: Live traffic routing (Routes API)"
        }

    except Exception as e:
        logger.warning(f"Routes API failed ({e}), using haversine fallback")
        return _haversine_travel_result(origin_lat, origin_lng, dest_lat, dest_lng, mode, str(e))


def _haversine_travel_result(
    lat1: float, lon1: float, lat2: float, lon2: float,
    mode: str, reason: str
) -> dict:
    """Haversine-based travel time estimate. Always succeeds."""
    mode_key = {"DRIVE": "driving", "WALK": "walking", "TRANSIT": "transit"}.get(mode, "driving")
    try:
        km = haversine_km(lat1, lon1, lat2, lon2)
        mins = estimate_travel_minutes(km, mode_key)
    except Exception:
        km, mins = 0.0, 0.0

    return {
        "travel_time_mins": round(mins, 1),
        "distance_km": round(km, 2),
        "source": "haversine_fallback",
        "source_label": "⚠️  Matched via: Estimated distance (API unavailable)",
        "fallback_reason": reason
    }


# ─── get_nearby_facilities() ─────────────────────────────────────────────────
async def get_nearby_facilities(
    lat: float, lng: float,
    facility_types: list[str] = None,
    radius_m: int = 2000
) -> dict:
    """
    Primary: Places API (New) → hospitals, clinics, water stations near need location.
    Fallback: Static list of generic facility types with contact format.
    """
    if facility_types is None:
        facility_types = ["hospital", "pharmacy", "fire_station", "police"]

    try:
        payload = {
            "includedTypes": facility_types,
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m)
                }
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": MAPS_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.location,places.types"
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(PLACES_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        places = []
        for p in data.get("places", []):
            places.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress", ""),
                "phone": p.get("nationalPhoneNumber"),
                "lat": p.get("location", {}).get("latitude"),
                "lng": p.get("location", {}).get("longitude"),
                "types": p.get("types", [])
            })

        return {
            "facilities": places,
            "source": "places_api",
            "count": len(places)
        }

    except Exception as e:
        logger.warning(f"Places API failed ({e}), returning static fallback facilities")
        return {
            "facilities": _static_facility_fallback(facility_types),
            "source": "static_fallback",
            "count": 0,
            "error": str(e)
        }


def _static_facility_fallback(facility_types: list[str]) -> list[dict]:
    """Generic placeholder facilities when Places API is unavailable."""
    type_defaults = {
        "hospital": {"name": "Nearest District Hospital", "phone": "104"},
        "fire_station": {"name": "Local Fire Station", "phone": "101"},
        "police": {"name": "Local Police Station", "phone": "100"},
        "pharmacy": {"name": "Nearby Pharmacy", "phone": None},
    }
    result = []
    for ft in facility_types:
        if ft in type_defaults:
            entry = type_defaults[ft].copy()
            entry["types"] = [ft]
            entry["address"] = "Contact local authorities for exact address"
            entry["lat"] = None
            entry["lng"] = None
            result.append(entry)
    return result


# ─── reverse_geocode() ───────────────────────────────────────────────────────
async def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Converts lat/lng → human-readable address + admin codes.
    Used for volunteer GPS check-in verification.
    """
    try:
        params = {
            "latlng": f"{lat},{lng}",
            "key": MAPS_KEY,
            "result_type": "administrative_area_level_3|locality"
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GEOCODE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {"formatted_address": f"{lat:.4f}, {lng:.4f}", "source": "raw_coords"}

        result = data["results"][0]
        return {
            "formatted_address": result.get("formatted_address", f"{lat:.4f}, {lng:.4f}"),
            "place_id": result.get("place_id"),
            "source": "reverse_geocoding_api"
        }
    except Exception as e:
        logger.warning(f"reverse_geocode failed ({e})")
        return {
            "formatted_address": f"{lat:.4f}, {lng:.4f}",
            "source": "fallback_raw_coords",
            "error": str(e)
        }


# ─── validate_checkin_proximity() ────────────────────────────────────────────
def validate_checkin_proximity(
    task_lat: float, task_lng: float,
    checkin_lat: float, checkin_lng: float,
    max_radius_km: float = 0.3
) -> dict:
    """
    Validates volunteer GPS check-in is within 300m of task location.
    Uses haversine (no quota, always available).
    Returns: { verified: bool, distance_m: float }
    """
    distance_km = haversine_km(task_lat, task_lng, checkin_lat, checkin_lng)
    return {
        "verified": distance_km <= max_radius_km,
        "distance_m": round(distance_km * 1000, 1),
        "max_allowed_m": max_radius_km * 1000
    }
