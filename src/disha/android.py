"""Safe, optional Android and Termux capability access."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import platform
import shutil
import subprocess
from typing import Any, Callable, Mapping, Sequence

from .environment import EnvironmentInfo, detect_environment


@dataclass(frozen=True)
class CapabilityResult:
    """A truthful result for one optional device capability."""

    available: bool
    status: str
    data: Mapping[str, Any] | None = None
    reason: str | None = None
    permission: str = "not_required"

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "status": self.status,
            "data": dict(self.data) if self.data is not None else None,
            "reason": self.reason,
            "permission": self.permission,
        }


CommandRunner = Callable[[Sequence[str]], str]


def _memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        return None
    return pages * page_size if pages > 0 and page_size > 0 else None


def _storage_bytes(path: str = "/") -> dict[str, int] | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def _default_runner(command: Sequence[str]) -> str:
    completed = subprocess.run(
        list(command),
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
        shell=False,
    )
    return completed.stdout


class AndroidCapabilities:
    """Read-only Android capabilities with no root or arbitrary shell access."""

    _COMMANDS = {
        "battery": ("termux-battery-status", "battery"),
        "network": ("termux-wifi-connectioninfo", "location"),
        "volume": ("termux-volume", "audio"),
    }

    def __init__(
        self,
        environment: EnvironmentInfo | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        command_runner: CommandRunner | None = None,
        command_lookup: Callable[[str], str | None] | None = None,
    ) -> None:
        self.environment = environment or detect_environment(environ)
        self._run = command_runner or _default_runner
        self._which = command_lookup or shutil.which
        self._commands = {
            name: self._which(command)
            for name, (command, _permission) in self._COMMANDS.items()
        }

    @property
    def termux_api_available(self) -> bool:
        return self.environment.is_termux and any(self._commands.values())

    def permission_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "available": bool(self._commands[name]) and self.environment.is_termux,
                "permission": permission,
                "status": (
                    "available"
                    if bool(self._commands[name]) and self.environment.is_termux
                    else "unavailable"
                ),
                "reason": None
                if self.environment.is_termux and self._commands[name]
                else "Termux:API command is unavailable",
            }
            for name, (_command, permission) in self._COMMANDS.items()
        }

    def device_information(self) -> CapabilityResult:
        storage = _storage_bytes()
        data = {
            "system": self.environment.system,
            "machine": self.environment.machine or platform.machine(),
            "is_android": self.environment.is_android,
            "is_termux": self.environment.is_termux,
            "termux_version": self.environment.termux_version,
            "memory_bytes": _memory_bytes(),
            "storage_bytes": storage,
        }
        return CapabilityResult(True, "available", data=data)

    def _termux_json(self, capability: str) -> CapabilityResult:
        command, permission = self._COMMANDS[capability]
        executable = self._commands[capability]
        if not self.environment.is_termux:
            return CapabilityResult(
                False,
                "not_applicable",
                reason="Termux is not detected",
                permission=permission,
            )
        if executable is None:
            return CapabilityResult(
                False,
                "unavailable",
                reason=f"{command} is not installed; Termux:API may be missing",
                permission=permission,
            )
        try:
            output = self._run((executable,))
            value = json.loads(output)
        except (OSError, subprocess.SubprocessError) as error:
            return CapabilityResult(
                False, "error", reason=f"{command} failed: {error}", permission=permission
            )
        except json.JSONDecodeError:
            return CapabilityResult(
                False, "error", reason=f"{command} returned invalid JSON", permission=permission
            )
        if isinstance(value, list) and capability == "volume":
            value = {"volumes": value}
        if not isinstance(value, dict):
            return CapabilityResult(
                False, "error", reason=f"{command} returned an unexpected response", permission=permission
            )
        return CapabilityResult(True, "available", data=value, permission=permission)

    def battery_status(self) -> CapabilityResult:
        return self._termux_json("battery")

    def network_status(self) -> CapabilityResult:
        return self._termux_json("network")

    def volume_status(self) -> CapabilityResult:
        return self._termux_json("volume")

    def as_dict(self) -> dict[str, Any]:
        return {
            "android": self.environment.is_android,
            "termux": self.environment.is_termux,
            "termux_api": {
                "available": self.termux_api_available,
                "status": "available" if self.termux_api_available else "unavailable",
                "reason": None
                if self.termux_api_available
                else "Termux:API commands are unavailable",
            },
            "permissions": self.permission_status(),
            "device": self.device_information().as_dict(),
            "battery": self.battery_status().as_dict(),
            "network": self.network_status().as_dict(),
            "volume": self.volume_status().as_dict(),
        }