"""
Classification gate tests for the LLM router.

These tests stub out the actual providers and only verify the
routing/refusal logic: external providers can never serve classified
data, and STATE_GRADE_MODE makes CONFIDENTIAL+ refuse without a local
provider.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.core.classification import ClassificationLevel
from app.services.llm.base import LLMProvider, LLMResult, LLMTask
from app.services.llm.exceptions import ClassificationViolationError
from app.services.llm.router import LLMRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _AlwaysOnExternalProvider(LLMProvider):
    name = "fake-external"
    forbidden_for_classified = True
    max_classification = ClassificationLevel.PUBLIC

    async def is_available(self) -> bool:  # always reachable
        return True

    async def _generate(self, task: LLMTask) -> LLMResult:
        return LLMResult(
            text="ok",
            provider=self.name,
            model="fake",
            classification=ClassificationLevel.PUBLIC,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_task_routes_to_external_when_fallback_enabled(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_OPENROUTER_FALLBACK", True)
    monkeypatch.setattr(config.settings, "STATE_GRADE_MODE", False)

    router = LLMRouter(providers=[_AlwaysOnExternalProvider()])
    result = await router.generate(
        LLMTask(prompt="hello", classification=ClassificationLevel.PUBLIC)
    )
    assert result.provider == "fake-external"


@pytest.mark.asyncio
async def test_secret_task_refuses_when_only_external_available(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ENABLE_OPENROUTER_FALLBACK", True)
    monkeypatch.setattr(config.settings, "STATE_GRADE_MODE", False)

    router = LLMRouter(providers=[_AlwaysOnExternalProvider()])
    with pytest.raises(ClassificationViolationError):
        await router.generate(
            LLMTask(prompt="x", classification=ClassificationLevel.SECRET)
        )


@pytest.mark.asyncio
async def test_confidential_task_refuses_in_state_grade_with_only_external(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "STATE_GRADE_MODE", True)
    monkeypatch.setattr(config.settings, "ENABLE_OPENROUTER_FALLBACK", True)

    router = LLMRouter(providers=[_AlwaysOnExternalProvider()])
    with pytest.raises(ClassificationViolationError):
        await router.generate(
            LLMTask(prompt="x", classification=ClassificationLevel.CONFIDENTIAL)
        )
