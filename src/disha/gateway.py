"""Private localhost gateway and command authorization boundary."""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping


LOGGER = logging.getLogger(__name__)
MASTER_CONTROLLER = "Neo/Hermes"
OWNER = "Rudra"
DEFAULT_HOST = "127.0.0.1"
MAX_BODY_BYTES = 64 * 1024
COMMAND_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
SECRET_KEYS = {"token", "password", "secret", "api_key", "authorization"}


class RiskLevel(IntEnum):
    """Increasing command sensitivity from read-only to restricted."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


@dataclass(frozen=True)
class GatewayRequest:
    """Validated request data passed to the gateway policy."""

    actor: str
    command: str
    payload: Mapping[str, Any]
    token: str


@dataclass(frozen=True)
class GatewayResponse:
    """Stable response returned by both direct and HTTP gateway callers."""

    status: int
    body: Mapping[str, Any]


@dataclass(frozen=True)
class CommandSpec:
    risk: RiskLevel
    handler: Callable[[Mapping[str, Any]], Any]


def _redacted(value: Any) -> Any:
    """Return log-safe data without exposing common credential fields."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SECRET_KEYS else _redacted(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redacted(item) for item in value]
    if isinstance(value, str):
        return value[:160]
    return value


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class LocalGateway:
    """Local-first command gateway with authentication and risk authorization."""

    def __init__(
        self,
        auth_token: str,
        host: str = DEFAULT_HOST,
        logger: logging.Logger | None = None,
    ) -> None:
        if not auth_token:
            raise ValueError("a gateway authentication token is required")
        if not _is_loopback(host):
            raise ValueError("gateway host must be localhost or a loopback address")
        self.host = host
        self._auth_token = auth_token
        self._commands: dict[str, CommandSpec] = {}
        self._logger = logger or LOGGER

    def register_command(
        self,
        name: str,
        risk: RiskLevel,
        handler: Callable[[Mapping[str, Any]], Any],
    ) -> None:
        """Register an explicit command; arbitrary shell commands are unsupported."""

        if not COMMAND_PATTERN.fullmatch(name):
            raise ValueError("command names must be lowercase identifier-like values")
        if not isinstance(risk, RiskLevel):
            raise TypeError("risk must be a RiskLevel")
        if not callable(handler):
            raise TypeError("command handler must be callable")
        self._commands[name] = CommandSpec(risk, handler)

    def handle(self, request: GatewayRequest) -> GatewayResponse:
        """Authenticate, validate, authorize, and dispatch one request."""

        if not isinstance(request.token, str):
            return self._reject(HTTPStatus.UNAUTHORIZED, "authentication required", request)
        if not hmac.compare_digest(request.token, self._auth_token):
            return self._reject(HTTPStatus.UNAUTHORIZED, "authentication required", request)
        if not isinstance(request.actor, str) or request.actor not in {MASTER_CONTROLLER, OWNER}:
            return self._reject(HTTPStatus.FORBIDDEN, "unknown principal", request)
        if not isinstance(request.command, str) or not COMMAND_PATTERN.fullmatch(request.command):
            return self._reject(HTTPStatus.BAD_REQUEST, "invalid command", request)
        if not isinstance(request.payload, Mapping):
            return self._reject(HTTPStatus.BAD_REQUEST, "payload must be an object", request)

        spec = self._commands.get(request.command)
        if spec is None:
            return self._reject(HTTPStatus.NOT_FOUND, "command is not registered", request)
        if request.actor == OWNER and spec.risk > RiskLevel.L2:
            return self._reject(HTTPStatus.FORBIDDEN, "principal is not authorized for risk level", request)

        self._audit(request, spec.risk, "authorized")
        try:
            result = spec.handler(request.payload)
        except Exception:
            self._logger.exception(
                "gateway_request actor=%s command=%s risk=%s outcome=handler_error",
                request.actor,
                request.command,
                spec.risk.name,
            )
            return GatewayResponse(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "command failed"})
        return GatewayResponse(HTTPStatus.OK, {"ok": True, "result": _redacted(result)})

    def _reject(self, status: HTTPStatus, reason: str, request: GatewayRequest) -> GatewayResponse:
        self._logger.warning(
            "gateway_request actor=%s command=%s outcome=rejected reason=%s",
            _redacted(request.actor),
            _redacted(request.command),
            reason,
        )
        return GatewayResponse(status, {"error": reason})

    def _audit(self, request: GatewayRequest, risk: RiskLevel, outcome: str) -> None:
        self._logger.info(
            "gateway_request actor=%s command=%s risk=%s outcome=%s payload=%s",
            _redacted(request.actor),
            _redacted(request.command),
            risk.name,
            outcome,
            json.dumps(_redacted(request.payload), sort_keys=True, default=str),
        )


def gateway_from_environment(environ: Mapping[str, str]) -> LocalGateway:
    """Build the private gateway from an explicitly supplied environment token."""

    token = environ.get("DISHA_GATEWAY_TOKEN", "")
    if not token:
        raise ValueError("DISHA_GATEWAY_TOKEN must be explicitly configured")
    return LocalGateway(token)


def create_server(gateway: LocalGateway, host: str = DEFAULT_HOST, port: int = 0) -> ThreadingHTTPServer:
    """Create a localhost-only HTTP server; no public bind is permitted."""

    if not _is_loopback(host):
        raise ValueError("gateway server must bind to localhost or a loopback address")

    class GatewayHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    class GatewayHandler(BaseHTTPRequestHandler):
        server_version = "DishaGateway/1"

        def do_POST(self) -> None:
            if self.path != "/v1/command":
                self._write(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                self._write(HTTPStatus.BAD_REQUEST, {"error": "invalid content length"})
                return
            if content_length < 0 or content_length > MAX_BODY_BYTES:
                self._write(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"})
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
                if not isinstance(payload, Mapping):
                    raise ValueError("request body must be an object")
                authorization = self.headers.get("Authorization", "")
                scheme, _, token = authorization.partition(" ")
                if scheme.lower() != "bearer" or not token:
                    raise PermissionError("authentication required")
                request = GatewayRequest(
                    actor=payload.get("actor", ""),
                    command=payload.get("command", ""),
                    payload=payload.get("payload", {}),
                    token=token,
                )
            except (json.JSONDecodeError, TypeError, ValueError):
                self._write(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON request"})
                return
            except PermissionError:
                self._write(HTTPStatus.UNAUTHORIZED, {"error": "authentication required"})
                return
            response = gateway.handle(request)
            self._write(response.status, response.body)

        def _write(self, status: int | HTTPStatus, body: Mapping[str, Any]) -> None:
            encoded = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: Any) -> None:
            LOGGER.info("gateway_http " + format, *args)

    return GatewayHTTPServer((host, port), GatewayHandler)


def gateway_diagnostics(environ: Mapping[str, str]) -> dict[str, object]:
    """Return safe gateway status without returning the configured token."""

    token = environ.get("DISHA_GATEWAY_TOKEN", "")
    return {
        "local_only": True,
        "host": DEFAULT_HOST,
        "authentication": "configured" if token else "missing",
        "master_controller": MASTER_CONTROLLER,
        "owner": OWNER,
        "risk_levels": {level.name: level.value for level in RiskLevel},
    }