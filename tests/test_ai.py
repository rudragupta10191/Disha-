from types import SimpleNamespace
from unittest.mock import Mock

from disha.ai import CactusNeedle2Provider, OpenAICompatibleProvider, ProviderState


def test_needle2_without_model_is_missing() -> None:
    provider = CactusNeedle2Provider(None)

    status = provider.status()

    assert status.state is ProviderState.MISSING
    assert status.configured is False


def test_needle2_uses_mock_runtime_and_model_without_a_model_file() -> None:
    model = SimpleNamespace(generate=Mock(return_value="local response"))
    provider = CactusNeedle2Provider(
        "/mock/needle2.bin",
        runtime_module="mock_needle2",
        module_importer=Mock(return_value=object()),
        model_loader=Mock(return_value=model),
        file_checker=Mock(return_value=True),
        readable_checker=Mock(return_value=True),
    )

    assert provider.status().state is ProviderState.AVAILABLE
    assert provider.generate("hello") == "local response"
    model.generate.assert_called_once_with("hello")


def test_needle2_runtime_failure_is_unavailable() -> None:
    provider = CactusNeedle2Provider(
        "/mock/needle2.bin",
        module_importer=Mock(side_effect=ImportError("runtime missing")),
        file_checker=Mock(return_value=True),
        readable_checker=Mock(return_value=True),
    )

    assert provider.status().state is ProviderState.UNAVAILABLE


def test_cloud_provider_is_disabled_by_default() -> None:
    status = OpenAICompatibleProvider(None, None, False).status()

    assert status.state is ProviderState.DISABLED
    assert status.configured is False


def test_cloud_provider_configuration_is_unverified_without_network_call() -> None:
    status = OpenAICompatibleProvider("example", "https://example.invalid", True).status()

    assert status.state is ProviderState.UNVERIFIED
    assert status.configured is True