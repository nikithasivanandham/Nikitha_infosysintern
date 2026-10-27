"""Weather Tool integrating Open-Meteo API and deterministic synthetic mode.

Documentation & Attribution Check:
----------------------------------
- Checked on: 2026-10-27
- Endpoint: https://api.open-meteo.com/v1/forecast
- Non-commercial terms: Free tier up to 10,000 daily calls, strictly non-commercial use.
- Data license & attribution: Creative Commons Attribution 4.0 International (CC BY 4.0).
  Attribution required when displaying or using data: "Weather data by Open-Meteo.com".
- Important disclaimer: Open-Meteo provides numerical forecast and model data.
  It is NEVER METAR, SPECI, or official aviation-grade weather observation data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any
import httpx
from pydantic import BaseModel, Field

from app.schemas import (
    DataMode,
    ErrorInfo,
    SourceRecord,
    WeatherDataType,
    WeatherResult,
    WeatherStatus,
)
from app.tools.airport_lookup import AirportNotFoundError, get_airport

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_VARIABLES = (
    "temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
    "visibility,precipitation,cloud_cover,weather_code"
)


class WeatherToolOutput(BaseModel):
    """Internal result envelope for Weather Tool execution."""

    weather: WeatherResult
    source: SourceRecord | None = None
    error: ErrorInfo | None = None


def _parse_iso_utc(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        # Open-Meteo with timezone=UTC returns "YYYY-MM-DDTHH:MM" or ISO strings
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _get_synthetic_weather(airport_code: str, as_of: datetime | None) -> WeatherToolOutput:
    now_utc = datetime.now(timezone.utc)
    valid_dt = as_of if as_of is not None else now_utc
    if valid_dt.tzinfo is None:
        valid_dt = valid_dt.replace(tzinfo=timezone.utc)

    cleaned_code = airport_code.strip().upper()
    ts = int(now_utc.timestamp())
    source_id = f"weather-open-meteo-{cleaned_code}-{ts}"

    obs = {
        "temperature_2m": 18.5,
        "wind_speed_10m": 12.0,
        "wind_direction_10m": 270,
        "wind_gusts_10m": 16.5,
        "visibility": 10000.0,
        "precipitation": 0.0,
        "cloud_cover": 20,
        "weather_code": 1,
    }
    units = {
        "temperature_2m": "°C",
        "wind_speed_10m": "km/h",
        "wind_direction_10m": "°",
        "wind_gusts_10m": "km/h",
        "visibility": "m",
        "precipitation": "mm",
        "cloud_cover": "%",
        "weather_code": "wmo code",
    }

    weather = WeatherResult(
        status=WeatherStatus.success,
        provider="synthetic",
        data_type=WeatherDataType.synthetic,
        observations=obs,
        units=units,
        valid_time=valid_dt,
        source_id=source_id,
    )

    source = SourceRecord(
        source_id=source_id,
        provider="synthetic",
        data_type="synthetic",
        retrieved_at=now_utc,
        source_url="synthetic://weather/open-meteo",
    )

    return WeatherToolOutput(weather=weather, source=source, error=None)


def get_weather(
    airport_code: str,
    as_of: datetime | None = None,
    *,
    mode: DataMode | str = DataMode.synthetic,
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
) -> WeatherToolOutput:
    """Retrieve weather data for an airport.

    In live mode, queries Open-Meteo forecast API using coordinates from airport lookup.
    In synthetic mode, returns deterministic synthetic fixtures with no network call.
    Never raises exceptions; errors are captured in WeatherToolOutput.
    """
    mode_str = mode.value if isinstance(mode, DataMode) else str(mode)
    now_utc = datetime.now(timezone.utc)

    # 1. Unknown airport validation
    try:
        airport = get_airport(airport_code)
    except AirportNotFoundError:
        err = ErrorInfo(
            tool="weather_tool",
            code="AIRPORT_NOT_FOUND",
            message=f"Airport '{airport_code}' could not be resolved to geographic coordinates.",
            retryable=False,
        )
        weather = WeatherResult(
            status=WeatherStatus.error,
            provider="open-meteo" if mode_str == "live" else "synthetic",
            data_type=WeatherDataType.current if mode_str == "live" else WeatherDataType.synthetic,
            observations={},
            units={},
            valid_time=None,
            source_id=None,
        )
        return WeatherToolOutput(weather=weather, source=None, error=err)

    # 2. Synthetic mode path
    if mode_str == "synthetic":
        return _get_synthetic_weather(airport.iata, as_of)

    # 3. Live mode path with Open-Meteo
    params: dict[str, Any] = {
        "latitude": airport.latitude,
        "longitude": airport.longitude,
        "current": WEATHER_VARIABLES,
        "hourly": WEATHER_VARIABLES,
        "timezone": "UTC",
    }

    # Internal helper for single request attempt
    def _do_request(c: httpx.Client) -> httpx.Response:
        return c.get(OPEN_METEO_FORECAST_URL, params=params)

    # Execute with at most 1 retry for timeout or 5xx
    managed_client = False
    if client is None:
        client = httpx.Client(timeout=timeout_seconds)
        managed_client = True

    try:
        response: httpx.Response | None = None
        last_error_code = ""
        last_error_message = ""
        retryable_error = False
        is_rate_limit = False

        for attempt in range(2):
            try:
                response = _do_request(client)
                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    is_rate_limit = True
                    last_error_code = "RATE_LIMITED"
                    last_error_message = "Open-Meteo rate limit exceeded (HTTP 429)."
                    retryable_error = True
                    break  # 429 is not retried immediately
                elif 500 <= response.status_code < 600:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"Open-Meteo upstream server error (HTTP {response.status_code})."
                    retryable_error = True
                    if attempt == 0:
                        continue  # retry once
                    break
                elif 400 <= response.status_code < 500:
                    last_error_code = "PROVIDER_REJECTED"
                    last_error_message = f"Open-Meteo rejected request (HTTP {response.status_code})."
                    retryable_error = False
                    break  # non-5xx 4xx: do not retry
                else:
                    last_error_code = "PROVIDER_ERROR"
                    last_error_message = f"Unexpected HTTP status {response.status_code}."
                    retryable_error = False
                    break
            except httpx.TimeoutException:
                last_error_code = "TIMEOUT"
                last_error_message = "Open-Meteo request timed out."
                retryable_error = True
                if attempt == 0:
                    continue  # retry once
                break
            except httpx.RequestError as exc:
                last_error_code = "PROVIDER_ERROR"
                last_error_message = "Network error connecting to Open-Meteo."
                retryable_error = True
                if attempt == 0:
                    continue
                break

        # Handle non-200 outcome
        if response is None or response.status_code != 200:
            err = ErrorInfo(
                tool="weather_tool",
                code=last_error_code,
                message=last_error_message,
                retryable=retryable_error,
            )
            status = WeatherStatus.unavailable if is_rate_limit else WeatherStatus.error
            weather = WeatherResult(
                status=status,
                provider="open-meteo",
                data_type=WeatherDataType.current,
                observations={},
                units={},
                valid_time=None,
                source_id=None,
            )
            return WeatherToolOutput(weather=weather, source=None, error=err)

        # Parse JSON
        try:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object.")
        except Exception:
            err = ErrorInfo(
                tool="weather_tool",
                code="INVALID_PAYLOAD",
                message="Malformed JSON returned by Open-Meteo.",
                retryable=False,
            )
            weather = WeatherResult(
                status=WeatherStatus.error,
                provider="open-meteo",
                data_type=WeatherDataType.current,
                observations={},
                units={},
                valid_time=None,
                source_id=None,
            )
            return WeatherToolOutput(weather=weather, source=None, error=err)

        # Extract current or hourly data
        current_data = payload.get("current")
        current_units = payload.get("current_units")
        hourly_data = payload.get("hourly")
        hourly_units = payload.get("hourly_units")

        if isinstance(current_data, dict) and isinstance(current_units, dict):
            data_type = WeatherDataType.current
            raw_time = current_data.get("time")
            valid_dt = _parse_iso_utc(raw_time) if raw_time else now_utc
            obs = {k: v for k, v in current_data.items() if k != "time"}
            units = {k: v for k, v in current_units.items() if k != "time"}
        elif isinstance(hourly_data, dict) and isinstance(hourly_units, dict) and hourly_data.get("time"):
            data_type = WeatherDataType.forecast
            first_time = hourly_data["time"][0] if hourly_data["time"] else None
            valid_dt = _parse_iso_utc(first_time) if first_time else now_utc
            obs = {k: v for k, v in hourly_data.items() if k != "time"}
            units = {k: v for k, v in hourly_units.items() if k != "time"}
        else:
            err = ErrorInfo(
                tool="weather_tool",
                code="INVALID_PAYLOAD",
                message="Open-Meteo response missing required observation blocks.",
                retryable=False,
            )
            weather = WeatherResult(
                status=WeatherStatus.error,
                provider="open-meteo",
                data_type=WeatherDataType.current,
                observations={},
                units={},
                valid_time=None,
                source_id=None,
            )
            return WeatherToolOutput(weather=weather, source=None, error=err)

        ts = int(now_utc.timestamp())
        source_id = f"weather-open-meteo-{airport.iata}-{ts}"

        weather = WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=data_type,
            observations=obs,
            units=units,
            valid_time=valid_dt,
            source_id=source_id,
        )

        source = SourceRecord(
            source_id=source_id,
            provider="open-meteo",
            data_type=data_type.value,
            retrieved_at=now_utc,
            source_url=str(response.url),
        )

        return WeatherToolOutput(weather=weather, source=source, error=None)

    finally:
        if managed_client:
            client.close()
