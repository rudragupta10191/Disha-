import pytest

from disha.tool_maker import MakerStage, ToolBlueprint, ToolMaker, ToolRequest
from disha.tools import ToolPermission, ToolRegistry, ToolRisk, ToolSpec


def test_registry_requires_registration_and_supports_disable() -> None:
    calls: list[dict[str, object]] = []
    registry = ToolRegistry()
    registry.register(ToolSpec("read", "read local value", ToolPermission.LOCAL_READ, ToolRisk.LOW, lambda payload: calls.append(dict(payload))))

    with pytest.raises(KeyError):
        registry.execute("unknown", {})
    registry.execute("read", {"key": "x"})
    registry.disable("read")
    with pytest.raises(PermissionError):
        registry.execute("read", {})

    assert calls == [{"key": "x"}]
    assert registry.status()[0]["risk"] == "low"


def test_tool_maker_runs_pipeline_and_registers_only_tested_tools() -> None:
    registry = ToolRegistry()
    maker = ToolMaker(registry)
    request = ToolRequest("sum", "add two local values")
    blueprint = ToolBlueprint("sum", "add values", ToolPermission.LOCAL_READ, ToolRisk.LOW)

    spec = maker.build(request, blueprint, lambda payload: payload["a"] + payload["b"], test=lambda item: item.name == "sum")

    assert spec.name == "sum"
    assert maker.last_stage is MakerStage.REGISTER
    assert registry.execute("sum", {"a": 2, "b": 3}) == 5


def test_tool_maker_rejects_high_risk_and_shell_like_handlers() -> None:
    registry = ToolRegistry()
    maker = ToolMaker(registry)

    with pytest.raises(PermissionError):
        maker.build(
            ToolRequest("danger", "run command"),
            ToolBlueprint("danger", "run command", ToolPermission.LOCAL_WRITE, ToolRisk.HIGH),
            lambda payload: None,
        )

    def shell_handler(payload):
        import subprocess
        return subprocess.run(payload["command"], shell=True)

    with pytest.raises(PermissionError):
        maker.build(
            ToolRequest("shell", "run command"),
            ToolBlueprint("shell", "run command", ToolPermission.LOCAL_WRITE, ToolRisk.MEDIUM),
            shell_handler,
        )