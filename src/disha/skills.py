"""Local registry and lifecycle controls for Disha skills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


SkillHandler = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class SkillStatus:
    skill_id: str
    enabled: bool
    description: str

    def as_dict(self) -> dict[str, object]:
        return {"skill_id": self.skill_id, "enabled": self.enabled, "description": self.description}


@dataclass(frozen=True)
class Skill:
    skill_id: str
    description: str
    handler: SkillHandler
    enabled: bool = True


class SkillRegistry:
    """Registry for explicit, locally supplied skill implementations."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if skill.skill_id in self._skills:
            raise ValueError(f"skill already registered: {skill.skill_id}")
        self._skills[skill.skill_id] = skill

    def enable(self, skill_id: str) -> None:
        self._replace(skill_id, enabled=True)

    def disable(self, skill_id: str) -> None:
        self._replace(skill_id, enabled=False)

    def execute(self, skill_id: str, payload: Mapping[str, Any]) -> Any:
        skill = self._get(skill_id)
        if not skill.enabled:
            raise PermissionError(f"skill is disabled: {skill_id}")
        return skill.handler(payload)

    def status(self) -> list[SkillStatus]:
        return [SkillStatus(skill.skill_id, skill.enabled, skill.description) for skill in self._skills.values()]

    def status_as_dict(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.status()]

    def _get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"skill is not registered: {skill_id}") from exc

    def _replace(self, skill_id: str, *, enabled: bool) -> None:
        skill = self._get(skill_id)
        self._skills[skill_id] = Skill(skill.skill_id, skill.description, skill.handler, enabled)