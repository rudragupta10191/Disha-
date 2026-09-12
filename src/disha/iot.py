"""Protocol-neutral, local Home IoT adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Callable, Mapping, Protocol


class DeviceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class DeviceStatusReport:
    device_id: str
    kind: str
    status: DeviceStatus
    reason: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "device_id": self.device_id,
            "kind": self.kind,
            "status": self.status.value,
            "reason": self.reason,
        }


class DeviceCommandError(RuntimeError):
    """Base error for the intentionally narrow device command boundary."""


class AuthorizationRequiredError(DeviceCommandError):
    """Raised when a device-changing command lacks authorization."""


class UnsupportedDeviceCommand(DeviceCommandError):
    """Raised when no explicitly configured adapter supports a command."""


class DeviceAuthorizer(Protocol):
    def authorize(self, actor: str, device_id: str, command: str) -> bool:
        ...


StatusProbe = Callable[[], DeviceStatus | DeviceStatusReport]
CommandHandler = Callable[[Mapping[str, Any]], Any]
COMMAND_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class DeviceAdapter(Protocol):
    device_id: str
    kind: str

    def status(self) -> DeviceStatusReport:
        ...

    def execute_command(
        self, command: str, payload: Mapping[str, Any], *, authorized: bool = False
    ) -> Any:
        ...

    def is_mutating(self, command: str) -> bool:
        ...


class ProtocolAdapter:
    """Adapter shell requiring explicit, injected protocol implementations."""

    def __init__(
        self,
        device_id: str,
        kind: str,
        *,
        status_probe: StatusProbe | None = None,
        commands: Mapping[str, CommandHandler] | None = None,
        mutating_commands: frozenset[str] = frozenset(),
    ) -> None:
        self.device_id = device_id
        self.kind = kind
        self._status_probe = status_probe
        self._commands = dict(commands or {})
        self._mutating_commands = mutating_commands
        if not all(COMMAND_PATTERN.fullmatch(command) for command in self._commands):
            raise ValueError("device commands must be lowercase identifier-like values")
        if not self._mutating_commands <= self._commands.keys():
            raise ValueError("mutating commands must be registered command handlers")

    def status(self) -> DeviceStatusReport:
        if self._status_probe is None:
            return DeviceStatusReport(
                self.device_id,
                self.kind,
                DeviceStatus.UNVERIFIED,
                "no protocol adapter configured",
            )
        try:
            result = self._status_probe()
        except Exception:
            return DeviceStatusReport(
                self.device_id,
                self.kind,
                DeviceStatus.UNAVAILABLE,
                "status probe failed",
            )
        if isinstance(result, DeviceStatusReport):
            return result
        return DeviceStatusReport(self.device_id, self.kind, result)

    def is_mutating(self, command: str) -> bool:
        return command in self._mutating_commands

    def execute_command(
        self, command: str, payload: Mapping[str, Any], *, authorized: bool = False
    ) -> Any:
        if not isinstance(payload, Mapping):
            raise TypeError("device command payload must be an object")
        handler = self._commands.get(command)
        if handler is None:
            raise UnsupportedDeviceCommand(f"{command} is not supported by {self.device_id}")
        if self.is_mutating(command) and not authorized:
            raise AuthorizationRequiredError("authorization required for device-changing command")
        return handler(payload)


class HaierACAdapter(ProtocolAdapter):
    """Haier AC adapter shell; no Haier protocol is assumed or implemented."""

    def __init__(self, *, status_probe: StatusProbe | None = None) -> None:
        super().__init__("haier-ac", "haier_ac", status_probe=status_probe)


class A9CameraAdapter(ProtocolAdapter):
    """A9 camera adapter shell limited to explicitly supplied capabilities."""

    def __init__(
        self,
        *,
        status_probe: StatusProbe | None = None,
        snapshot: CommandHandler | None = None,
        stream: CommandHandler | None = None,
    ) -> None:
        commands = {
            command: handler
            for command, handler in (("snapshot", snapshot), ("stream", stream))
            if handler is not None
        }
        super().__init__("a9-camera", "a9_camera", status_probe=status_probe, commands=commands)


class DeviceRegistry:
    """Registry for known adapters; it performs no network discovery."""

    def __init__(self, authorizer: DeviceAuthorizer | None = None) -> None:
        self._devices: dict[str, DeviceAdapter] = {}
        self._authorizer = authorizer

    def register(self, adapter: DeviceAdapter) -> None:
        if adapter.device_id in self._devices:
            raise ValueError(f"device already registered: {adapter.device_id}")
        self._devices[adapter.device_id] = adapter

    def status(self) -> list[DeviceStatusReport]:
        return [adapter.status() for adapter in self._devices.values()]

    def status_as_dict(self) -> list[dict[str, str | None]]:
        return [report.as_dict() for report in self.status()]

    def execute(
        self,
        device_id: str,
        command: str,
        payload: Mapping[str, Any],
        *,
        actor: str,
    ) -> Any:
        adapter = self._devices.get(device_id)
        if adapter is None:
            raise KeyError(f"device is not registered: {device_id}")
        if adapter.is_mutating(command):
            if self._authorizer is None or not self._authorizer.authorize(actor, device_id, command):
                raise AuthorizationRequiredError("authorization required for device-changing command")
        return adapter.execute_command(command, payload, authorized=adapter.is_mutating(command))


def default_registry() -> DeviceRegistry:
    """Return Phase 6 devices without probing or connecting to a network."""

    registry = DeviceRegistry()
    registry.register(HaierACAdapter())
    registry.register(A9CameraAdapter())
    return registry