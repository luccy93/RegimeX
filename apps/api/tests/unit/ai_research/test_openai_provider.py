"""
RegimeX AI Research — OpenAI-Compatible Provider Tests
======================================================
Tests for OpenAICompatibleProvider:
- Initialization with and without API key
- Generate method parsing chat completion payload
- Stream method parsing Server-Sent Events (SSE) stream
- Error handling: HTTP errors, timeout, connection failures
- Malformed SSE line handling
"""

from __future__ import annotations

import unittest.mock as mock

import httpx
import pytest
from app.modules.ai_research.domain.errors import ProviderUnavailableError
from app.modules.ai_research.domain.models import EvidencePacket
from app.modules.ai_research.infrastructure.providers.openai_provider import (
    OpenAICompatibleProvider,
)

_ORIG_ASYNC_CLIENT = httpx.AsyncClient


def _make_client_factory(transport: httpx.BaseTransport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return _ORIG_ASYNC_CLIENT(*args, **kwargs)

    return _factory


@pytest.fixture
def sample_evidence() -> list[EvidencePacket]:
    return [
        EvidencePacket(
            source_id="regime:SPY:current",
            source_type="regime",
            title="Regime Intelligence — SPY",
            facts={
                "symbol": "SPY",
                "current_regime_label": "BULLISH",
                "current_regime_id": 1,
                "confidence": 0.88,
            },
            timestamp="2026-09-26T20:00:00Z",
        )
    ]


class TestOpenAICompatibleProviderInit:
    """Tests configuration and initialization invariants."""

    def test_init_defaults(self) -> None:
        provider = OpenAICompatibleProvider(
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
        assert provider.provider_name == "openai"
        assert provider.model_name == "gpt-4o-mini"

    def test_init_custom_model_and_timeout(self) -> None:
        provider = OpenAICompatibleProvider(
            api_key="sk-custom",
            base_url="https://custom.endpoint.com/v1",
            model_name="deepseek-v3",
            timeout=45.0,
            max_tokens=2048,
        )
        assert provider.model_name == "deepseek-v3"
        assert provider._timeout == 45.0
        assert provider._max_tokens == 2048


class TestOpenAICompatibleProviderGenerate:
    """Tests for generate() using httpx mock transport."""

    @pytest.mark.asyncio
    async def test_generate_success(self, sample_evidence: list[EvidencePacket]) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer test-api-key"
            resp_payload = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "SPY is in the BULLISH regime [1].",
                        }
                    }
                ]
            }
            return httpx.Response(200, json=resp_payload)

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(
            api_key="test-api-key",
            base_url="https://mock-api.example.com/v1",
            model_name="test-model",
            timeout=5.0,
        )

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            result = await provider.generate(
                prompt="What regime is SPY in?",
                system_prompt="Ground answers.",
                evidence=sample_evidence,
            )

        assert result == "SPY is in the BULLISH regime [1]."
        assert provider.provider_name == "openai"
        assert provider.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_generate_without_api_key(self, sample_evidence: list[EvidencePacket]) -> None:
        captured_auth: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_auth.append(request.headers.get("Authorization"))
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"role": "assistant", "content": "Local model output"}}]
                },
            )

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(
            api_key=None,
            base_url="http://localhost:11434/v1",
            model_name="llama3",
        )

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            result = await provider.generate("hello", "sys", sample_evidence)

        assert result == "Local model output"
        assert captured_auth[0] is None

    @pytest.mark.asyncio
    async def test_generate_http_error(self, sample_evidence: list[EvidencePacket]) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1")

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            with pytest.raises(ProviderUnavailableError, match="status 500"):
                await provider.generate("hello", "sys", sample_evidence)

    @pytest.mark.asyncio
    async def test_generate_timeout(self, sample_evidence: list[EvidencePacket]) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Request timed out")

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(
            api_key="key", base_url="https://api.openai.com/v1", timeout=1.0
        )

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            with pytest.raises(ProviderUnavailableError, match="timed out"):
                await provider.generate("hello", "sys", sample_evidence)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, sample_evidence: list[EvidencePacket]) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1")

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            with pytest.raises(ProviderUnavailableError, match="connection error"):
                await provider.generate("hello", "sys", sample_evidence)


class TestOpenAICompatibleProviderStream:
    """Tests for stream() using httpx mock streaming."""

    @pytest.mark.asyncio
    async def test_stream_tokens_success(self, sample_evidence: list[EvidencePacket]) -> None:
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"SPY "}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"is "}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"BULLISH [1]."}}]}\n\n',
            "data: [DONE]\n\n",
        ]
        body = "".join(sse_lines).encode("utf-8")

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers.get("Accept") == "text/event-stream"
            return httpx.Response(200, content=body, headers={"Content-Type": "text/event-stream"})

        transport = httpx.MockTransport(handler)
        provider = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1")

        tokens: list[str] = []
        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            async for token in provider.stream("query", "sys", sample_evidence):
                tokens.append(token)

        assert "".join(tokens) == "SPY is BULLISH [1]."

    @pytest.mark.asyncio
    async def test_stream_skips_malformed_lines(
        self, sample_evidence: list[EvidencePacket]
    ) -> None:
        sse_lines = [
            "data: not-valid-json\n\n",
            'data: {"choices":[]}\n\n',  # empty choices
            'data: {"choices":[{"delta":{}}]}\n\n',  # empty delta
            'data: {"choices":[{"delta":{"content":"Valid token"}}]}\n\n',
            "data: [DONE]\n\n",
        ]
        body = "".join(sse_lines).encode("utf-8")

        transport = httpx.MockTransport(lambda _: httpx.Response(200, content=body))
        provider = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1")

        tokens: list[str] = []
        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            async for token in provider.stream("query", "sys", sample_evidence):
                tokens.append(token)

        assert tokens == ["Valid token"]

    @pytest.mark.asyncio
    async def test_stream_http_error(self, sample_evidence: list[EvidencePacket]) -> None:
        transport = httpx.MockTransport(lambda _: httpx.Response(401, text="Unauthorized"))
        provider = OpenAICompatibleProvider(api_key="bad-key", base_url="https://api.openai.com/v1")

        with mock.patch(
            "app.modules.ai_research.infrastructure.providers.openai_provider.httpx.AsyncClient",
            side_effect=_make_client_factory(transport),
        ):
            with pytest.raises(ProviderUnavailableError, match="streaming returned status 401"):
                async for _ in provider.stream("query", "sys", sample_evidence):
                    pass
