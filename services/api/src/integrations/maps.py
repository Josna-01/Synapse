"""
integrations/maps.py — SYNAPSE Maps & Location Integration
Uses open-source, API-key-free services:
  - Nominatim (OpenStreetMap) for geocoding
  - OSRM for routing / travel time
  - Overpass API for nearby facilities
  - Haversine formula (inline, no API) as primary distance fallback

All function signatures are identical to the previous version so no
calling code needs to change.
"""

import math
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Base URLs (overridable via .env) ─────────────────────────────────────────
NOMINATIM_BASE_URL = os.getenv(
    "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
)
OSRM_BASE_URL = os.getenv(
    "OSRM_BASE_URL", "http://router.project-osrm.org"
)
OVERPASS_BASE_URL = os.getenv(
    "OVERPASS_BASE_URL", "https://overpass-api.de/api"
)

# Nominatim usage policy: identify your app in the User-Agent header
NOMINATIM_USER_AGENT = "synapse-platform/1.0 (contact@synapse.example.com)"

# HTTP timeouts (seconds)
GEOCODE_TIMEOUT = 10
ROUTING_TIMEOUT = 15
PLACES_TIMEOUT = 20


# ── Haversine (no API, always available) ─────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate straight-line distance between two coordinates in kilometres.
    Used as the primary distance measure and as fallback when OSRM is unavailable.
    """
    R = 6371.0  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Geocoding — Nominatim ─────────────────────────────────────────────────────

async def geocode_address(address: str) -> Optional[dict]:
    """
    Convert a free-text address to lat/lng + admin boundary codes using Nominatim.

    Returns:
        {
            "lat": float,
            "lng": float,
            "display_name": str,
            "admin_boundary_code": str,   # e.g. "KA-DAKSHINA KANNADA"
            "source": "nominatim"
        }
    Returns None on failure (caller should prompt for manual lat/lng entry).

    Replaces: Google Geocoding API v4
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "in",          # bias to India
        "addressdetails": 1,
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=GEOCODE_TIMEOUT) as client:
            resp = await client.get(
                f"{NOMINATIM_BASE_URL}/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            results = resp.json()

        if not results:
            logger.warning("Nominatim: no results for address '%s'", address)
            return None

        r = results[0]
        addr = r.get("address", {})

        # Build an admin boundary code from state + district fields
        state = addr.get("state", "")
        district = addr.get("county", addr.get("state_district", ""))
        admin_code = f"{state[:2].upper()}-{district.upper()}" if state else ""

        return {
            "lat": float(r["lat"]),
            "lng": float(r["lon"]),
            "display_name": r.get("display_name", address),
            "admin_boundary_code": admin_code,
            "source": "nominatim",
        }

    except httpx.TimeoutException:
        logger.error("Nominatim geocoding timeout for address '%s'", address)
        return None
    except Exception as exc:
        logger.error("Nominatim geocoding error: %s", exc)
        return None


async def reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    """
    Convert lat/lng to a human-readable address + admin boundary code.

    Replaces: Google Geocoding API v4 (reverse mode)
    """
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=GEOCODE_TIMEOUT) as client:
            resp = await client.get(
                f"{NOMINATIM_BASE_URL}/reverse",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            r = resp.json()

        addr = r.get("address", {})
        state = addr.get("state", "")
        district = addr.get("county", addr.get("state_district", ""))
        admin_code = f"{state[:2].upper()}-{district.upper()}" if state else ""

        return {
            "lat": lat,
            "lng": lng,
            "display_name": r.get("display_name", ""),
            "admin_boundary_code": admin_code,
            "source": "nominatim",
        }

    except Exception as exc:
        logger.error("Nominatim reverse geocoding error: %s", exc)
        return None


# ── Routing — OSRM ────────────────────────────────────────────────────────────

async def get_travel_time(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> Optional[dict]:
    """
    Get actual road travel time and distance between two points using OSRM.

    Returns:
        {
            "duration_seconds": int,
            "distance_km": float,
            "source": "osrm"
        }
    Falls back to haversine estimate if OSRM is unavailable.

    Replaces: Google Routes API
    """
    # OSRM route endpoint: /route/v1/{profile}/{lng,lat};{lng,lat}
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coords}"
    params = {"overview": "false", "steps": "false"}

    try:
        async with httpx.AsyncClient(timeout=ROUTING_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM returned code: {data.get('code')}")

        route = data["routes"][0]
        return {
            "duration_seconds": int(route["duration"]),
            "distance_km": round(route["distance"] / 1000, 2),
            "source": "osrm",
        }

    except httpx.TimeoutException:
        logger.warning("OSRM timeout — falling back to haversine estimate")
    except Exception as exc:
        logger.warning("OSRM routing error (%s) — falling back to haversine", exc)

    # ── Haversine fallback ────────────────────────────────────────────────────
    straight_km = haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    # Approximate road distance = 1.4× straight-line; assume 40 km/h average
    road_km = straight_km * 1.4
    duration_sec = int((road_km / 40) * 3600)
    return {
        "duration_seconds": duration_sec,
        "distance_km": round(road_km, 2),
        "source": "haversine_fallback",
    }


async def get_travel_time_matrix(
    origins: list[dict],
    destinations: list[dict],
) -> Optional[list[list[Optional[dict]]]]:
    """
    Compute a travel-time matrix between multiple origins and destinations.

    origins / destinations: list of {"lat": float, "lng": float}
    Returns: 2D list where result[i][j] = get_travel_time result for origin i → dest j

    Falls back to haversine for any failed pair.

    Replaces: Google Routes API (computeRouteMatrix)
    """
    matrix: list[list[Optional[dict]]] = []
    for orig in origins:
        row: list[Optional[dict]] = []
        for dest in destinations:
            result = await get_travel_time(
                orig["lat"], orig["lng"], dest["lat"], dest["lng"]
            )
            row.append(result)
        matrix.append(row)
    return matrix


# ── Nearby Places — Overpass API ──────────────────────────────────────────────

async def get_nearby_facilities(
    lat: float,
    lng: float,
    radius_m: int = 2000,
    facility_types: Optional[list[str]] = None,
) -> list[dict]:
    """
    Find nearby facilities (hospitals, clinics, pharmacies, schools, water points)
    using the Overpass API (OpenStreetMap data).

    Args:
        lat, lng: centre point
        radius_m: search radius in metres (default 2000m)
        facility_types: OSM amenity tags to search for.
                        Defaults to health and education facilities.

    Returns:
        List of {"name": str, "type": str, "lat": float, "lng": float,
                 "distance_km": float}

    Replaces: Google Places API (Nearby Search)
    """
    if facility_types is None:
        facility_types = ["hospital", "clinic", "pharmacy", "school", "water_point"]

    # Build Overpass QL query
    amenity_filter = "|".join(facility_types)
    query = f"""
    [out:json][timeout:20];
    (
      node["amenity"~"{amenity_filter}"](around:{radius_m},{lat},{lng});
      way["amenity"~"{amenity_filter}"](around:{radius_m},{lat},{lng});
    );
    out center;
    """

    try:
        async with httpx.AsyncClient(timeout=PLACES_TIMEOUT) as client:
            resp = await client.post(
                f"{OVERPASS_BASE_URL}/interpreter",
                data={"data": query},
            )
            resp.raise_for_status()
            data = resp.json()

        places: list[dict] = []
        for element in data.get("elements", []):
            # way elements have a "center" sub-object; node elements have lat/lon directly
            if element["type"] == "node":
                p_lat, p_lng = element["lat"], element["lon"]
            elif element["type"] == "way" and "center" in element:
                p_lat, p_lng = element["center"]["lat"], element["center"]["lon"]
            else:
                continue

            tags = element.get("tags", {})
            name = tags.get("name", tags.get("amenity", "Unknown"))
            amenity = tags.get("amenity", "facility")

            places.append({
                "name": name,
                "type": amenity,
                "lat": p_lat,
                "lng": p_lng,
                "distance_km": round(haversine_km(lat, lng, p_lat, p_lng), 2),
            })

        # Sort by distance
        places.sort(key=lambda x: x["distance_km"])
        return places

    except httpx.TimeoutException:
        logger.error("Overpass API timeout for lat=%s, lng=%s", lat, lng)
        return []
    except Exception as exc:
        logger.error("Overpass API error: %s", exc)
        return []


# ── Startup Health Check ──────────────────────────────────────────────────────

async def check_nominatim_connectivity() -> bool:
    """
    Verify Nominatim is reachable. Called on FastAPI startup.
    Uses a lightweight status endpoint.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{NOMINATIM_BASE_URL}/status.php",
                params={"format": "json"},
                headers={"User-Agent": NOMINATIM_USER_AGENT},
            )
            return resp.status_code == 200
    except Exception as exc:
        logger.warning("Nominatim connectivity check failed: %s", exc)
        return False
