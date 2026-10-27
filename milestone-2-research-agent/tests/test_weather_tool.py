import json
from datetime import datetime, timezone
import httpx
import pytest

from app.schemas import DataMode, WeatherDataType, WeatherResult, SourceRecord, WeatherStatus
from app.tools.weather_tool import get_weather


def _sample_open_meteo_payload():
    return {
        "latitude": 28.5665,
        "longitude": 77.1031,
        "current_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "wind_speed_10m": "km/h",
            "wind_direction_10m": "°",
            "wind_gusts_10m": "km/h",
            "visibility": "m",
            "precipitation": "mm",
            "cloud_cover": "%",
            "weather_code": "wmo code",
        },
        "current": {
            "time": "2026-10-27T06:00",
            "temperature_2m": 22.4,
            "wind_speed_10m": 8.5,
            "wind_direction_10m": 120,
            "wind_gusts_10m": 14.0,
            "visibility": 800.0,
            "precipitation": 0.0,
            "cloud_cover": 75,
            "weather_code": 45,
        },
    }


def test_weather_synthetic_mode_no_network():
    def dummy_handler(request: httpx.Request):
        pytest.fail("Network call was made in synthetic mode!")

    client = httpx.Client(transport=httpx.MockTransport(dummy_handler))
    output = get_weather("DEL", mode=DataMode.synthetic, client=client)

    assert output.error is None
    assert output.weather.status == WeatherStatus.success
    assert output.weather.data_type == WeatherDataType.synthetic
    assert output.weather.provider == "synthetic"
    assert output.source is not None
    assert output.source.data_type == "synthetic"
    assert output.weather.source_id == output.source.source_id

    # Schema validation check
    WeatherResult.model_validate(output.weather)
    SourceRecord.model_validate(output.source)


def test_weather_live_success_with_mock_transport():
    called = False

    def handler(request: httpx.Request):
        nonlocal called
        called = True
        assert "api.open-meteo.com" in request.url.host
        assert "latitude=" in request.url.query.decode()
        return httpx.Response(200, json=_sample_open_meteo_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    assert called is True
    assert output.error is None
    assert output.weather.status == WeatherStatus.success
    assert output.weather.provider == "open-meteo"
    assert output.weather.data_type == WeatherDataType.current
    assert output.weather.observations["visibility"] == 800.0
    assert output.weather.units["visibility"] == "m"
    assert output.weather.units["temperature_2m"] == "°C"
    assert output.weather.valid_time is not None
    assert output.weather.source_id is not None
    assert output.source is not None
    assert output.weather.source_id == output.source.source_id

    # Schema validation check
    WeatherResult.model_validate(output.weather)
    SourceRecord.model_validate(output.source)


def test_weather_unknown_airport():
    output = get_weather("UNKNOWN_AIRPORT", mode=DataMode.live)
    assert output.weather.status == WeatherStatus.error
    assert output.error is not None
    assert output.error.code == "AIRPORT_NOT_FOUND"
    assert output.error.retryable is False
    assert output.source is None


def test_weather_timeout_and_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Mock read timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    # Verify exactly 1 retry (2 attempts total)
    assert call_count == 2
    assert output.weather.status == WeatherStatus.error
    assert output.error is not None
    assert output.error.code == "TIMEOUT"
    assert output.error.retryable is True


def test_weather_429_rate_limited_no_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="Rate limit exceeded")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    # 429 should NOT retry
    assert call_count == 1
    assert output.weather.status == WeatherStatus.unavailable
    assert output.error is not None
    assert output.error.code == "RATE_LIMITED"
    assert output.error.retryable is True


def test_weather_500_then_success_on_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=_sample_open_meteo_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    assert call_count == 2
    assert output.error is None
    assert output.weather.status == WeatherStatus.success
    assert output.source is not None


def test_weather_400_rejected_no_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(400, text="Bad Request")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    assert call_count == 1
    assert output.weather.status == WeatherStatus.error
    assert output.error is not None
    assert output.error.code == "PROVIDER_REJECTED"
    assert output.error.retryable is False


def test_weather_malformed_json():
    def handler(request: httpx.Request):
        return httpx.Response(200, text="This is not JSON {")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    assert output.weather.status == WeatherStatus.error
    assert output.error is not None
    assert output.error.code == "INVALID_PAYLOAD"
    assert output.error.retryable is False


def test_weather_missing_fields_payload():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"something_else": 123})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_weather("DEL", mode=DataMode.live, client=client)

    assert output.weather.status == WeatherStatus.error
    assert output.error is not None
    assert output.error.code == "INVALID_PAYLOAD"
    assert output.error.retryable is False
