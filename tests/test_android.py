from disha.android import AndroidCapabilities
from disha.environment import EnvironmentInfo


def test_non_android_reports_termux_capabilities_as_not_applicable() -> None:
    capabilities = AndroidCapabilities(
        EnvironmentInfo("Linux", "x86_64", False, False, None),
        command_lookup=lambda _command: "/unexpected/command",
    )

    report = capabilities.as_dict()

    assert report["android"] is False
    assert report["termux"] is False
    assert report["termux_api"]["available"] is False
    assert report["battery"]["status"] == "not_applicable"
    assert report["network"]["status"] == "not_applicable"
    assert report["volume"]["status"] == "not_applicable"


def test_termux_api_capabilities_use_fixed_commands_and_report_permissions() -> None:
    environment = EnvironmentInfo("Linux", "aarch64", True, True, "0.118.0")
    responses = {
        "termux-battery-status": '{"percentage": 82, "status": "CHARGING"}',
        "termux-wifi-connectioninfo": '{"ssid": "home", "link_speed_mbps": 100}',
        "termux-volume": '[{"stream": "music", "volume": 7, "max_volume": 15}]',
    }
    calls: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...]) -> str:
        calls.append(command)
        return responses[command[0].split("/")[-1]]

    capabilities = AndroidCapabilities(
        environment,
        command_runner=run,
        command_lookup=lambda command: f"/termux/bin/{command}",
    )

    report = capabilities.as_dict()

    assert report["termux_api"]["available"] is True
    assert report["battery"]["data"]["percentage"] == 82
    assert report["network"]["data"]["ssid"] == "home"
    assert report["volume"]["data"]["volumes"][0]["volume"] == 7
    assert all(len(command) == 1 for command in calls)
    assert {command[0].split("/")[-1] for command in calls} == set(responses)
    assert report["permissions"] == {
        "battery": {
            "available": True,
            "permission": "battery",
            "status": "available",
            "reason": None,
        },
        "network": {
            "available": True,
            "permission": "location",
            "status": "available",
            "reason": None,
        },
        "volume": {
            "available": True,
            "permission": "audio",
            "status": "available",
            "reason": None,
        },
    }


def test_termux_api_invalid_response_is_not_claimed_available() -> None:
    capabilities = AndroidCapabilities(
        EnvironmentInfo("Linux", "aarch64", True, True, "0.118.0"),
        command_runner=lambda _command: "not json",
        command_lookup=lambda _command: "/termux/bin/api",
    )

    result = capabilities.battery_status()

    assert result.available is False
    assert result.status == "error"
    assert result.reason == "termux-battery-status returned invalid JSON"