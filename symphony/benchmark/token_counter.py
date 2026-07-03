"""A thin `LLMProvider` wrapper that tallies token usage across every call it
forwards, so the benchmark harness can report each mode's real per-run
`token_cost` without instrumenting every agent or the Parliament Protocol
itself — one shared counting provider wraps whatever backend a run's agents
already use.
"""

from __future__ import annotations

from symphony.llm.provider import LLMProvider, LLMResult


class TokenCountingProvider:
    """Wraps another `LLMProvider`, accumulating `total_tokens` across calls."""

    def __init__(self, inner: LLMProvider) -> None:
        self.inner = inner
        self.total_tokens = 0

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> LLMResult:
        result = self.inner.complete(
            system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens
        )
        self.total_tokens += result.total_tokens
        return result
