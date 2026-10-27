# Airport Operations Coordination Engine - Research Agent

Standalone advisory decision support agent for gathering and summarizing weather and flight evidence.

> **Developer Note**: `GEMINI.md` in the repository root provides development guidance and constraints for AI coding tools. It is not runtime configuration.

---

## 1. Overview

The **Research Agent** is an advisory evidence-gathering service within the Airport Operations Coordination Engine. It inspects submitted operational requirements, queries weather and flight providers, normalizes the resulting observations into typed schemas, links factual findings to verified source identifiers, and produces structured analytical summaries.

### What the Research Agent DOES:
- Gathers weather forecasts, surface observations, and live transponder state vectors for specified airports and flights.
- Provides strict, source-grounded findings citing unambiguous source IDs (`provider_fact`).
- Optionally uses configured LLM engines (Gemini or Ollama) to synthesize advisory summaries and inferences (`inference`), guarded by strict anti-hallucination policies.
- Validates inputs and returns standard, deterministic Pydantic v2 data contracts.
- Provides hermetic test and execution capabilities via synthetic simulation fixtures (`DATA_MODE=synthetic`).

### What the Research Agent DOES NOT DO:
- **Never allocates gates, runways, or staff.**
- **Never makes final operational decisions.**
- **Never approves or rejects operational actions.**
- **Never controls aircraft or issues instructions to flight crews or controllers.**
- **Not certified Air Traffic Control (ATC) or an aviation safety-critical system.**

---

## 2. Quick Start (Windows PowerShell)

Follow these exact steps in Windows PowerShell to set up, test, and run the service locally:

```powershell
# 1. Create a virtual environment using Python 3.11+
python -m venv venv

# 2. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Copy the environment configuration template
Copy-Item .env.example .env

# 5. Run the complete test suite (all tests run hermetically with no internet access or API keys required)
.\venv\Scripts\pytest -v

# 6. Start the FastAPI application server locally on port 8000
.\venv\Scripts\uvicorn app.main:app --port 8000

# 7. In a separate PowerShell terminal, verify service health
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

---

## 3. Configuration

The application is configured using environment variables loaded from `.env` via `pydantic-settings`. 

> **Zero-Key Out of the Box**: Setting `DATA_MODE=synthetic` allows the full application, test suite, and HTTP API to run with zero API keys or external credentials.

| Environment Variable | Purpose | Required / Optional | Default Value | Example Placeholder |
|---|---|---|---|---|
| `LLM_PROVIDER` | LLM synthesis backend engine (`gemini` or `ollama`) | Optional | `gemini` | `gemini` |
| `GOOGLE_API_KEY` | Google Gemini API key (needed only if `LLM_PROVIDER=gemini` and synthesis is desired) | Optional | `""` (empty) | `AIzaSyYourSecretKeyHere` |
| `GEMINI_MODEL` | Google Gemini model identifier | Optional | `gemini-1.5-flash` | `gemini-1.5-flash` |
| `OLLAMA_BASE_URL` | Base URL for local Ollama HTTP instance | Optional | `http://localhost:11434` | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model identifier to query | Optional | `llama3` | `llama3` |
| `WEATHER_PROVIDER` | Weather tool backend provider name | Optional | `open-meteo` | `open-meteo` |
| `FLIGHT_PROVIDER` | Flight tool backend provider name | Optional | `opensky` | `opensky` |
| `FLIGHT_API_KEY` | Legacy OpenSky API key parameter placeholder | Optional | `""` (empty) | `""` |
| `FLIGHT_CLIENT_ID` | OpenSky Network OAuth2 Client ID | Optional | `""` (empty) | `your_opensky_client_id` |
| `FLIGHT_CLIENT_SECRET` | OpenSky Network OAuth2 Client Secret | Optional | `""` (empty) | `your_opensky_client_secret` |
| `REQUEST_TIMEOUT_SECONDS` | Network request timeout for provider calls and LLM invocations | Optional | `30` | `30` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | Optional | `INFO` | `INFO` |
| `DATA_MODE` | Runtime execution mode (`live` for real APIs, `synthetic` for local fixtures) | Optional | `synthetic` | `synthetic` |

---

## 4. API Reference

The Research Agent exposes three synchronous HTTP endpoints.

- **No CORS**: Cross-Origin Resource Sharing headers are deliberately omitted.
- **No Auth**: The service operates within an internal microservice perimeter without inbound authentication.
- **Recommended Architectural Pattern**: `Frontend / UI -> Main Backend Orchestrator -> Research Agent`.
- **Execution Model**: All requests are processed synchronously.

### `GET /health`
Returns service status and package version.

#### PowerShell:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

#### curl:
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

#### Response (HTTP 200):
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

### `GET /v1/capabilities`
Returns runtime capabilities, active data mode, supported tools, and bundled airport IATA codes. Never exposes secrets, keys, or internal tokens.

#### PowerShell:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/capabilities
```

#### curl:
```bash
curl -X GET "http://127.0.0.1:8000/v1/capabilities"
```

#### Response (HTTP 200):
```json
{
  "version": "0.1.0",
  "schema_version": "1.0",
  "supported_data_modes": [
    "live",
    "synthetic"
  ],
  "default_data_mode": "synthetic",
  "tools": [
    {
      "name": "weather_tool",
      "provider": "open-meteo",
      "live_supported": true,
      "synthetic_supported": true,
      "notes": "forecast/current model data, not METAR"
    },
    {
      "name": "flight_tool",
      "provider": "opensky",
      "live_supported": true,
      "synthetic_supported": true,
      "notes": "live aircraft state by exact callsign only; no schedule or delay data"
    }
  ],
  "llm": {
    "provider": "gemini",
    "configured": false
  },
  "supported_airports": [
    "AMS",
    "BLR",
    "BOM",
    "CCU",
    "CDG",
    "COK",
    "DEL",
    "DXB",
    "FRA",
    "HND",
    "HYD",
    "JFK",
    "LHR",
    "MAA",
    "ORD",
    "SIN"
  ]
}
```

---

### `POST /v1/research`
Executes synchronous research against submitted operational requirements.

#### Example Request Payload (`examples/request.json`):
```json
{
  "request_id": "req-20261027-001",
  "workflow_id": "wf-ops-883",
  "airport_code": "DEL",
  "disruption_type": "weather",
  "disruption_description": "Dense fog causing reduced runway visibility during morning departure bank.",
  "affected_flights": [
    "AIC101",
    "6E204"
  ],
  "research_requirements": [
    "Assess surface visibility trend over the next 3 hours.",
    "Verify current airborne status and positions of scheduled arrival flights."
  ],
  "planning_objective": "Determine whether ground delay program or flight holding recommendations are warranted.",
  "as_of": "2026-10-27T06:00:00Z",
  "data_mode": "synthetic"
}
```

#### PowerShell:
```powershell
$requestBody = Get-Content -Raw -Path .\examples\request.json
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/research -Method Post -ContentType "application/json" -Body $requestBody
```

#### curl:
```bash
curl -X POST "http://127.0.0.1:8000/v1/research" \
     -H "Content-Type: application/json" \
     -d @examples/request.json
```

#### Real Output from Synthetic Execution (HTTP 200):
```json
{
  "schema_version": "1.0",
  "request_id": "req-20261027-001",
  "workflow_id": "wf-ops-883",
  "agent": "research_agent",
  "status": "partial_success",
  "airport_code": "DEL",
  "data_mode": "synthetic",
  "summary": "Operational research summary for DEL [partial_success]: Surface weather at DEL: visibility 10000.0 m, wind 12.0 km/h at 270°, temperature 18.5 °C Gaps noted: 2 item(s) unfulfilled or missing.",
  "weather": {
    "status": "success",
    "provider": "synthetic",
    "data_type": "synthetic",
    "observations": {
      "temperature_2m": 18.5,
      "wind_speed_10m": 12.0,
      "wind_direction_10m": 270,
      "wind_gusts_10m": 16.5,
      "visibility": 10000.0,
      "precipitation": 0.0,
      "cloud_cover": 20,
      "weather_code": 1
    },
    "units": {
      "temperature_2m": "°C",
      "wind_speed_10m": "km/h",
      "wind_direction_10m": "°",
      "wind_gusts_10m": "km/h",
      "visibility": "m",
      "precipitation": "mm",
      "cloud_cover": "%",
      "weather_code": "wmo code"
    },
    "valid_time": "2026-10-27T06:00:00Z",
    "source_id": "weather-open-meteo-DEL-1793123235"
  },
  "flights": [
    {
      "requested_identifier": "AIC101",
      "status": "unsupported",
      "provider": "synthetic",
      "data": {
        "unsupported_fields": [
          "scheduled"
        ],
        "reason": "Flight provider only provides live aircraft state vectors. Requested attributes ['scheduled'] are unsupported."
      },
      "data_timestamp": "2026-10-27T17:47:15.139867Z",
      "source_id": "flight-opensky-DEL-1793123235"
    },
    {
      "requested_identifier": "6E204",
      "status": "unsupported",
      "provider": "synthetic",
      "data": {
        "unsupported_fields": [
          "scheduled"
        ],
        "reason": "Flight provider only provides live aircraft state vectors. Requested attributes ['scheduled'] are unsupported."
      },
      "data_timestamp": "2026-10-27T17:47:15.139867Z",
      "source_id": "flight-opensky-DEL-1793123235"
    }
  ],
  "findings": [
    {
      "finding": "Surface weather at DEL: visibility 10000.0 m, wind 12.0 km/h at 270°, temperature 18.5 °C",
      "evidence_refs": [
        "weather-open-meteo-DEL-1793123235"
      ],
      "kind": "provider_fact",
      "limitations": [
        "Open-Meteo numerical forecast/model data; not official METAR or certified aviation observation.",
        "Synthetic test fixture data."
      ]
    }
  ],
  "sources": [
    {
      "source_id": "weather-open-meteo-DEL-1793123235",
      "provider": "synthetic",
      "data_type": "synthetic",
      "retrieved_at": "2026-10-27T17:47:15.140868Z",
      "source_url": "synthetic://weather/open-meteo"
    },
    {
      "source_id": "flight-opensky-DEL-1793123235",
      "provider": "synthetic",
      "data_type": "synthetic",
      "retrieved_at": "2026-10-27T17:47:15.139867Z",
      "source_url": "synthetic://flight/opensky"
    }
  ],
  "missing_information": [
    "Flight 'AIC101' attribute query unsupported: ['scheduled'].",
    "Flight '6E204' attribute query unsupported: ['scheduled']."
  ],
  "errors": [],
  "created_at": "2026-10-27T17:47:15.144867Z"
}
```

*(Note: When requirements ask for "scheduled" flights, the OpenSky flight tool explicitly detects that schedule querying is unsupported, labels the flight results as `unsupported`, and the overall workflow yields `partial_success` because weather succeeded while flight requirements had unsupported gaps).*

---

## 5. Python Import Usage

Backend services running Python can import and call `run_research_agent` directly without HTTP overhead:

```python
from datetime import datetime, timezone
from app.agent import AgentDependencies, run_research_agent
from app.schemas import DataMode, DisruptionType, ResearchRequest, ResearchResult

# 1. Construct a typed request
request = ResearchRequest(
    request_id="req-local-001",
    workflow_id="wf-dispatch-101",
    airport_code="DEL",
    disruption_type=DisruptionType.weather,
    disruption_description="Reduced visibility conditions",
    affected_flights=["AIC101"],
    research_requirements=["surface visibility", "aircraft state"],
    planning_objective="Assess ground conditions",
    as_of=datetime.now(timezone.utc),
    data_mode=DataMode.synthetic,
)

# 2. Execute with default dependencies
result: ResearchResult = run_research_agent(request)
print(f"Status: {result.status.value}")
print(f"Summary: {result.summary}")

# 3. Executing with custom/mocked dependencies for integration testing
from app.tools.weather_tool import WeatherToolOutput
from app.schemas import WeatherResult, WeatherStatus, WeatherDataType

def custom_weather_mock(**kwargs) -> WeatherToolOutput:
    return WeatherToolOutput(
        weather=WeatherResult(
            status=WeatherStatus.success,
            provider="mock-provider",
            data_type=WeatherDataType.current,
            observations={"visibility": 8000.0, "temperature_2m": 22.0},
            units={"visibility": "m", "temperature_2m": "°C"},
            valid_time=datetime.now(timezone.utc),
            source_id="src-mock-wx-01",
        ),
        source=None,
        error=None,
    )

test_deps = AgentDependencies(weather_fn=custom_weather_mock)
mocked_result = run_research_agent(request, deps=test_deps)
assert mocked_result.weather.observations["visibility"] == 8000.0
```

---

## 6. Contract and Versioning

- **Schema Version**: `"1.0"` (represented in `SCHEMA_VERSION`).
- **Compatibility Rules**:
  - Additive changes (e.g. adding optional fields) are allowed within version `1.x`.
  - Any breaking change (removing fields, changing field types, changing enum meanings) requires a major version bump (`2.0`).
  - All timestamps are ISO-8601 strings in UTC (`YYYY-MM-DDTHH:MM:SS.mmmmmmZ`).
  - Provider-specific observations and state vector fields are flexible dictionaries where keys remain optional based on provider coverage.

### Top-Level Fields of `ResearchResult`
1. `schema_version` (`str`): Contract version (currently `"1.0"`).
2. `request_id` (`str`): Client-supplied request identifier.
3. `workflow_id` (`str`): Client-supplied workflow tracking identifier.
4. `agent` (`str`): Identifier of the responding agent (`"research_agent"`).
5. `status` (`ResultStatus`): Outcome enumeration (`success`, `partial_success`, `no_data`, `failed`).
6. `airport_code` (`str`): Uppercase 3-letter IATA or 4-letter ICAO airport code.
7. `data_mode` (`DataMode`): Mode used for evidence collection (`live` or `synthetic`).
8. `summary` (`str`): Executive analytical summary grounded entirely in evidence.
9. `weather` (`WeatherResult | None`): Weather observation object or `None` if weather tool was not executed.
10. `flights` (`list[FlightResult]`): Aircraft state vector lookup results for requested flight identifiers.
11. `findings` (`list[Finding]`): Grounded findings, tagged by kind (`provider_fact` or `inference`) with source references and limitations.
12. `sources` (`list[SourceRecord]`): Metadata for each upstream evidence payload retrieved.
13. `missing_information` (`list[str]`): List of gaps, unfound flights, unsupported attributes, or failed tools.
14. `errors` (`list[ErrorInfo]`): Structured diagnostics for encountered failures, including retryable flags.
15. `created_at` (`datetime`): UTC timestamp when the result was generated.

---

## 7. Status Semantics for Callers

> **CRITICAL RULE FOR CALLERS**: An HTTP `200 OK` status from `POST /v1/research` does **NOT** mean research succeeded. It only indicates that the Research Agent pipeline executed cleanly without crashing. Callers **must inspect the `status` field in the response JSON body**.

| Status Value | Meaning | Recommended Caller Action |
|---|---|---|
| `success` | All required tools ran successfully and all requested evidence was collected. | Proceed with full confidence. Pass findings and observations to downstream agents (Analysis and Resource Agents). |
| `partial_success` | At least one required tool returned valid evidence, but another tool failed, requested flights were not found, or unsupported requirements were omitted. | Proceed with caution. Check `missing_information` and `errors` to determine which evidence was degraded before deciding whether downstream agents can proceed. |
| `no_data` | Tools executed without fatal crashes, but zero relevant observations or aircraft states could be found (e.g. flight transponders off, zero matches). | Advise operational personnel that real-time situational evidence is currently unavailable for this target. Do not assume normal operations. |
| `failed` | No evidence could be gathered due to request validation failures, missing coordinates, or upstream provider errors. | Inspect `errors` array. If any error has `retryable=true`, the caller may retry after an exponential backoff. If `retryable=false`, do not retry without modifying request parameters. |

### HTTP Status Code Semantics
- **`200 OK`**: Pipeline completed. The result body contains the authoritative `ResearchResult` object whose `status` tells you whether data was found.
- **`422 Unprocessable Entity`**: Invalid request format, invalid airport code, missing required fields, or empty requirements list. The caller must fix the payload.
- **`500 Internal Server Error`**: Unexpected fatal crash outside the agent pipeline (e.g. server infrastructure failure).

### Error Objects and Retryability
The `errors` list contains objects of shape:
```json
{
  "tool": "weather_tool",
  "code": "PROVIDER_ERROR",
  "message": "Open-Meteo upstream server error (HTTP 502).",
  "retryable": true
}
```
- When `retryable: true`: Indicates a transient failure (e.g. network timeout, upstream 5xx, or HTTP 429 rate limit). The caller may retry the request after a delay.
- When `retryable: false`: Indicates a deterministic or configuration rejection (e.g. unknown airport code, HTTP 400 bad request, or invalid OAuth2 credentials). Retrying without changes will fail.

---

## 8. Timeouts and Performance

### Configuration Values
- `REQUEST_TIMEOUT_SECONDS` (default: `30` seconds): Applied to each outbound HTTP call to upstream providers (Open-Meteo, OpenSky, and LLM providers).
- **Internal Tool Retries**: At most **1 retry** (maximum 2 total attempts) for transient failures (timeouts and 5xx errors).

### Pipeline Execution Architecture
The LangGraph pipeline branches from `determine_required_tools` to execute tools. When running synchronously in standard Python threads:
- Weather collection and flight collection execute as branch nodes before synchronizing at `normalize_and_validate_evidence`.
- Upstream calls within each tool are executed sequentially per attempt.
- LLM synthesis runs after tools complete.

### Arithmetic Derivation of Recommended Caller Timeout
1. **Weather Tool Execution**:
   - Up to 2 attempts $\times$ `REQUEST_TIMEOUT_SECONDS` (30s) = **60 seconds maximum**.
2. **Flight Tool Execution**:
   - OAuth2 Token Fetch (if credentials present): up to 2 attempts $\times$ 30s = **60 seconds maximum**.
   - Flight States Request: up to 2 attempts $\times$ 30s = **60 seconds maximum**.
   - Total Flight Tool = **120 seconds maximum**.
3. **LLM Synthesis**:
   - 1 attempt $\times$ `REQUEST_TIMEOUT_SECONDS` (30s) = **30 seconds maximum**.

$$\text{Worst-Case Server Execution} \approx 60\text{s (Weather)} + 120\text{s (Flight)} + 30\text{s (LLM)} = 210\text{ seconds}$$

### Recommended Caller Timeouts
- **For Live Mode (`DATA_MODE=live`)**: Set caller client timeout to **`210` - `240` seconds** to accommodate full worst-case retries and upstream backoff.
- **For Synthetic Mode (`DATA_MODE=synthetic`)**: In-memory mock evaluation completes in under 200ms; a caller timeout of **`5` - `10` seconds** is more than sufficient.

---

## 9. Planning Agent Mapping

The Research Agent maps string items in `research_requirements` to internal tools using case-insensitive whole-word regular expression matching in `app/graph.py`.

### Exact Keyword Lists from `app/graph.py`
- **Weather Tool Keywords**:
  `"weather"`, `"wind"`, `"visibility"`, `"rain"`, `"precipitation"`, `"forecast"`, `"temperature"`, `"cloud"`, `"gust"`
- **Flight Tool Keywords**:
  `"flight"`, `"aircraft"`, `"aircraft state"`, `"status"`, `"delay"`, `"schedule"`, `"eta"`, `"arrival"`, `"departure"`

### Triggering Rules
1. If any requirement matches a weather keyword $\rightarrow$ `weather_tool` is activated.
2. If any requirement matches a flight keyword $\rightarrow$ `flight_tool` is activated.
3. If `affected_flights` list is non-empty $\rightarrow$ `flight_tool` is activated automatically.
4. **Unrecognized Requirements**: If a requirement string does not match any keyword from either list, it is preserved and flagged in `missing_information` as:  
   `"Unsupported or unrecognized requirement: <text>"`.

### Examples of Requirement Strings to Tools
| Requirement String | Tools Activated | Note |
|---|---|---|
| `"Assess surface visibility trend over next 3 hours"` | `weather_tool` | Matches `"visibility"` |
| `"Check wind gusts and cloud ceiling"` | `weather_tool` | Matches `"wind"`, `"gust"`, `"cloud"` |
| `"Verify current airborne status of inbound traffic"` | `flight_tool` | Matches `"status"` |
| `"Verify aircraft state and altitude"` | `flight_tool` | Matches `"aircraft"`, `"aircraft state"` |
| `"Check weather conditions and flight delays"` | `weather_tool`, `flight_tool` | Matches `"weather"` and `"flight"`, `"delay"` (Flight tool will flag schedule/delay queries as unsupported) |
| `"Check catering logistics and passenger baggage status"` | None | Unrecognized; recorded in `missing_information` |

### How Request Fields are Used or Ignored Today
- `airport_code`: **Used**. Geocoded via `app/data/airports.json` to coordinates for weather and OpenSky bounding box queries.
- `research_requirements`: **Used**. Parsed to determine required tools and check for unsupported capabilities.
- `affected_flights`: **Used**. Triggers flight tool; each identifier is looked up by exact callsign match.
- `data_mode`: **Used**. Dictates live network calls vs. synthetic fixture evaluation.
- `request_id`, `workflow_id`: **Used**. Carried through to the output result for distributed tracing.
- `as_of`: **Accepted, partially used**. Passed to weather tool; in synthetic mode controls deterministic mock timestamps; OpenSky live API only provides current live states.
- `disruption_type`: **Accepted, not used for routing**. Included in evidence bundle for LLM synthesis context, but does not alter tool selection.
- `disruption_description`: **Accepted, not used for routing**. Passed as background context for LLM synthesis.
- `planning_objective`: **Accepted, not yet used**. Stored for context, but does not alter tool selection or algorithmic decisions.

---

## 10. How Other Agents Consume the Result

Downstream agents in the Airport Operations Coordination Engine should consume `ResearchResult` according to strict boundary rules:

### Analysis Agent Consumption
- **Primary Fields**: `findings`, `sources`, `missing_information`.
- **Finding Kinds**:
  - `provider_fact`: Authoritative, verified measurements originating directly from provider payloads. **Safe to use as ground-truth evidence.**
  - `inference`: High-level analytical deductions generated during LLM synthesis. **Must NOT be treated as hard evidence.** Always inspect attached `limitations`.
- **Citations**: Each fact references a `source_id` in `evidence_refs`. The Analysis Agent can look up the corresponding record in `sources` to audit origin URLs and retrieval timestamps.
- **Handling Gaps**: Must check `missing_information` to see what operational data is incomplete before drawing conclusions.

### Resource Agent Consumption
- **Primary Fields**: `weather.observations`, `weather.units`, `flights.data`.
- **Weather Metrics**: Use `weather.observations` (e.g. `visibility`, `wind_speed_10m`, `wind_gusts_10m`, `temperature_2m`) and verify units against `weather.units`. Remember: Open-Meteo provides forecast model outputs, never certified METAR.
- **Flight Vectors**: Use `flights` array. Inspect each `flight.status`:
  - `found`: Real live transponder telemetry (`latitude`, `longitude`, `baro_altitude`, `velocity`, `true_track`, `on_ground`).
  - `not_found`: Aircraft transponder is not within receiver coverage.
  - `unsupported`: The requested query asked for commercial schedules, gates, or delays that OpenSky does not provide.
- **Safety Boundary**: The Resource Agent must never assume gate assignments, passenger connections, or ATC clearances based on Research Agent output.

---

## 11. Providers and Limitations

### 1. Open-Meteo (Weather Provider)
- **Attribution**: Weather data provided by [Open-Meteo.com](https://open-meteo.com) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Terms Verified**: **2026-10-27**. Terms and rate limits are subject to change by the provider.
- **Commercial Terms**: Open-Meteo is free for non-commercial use up to 10,000 daily API calls. Commercial deployment requires an enterprise license.
- **Data Nature**: Numerical forecast and global model weather data. **Never describe or treat Open-Meteo output as METAR or certified aviation weather.**

### 2. OpenSky Network (Flight Provider)
- **Attribution**: Aircraft state data provided by [The OpenSky Network](https://opensky-network.org).
- **Terms Verified**: **2026-10-27**.
- **Scope & Capabilities**: OpenSky provides **live transponder state vectors only** (ADS-B and Mode S). Lookups require an exact callsign match (e.g. `AIC101`).
- **Strict Inabilities**: OpenSky does **NOT** provide commercial airline flight schedules, passenger manifests, delay statuses, runway assignments, or gate assignments.
- **Authentication**: Supports OAuth2 client credentials via `FLIGHT_CLIENT_ID` and `FLIGHT_CLIENT_SECRET`. Tokens are cached and refreshed automatically before expiration. Anonymous access has strict hourly query limits.

### 3. Google Gemini (LLM Provider)
- **Terms Verified**: **2026-10-27**.
- **Free Tier Data-Use Caveat**: On Google AI Studio free tier models, prompts and completions may be reviewed by human reviewers and used to improve Google products.
- **Guardrail Protection**: The Research Agent sends **only** collected operational evidence and anonymized context to the model. Internal secrets, tokens, API keys, and private infrastructure details are never included in prompts.

### 4. Ollama (Local LLM Provider)
- **Characteristics**: Completely offline and self-hosted. Zero network data egress or external privacy exposure. Requires local GPU/CPU resources and a pre-pulled model (e.g. `llama3`).

---

## 12. LLM Synthesis Behaviour and Guardrails

LLM synthesis is an optional layer that enhances the executive summary. If no LLM is configured (`GOOGLE_API_KEY` is empty and Ollama is not configured), the agent uses a deterministic summary and skips LLM execution without error.

### Grounding and Anti-Hallucination Guardrails
When an LLM is configured, its output must pass two strict programmatic guardrails in `app/synthesis.py`:

1. **Numeric Token Guard**:
   - Every number (integer or float) in the LLM summary and findings must exist in the evidence bundle (tool findings, source IDs, or request timestamps).
   - If the LLM invents a number (e.g. claiming a "30-minute delay" when 30 was never in the evidence), the synthesis is rejected.
2. **Forbidden Keyword Guard**:
   - The LLM is forbidden from claiming operational authority or using out-of-scope terminology (`"metar"`, `"speci"`, `"schedule"`, `"delay"`, `"gate"`, `"allocate"`, `"approve"`, `"authorize"`, `"instruction"`).
   - **Known False-Positive Limit**: The guard uses word boundary matching. If the LLM legitimately tries to explain a limitation (e.g., writing *"No delay information was provided"*), the keyword guard will detect `"delay"` and reject the synthesis.

### Fallback Behavior
- If the LLM times out, errors, or fails either guardrail:
  - The agent silently discards the LLM response.
  - The deterministic summary and provider facts are retained.
  - An entry is added to `errors` with `tool: "llm"`, describing the rejection.
  - **Overall status is unaffected**: If tools gathered valid evidence, status remains `success` or `partial_success`.

---

## 13. Known Limitations

1. **Airport Coverage**: Geocoding is restricted to the bundled dataset in `app/data/airports.json` (**16 major international airports**: AMS, BLR, BOM, CCU, CDG, COK, DEL, DXB, FRA, HND, HYD, JFK, LHR, MAA, ORD, SIN). Requests for airports outside this list return an `AIRPORT_NOT_FOUND` error.
2. **Synchronous Execution**: All requests run synchronously; long-running batch polling is not supported.
3. **No Database or Persistent Job Store**: The service is completely stateless; no request history or state is persisted across requests.
4. **No In-Memory Caching Across Requests**: Each request triggers fresh provider queries.
5. **No Built-in Authentication**: Designed to run behind an authenticating gateway or orchestrator backend.

---

## 14. Troubleshooting

### 1. Missing API Key or Model Name
- **Symptom**: `GET /v1/capabilities` shows `"llm": {"configured": false}` or `errors` contains `LLM_CONFIG_ERROR`.
- **Fix**: Check `.env`. For Gemini, ensure `GOOGLE_API_KEY` and `GEMINI_MODEL` are set. For Ollama, verify `OLLAMA_BASE_URL` is reachable and `OLLAMA_MODEL` is pulled (`ollama pull llama3`).

### 2. Provider Rate Limits (HTTP 429)
- **Symptom**: `errors` array contains `RATE_LIMITED` from Open-Meteo or OpenSky.
- **Fix**: Switch to `DATA_MODE=synthetic` for development and testing. For OpenSky in live mode, supply valid `FLIGHT_CLIENT_ID` and `FLIGHT_CLIENT_SECRET`.

### 3. OneDrive File Lock Issues with pytest Cache
- **Symptom**: `pytest` fails with Windows file permission errors in `.pytest_cache`.
- **Fix**: The repository includes `pytest.ini` with `addopts = -p no:cacheprovider` to disable writing to the cache folder inside OneDrive.

### 4. Port Already in Use
- **Symptom**: Uvicorn fails to start with `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`.
- **Fix**: Stop the existing process or run Uvicorn on an alternate port:
  ```powershell
  .\venv\Scripts\uvicorn app.main:app --port 8080
  ```

---

## 15. Live Provider Check (Opt-In Diagnostic)

An opt-in diagnostic script is provided at `scripts/live_check.py` to verify real connectivity with upstream live providers (Open-Meteo, OpenSky Network, and configured LLM endpoints) without modifying `.env` or application code.

### Key Characteristics:
- **Not part of pytest**: `pytest` ignores this script completely. It is run only on demand.
- **Quota Politeness**: Uses a strict 1-call limit per provider (at most 1 weather call, 1 flight bounding box call, 1 LLM ping call).
- **In-Memory Live Mode**: Temporarily sets `DATA_MODE=live` inside the running process memory; disk `.env` remains untouched.
- **Privacy & Security**: Never prints, logs, or displays credentials, tokens, or `.env` contents. Only reports whether credentials are configured (`yes`/`no`) and error codes.
- **Google Gemini Free Tier Reminder**: Prompts and completions on the free tier may be used by Google to improve products. Only minimal, safe operational evidence is ever sent to the model.

### Exact PowerShell Commands:

```powershell
# Run full diagnostic for default airport (DEL) with empty flight callsign list
.\venv\Scripts\python scripts\live_check.py

# Run diagnostic for specific airport and flight callsigns
.\venv\Scripts\python scripts\live_check.py --airport DEL --flights AIC101,6E204

# Run diagnostic for a single provider/stage only
.\venv\Scripts\python scripts\live_check.py --only weather
.\venv\Scripts\python scripts\live_check.py --only flight --airport DEL --flights AIC101
.\venv\Scripts\python scripts\live_check.py --only llm
.\venv\Scripts\python scripts\live_check.py --only agent --airport DEL
```

### Interpreting the Summary Table:
| Status | Meaning | Action / Interpretation |
|---|---|---|
| `PASS` | Provider or pipeline connected and returned valid live data, or gracefully skipped without network call. | Upstream provider integration is functioning normally. |
| `PARTIAL` | Request connected, but transient rate limiting (HTTP 429) was encountered, or non-fatal data gaps occurred. | Retry after the rate limit window or verify quota. |
| `FAIL` | Upstream provider rejected the call (HTTP 401/403/400) or an unhandled exception occurred. | Check network connectivity, credentials in `.env`, or model availability. |

---

## 16. Project Layout

The repository is organized cleanly without dead code or placeholder files:

```
infosys_intern/
├── app/
│   ├── __init__.py                # Package version definition
│   ├── agent.py                   # Public entry point: run_research_agent & AgentDependencies
│   ├── config.py                  # Pydantic BaseSettings loading environment configuration
│   ├── graph.py                   # LangGraph research workflow pipeline
│   ├── main.py                    # FastAPI application & HTTP route definitions
│   ├── prompts.py                 # Grounded prompts for LLM advisory synthesis
│   ├── schemas.py                 # Pydantic v2 data models & contracts
│   ├── synthesis.py               # Evidence bundling, LLM execution & guardrails
│   ├── data/
│   │   └── airports.json          # Bundled coordinates for 16 major airports
│   ├── providers/
│   │   ├── __init__.py            # Provider package initializer
│   │   └── llm_provider.py        # LangChain ChatGoogleGenerativeAI & ChatOllama factory
│   └── tools/
│       ├── __init__.py            # Tools package initializer
│       ├── airport_lookup.py      # Offline airport coordinate geocoder
│       ├── flight_tool.py         # OpenSky Network live state vector tool & synthetic fixtures
│       ├── opensky_auth.py        # OpenSky OAuth2 token manager & renewal cache
│       └── weather_tool.py        # Open-Meteo weather forecast tool & synthetic fixtures
├── examples/
│   ├── request.json               # Canonical research request sample
│   └── response.json              # Canonical research result sample
├── scripts/
│   └── live_check.py              # Opt-in live provider verification script
├── tests/
│   ├── test_agent.py              # Tests for agent execution pipeline
│   ├── test_agent_llm.py          # Tests for agent LLM integration
│   ├── test_airport_lookup.py     # Tests for airport geocoder
│   ├── test_api.py                # Tests for FastAPI HTTP endpoints (/health, /v1/capabilities, /v1/research)
│   ├── test_flight_auth.py        # Tests for OpenSky OAuth2 authentication
│   ├── test_flight_tool.py        # Tests for flight tool lookups & synthetic fixtures
│   ├── test_health.py             # Health check tests
│   ├── test_live_check.py         # Safety & secret isolation tests for live_check script
│   ├── test_llm_provider.py       # Tests for LLM factory & provider isolation
│   ├── test_schemas.py            # Tests for Pydantic v2 schemas & contract validation
│   ├── test_synthesis.py          # Tests for synthesis guardrails & evidence bundling
│   └── test_weather_tool.py       # Tests for weather tool & Open-Meteo parsing
├── .env.example                   # Complete template of all environment variables
├── .gitignore                     # Git ignore rules (.env, venv, pycache, pytest cache)
├── GEMINI.md                      # Standing developer guidance for AI coding tools
├── pytest.ini                     # Pytest configuration with OneDrive cache workaround
├── README.md                      # Backend handoff and integration documentation
└── requirements.txt               # Complete pinned dependency list
```

