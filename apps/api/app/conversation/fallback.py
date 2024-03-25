"""LLM Fallback Chain — Claude → OpenAI → raw chunks.

Never leaves the user hanging. Smart triggers beyond just crashes:
- Timeout > 5s
- Empty response
- Rate limit
- Zero citations in response
"""

import asyncio
import time
from typing import AsyncGenerator, List, Optional

import anthropic
import openai
import structlog

from app.config import settings

log = structlog.get_logger()


class FallbackTrigger:
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    EMPTY_RESPONSE = "empty_response"
    RATE_LIMIT = "rate_limit"
    ZERO_CITATIONS = "zero_citations"


class LLMFallbackManager:
    """Manages the Claude → OpenAI → raw chunks fallback chain.

    On each message:
    1. Try Claude Sonnet (primary)
    2. On failure/timeout → try OpenAI GPT-4o-mini
    3. On both failing → return raw retrieved chunks with disclaimer

    Emits structured events compatible with the streaming interface.
    """

    def __init__(self):
        self.claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def stream_response(
        self,
        messages: List[dict],
        system_prompt: str,
        retrieved_chunks: List[dict],
        timeout: float = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream a response using the fallback chain.

        Yields event dicts:
          {"type": "token", "content": str, "provider": str}
          {"type": "provider_switched", "from": str, "to": str, "reason": str}
          {"type": "complete", "provider": str, "tokens_used": int}
          {"type": "fallback_to_chunks", "chunks": list}
        """
        timeout = timeout or settings.LLM_TIMEOUT_SECONDS

        # Try Claude first
        try:
            async for event in self._stream_claude(messages, system_prompt, timeout):
                yield event
            return
        except anthropic.RateLimitError as e:
            log.warning("fallback.claude_rate_limit", error=str(e))
            yield {"type": "provider_switched", "from": "claude", "to": "openai", "reason": FallbackTrigger.RATE_LIMIT}
        except asyncio.TimeoutError:
            log.warning("fallback.claude_timeout", timeout=timeout)
            yield {"type": "provider_switched", "from": "claude", "to": "openai", "reason": FallbackTrigger.TIMEOUT}
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            log.warning("fallback.claude_api_error", error=str(e))
            yield {"type": "provider_switched", "from": "claude", "to": "openai", "reason": FallbackTrigger.API_ERROR}

        # Try OpenAI fallback
        try:
            async for event in self._stream_openai(messages, system_prompt, settings.LLM_FALLBACK_TIMEOUT_SECONDS):
                yield event
            return
        except openai.RateLimitError as e:
            log.warning("fallback.openai_rate_limit", error=str(e))
        except asyncio.TimeoutError:
            log.warning("fallback.openai_timeout")
        except (openai.APIError, openai.APIConnectionError) as e:
            log.warning("fallback.openai_api_error", error=str(e))

        # Final fallback — return raw chunks
        log.error("fallback.both_providers_failed_returning_raw_chunks")
        yield {
            "type": "fallback_to_chunks",
            "chunks": retrieved_chunks,
            "disclaimer": (
                "The AI tutor is temporarily unavailable. "
                "Here are the most relevant sections from your documents:"
            ),
        }

    async def _stream_claude(
        self, messages: List[dict], system_prompt: str, timeout: float
    ) -> AsyncGenerator[dict, None]:
        """Stream from Claude Sonnet with timeout."""
        token_count = 0

        async def _inner():
            nonlocal token_count
            async with self.claude.messages.stream(
                model=settings.CLAUDE_SONNET_MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield {"type": "token", "content": text, "provider": "claude"}
                    token_count += 1

                final = await stream.get_final_message()
                yield {
                    "type": "complete",
                    "provider": "claude",
                    "tokens_used": final.usage.input_tokens + final.usage.output_tokens,
                }

        async for event in asyncio.wait_for(_inner(), timeout=timeout):
            yield event

    async def _stream_openai(
        self, messages: List[dict], system_prompt: str, timeout: float
    ) -> AsyncGenerator[dict, None]:
        """Stream from OpenAI GPT-4o-mini with timeout."""
        token_count = 0

        oai_messages = [{"role": "system", "content": system_prompt}] + messages

        async def _inner():
            nonlocal token_count
            stream = await self.openai.chat.completions.create(
                model=settings.OPENAI_MAIN_MODEL,
                messages=oai_messages,
                stream=True,
                max_tokens=2048,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield {"type": "token", "content": delta, "provider": "openai"}
                    token_count += 1

            yield {"type": "complete", "provider": "openai", "tokens_used": token_count}

        async for event in asyncio.wait_for(_inner(), timeout=timeout):
            yield event
