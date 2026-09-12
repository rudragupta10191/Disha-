"""Provider contracts and honest local/cloud provider status reporting."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol


class ProviderState(StrEnum):
    """States exposed by provider diagnostics."""

    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED = "UNVERIFIED"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class ProviderStatus:
    """Safe provider status; it never contains credentials or prompt data."""

    provider: str
    state: ProviderState
    message: str
    local: bool
    configured: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "state": self.state.value,
            "message": self.message,
            "local": self.local,
            "configured": self.configured,
        }


class AIProvider(Protocol):
    """Minimal provider interface used by the rest of Disha."""

    name: str
    local: bool

    def status(self) -> ProviderStatus:
        ...

    def generate(self, prompt: str) -> str:
        ...


RuntimeLoader = Callable[[str], Any]


def _load_needle2_model(module: Any, model_path: str) -> Any:
    loader = getattr(module, "load_model", None)
    if not callable(loader):
        raise AttributeError("runtime does not expose load_model(model_path)")
    return loader(model_path)


class CactusNeedle2Provider:
    """Adapter for a real Needle 2 runtime following the local runtime contract.

    The runtime module must expose ``load_model(path)``. The loaded model must
    expose either ``generate(prompt)`` or ``complete(prompt)``. No runtime or
    model is bundled by Disha.
    """

    name = "Cactus Needle 2"
    local = True

    def __init__(
        self,
        model_path: str | os.PathLike[str] | None,
        runtime_module: str = "cactus_needle2",
        module_importer: Callable[[str], Any] = importlib.import_module,
        model_loader: RuntimeLoader | None = None,
        file_checker: Callable[[Path], bool] | None = None,
        readable_checker: Callable[[Path], bool] | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.runtime_module = runtime_module
        self._module_importer = module_importer
        self._model_loader = model_loader
        self._file_checker = file_checker or Path.is_file
        self._readable_checker = readable_checker or (lambda path: os.access(path, os.R_OK))

    def _model(self) -> Any:
        if self.model_path is None:
            raise FileNotFoundError("no Needle 2 model path configured")
        if not self._file_checker(self.model_path):
            raise FileNotFoundError(f"model path is not a file: {self.model_path}")
        if not self._readable_checker(self.model_path):
            raise PermissionError(f"model path is not readable: {self.model_path}")
        module = self._module_importer(self.runtime_module)
        loader = self._model_loader or (lambda path: _load_needle2_model(module, path))
        return loader(str(self.model_path))

    def status(self) -> ProviderStatus:
        if self.model_path is None:
            return ProviderStatus(
                self.name,
                ProviderState.MISSING,
                "Needle 2 model path is not configured",
                self.local,
                False,
            )
        if not self._file_checker(self.model_path):
            return ProviderStatus(
                self.name,
                ProviderState.MISSING,
                "configured Needle 2 model file was not found",
                self.local,
                True,
            )
        try:
            model = self._model()
        except Exception as error:
            return ProviderStatus(
                self.name,
                ProviderState.UNAVAILABLE,
                f"Needle 2 runtime/model is unavailable: {error}",
                self.local,
                True,
            )
        if not callable(getattr(model, "generate", None)) and not callable(
            getattr(model, "complete", None)
        ):
            return ProviderStatus(
                self.name,
                ProviderState.UNVERIFIED,
                "loaded model does not expose generate(prompt) or complete(prompt)",
                self.local,
                True,
            )
        return ProviderStatus(
            self.name,
            ProviderState.AVAILABLE,
            "Needle 2 runtime and model are usable",
            self.local,
            True,
        )

    def generate(self, prompt: str) -> str:
        model = self._model()
        generator = getattr(model, "generate", None) or getattr(model, "complete", None)
        if not callable(generator):
            raise RuntimeError("Needle 2 model has no supported generation method")
        return str(generator(prompt))


class OpenAICompatibleProvider:
    """Configuration placeholder for future cloud providers.

    It deliberately performs no network calls. A configured endpoint remains
    unverified until a real adapter is implemented and explicitly enabled.
    """

    name = "OpenAI-compatible cloud"
    local = False

    def __init__(self, provider: str | None, base_url: str | None, api_key_configured: bool):
        self.provider = provider
        self.base_url = base_url
        self.api_key_configured = api_key_configured

    def status(self) -> ProviderStatus:
        if not self.provider or not self.base_url or not self.api_key_configured:
            return ProviderStatus(
                self.name,
                ProviderState.DISABLED,
                "cloud providers are disabled unless explicitly configured",
                self.local,
                False,
            )
        return ProviderStatus(
            self.name,
            ProviderState.UNVERIFIED,
            f"cloud provider {self.provider!r} is configured but no adapter is enabled",
            self.local,
            True,
        )

    def generate(self, prompt: str) -> str:
        raise RuntimeError("cloud providers are not enabled in Phase 3")


def build_providers(settings: Any) -> Mapping[str, AIProvider]:
    """Build providers without downloading models or contacting networks."""

    return {
        "cactus_needle2": CactusNeedle2Provider(
            settings.needle2_model, runtime_module=settings.needle2_runtime
        ),
        "cloud": OpenAICompatibleProvider(
            settings.cloud_provider,
            settings.cloud_base_url,
            settings.cloud_api_key_configured,
        ),
    }