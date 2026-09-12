import logging

import pytest

from disha.gateway import (
    MASTER_CONTROLLER,
    OWNER,
    GatewayRequest,
    LocalGateway,
    RiskLevel,
    create_server,
    gateway_from_environment,
    gateway_diagnostics,
)


def request(actor: str, command: str, token: str = "test-token", payload=None) -> GatewayRequest:
    return GatewayRequest(actor, command, payload or {}, token)


def test_owner_can_run_registered_low_risk_command() -> None:
    gateway = LocalGateway("test-token")
    gateway.register_command("status", RiskLevel.L0, lambda payload: {"state": "ready"})

    response = gateway.handle(request(OWNER, "status"))

    assert response.status == 200
    assert response.body == {"ok": True, "result": {"state": "ready"}}


def test_wrong_token_is_rejected_and_handler_is_not_called() -> None:
    handler = lambda payload: pytest.fail("unauthenticated handler executed")
    gateway = LocalGateway("test-token")
    gateway.register_command("status", RiskLevel.L0, handler)

    response = gateway.handle(request(OWNER, "status", token="wrong"))

    assert response.status == 401
    assert response.body == {"error": "authentication required"}


def test_unknown_principal_is_rejected() -> None:
    gateway = LocalGateway("test-token")
    gateway.register_command("status", RiskLevel.L0, lambda payload: None)

    response = gateway.handle(request("stranger", "status"))

    assert response.status == 403


def test_owner_cannot_run_security_sensitive_command() -> None:
    gateway = LocalGateway("test-token")
    gateway.register_command("rotate-keys", RiskLevel.L3, lambda payload: None)

    response = gateway.handle(request(OWNER, "rotate-keys"))

    assert response.status == 403


def test_master_can_run_restricted_command() -> None:
    gateway = LocalGateway("test-token")
    gateway.register_command("rotate-keys", RiskLevel.L4, lambda payload: {"done": True})

    response = gateway.handle(request(MASTER_CONTROLLER, "rotate-keys"))

    assert response.status == 200


def test_secret_payload_is_redacted_from_security_log(caplog) -> None:
    gateway = LocalGateway("test-token")
    gateway.register_command("status", RiskLevel.L0, lambda payload: payload)

    with caplog.at_level(logging.INFO, logger="disha.gateway"):
        gateway.handle(request(OWNER, "status", payload={"api_key": "super-secret"}))

    assert "super-secret" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_gateway_rejects_public_bind_and_allows_loopback() -> None:
    gateway = LocalGateway("test-token")

    with pytest.raises(ValueError):
        create_server(gateway, host="0.0.0.0")

    server = create_server(gateway, port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_gateway_diagnostics_do_not_expose_token() -> None:
    diagnostics = gateway_diagnostics({"DISHA_GATEWAY_TOKEN": "super-secret"})

    assert diagnostics["local_only"] is True
    assert diagnostics["authentication"] == "configured"
    assert "super-secret" not in str(diagnostics)


def test_gateway_requires_explicit_environment_token() -> None:
    with pytest.raises(ValueError):
        gateway_from_environment({})

    gateway = gateway_from_environment({"DISHA_GATEWAY_TOKEN": "test-token"})
    gateway.register_command("status", RiskLevel.L0, lambda payload: "ready")
    assert gateway.handle(request(OWNER, "status")).status == 200