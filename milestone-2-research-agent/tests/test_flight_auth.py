import concurrent.futures
import json
import logging
import time
import httpx
import pytest

from app.config import settings
from app.schemas import DataMode, FlightLookupStatus
from app.tools.flight_tool import get_flights
from app.tools.opensky_auth import OPENSKY_TOKEN_URL, global_auth_manager


@pytest.fixture(autouse=True)
def reset_token_cache():
    """Ensure token cache is clean before and after every test."""
    global_auth_manager.clear()
    orig_cid = settings.FLIGHT_CLIENT_ID
    orig_csec = settings.FLIGHT_CLIENT_SECRET
    yield
    global_auth_manager.clear()
    settings.FLIGHT_CLIENT_ID = orig_cid
    settings.FLIGHT_CLIENT_SECRET = orig_csec


def _sample_states_payload():
    return {
        "time": 1793088005,
        "states": [
            [
                "8005b1",
                "AIC101",
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
        ],
    }


def test_anonymous_request_no_token_call_no_auth_header():
    token_called = False
    states_had_auth_header = False

    def handler(request: httpx.Request):
        nonlocal token_called, states_had_auth_header
        if "openid-connect/token" in str(request.url):
            token_called = True
            return httpx.Response(200, json={"access_token": "mock-token", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            if "Authorization" in request.headers:
                states_had_auth_header = True
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = ""
    settings.FLIGHT_CLIENT_SECRET = ""

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track aircraft"], mode=DataMode.live, client=client)

    assert token_called is False
    assert states_had_auth_header is False
    assert len(output.flights) == 1
    assert output.flights[0].status == FlightLookupStatus.found


def test_with_credentials_token_endpoint_called_and_bearer_sent():
    token_called = False
    received_bearer_header = None

    def handler(request: httpx.Request):
        nonlocal token_called, received_bearer_header
        if "openid-connect/token" in str(request.url):
            token_called = True
            assert request.method == "POST"
            assert "client_credentials" in request.read().decode()
            return httpx.Response(200, json={"access_token": "valid-bearer-xyz", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            received_bearer_header = request.headers.get("Authorization")
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "my_client_id"
    settings.FLIGHT_CLIENT_SECRET = "my_client_secret"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track aircraft"], mode=DataMode.live, client=client)

    assert token_called is True
    assert received_bearer_header == "Bearer valid-bearer-xyz"
    assert output.flights[0].status == FlightLookupStatus.found


def test_token_cached_two_consecutive_calls_one_token_request():
    token_request_count = 0
    states_request_count = 0

    def handler(request: httpx.Request):
        nonlocal token_request_count, states_request_count
        if "openid-connect/token" in str(request.url):
            token_request_count += 1
            return httpx.Response(200, json={"access_token": "cached-token-123", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            states_request_count += 1
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    # Call 1
    get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)
    # Call 2
    get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    assert token_request_count == 1
    assert states_request_count == 2


def test_expired_token_is_refreshed():
    token_request_count = 0

    def handler(request: httpx.Request):
        nonlocal token_request_count
        if "openid-connect/token" in str(request.url):
            token_request_count += 1
            # Return token expiring immediately (1 second)
            return httpx.Response(200, json={"access_token": f"token-{token_request_count}", "expires_in": 1})
        if "api/states/all" in str(request.url):
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    # First call fetches token-1
    get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)
    assert token_request_count == 1

    # Second call detects token expired/expiring (<60s remaining) and fetches token-2
    get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)
    assert token_request_count == 2


def test_states_401_with_cached_token_refreshes_and_retries_success():
    token_call_count = 0
    states_call_count = 0

    def handler(request: httpx.Request):
        nonlocal token_call_count, states_call_count
        if "openid-connect/token" in str(request.url):
            token_call_count += 1
            return httpx.Response(200, json={"access_token": f"token-attempt-{token_call_count}", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            states_call_count += 1
            # First states call rejects with 401
            if states_call_count == 1:
                return httpx.Response(401, text="Unauthorized: Token expired")
            # Second states call succeeds
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    # 1 initial token + 1 refresh on 401 = 2 token calls
    assert token_call_count == 2
    # 1 initial states + 1 retry = 2 states calls
    assert states_call_count == 2
    assert output.flights[0].status == FlightLookupStatus.found


def test_states_second_401_fails_with_auth_failed():
    def handler(request: httpx.Request):
        if "openid-connect/token" in str(request.url):
            return httpx.Response(200, json={"access_token": "token-always-bad", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            return httpx.Response(401, text="Unauthorized permanently")
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    assert len(output.errors) == 1
    assert output.errors[0].code == "AUTH_FAILED"
    assert output.flights[0].status == FlightLookupStatus.error


def test_token_endpoint_failures_and_no_fallback_to_anonymous():
    states_called = False

    for status_code, expected_code, expected_retryable in [
        (401, "AUTH_FAILED", False),
        (403, "AUTH_FAILED", False),
        (429, "RATE_LIMITED", True),
        (500, "PROVIDER_ERROR", True),
    ]:
        global_auth_manager.clear()
        states_called = False

        def handler(request: httpx.Request):
            nonlocal states_called
            if "openid-connect/token" in str(request.url):
                return httpx.Response(status_code, text="Token error")
            if "api/states/all" in str(request.url):
                states_called = True
                return httpx.Response(200, json=_sample_states_payload())
            return httpx.Response(404)

        settings.FLIGHT_CLIENT_ID = "test_cid"
        settings.FLIGHT_CLIENT_SECRET = "test_csec"

        client = httpx.Client(transport=httpx.MockTransport(handler))
        output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

        # Assert states endpoint was NEVER called (no silent fallback to anonymous)
        assert states_called is False
        assert len(output.errors) == 1
        assert output.errors[0].code == expected_code
        assert output.errors[0].retryable == expected_retryable
        assert output.flights[0].status == FlightLookupStatus.error


def test_token_endpoint_malformed_json():
    states_called = False

    def handler(request: httpx.Request):
        nonlocal states_called
        if "openid-connect/token" in str(request.url):
            return httpx.Response(200, text="Not JSON {")
        if "api/states/all" in str(request.url):
            states_called = True
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    assert states_called is False
    assert output.errors[0].code == "INVALID_PAYLOAD"
    assert output.flights[0].status == FlightLookupStatus.error


def test_token_endpoint_timeout_with_retry():
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        if "openid-connect/token" in str(request.url):
            call_count += 1
            raise httpx.ReadTimeout("Mock token timeout")
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    # Exactly 1 retry (2 total attempts)
    assert call_count == 2
    assert output.errors[0].code == "TIMEOUT"
    assert output.errors[0].retryable is True


def test_synthetic_mode_never_calls_token_endpoint():
    token_called = False

    def handler(request: httpx.Request):
        nonlocal token_called
        if "openid-connect/token" in str(request.url):
            token_called = True
        return httpx.Response(200)

    settings.FLIGHT_CLIENT_ID = "test_cid"
    settings.FLIGHT_CLIENT_SECRET = "test_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.synthetic, client=client)

    assert token_called is False
    assert output.flights[0].status == FlightLookupStatus.found
    assert output.flights[0].provider == "synthetic"


def test_fake_credentials_and_tokens_never_appear_in_output_or_logs(caplog):
    fake_cid = "PLANTED_CLIENT_ID_XYZ"
    fake_secret = "PLANTED_SECRET_987654321"
    fake_token = "PLANTED_TOKEN_BEARER_TOKEN_VALUE"

    def handler(request: httpx.Request):
        if "openid-connect/token" in str(request.url):
            return httpx.Response(200, json={"access_token": fake_token, "expires_in": 1800})
        if "api/states/all" in str(request.url):
            return httpx.Response(500, text="Simulated server error")
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = fake_cid
    settings.FLIGHT_CLIENT_SECRET = fake_secret

    with caplog.at_level(logging.DEBUG):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        output = get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    # String representation of all output fields
    output_str = str(output.model_dump())
    log_text = caplog.text

    for sensitive_str in (fake_cid, fake_secret, fake_token):
        assert sensitive_str not in output_str
        assert sensitive_str not in log_text


def test_concurrent_calls_produce_single_token_fetch():
    token_fetch_count = 0

    def handler(request: httpx.Request):
        nonlocal token_fetch_count
        if "openid-connect/token" in str(request.url):
            token_fetch_count += 1
            time.sleep(0.05)  # simulate network delay
            return httpx.Response(200, json={"access_token": "shared-token-concurrent", "expires_in": 1800})
        if "api/states/all" in str(request.url):
            return httpx.Response(200, json=_sample_states_payload())
        return httpx.Response(404)

    settings.FLIGHT_CLIENT_ID = "concurrent_cid"
    settings.FLIGHT_CLIENT_SECRET = "concurrent_csec"

    client = httpx.Client(transport=httpx.MockTransport(handler))

    def run_worker():
        return get_flights("DEL", ["AIC101"], ["Track"], mode=DataMode.live, client=client)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_worker) for _ in range(5)]
        results = [f.result() for f in futures]

    assert token_fetch_count == 1
    for res in results:
        assert res.flights[0].status == FlightLookupStatus.found
