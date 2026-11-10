"""Shared, conservative error normalization for HTTP model providers."""

from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.error import URLError

from ..errors import ModelProviderError

_SAFE_CODE = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_SECRET_SHAPE = re.compile(r"(?i)(?:sk[-_][A-Za-z0-9_-]{12,}|bearer\s+[A-Za-z0-9._~-]{12,})")
_BILLING_CODES = {
    "insufficient_quota",
    "quota_exceeded",
    "billing_hard_limit_reached",
    "payment_required",
    "insufficient_balance",
}


def safe_provider_code(value: Any, *, secret: str | None = None) -> str | None:
    if (
        isinstance(value, str)
        and _SAFE_CODE.fullmatch(value)
        and not _SECRET_SHAPE.search(value)
        and (not secret or secret not in value)
    ):
        return value
    return None


def safe_request_id(value: Any, *, secret: str | None = None) -> str | None:
    if (
        isinstance(value, str)
        and _SAFE_REQUEST_ID.fullmatch(value)
        and not _SECRET_SHAPE.search(value)
        and (not secret or secret not in value)
    ):
        return value
    return None


def error_fields(
    data: Any,
    headers: Mapping[str, Any] | None = None,
    *,
    secret: str | None = None,
) -> tuple[str | None, str | None]:
    provider_code = None
    request_id = None
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            provider_code = safe_provider_code(
                error.get("code") or error.get("type"), secret=secret
            )
            request_id = safe_request_id(
                error.get("request_id") or error.get("requestId"), secret=secret
            )
        request_id = safe_request_id(
            data.get("request_id") or data.get("requestId"), secret=secret
        ) or request_id

    if headers:
        normalized = {str(key).lower(): value for key, value in headers.items()}
        for name in ("x-request-id", "request-id", "x-amzn-requestid"):
            candidate = safe_request_id(normalized.get(name), secret=secret)
            if candidate:
                request_id = candidate
                break
    return provider_code, request_id


def classify_http_error(status: int, provider_code: str | None) -> tuple[str, bool]:
    normalized_code = (provider_code or "").lower().replace("-", "_")
    if status == 402 or normalized_code in _BILLING_CODES or any(
        marker in normalized_code for marker in ("insufficient_quota", "quota_exceeded", "balance", "billing")
    ):
        return "billing", False
    if status == 401:
        return "authentication", False
    if status == 403:
        return "permission", False
    if status == 404:
        return "not_found", False
    if status in {408, 504}:
        return "timeout", True
    if status == 413:
        return "request_too_large", False
    if status == 429:
        return "rate_limit", True
    if status in {400, 409, 422}:
        return "invalid_request", False
    if status >= 500:
        return "provider_unavailable", True
    return "unknown", False


def http_provider_error(
    *,
    provider_id: str,
    status: int,
    data: Any,
    headers: Mapping[str, Any] | None = None,
    secret: str | None = None,
) -> ModelProviderError:
    code, request_id = error_fields(data, headers, secret=secret)
    category, retryable = classify_http_error(status, code)
    return ModelProviderError(
        f"{provider_id} returned HTTP {status}",
        provider_id=provider_id,
        status=status,
        code=code,
        request_id=request_id,
        category=category,
        retryable=retryable,
    )


def provider_transport_error(provider_id: str, error: BaseException) -> ModelProviderError:
    reason = getattr(error, "reason", None) if isinstance(error, URLError) else None
    if (
        isinstance(error, TimeoutError)
        or isinstance(reason, TimeoutError)
        or type(error).__name__ in {"timeout", "Timeout"}
    ):
        category = "timeout"
        retryable = True
    else:
        # Do not include an exception string: urllib errors can include endpoint
        # URLs, proxy details, or other deployment-specific information.
        category = "transport"
        retryable = True
    message = (
        f"{provider_id} request timed out"
        if category == "timeout"
        else f"{provider_id} transport request failed"
    )
    return ModelProviderError(
        message,
        provider_id=provider_id,
        category=category,
        retryable=retryable,
    )


def attach_provider_context(
    error: ModelProviderError, provider_id: str, *, category: str
) -> ModelProviderError:
    if error.provider_id is None:
        error.provider_id = provider_id
    if error.category == "unknown":
        error.category = category
    return error


def validate_status(status: Any, provider_id: str) -> int:
    if type(status) is int and 100 <= status <= 599:
        return status
    raise ModelProviderError(
        "transport returned an invalid HTTP status",
        provider_id=provider_id,
        category="protocol",
    )
