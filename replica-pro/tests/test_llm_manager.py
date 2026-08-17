from __future__ import annotations

import pytest

from rmao.config.models import LLMConfig
from rmao.domain.errors import ConfigError
from rmao.llm.factory import LLMFactory
from rmao.llm.fake_adapter import FakeLLMAdapter


def test_factory_selects_fake_provider() -> None:
    provider = LLMFactory.create(LLMConfig(provider="fake"))
    assert isinstance(provider, FakeLLMAdapter)
    assert provider.provider_name == "fake"


def test_factory_rejects_missing_real_provider_secret() -> None:
    with pytest.raises(ConfigError, match="requires an API key"):
        LLMFactory.create(LLMConfig(provider="openai"))


@pytest.mark.asyncio
async def test_fake_provider_returns_structured_output() -> None:
    provider = FakeLLMAdapter(structured_response={"tasks": []})
    result = await provider.generate_structured("test")
    assert result.data == {"tasks": []}


@pytest.mark.asyncio
async def test_fake_provider_rejects_malformed_request() -> None:
    provider = FakeLLMAdapter()
    with pytest.raises(Exception, match="malformed"):
        await provider.generate_structured("malformed output")