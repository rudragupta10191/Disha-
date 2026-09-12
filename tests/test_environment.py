from disha.environment import detect_environment


def test_detects_termux_from_termux_version() -> None:
    environment = detect_environment(
        {"TERMUX_VERSION": "0.118.0", "PREFIX": "/data/data/com.termux/files/usr"}
    )

    assert environment.is_termux is True
    assert environment.is_android is True
    assert environment.termux_version == "0.118.0"


def test_non_termux_environment_is_not_marked_termux() -> None:
    environment = detect_environment({"PREFIX": "/usr/local"})

    assert environment.is_termux is False
