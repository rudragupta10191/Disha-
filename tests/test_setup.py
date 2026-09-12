import json

from disha.config import load_settings
from disha.setup import SetupProfile, load_profile, run_setup, save_profile


def test_quick_setup_saves_defaults(tmp_path) -> None:
    answers = iter(["1", ""])
    profile = run_setup(
        load_settings({"DISHA_OWNER": "Rudra"}),
        input_fn=lambda _: next(answers),
        output_fn=lambda _: None,
        path=tmp_path / "setup.json",
    )

    assert profile == SetupProfile(owner="Rudra")
    assert load_profile(tmp_path / "setup.json") == profile


def test_full_setup_supports_explicit_choices(tmp_path) -> None:
    answers = iter(["2", "Alex", "1", "1", "1", "2"])
    profile = run_setup(
        load_settings({}),
        input_fn=lambda _: next(answers),
        output_fn=lambda _: None,
        path=tmp_path / "setup.json",
    )

    assert profile == SetupProfile(
        owner="Alex",
        primary_ai="Cactus Needle 2",
        messenger="none",
        storage="local",
        skills_enabled=False,
    )


def test_setup_file_is_private_and_rerun_can_be_skipped(tmp_path) -> None:
    path = tmp_path / "nested" / "setup.json"
    save_profile(SetupProfile(owner="Rudra"), path)
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text())["profile"]["primary_ai"] == "Cactus Needle 2"

    result = run_setup(
        load_settings({}),
        input_fn=lambda _: "n",
        output_fn=lambda _: None,
        path=path,
    )
    assert result == SetupProfile(owner="Rudra")
