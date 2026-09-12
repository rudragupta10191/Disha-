import json

from disha.cli import main


def test_diagnostics_command_emits_safe_json(capsys) -> None:
    assert main(["--diagnostics"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["phase"] == "7-skills-tools-automation"
    assert output["integrations"] == {
        "cloud": False,
        "hardware": False,
        "telegram": False,
    }
    assert [device["status"] for device in output["iot"]["devices"]] == [
        "UNVERIFIED",
        "UNVERIFIED",
    ]
