"""Interactive, offline first-run setup for Disha."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .config import Settings

Input = Callable[[str], str]
Output = Callable[[str], None]


@dataclass(frozen=True)
class SetupProfile:
    """User-selected setup preferences; no credentials are stored."""

    owner: str
    primary_ai: str = "Cactus Needle 2"
    messenger: str = "none"
    storage: str = "local"
    skills_enabled: bool = True


def config_path(environ: dict[str, str] | None = None) -> Path:
    """Return the platform-appropriate private Disha config path."""

    values = os.environ if environ is None else environ
    config_home = values.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "disha" / "setup.json"
    return Path.home() / ".config" / "disha" / "setup.json"


def save_profile(profile: SetupProfile, path: Path | None = None) -> Path:
    """Atomically save a setup profile with owner-only permissions."""

    destination = path or config_path()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.parent.chmod(0o700)
    payload = {"version": 1, "profile": asdict(profile)}
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix="setup-", suffix=".tmp", dir=destination.parent
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(payload, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
        os.replace(temporary_name, destination)
    except Exception:
        os.unlink(temporary_name)
        raise
    return destination


def load_profile(path: Path | None = None) -> SetupProfile | None:
    """Load a valid local setup profile, or return ``None`` if absent."""

    destination = path or config_path()
    if not destination.is_file():
        return None
    with destination.open(encoding="utf-8") as setup_file:
        data = json.load(setup_file)
    profile = data["profile"]
    return SetupProfile(
        owner=str(profile["owner"]),
        primary_ai=str(profile["primary_ai"]),
        messenger=str(profile["messenger"]),
        storage=str(profile["storage"]),
        skills_enabled=bool(profile["skills_enabled"]),
    )


def _ask_choice(
    prompt: str, choices: list[tuple[str, str]], input_fn: Input, output_fn: Output
) -> str:
    output_fn(prompt)
    for number, (label, _) in enumerate(choices, start=1):
        output_fn(f"  {number}. {label}")
    while True:
        answer = input_fn("Choice: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1][1]
        output_fn("Please choose one of the listed numbers.")


def run_setup(
    settings: Settings,
    input_fn: Input = input,
    output_fn: Output = print,
    path: Path | None = None,
) -> SetupProfile | None:
    """Run setup interactively and save the selected profile."""

    destination = path or config_path()
    existing = load_profile(destination)
    if existing is not None:
        output_fn(f"A setup profile already exists at {destination}.")
        if input_fn("Overwrite it? [y/N]: ").strip().lower() not in {"y", "yes"}:
            output_fn("Setup unchanged.")
            return existing

    mode = _ask_choice(
        "Choose setup mode:",
        [("Quick Setup", "quick"), ("Full Setup", "full"), ("Manual Setup", "manual")],
        input_fn,
        output_fn,
    )
    owner = input_fn(f"Owner name [{settings.owner}]: ").strip() or settings.owner
    profile = SetupProfile(owner=owner)

    if mode == "quick":
        output_fn("Quick Setup uses local storage, no messenger, and enables skills.")
    else:
        primary_ai = _ask_choice(
            "Primary AI provider:",
            [("Cactus Needle 2 (not installed)", "Cactus Needle 2"), ("None yet", "none")],
            input_fn,
            output_fn,
        )
        messenger = _ask_choice(
            "Messenger/Gateway:",
            [("None (offline)", "none"), ("Console only", "console"), ("Telegram (not connected)", "telegram")],
            input_fn,
            output_fn,
        )
        storage = _ask_choice(
            "Storage/cloud:",
            [("Local only", "local"), ("Cloud (not connected)", "cloud")],
            input_fn,
            output_fn,
        )
        skills = _ask_choice(
            "Skills:", [("Enable", "enabled"), ("Disable", "disabled")], input_fn, output_fn
        )
        profile = SetupProfile(
            owner=owner,
            primary_ai=primary_ai,
            messenger=messenger,
            storage=storage,
            skills_enabled=skills == "enabled",
        )

    save_profile(profile, destination)
    output_fn(f"Setup saved to {destination}.")
    return profile
