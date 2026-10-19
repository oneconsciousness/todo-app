"""Per-request context: the request id, the replica's name, no caching of API responses, and the access line."""

import logging
import re
import socket
import time
from typing import Final
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.log import request_id_var, user_id_var

access_log = logging.getLogger("app.access")

REQUEST_ID: Final = re.compile(r"[A-Za-z0-9._-]{1,64}")
PROBE_PATHS: Final = frozenset({"/livez", "/readyz"})


class RequestContextMiddleware:
    """Tag each request and response, and log one access line per request.

    A pure ASGI middleware, not `BaseHTTPMiddleware`, so it runs in the request's own task and the
    context variables set here, and by the dependencies, are visible on both sides
    (https://www.starlette.io/middleware/#pure-asgi-middleware).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.served_by = socket.gethostname()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle one HTTP request; pass every other kind of connection straight through."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        sent_id = Headers(scope=scope).get("x-request-id", "")
        request_id = sent_id if REQUEST_ID.fullmatch(sent_id) else uuid4().hex
        request_id_var.set(request_id)
        user_id_var.set(None)
        response_status = 500
        started = time.perf_counter()

        async def send_with_headers(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
                headers.append("X-Served-By", self.served_by)
                if scope["path"].startswith("/api/"):
                    headers.append("Cache-Control", "no-store")
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            self.log_access(scope, 500, started)
            raise
        self.log_access(scope, response_status, started)

    def log_access(self, scope: Scope, status: int, started: float) -> None:
        """Log the access line, except for a probe that succeeded, which would only bury the useful lines."""
        if scope["path"] in PROBE_PATHS and status < 400:
            return
        route = scope.get("route")
        access_log.info(
            "request",
            extra={
                "method": scope["method"],
                "route": route.path if route is not None else scope["path"],
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
