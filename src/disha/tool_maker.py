"""Constrained pipeline for proposing and registering local tools."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .tools import ToolHandler, ToolPermission, ToolRegistry, ToolRisk, ToolSpec


class MakerStage(str, Enum):
    REQUEST = "request"
    SPECIFY = "specify"
    SECURITY_CHECK = "security_check"
    GENERATE = "generate"
    TEST = "test"
    REGISTER = "register"


@dataclass(frozen=True)
class ToolRequest:
    name: str
    purpose: str


@dataclass(frozen=True)
class ToolBlueprint:
    name: str
    description: str
    permission: ToolPermission
    risk: ToolRisk


class ToolMaker:
    """Builds tools from injected handlers, never from arbitrary source or shell."""

    _FORBIDDEN_MARKERS = ("subprocess", "os.system", "os.popen", "socket", "urllib", "requests", "http.client")

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.last_stage: MakerStage | None = None

    def build(self, request: ToolRequest, blueprint: ToolBlueprint, handler: ToolHandler, *, test: Callable[[ToolSpec], bool] | None = None) -> ToolSpec:
        self.last_stage = MakerStage.REQUEST
        if request.name != blueprint.name or not request.name:
            raise ValueError("request and blueprint must identify the same tool")
        self.last_stage = MakerStage.SPECIFY
        spec = ToolSpec(blueprint.name, blueprint.description, blueprint.permission, blueprint.risk, handler)
        self.last_stage = MakerStage.SECURITY_CHECK
        self._security_check(spec)
        self.last_stage = MakerStage.GENERATE
        self.last_stage = MakerStage.TEST
        if test is not None and not test(spec):
            raise ValueError("generated tool test failed")
        self.last_stage = MakerStage.REGISTER
        self.registry.register(spec)
        return spec

    def _security_check(self, spec: ToolSpec) -> None:
        if spec.risk is ToolRisk.HIGH:
            raise PermissionError("high-risk tools require a reviewed implementation")
        try:
            source = inspect.getsource(spec.handler).lower()
        except (OSError, TypeError):
            source = ""
        if any(marker in source for marker in self._FORBIDDEN_MARKERS):
            raise PermissionError("tool requests forbidden shell or network capability")