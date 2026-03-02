"""Integration service — outbound CRM webhook push.

Sends call analysis results to tenant-configured external webhook
endpoints.  Supports basic auth and API key authentication headers.
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT_SECONDS: float = 30.0
_MAX_RETRIES: int = 3


class AuthType(str, Enum):
    """Supported authentication methods for outbound webhooks."""

    none = "none"
    basic = "basic"
    api_key = "api_key"
    bearer = "bearer"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def push_to_crm(
    integration: Any,
    call_data: Dict[str, Any],
) -> bool:
    """Push call analysis results to the configured CRM webhook.

    Parameters
    ----------
    integration:
        An integration configuration object (typically the ``Integration``
        SQLAlchemy model instance).  Expected attributes:

        * ``webhook_url`` (str) — the target URL
        * ``auth_type`` (str) — ``"none"``, ``"basic"``, ``"api_key"``, or
          ``"bearer"``
        * ``auth_config`` (dict | None) — authentication credentials:

          - For ``basic``: ``{"username": "...", "password": "..."}``
          - For ``api_key``: ``{"header_name": "X-API-Key", "api_key": "..."}``
          - For ``bearer``: ``{"token": "..."}``

        * ``custom_headers`` (dict | None) — additional HTTP headers

    call_data:
        Dictionary containing the call analysis payload to send.

    Returns
    -------
    bool
        ``True`` if the webhook was delivered successfully (2xx),
        ``False`` otherwise.  Failures are logged but never raise.
    """
    webhook_url: str = getattr(integration, "webhook_url", "")
    if not webhook_url:
        logger.error(
            "Integration %s has no webhook_url configured — skipping push",
            getattr(integration, "id", "unknown"),
        )
        return False

    auth_type_raw = getattr(integration, "auth_type", "none")
    auth_type = (
        auth_type_raw.value if hasattr(auth_type_raw, "value") else str(auth_type_raw)
    ).lower()
    auth_config: Dict[str, str] = getattr(integration, "auth_config", None) or {}
    custom_headers: Dict[str, str] = getattr(integration, "custom_headers", None) or {}

    headers = _build_headers(auth_type, auth_config, custom_headers)

    logger.info(
        "Pushing call data to CRM webhook url=%s auth_type=%s",
        webhook_url,
        auth_type,
    )

    last_error: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url=webhook_url,
                    json=call_data,
                    headers=headers,
                )

            if response.is_success:
                logger.info(
                    "CRM webhook delivered successfully — status=%d url=%s",
                    response.status_code,
                    webhook_url,
                )
                return True

            # Log non-2xx responses but only retry on 5xx.
            logger.warning(
                "CRM webhook returned status=%d on attempt %d/%d — url=%s body=%s",
                response.status_code,
                attempt,
                _MAX_RETRIES,
                webhook_url,
                response.text[:500],
            )

            if response.status_code < 500:
                # Client error — don't retry.
                return False

        except httpx.TimeoutException as exc:
            last_error = exc
            logger.warning(
                "CRM webhook timed out on attempt %d/%d — url=%s: %s",
                attempt,
                _MAX_RETRIES,
                webhook_url,
                exc,
            )
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning(
                "CRM webhook request error on attempt %d/%d — url=%s: %s",
                attempt,
                _MAX_RETRIES,
                webhook_url,
                exc,
            )
        except Exception as exc:
            last_error = exc
            logger.exception(
                "Unexpected error pushing to CRM webhook on attempt %d/%d — url=%s",
                attempt,
                _MAX_RETRIES,
                webhook_url,
            )

    logger.error(
        "CRM webhook delivery failed after %d attempts — url=%s last_error=%s",
        _MAX_RETRIES,
        webhook_url,
        last_error,
    )
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_headers(
    auth_type: str,
    auth_config: Dict[str, str],
    custom_headers: Dict[str, str],
) -> Dict[str, str]:
    """Build the HTTP headers for the outbound webhook request.

    Parameters
    ----------
    auth_type:
        One of ``"none"``, ``"basic"``, ``"api_key"``, ``"bearer"``.
    auth_config:
        Credentials associated with the auth type.
    custom_headers:
        Additional headers supplied by the tenant.

    Returns
    -------
    dict
        Merged headers dictionary.
    """
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": f"SalesLens/{settings.APP_VERSION}",
    }

    # Merge custom headers (tenant may override Content-Type if needed).
    headers.update(custom_headers)

    if auth_type == "basic":
        import base64

        username = auth_config.get("username", "")
        password = auth_config.get("password", "")
        credentials = base64.b64encode(
            f"{username}:{password}".encode()
        ).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"

    elif auth_type == "api_key":
        header_name = auth_config.get("header_name", "X-API-Key")
        api_key = auth_config.get("api_key", "")
        headers[header_name] = api_key

    elif auth_type == "bearer":
        token = auth_config.get("token", "")
        headers["Authorization"] = f"Bearer {token}"

    return headers
