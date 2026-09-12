"""Safe diagnostic data for local troubleshooting."""

from __future__ import annotations

from dataclasses import asdict
import os

from .ai import build_providers
from .android import AndroidCapabilities
from .config import Settings
from .environment import EnvironmentInfo
from .gateway import gateway_diagnostics
from .iot import default_registry
from .automation import AutomationRegistry
from .skills import SkillRegistry
from .tools import ToolRegistry


def diagnostics(settings: Settings, environment: EnvironmentInfo) -> dict[str, object]:
    """Return non-secret identity and environment information."""

    return {
        "identity": {
            "name": settings.name,
            "owner": settings.owner,
            "master": settings.master,
            "primary_ai": settings.primary_ai,
        },
        "environment": asdict(environment),
        "phase": "7-skills-tools-automation",
        "ai": {
            name: provider.status().as_dict()
            for name, provider in build_providers(settings).items()
        },
        "gateway": gateway_diagnostics(os.environ),
        "android": AndroidCapabilities(environment).as_dict(),
        "iot": {"devices": default_registry().status_as_dict()},
        "skills": {"status": SkillRegistry().status_as_dict()},
        "tools": {"status": ToolRegistry().status()},
        "automations": {"status": AutomationRegistry().status_as_dict()},
        "integrations": {
            "hardware": False,
            "telegram": False,
            "cloud": False,
        },
    }
