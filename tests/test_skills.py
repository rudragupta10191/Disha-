import pytest

from disha.skills import Skill, SkillRegistry


def test_skills_execute_only_when_registered_and_enabled() -> None:
    calls: list[dict[str, object]] = []
    registry = SkillRegistry()
    registry.register(Skill("weather", "read local weather", lambda payload: calls.append(dict(payload))))

    registry.execute("weather", {"city": "local"})
    registry.disable("weather")
    with pytest.raises(PermissionError):
        registry.execute("weather", {})
    with pytest.raises(KeyError):
        registry.execute("missing", {})

    assert calls == [{"city": "local"}]
    assert registry.status_as_dict()[0]["enabled"] is False
