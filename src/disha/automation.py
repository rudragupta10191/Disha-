"""Event-driven automation without polling loops."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping


class TriggerType(str, Enum):
    TIME = "time"
    DEVICE = "device"
    MOTION = "motion"
    TEMPERATURE = "temperature"
    NETWORK = "network"
    BATTERY = "battery"


@dataclass(frozen=True)
class Event:
    trigger: TriggerType
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class AutomationStatus:
    automation_id: str
    trigger: TriggerType
    enabled: bool

    def as_dict(self) -> dict[str, object]:
        return {"automation_id": self.automation_id, "trigger": self.trigger.value, "enabled": self.enabled}


@dataclass(frozen=True)
class Automation:
    automation_id: str
    trigger: TriggerType
    action: Callable[[Event], Any]
    condition: Callable[[Event], bool] = lambda event: True
    enabled: bool = True


class AutomationRegistry:
    """Subscriptions are invoked only when a matching event is published."""

    def __init__(self) -> None:
        self._automations: dict[str, Automation] = {}

    def register(self, automation: Automation) -> None:
        if automation.automation_id in self._automations:
            raise ValueError(f"automation already registered: {automation.automation_id}")
        self._automations[automation.automation_id] = automation

    def enable(self, automation_id: str) -> None:
        self._replace(automation_id, enabled=True)

    def disable(self, automation_id: str) -> None:
        self._replace(automation_id, enabled=False)

    def publish(self, event: Event) -> list[Any]:
        results: list[Any] = []
        for automation in self._automations.values():
            if automation.enabled and automation.trigger is event.trigger and automation.condition(event):
                results.append(automation.action(event))
        return results

    def status(self) -> list[AutomationStatus]:
        return [AutomationStatus(item.automation_id, item.trigger, item.enabled) for item in self._automations.values()]

    def status_as_dict(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.status()]

    def _replace(self, automation_id: str, *, enabled: bool) -> None:
        try:
            item = self._automations[automation_id]
        except KeyError as exc:
            raise KeyError(f"automation is not registered: {automation_id}") from exc
        self._automations[automation_id] = Automation(item.automation_id, item.trigger, item.action, item.condition, enabled)