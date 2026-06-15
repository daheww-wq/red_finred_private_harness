from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Dict

from .models import ProviderRequest, ProviderResponse


class Provider(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError


class FakeProvider(Provider):
    def __init__(self, model: str):
        self.name = "fake"
        self.model = model

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        text = (
            f"[fake:{request.role}] category={request.case.category}; "
            f"case_id={request.case.case_id}; expected={request.case.expected_behavior}"
        )
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            text=text,
            raw={"deterministic": True},
        )


class OpenAIProvider(Provider):
    def __init__(self, model: str):
        self.name = "openai"
        self.model = model

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if os.environ.get("RUN_LIVE_LLM_TESTS", "false").lower() != "true":
            raise RuntimeError("OpenAI live calls require RUN_LIVE_LLM_TESTS=true")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI live calls")
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": request.prompt}],
        )
        text = response.choices[0].message.content or ""
        return ProviderResponse(provider=self.name, model=self.model, text=text, raw={"live": True})


class GeminiProvider(Provider):
    def __init__(self, model: str):
        self.name = "gemini"
        self.model = model

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if os.environ.get("RUN_LIVE_LLM_TESTS", "false").lower() != "true":
            raise RuntimeError("Gemini live calls require RUN_LIVE_LLM_TESTS=true")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini live calls")
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=self.model, contents=request.prompt)
        return ProviderResponse(provider=self.name, model=self.model, text=response.text or "", raw={"live": True})


def build_provider(provider_type: str, model: str) -> Provider:
    provider_type = provider_type.lower()
    providers: Dict[str, type[Provider]] = {
        "fake": FakeProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }
    if provider_type not in providers:
        raise ValueError(f"unsupported provider type: {provider_type}")
    return providers[provider_type](model)
