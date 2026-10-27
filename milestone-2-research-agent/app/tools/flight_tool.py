"""Flight Tool integrating OpenSky Network live aircraft states and deterministic synthetic mode.

Documentation & Attribution Check:
----------------------------------
- Checked on: 2026-10-27
- Endpoint: https://opensky-network.org/api/states/all
- Bounding Box query parameters:
  - lamin: minimum latitude (decimal degrees)
  - lomin: minimum longitude (decimal degrees)
  - lamax: maximum latitude (decimal degrees)
  - lomax: maximum longitude (decimal degrees)
- State Vector fields (index mapping):
  0: icao24 (str)
  1: callsign (str, up to 8 chars)
  2: origin_country (str)
  3: time_position (int/null, unix ts)
  4: last_contact (int, unix ts)
  5: longitude (float/null)
  6: latitude (float/null)
  7: baro_altitude (float/null, meters)
  8: on_ground (bool)
  9: velocity (float/null, m/s)
  10: true_track (float/null, degrees)
  11: vertical_rate (float/null, m/s)
  12: sensors (list[int]/null)
  13: geo_altitude (float/null, meters)
  14: squawk (str/null)
  15: spi (bool)
  16: position_source (int)
  17: category (int, optional)
- Authentication & Rate Limits:
  - OpenSky migrated to OAuth2 client credentials flow (auth token endpoint:
    https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token).
  - Anonymous access is strictly rate-limited (~400 credits/day, min 10s between requests).
  - Authenticated accounts receive higher credit allowances.
- Important Scope Notice:
  - OpenSky provides ONLY live transponder state vectors.
  - It NEVER provides airline schedules, flight delays, passenger gates, cancellations, or estimated arrivals.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
import httpx
from pydantic import BaseModel, Field

from app.schemas import (
    DataMode,
    ErrorInfo,
    FlightLookupStatus,
    FlightResult,
    SourceRecord,
)
from app.tools.airport_lookup import AirportNotFoundError, get_airport

OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
UNSUPPORTED_KEYWORDS = [
    "schedule",
    "scheduled",
    "delay",
    "delays",
    "delayed",
    "gate",
    "gates",
    "airline status",
    "cancellation",
    "cancelled",
    "estimated arrival",
    "eta",
    "etd",
]


class FlightToolOutput(BaseModel):
    """Internal envelope for Flight Tool outputs."""

    flights: list[FlightResult] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    errors: list[ErrorInfo] = Field(default_factory=list)


def _detect_unsupported_requirements(requirements: list[str]) -> list[str]:
    """Identify requirement terms that OpenSky live aircraft states cannot provide."""
    detected = set()
    for req in requirements:
        req_lower = req.lower()
        for kw in UNSUPPORTED_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", req_lower):
                detected.add(kw)
    return sorted(list(detected))


def _clean_str(val: str | None) -> str:
    return val.strip() if val else ""


def _parse_unix_utc(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


def _get_synthetic_flights(
    airport_code: str,
    flight_identifiers: list[str],
    unsupported_fields: list[str],
) -> FlightToolOutput:
    now_utc = datetime.now(timezone.utc)
    ts = int(now_utc.timestamp())
    source_id = f"flight-opensky-{airport_code}-{ts}"

    # Synthetic fixture data dictionary
    synth_db: dict[str, dict[str, Any]] = {
        "AIC101": {
            "icao24": "8005b1",
            "callsign": "AIC101",
            "origin_country": "India",
            "latitude": 28.60,
            "longitude": 77.15,
            "baro_altitude": 3200.0,
            "velocity": 140.0,
            "true_track": 110.0,
            "on_ground": False,
            "time_position": ts - 20,
        },
        "6E204": {
            "icao24": "800a42",
            "callsign": "6E204",
            "origin_country": "India",
            "latitude": 28.57,
            "longitude": 77.11,
            "baro_altitude": 220.0,
            "velocity": 0.0,
            "true_track": 280.0,
            "on_ground": True,
            "time_position": ts - 45,
        },
    }

    results: list[FlightResult] = []
    for identifier in flight_identifiers:
        ident_clean = _clean_str(identifier).upper()
        if unsupported_fields:
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.unsupported,
                    provider="synthetic",
                    data={
                        "unsupported_fields": unsupported_fields,
                        "reason": (
                            "Flight provider only provides live aircraft state vectors. "
                            f"Requested attributes {unsupported_fields} are unsupported."
                        ),
                    },
                    data_timestamp=now_utc,
                    source_id=source_id,
                )
            )
        elif ident_clean in synth_db:
            data = synth_db[ident_clean]
            data_ts = _parse_unix_utc(data.get("time_position")) or now_utc
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.found,
                    provider="synthetic",
                    data=data,
                    data_timestamp=data_ts,
                    source_id=source_id,
                )
            )
        else:
            results.append(
                FlightResult(
                    requested_identifier=identifier,
                    status=FlightLookupStatus.not_found,
                    provider="synthetic",
                    data={
                        "note": "Identifier not found in synthetic aircraft state database. Matching is by callsign only."
                    },
                    data_timestamp=None,
                    source_id=source_id,
                )
            )

    source = SourceRecord(
        source_id=source_id,
        provider="synthetic",
        data_type="synthetic",
        retrieved_at=now_utc,
        source_url="synthetic://flight/opensky",
    )

    return FlightToolOutput(flights=results, sources=[source], errors=[])


def get_flights(
    airport_code: str,
    flight_identifiers: list[str],
    research_requirements: list[str],
    *,
    mode: DataMode | str = DataMode.synthetic,
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
    bounding_box_radius_deg: float = 0.5,
) -> FlightToolOutput:
    """Retrieve aircraft states matching requested flight identifiers around an airport.

    Never raises exceptions to callers; errors are captured in FlightToolOutput.
    """
    mode_str = mode.value if isinstance(mode, DataMode) else str(mode)
    now_utc = datetime.now(timezone.utc)

    # 1. Unknown airport validation
    try:
        airport = get_airport(airport_code)
    except AirportNotFoundError:
        err = ErrorInfo(
            tool="flight_tool",
            code="AIRPORT_NOT_FOUND",
            message=f"Airport '{airport_code}' could not be resolved to geographic coordinates.",
            retryable=False,
        )
        flight_results = [
            FlightResult(
                requested_identifier=ident,
                status=FlightLookupStatus.error,
                provider="opensky" if mode_str == "live" else "synthetic",
                data={"error": "Airport not found."},
                data_timestamp=None,
                source_id=None,
            )
            for ident in flight_identifiers
        ]
        return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

    # 2. Early return if no flight identifiers requested
    if not flight_identifiers:
        return FlightToolOutput(flights=[], sources=[], errors=[])

    # Check for unsupported requirements
    unsupported_fields = _detect_unsupported_requirements(research_requirements)

    # 3. Synthetic mode
    if mode_str == "synthetic":
        return _get_synthetic_flights(airport.iata, flight_identifiers, unsupported_fields)

    # 4. Live mode with OpenSky Network
    from app.config import settings as app_settings
    from app.tools.opensky_auth import global_auth_manager

    # Calculate bounding box coordinates
    lat = airport.latitude
    lon = airport.longitude
    params: dict[str, Any] = {
        "lamin": round(lat - bounding_box_radius_deg, 4),
        "lamax": round(lat + bounding_box_radius_deg, 4),
        "lomin": round(lon - bounding_box_radius_deg, 4),
        "lomax": round(lon + bounding_box_radius_deg, 4),
    }

    managed_client = False
    if client is None:
        client = httpx.Client(timeout=timeout_seconds)
        managed_client = True

    try:
        # Check OAuth2 credentials
        cid = (app_settings.FLIGHT_CLIENT_ID or "").strip()
        csec = (app_settings.FLIGHT_CLIENT_SECRET or "").strip()
        use_auth = bool(cid and csec)

        headers: dict[str, str] = {}
        token: str | None = None

        if use_auth:
            token, auth_err = global_auth_manager.get_token(cid, csec, client)
            if auth_err:
                # Token failure must produce error FlightResults for all identifiers and never silently fall back
                flight_results = [
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.error,
                        provider="opensky",
                        data={"error": auth_err.message, "code": auth_err.code},
                        data_timestamp=None,
                        source_id=None,
                    )
                    for ident in flight_identifiers
                ]
                return FlightToolOutput(flights=flight_results, sources=[], errors=[auth_err])
            headers["Authorization"] = f"Bearer {token}"

        response: httpx.Response | None = None
        last_error_code = ""
        last_error_message = ""
        retryable_error = False

        for attempt in range(2):
            try:
                response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                if response.status_code == 200:
                    break
                elif response.status_code == 401 and use_auth:
                    # Token might have expired: invalidate cache and retry once with fresh token
                    global_auth_manager.clear()
                    token, auth_err = global_auth_manager.get_token(cid, csec, client, force_refresh=True)
                    if auth_err:
                        last_error_code = auth_err.code
                        last_error_message = auth_err.message
                        retryable_error = auth_err.retryable
                        break
                    headers["Authorization"] = f"Bearer {token}"
                    # Try states request once more
                    response = client.get(OPENSKY_STATES_URL, params=params, headers=headers)
                    if response.status_code == 200:
                        break
                    elif response.status_code in (401, 403):
                        last_error_code = "AUTH_FAILED"
                        last_error_message = f"OpenSky authentication failed (HTTP {response.status_code})."
                        retryable_error = False
                        break
                elif response.status_code == 429:
                    last_error_code = "RATE_LIMITED"
                    last_error_message = "OpenSky rate limit exceeded (HTTP 429)."
                    retryable_error = True
                    break  # no retry on 429
                elif response.status_code in (401, 403):
                    last_error_code = "AUTH_FAILED"
                    last_error_message = f"OpenSky authentication failed (HTTP {response.status_code})."
                    retryable_error = False
                    break  # no retry on auth failure
                elif 500 <= response.status_code < 600:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"OpenSky upstream server error (HTTP {response.status_code})."
                    retryable_error = True
                    if attempt == 0:
                        continue  # retry once
                    break
                elif 400 <= response.status_code < 500:
                    last_error_code = "PROVIDER_REJECTED"
                    last_error_message = f"OpenSky rejected request (HTTP {response.status_code})."
                    retryable_error = False
                    break
                else:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"Unexpected HTTP status {response.status_code}."
                    retryable_error = False
                    break
            except httpx.TimeoutException:
                last_error_code = "TIMEOUT"
                last_error_message = "OpenSky request timed out."
                retryable_error = True
                if attempt == 0:
                    continue  # retry once
                break
            except httpx.RequestError:
                last_error_code = "PROVIDER_ERROR"
                last_error_message = "Network error connecting to OpenSky."
                retryable_error = True
                if attempt == 0:
                    continue
                break

        # Handle non-200 outcome
        if response is None or response.status_code != 200:
            err = ErrorInfo(
                tool="flight_tool",
                code=last_error_code,
                message=last_error_message,
                retryable=retryable_error,
            )
            flight_results = [
                FlightResult(
                    requested_identifier=ident,
                    status=FlightLookupStatus.error,
                    provider="opensky",
                    data={"error": last_error_message, "code": last_error_code},
                    data_timestamp=None,
                    source_id=None,
                )
                for ident in flight_identifiers
            ]
            return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

        # Parse JSON
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object.")
        except Exception:
            err = ErrorInfo(
                tool="flight_tool",
                code="INVALID_PAYLOAD",
                message="Malformed JSON returned by OpenSky.",
                retryable=False,
            )
            flight_results = [
                FlightResult(
                    requested_identifier=ident,
                    status=FlightLookupStatus.error,
                    provider="opensky",
                    data={"error": "Malformed JSON payload from provider."},
                    data_timestamp=None,
                    source_id=None,
                )
                for ident in flight_identifiers
            ]
            return FlightToolOutput(flights=flight_results, sources=[], errors=[err])

        ts = int(now_utc.timestamp())
        source_id = f"flight-opensky-{airport.iata}-{ts}"

        # Treat null 'states' as empty list (OpenSky returns null states when no aircraft are in the box)
        raw_states = payload.get("states")
        states_list: list[list[Any]] = raw_states if isinstance(raw_states, list) else []

        # Index states by trimmed, uppercase callsign
        callsign_to_states: dict[str, list[list[Any]]] = {}
        for state in states_list:
            if isinstance(state, list) and len(state) > 1 and state[1] is not None:
                cs = str(state[1]).strip().upper()
                if cs:
                    callsign_to_states.setdefault(cs, []).append(state)

        source_record = SourceRecord(
            source_id=source_id,
            provider="opensky",
            data_type="current",
            retrieved_at=now_utc,
            source_url="https://opensky-network.org/api/states/all",
        )

        flight_results = []
        errors: list[ErrorInfo] = []

        for ident in flight_identifiers:
            if unsupported_fields:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.unsupported,
                        provider="opensky",
                        data={
                            "unsupported_fields": unsupported_fields,
                            "reason": (
                                "OpenSky provides live aircraft state vectors only. "
                                f"Requested attributes {unsupported_fields} are unsupported."
                            ),
                        },
                        data_timestamp=now_utc,
                        source_id=source_id,
                    )
                )
                continue

            ident_clean = _clean_str(ident).upper()
            matching_states = callsign_to_states.get(ident_clean, [])

            if len(matching_states) == 1:
                st = matching_states[0]
                time_pos = st[3] if len(st) > 3 else None
                state_data = {
                    "icao24": st[0] if len(st) > 0 else None,
                    "callsign": str(st[1]).strip() if len(st) > 1 and st[1] else None,
                    "origin_country": st[2] if len(st) > 2 else None,
                    "time_position": time_pos,
                    "last_contact": st[4] if len(st) > 4 else None,
                    "longitude": st[5] if len(st) > 5 else None,
                    "latitude": st[6] if len(st) > 6 else None,
                    "baro_altitude": st[7] if len(st) > 7 else None,
                    "on_ground": st[8] if len(st) > 8 else None,
                    "velocity": st[9] if len(st) > 9 else None,
                    "true_track": st[10] if len(st) > 10 else None,
                    "vertical_rate": st[11] if len(st) > 11 else None,
                    "geo_altitude": st[13] if len(st) > 13 else None,
                    "squawk": st[14] if len(st) > 14 else None,
                }
                data_ts = _parse_unix_utc(time_pos) or now_utc
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.found,
                        provider="opensky",
                        data=state_data,
                        data_timestamp=data_ts,
                        source_id=source_id,
                    )
                )
            elif len(matching_states) > 1:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.error,
                        provider="opensky",
                        data={
                            "error": f"Multiple aircraft ({len(matching_states)}) reported callsign '{ident_clean}'.",
                            "code": "AMBIGUOUS_MATCH",
                        },
                        data_timestamp=None,
                        source_id=source_id,
                    )
                )
                errors.append(
                    ErrorInfo(
                        tool="flight_tool",
                        code="AMBIGUOUS_MATCH",
                        message=f"Ambiguous match: {len(matching_states)} aircraft found for callsign '{ident_clean}'.",
                        retryable=False,
                    )
                )
            else:
                flight_results.append(
                    FlightResult(
                        requested_identifier=ident,
                        status=FlightLookupStatus.not_found,
                        provider="opensky",
                        data={
                            "note": (
                                f"Aircraft with callsign '{ident_clean}' not found within airport coverage area. "
                                "Matching is by exact callsign only (no commercial schedule translation)."
                            )
                        },
                        data_timestamp=None,
                        source_id=source_id,
                    )
                )

        return FlightToolOutput(flights=flight_results, sources=[source_record], errors=errors)

    finally:
        if managed_client:
            client.close()
