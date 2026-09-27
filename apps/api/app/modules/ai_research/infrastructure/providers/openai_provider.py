"""
RegimeX AI Research — OpenAI-Compatible Model Provider
======================================================
Provider communicating with OpenAI or OpenAI-compatible REST endpoints (e.g. Ollama,
vLLM, LiteLLM, Groq, or Azure OpenAI). Uses httpx with zero hardcoded API keys.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.modules.ai_research.domain.errors import ProviderUnavailableError
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import EvidencePacket

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(ResearchModelProvider):
    """
    HTTP provider for OpenAI-compatible chat completion APIs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_tokens: int = 2000,
    ) -> None:
        self._api_key = api_key or ""
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._model_name = model_name
        self._timeout = timeout
        self._max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> str:
        """
        Execute chat completion request against the provider.
        """
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self._max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(
                        "AI provider returned error %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    raise ProviderUnavailableError(
                        f"AI provider returned status {response.status_code}."
                    )
                data = response.json()
                content: str = data["choices"][0]["message"]["content"]
                return content.strip()
        except httpx.TimeoutException as exc:
            logger.warning("AI provider timed out after %.1f seconds", self._timeout)
            raise ProviderUnavailableError(
                f"AI provider request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("AI provider connection error: %s", exc)
            raise ProviderUnavailableError(f"AI provider connection error: {exc}") from exc

    async def stream(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> AsyncGenerator[str, None]:
        """
        Execute streaming chat completion and yield tokens.
        """
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self._max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        raise ProviderUnavailableError(
                            f"AI provider streaming returned status {response.status_code}."
                        )
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[len("data: ") :].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, KeyError, IndexError) as parse_err:
                            logger.debug("Skipping unparseable SSE chunk: %s", parse_err)
                            continue
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error("AI provider streaming error: %s", exc)
            raise ProviderUnavailableError(f"AI provider streaming failure: {exc}") from exc
