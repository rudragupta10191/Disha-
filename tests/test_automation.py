from disha.automation import Automation, AutomationRegistry, Event, TriggerType


def test_event_driven_automation_supports_future_trigger_types_without_polling() -> None:
    seen: list[TriggerType] = []
    registry = AutomationRegistry()
    for trigger in TriggerType:
        registry.register(Automation(trigger.value, trigger, lambda event: seen.append(event.trigger)))

    for trigger in TriggerType:
        assert registry.publish(Event(trigger, {"value": 1})) == [None]

    assert seen == list(TriggerType)
    assert len(registry.status()) == len(TriggerType)


def test_automation_disable_and_condition_gate_actions() -> None:
    calls: list[str] = []
    registry = AutomationRegistry()
    registry.register(
        Automation(
            "hot-room",
            TriggerType.TEMPERATURE,
            lambda event: calls.append("ran"),
            condition=lambda event: event.payload.get("celsius") > 25,
        )
    )

    assert registry.publish(Event(TriggerType.TEMPERATURE, {"celsius": 20})) == []
    registry.disable("hot-room")
    assert registry.publish(Event(TriggerType.TEMPERATURE, {"celsius": 30})) == []
    registry.enable("hot-room")
    assert registry.publish(Event(TriggerType.TEMPERATURE, {"celsius": 30})) == [None]
    assert calls == ["ran"]