import json
from datetime import datetime, timezone
import httpx
import pytest

from app.config import settings
from app.schemas import DataMode, FlightLookupStatus, FlightResult, SourceRecord
from app.tools.flight_tool import get_flights
from app.tools.opensky_auth import global_auth_manager


@pytest.fixture(autouse=True)
def isolate_flight_credentials():
    """Ensure tests in test_flight_tool run without ambient environment credentials."""
    global_auth_manager.clear()
    orig_cid = settings.FLIGHT_CLIENT_ID
    orig_csec = settings.FLIGHT_CLIENT_SECRET
    object.__setattr__(settings, "FLIGHT_CLIENT_ID", "")
    object.__setattr__(settings, "FLIGHT_CLIENT_SECRET", "")
    yield
    global_auth_manager.clear()
    object.__setattr__(settings, "FLIGHT_CLIENT_ID", orig_cid)
    object.__setattr__(settings, "FLIGHT_CLIENT_SECRET", orig_csec)


def _sample_opensky_payload(states=None):

    if states is None:
        states = [
            [
                "8005b1",
                "AIC101  ",
                "India",
                1793088000,
                1793088005,
                77.1031,
                28.5665,
                3200.0,
                False,
                140.5,
                110.0,
                0.0,
                None,
                3350.0,
                "4501",
                False,
                0,
            ]
        ]
    return {
        "time": 1793088005,
        "states": states,
    }


def test_flight_tool_synthetic_mode_zero_http_calls():
    def dummy_handler(request: httpx.Request):
        pytest.fail("Network call made in synthetic mode!")

    client = httpx.Client(transport=httpx.MockTransport(dummy_handler))
    output = get_flights(
        "DEL",
        ["AIC101", "UNKNOWN999"],
        ["Find aircraft position"],
        mode=DataMode.synthetic,
        client=client,
    )

    assert len(output.errors) == 0
    assert len(output.sources) == 1
    assert output.sources[0].provider == "synthetic"
    assert len(output.flights) == 2

    # AIC101 found
    assert output.flights[0].requested_identifier == "AIC101"
    assert output.flights[0].status == FlightLookupStatus.found
    assert output.flights[0].provider == "synthetic"
    assert output.flights[0].data["callsign"] == "AIC101"

    # UNKNOWN999 not_found
    assert output.flights[1].requested_identifier == "UNKNOWN999"
    assert output.flights[1].status == FlightLookupStatus.not_found

    # Schema validation check
    for f in output.flights:
        FlightResult.model_validate(f)
    for s in output.sources:
        SourceRecord.model_validate(s)


def test_flight_tool_live_exact_and_case_whitespace_match():
    request_count = 0

    def handler(request: httpx.Request):
        nonlocal request_count
        request_count += 1
        assert "opensky-network.org" in request.url.host
        assert "lamin=" in request.url.query.decode()
        return httpx.Response(200, json=_sample_opensky_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["  aic101  "],  # case-insensitive and whitespace-padded
        ["Monitor flight position"],
        mode=DataMode.live,
        client=client,
    )

    assert request_count == 1
    assert len(output.flights) == 1
    flt = output.flights[0]
    assert flt.status == FlightLookupStatus.found
    assert flt.data["callsign"] == "AIC101"
    assert flt.data["icao24"] == "8005b1"
    assert flt.data["baro_altitude"] == 3200.0
    assert flt.data_timestamp is not None
    assert flt.source_id == output.sources[0].source_id

    FlightResult.model_validate(flt)


def test_flight_tool_no_match_returns_not_found():
    def handler(request: httpx.Request):
        return httpx.Response(200, json=_sample_opensky_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["BAW123"],
        ["Track aircraft"],
        mode=DataMode.live,
        client=client,
    )

    assert len(output.flights) == 1
    flt = output.flights[0]
    assert flt.status == FlightLookupStatus.not_found
    assert "not found" in flt.data["note"]


def test_flight_tool_duplicate_callsign_ambiguous_match():
    # Two states with the same callsign
    dup_states = [
        ["8005b1", "AIC101", "India", 1793088000, 1793088005, 77.1, 28.5, 3200.0, False, 140.0, 110.0, 0.0, None, 3300.0, "4501", False, 0],
        ["8005b2", "AIC101", "India", 1793088000, 1793088005, 77.2, 28.6, 1200.0, False, 120.0, 90.0, 0.0, None, 1300.0, "4502", False, 0],
    ]

    def handler(request: httpx.Request):
        return httpx.Response(200, json=_sample_opensky_payload(dup_states))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track aircraft"],
        mode=DataMode.live,
        client=client,
    )

    assert len(output.flights) == 1
    assert output.flights[0].status == FlightLookupStatus.error
    assert output.flights[0].data["code"] == "AMBIGUOUS_MATCH"
    assert len(output.errors) == 1
    assert output.errors[0].code == "AMBIGUOUS_MATCH"


def test_flight_tool_null_states_returns_not_found():
    # OpenSky returns null 'states' when no aircraft are inside bounding box
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"time": 1793088005, "states": None})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101", "6E204"],
        ["Track aircraft"],
        mode=DataMode.live,
        client=client,
    )

    assert len(output.errors) == 0  # not an error!
    assert len(output.flights) == 2
    assert output.flights[0].status == FlightLookupStatus.not_found
    assert output.flights[1].status == FlightLookupStatus.not_found


def test_flight_tool_unsupported_requirements():
    def dummy_handler(request: httpx.Request):
        return httpx.Response(200, json=_sample_opensky_payload())

    client = httpx.Client(transport=httpx.MockTransport(dummy_handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["What is the flight delay and commercial schedule?"],
        mode=DataMode.live,
        client=client,
    )

    assert len(output.flights) == 1
    flt = output.flights[0]
    assert flt.status == FlightLookupStatus.unsupported
    assert "delay" in flt.data["unsupported_fields"]
    assert "schedule" in flt.data["unsupported_fields"]
    assert "unsupported" in flt.data["reason"]


def test_flight_tool_timeout_and_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Mock timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert call_count == 2
    assert len(output.errors) == 1
    assert output.errors[0].code == "TIMEOUT"
    assert output.errors[0].retryable is True
    assert output.flights[0].status == FlightLookupStatus.error


def test_flight_tool_429_rate_limited_no_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="Rate limit exceeded")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert call_count == 1
    assert output.errors[0].code == "RATE_LIMITED"
    assert output.errors[0].retryable is True


def test_flight_tool_401_403_auth_failed():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, text="Unauthorized")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert call_count == 1
    assert output.errors[0].code == "AUTH_FAILED"
    assert output.errors[0].retryable is False


def test_flight_tool_500_then_success():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, text="Server error")
        return httpx.Response(200, json=_sample_opensky_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert call_count == 2
    assert len(output.errors) == 0
    assert output.flights[0].status == FlightLookupStatus.found


def test_flight_tool_malformed_json():
    def handler(request: httpx.Request):
        return httpx.Response(200, text="Not valid json")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert output.errors[0].code == "INVALID_PAYLOAD"
    assert output.flights[0].status == FlightLookupStatus.error


def test_flight_tool_no_identifiers_zero_network_calls():
    def dummy_handler(request: httpx.Request):
        pytest.fail("Network called when identifiers list is empty!")

    client = httpx.Client(transport=httpx.MockTransport(dummy_handler))
    output = get_flights(
        "DEL",
        [],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    assert len(output.flights) == 0
    assert len(output.sources) == 0
    assert len(output.errors) == 0


def test_flight_tool_one_http_request_for_multiple_identifiers():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_sample_opensky_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights(
        "DEL",
        ["AIC101", "6E204", "VTI305"],
        ["Track"],
        mode=DataMode.live,
        client=client,
    )

    # Crucial rule: exactly 1 HTTP request for the bounding box
    assert call_count == 1
    assert len(output.flights) == 3
