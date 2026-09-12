"""Runtime environment detection for Termux and Android."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EnvironmentInfo:
    """Detected runtime facts used by diagnostics."""

    system: str
    machine: str
    is_android: bool
    is_termux: bool
    termux_version: str | None


def detect_environment(environ: Mapping[str, str] | None = None) -> EnvironmentInfo:
    """Detect Android and Termux from platform data and conventional variables."""

    values = os.environ if environ is None else environ
    system = platform.system()
    machine = platform.machine()
    prefix = values.get("PREFIX", "")
    termux_version = values.get("TERMUX_VERSION")
    is_termux = bool(termux_version or "com.termux" in prefix.lower())
    is_android = is_termux or system.lower() == "android"
    return EnvironmentInfo(
        system=system,
        machine=machine,
        is_android=is_android,
        is_termux=is_termux,
        termux_version=termux_version,
    )
