"""Keep an adapter attempt on its explicitly configured endpoint."""
import urllib.request
import threading
from types import MappingProxyType

from ..errors import ModelProviderError


def guarded_transport_attempt(transport, guard, url, headers, body):
    """Trusted synchronous assembly around one bound, unmodified attempt.

    This is not a Python sandbox. The callback expires when the guard exits;
    violation or swallowed send errors can never become normal success.
    """
    if guard is None:
        return transport(url, headers, body)
    owner = threading.get_ident()
    active, called, violated = True, False, False
    result = None
    send_error = None
    immutable_headers = MappingProxyType(dict(headers))

    def contract_error():
        return ModelProviderError('transport guard contract violated', category='protocol')

    def send_once():
        nonlocal called, violated, result, send_error
        if not active or threading.get_ident() != owner or called or violated:
            violated = True
            raise contract_error()
        called = True  # Consume before transport, including an uncertain failure.
        try:
            result = transport(url, immutable_headers, body)
            return result
        except BaseException as exc:
            send_error = exc
            raise

    try:
        returned = guard(send_once, url, immutable_headers, body)
        if violated or not called or send_error is not None or returned is not result:
            raise contract_error()
        return returned
    finally:
        active = False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A redirect could disclose credentials or produce an uncounted request.
        # Let urllib surface HTTPError to the existing safe error normalization.
        return None


def open_single_attempt(request, *, timeout):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)
