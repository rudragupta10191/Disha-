from disha.config import load_settings


def test_load_settings_uses_environment_values() -> None:
    settings = load_settings(
        {
            "DISHA_NAME": " Local Disha ",
            "DISHA_OWNER": "Owner",
            "DISHA_LOG_LEVEL": "debug",
        }
    )

    assert settings.name == "Local Disha"
    assert settings.owner == "Owner"
    assert settings.log_level == "DEBUG"
    assert settings.master == "Neo/Hermes"


def test_load_settings_does_not_require_secrets() -> None:
    assert load_settings({}).primary_ai == "Cactus Needle 2"
