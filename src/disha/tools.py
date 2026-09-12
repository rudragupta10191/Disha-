"""Typed, permission-gated tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping


class ToolPermission(str, Enum):
    LOCAL_READ = "local_read"
    LOCAL_WRITE = "local_write"
    DEVICE_CONTROL = "device_control"


class ToolRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ToolHandler = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: ToolPermission
    risk: ToolRisk
    handler: ToolHandler
    enabled: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "permission": self.permission.value, "risk": self.risk.value, "enabled": self.enabled}


class ToolRegistry:
    """Only registered and enabled handlers can cross the tool boundary."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._require(name)
        del self._tools[name]

    def enable(self, name: str) -> None:
        self._replace(name, enabled=True)

    def disable(self, name: str) -> None:
        self._replace(name, enabled=False)

    def execute(self, name: str, payload: Mapping[str, Any]) -> Any:
        tool = self._require(name)
        if not tool.enabled:
            raise PermissionError(f"tool is disabled: {name}")
        if not isinstance(payload, Mapping):
            raise TypeError("tool payload must be an object")
        return tool.handler(payload)

    def get(self, name: str) -> ToolSpec:
        return self._require(name)

    def status(self) -> list[dict[str, object]]:
        return [tool.as_dict() for tool in self._tools.values()]

    def _require(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"tool is not registered: {name}") from exc

    def _replace(self, name: str, *, enabled: bool) -> None:
        tool = self._require(name)
        self._tools[name] = ToolSpec(tool.name, tool.description, tool.permission, tool.risk, tool.handler, enabled)