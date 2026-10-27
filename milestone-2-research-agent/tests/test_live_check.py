"""Unit and safety tests for scripts/live_check.py.

Verifies:
1. live_check is structured with a callable main(argv) entry point.
2. Under stubbed providers, live_check executes safely without network calls.
3. Secret-isolation test: fake keys and client secrets planted in settings
   never leak to stdout or stderr.
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import patch

from app.config import settings
from app.schemas import (
    DataMode,
    FlightLookupStatus,
    FlightResult,
    ResultStatus,
    WeatherDataType,
    WeatherResult,
    WeatherStatus,
)
from app.tools.flight_tool import FlightToolOutput
from app.tools.weather_tool import WeatherToolOutput
from scripts.live_check import main


def test_live_check_safety_and_no_secret_leak(capsys: Any) -> None:
    """Plant fake credentials into settings and verify they NEVER appear in output."""
    planted_google_key = "AIzaSySecretNeverLeakInLiveCheckReport12345"
    planted_client_id = "secret_opensky_client_id_9999"
    planted_client_sec = "secret_opensky_client_sec_8888"

    object.__setattr__(settings, "GOOGLE_API_KEY", planted_google_key)
    object.__setattr__(settings, "FLIGHT_CLIENT_ID", planted_client_id)
    object.__setattr__(settings, "FLIGHT_CLIENT_SECRET", planted_client_sec)

    # Mock weather tool
    fake_weather = WeatherToolOutput(
        weather=WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={"visibility": 10000.0, "temperature_2m": 25.0},
            units={"visibility": "m", "temperature_2m": "°C"},
            valid_time=None,
            source_id="test-wx-source-01",
        ),
        source=None,
        error=None,
    )

    # Mock flight tool
    fake_flight = FlightToolOutput(
        flights=[
            FlightResult(
                requested_identifier="AIC101",
                status=FlightLookupStatus.found,
                provider="opensky",
                data={"baro_altitude": 4000.0, "velocity": 150.0, "on_ground": False},
                data_timestamp=None,
                source_id="test-flt-source-01",
            )
        ],
        sources=[],
        errors=[],
    )

    with patch("scripts.live_check.get_weather", return_value=fake_weather), \
         patch("scripts.live_check.get_flights", return_value=fake_flight), \
         patch("scripts.live_check.get_llm") as mock_get_llm:

        class StubResponse:
            content = "OK"

        mock_llm_instance = mock_get_llm.return_value
        mock_llm_instance.invoke.return_value = StubResponse()

        # Run script via main() with flags
        exit_code = main(["--airport", "DEL", "--flights", "AIC101"])

        captured = capsys.readouterr()
        combined_output = captured.out + captured.err

        # Assert zero secret leakage
        assert planted_google_key not in combined_output
        assert planted_client_id not in combined_output
        assert planted_client_sec not in combined_output

        # Assert expected summary markers
        assert "CHECK SUMMARY TABLE" in combined_output
        assert "Weather (Open-Meteo)" in combined_output
        assert "Flight (OpenSky)" in combined_output
        assert "LLM Engine" in combined_output
        assert "Full Agent Pipeline" in combined_output
        assert exit_code == 0


def test_live_check_only_flag_filters_checks(capsys: Any) -> None:
    """Verify that --only weather restricts execution to weather check only."""
    fake_weather = WeatherToolOutput(
        weather=WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={"visibility": 9000.0},
            units={"visibility": "m"},
            valid_time=None,
            source_id="test-wx-source-02",
        ),
        source=None,
        error=None,
    )

    with patch("scripts.live_check.get_weather", return_value=fake_weather):
        exit_code = main(["--airport", "DEL", "--only", "weather"])
        captured = capsys.readouterr()

        assert "CHECK 1: WEATHER PROVIDER" in captured.out
        assert "CHECK 2: FLIGHT PROVIDER" not in captured.out
        assert "CHECK 3: LLM SYNTHESIS ENGINE" not in captured.out
        assert "CHECK 4: FULL RESEARCH AGENT PIPELINE" not in captured.out
        assert exit_code == 0
