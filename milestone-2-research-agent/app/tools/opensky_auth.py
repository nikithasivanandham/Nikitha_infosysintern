"""OpenSky Network OAuth2 client credentials authentication helper.

Documentation & Specifications:
-------------------------------
- Checked on: 2026-10-27
- Token Endpoint: https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token
- Request format: POST with application/x-www-form-urlencoded
  - grant_type: client_credentials
  - client_id: <client_id>
  - client_secret: <client_secret>
- Token Lifetime: Typically 1800s (30 minutes).
- Refresh/Renewal Pattern:
  - Tokens should be cached in-memory and proactively refreshed with an expiry margin (e.g. 60 seconds).
  - If a resource endpoint returns 401 Unauthorized, the token cache should be invalidated
    and a fresh token requested once before failing with AUTH_FAILED.
- API Header: Authorization: Bearer <access_token>
- Security:
  - Secrets, client IDs, and token strings are NEVER logged or included in ErrorInfo / URLs.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Tuple
import httpx

from app.schemas import ErrorInfo

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float


class OpenSkyAuthManager:
    """Thread-safe in-memory cache and token fetcher for OpenSky OAuth2."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cached: _CachedToken | None = None

    def clear(self) -> None:
        """Clear cached token."""
        with self._lock:
            self._cached = None

    def get_token(
        self,
        client_id: str,
        client_secret: str,
        client: httpx.Client,
        *,
        force_refresh: bool = False,
    ) -> Tuple[str | None, ErrorInfo | None]:
        """Fetch or return cached OAuth2 access token.

        Never logs, returns, or leaks credentials or tokens in errors.
        """
        with self._lock:
            now = time.time()
            if not force_refresh and self._cached is not None:
                # Use cached token if more than 60 seconds of validity remain
                if now < (self._cached.expires_at - 60):
                    return self._cached.access_token, None

            # Fetch fresh token
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response: httpx.Response | None = None
            last_code = ""
            last_msg = ""
            retryable = False

            for attempt in range(2):
                try:
                    response = client.post(OPENSKY_TOKEN_URL, data=data, headers=headers)
                    if response.status_code == 200:
                        break
                    elif response.status_code in (401, 403):
                        last_code = "AUTH_FAILED"
                        last_msg = f"OpenSky OAuth2 token authentication failed (HTTP {response.status_code})."
                        retryable = False
                        break  # no retry on invalid credentials
                    elif response.status_code == 429:
                        last_code = "RATE_LIMITED"
                        last_msg = "OpenSky token endpoint rate limited (HTTP 429)."
                        retryable = True
                        break  # no retry
                    elif 500 <= response.status_code < 600:
                        last_code = "PROVIDER_ERROR"
                        last_msg = f"OpenSky token endpoint error (HTTP {response.status_code})."
                        retryable = True
                        if attempt == 0:
                            continue
                        break
                    else:
                        last_code = "PROVIDER_REJECTED"
                        last_msg = f"OpenSky token endpoint returned HTTP {response.status_code}."
                        retryable = False
                        break
                except httpx.TimeoutException:
                    last_code = "TIMEOUT"
                    last_msg = "OpenSky token request timed out."
                    retryable = True
                    if attempt == 0:
                        continue
                    break
                except httpx.RequestError:
                    last_code = "PROVIDER_ERROR"
                    last_msg = "Network error connecting to OpenSky token endpoint."
                    retryable = True
                    if attempt == 0:
                        continue
                    break

            if response is None or response.status_code != 200:
                self._cached = None
                return None, ErrorInfo(
                    tool="flight_tool",
                    code=last_code,
                    message=last_msg,
                    retryable=retryable,
                )

            try:
                payload = response.json()
                token = payload.get("access_token")
                expires_in = payload.get("expires_in", 1800)
                if not token or not isinstance(token, str):
                    raise ValueError("Missing access_token in response payload")

                expires_at = now + float(expires_in)
                self._cached = _CachedToken(access_token=token, expires_at=expires_at)
                return token, None
            except Exception:
                self._cached = None
                return None, ErrorInfo(
                    tool="flight_tool",
                    code="INVALID_PAYLOAD",
                    message="Malformed token payload returned by OpenSky token endpoint.",
                    retryable=False,
                )


# Global thread-safe singleton
global_auth_manager = OpenSkyAuthManager()
