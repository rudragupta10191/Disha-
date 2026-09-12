from collections.abc import Mapping

import pytest

from disha.iot import (
    A9CameraAdapter,
    AuthorizationRequiredError,
    DeviceRegistry,
    DeviceStatus,
    DeviceStatusReport,
    HaierACAdapter,
    ProtocolAdapter,
    UnsupportedDeviceCommand,
    default_registry,
)


class MockAuthorizer:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[str, str, str]] = []

    def authorize(self, actor: str, device_id: str, command: str) -> bool:
        self.calls.append((actor, device_id, command))
        return self.allowed


def test_default_devices_are_unverified_without_protocol_access() -> None:
    reports = default_registry().status()

    assert [(report.kind, report.status) for report in reports] == [
        ("haier_ac", DeviceStatus.UNVERIFIED),
        ("a9_camera", DeviceStatus.UNVERIFIED),
    ]


def test_registry_registers_devices_and_reports_mock_status() -> None:
    registry = DeviceRegistry()
    registry.register(HaierACAdapter(status_probe=lambda: DeviceStatus.AVAILABLE))
    registry.register(
        A9CameraAdapter(
            status_probe=lambda: DeviceStatusReport(
                "a9-camera", "a9_camera", DeviceStatus.UNAVAILABLE, "camera is offline"
            )
        )
    )

    assert registry.status_as_dict() == [
        {"device_id": "haier-ac", "kind": "haier_ac", "status": "AVAILABLE", "reason": None},
        {"device_id": "a9-camera", "kind": "a9_camera", "status": "UNAVAILABLE", "reason": "camera is offline"},
    ]


def test_status_probe_failure_is_unavailable() -> None:
    def failing_probe() -> DeviceStatus:
        raise RuntimeError("mock failure")

    report = HaierACAdapter(status_probe=failing_probe).status()

    assert report.status is DeviceStatus.UNAVAILABLE
    assert report.reason == "status probe failed"


def test_unconfigured_camera_capabilities_are_not_claimed_supported() -> None:
    with pytest.raises(UnsupportedDeviceCommand):
        A9CameraAdapter().execute_command("snapshot", {})


def test_mutating_commands_require_authorization_before_handler() -> None:
    calls: list[Mapping[str, object]] = []
    authorizer = MockAuthorizer(allowed=False)
    adapter = ProtocolAdapter(
        "mock-ac", "haier_ac", commands={"power": lambda payload: calls.append(payload)}, mutating_commands=frozenset({"power"})
    )
    registry = DeviceRegistry(authorizer)
    registry.register(adapter)

    with pytest.raises(AuthorizationRequiredError):
        registry.execute("mock-ac", "power", {"on": True}, actor="Rudra")

    assert calls == []
    assert authorizer.calls == [("Rudra", "mock-ac", "power")]