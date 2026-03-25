"""Claude and OpenAI streaming clients.

This module provides thin async streaming wrappers used directly by the
LLMFallbackManager in fallback.py. Having them here as standalone functions
makes them independently testable.

These are intentionally stateless — all context (messages, system prompt)
is passed in per-call.
"""

import asyncio
from typing import AsyncGenerator, List

import anthropic
import openai
import structlog

from app.config import settings

log = structlog.get_logger()


async def stream_claude(
    messages: List[dict],
    system_prompt: str,
    timeout: float = None,
) -> AsyncGenerator[dict, None]:
    """Stream from Claude Sonnet.

    Yields event dicts:
      {"type": "token",    "content": str, "provider": "claude"}
      {"type": "complete", "provider": "claude", "tokens_used": int}

    Raises: anthropic.APIError, anthropic.RateLimitError, asyncio.TimeoutError
    """
    timeout = timeout or settings.LLM_TIMEOUT_SECONDS
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    tokens_used = 0

    async def _inner():
        nonlocal tokens_used
        async with client.messages.stream(
            model=settings.CLAUDE_SONNET_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "content": text, "provider": "claude"}
                tokens_used += 1

            final = await stream.get_final_message()
            yield {
                "type": "complete",
                "provider": "claude",
                "tokens_used": (
                    final.usage.input_tokens + final.usage.output_tokens
                    if final.usage
                    else tokens_used
                ),
            }

    async for event in asyncio.wait_for(_inner(), timeout=timeout):
        yield event


async def stream_openai(
    messages: List[dict],
    system_prompt: str,
    timeout: float = None,
) -> AsyncGenerator[dict, None]:
    """Stream from OpenAI GPT-4o-mini.

    Yields event dicts:
      {"type": "token",    "content": str, "provider": "openai"}
      {"type": "complete", "provider": "openai", "tokens_used": int}

    Raises: openai.APIError, openai.RateLimitError, asyncio.TimeoutError
    """
    timeout = timeout or settings.LLM_FALLBACK_TIMEOUT_SECONDS
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    tokens_used = 0

    oai_messages = [{"role": "system", "content": system_prompt}] + messages

    async def _inner():
        nonlocal tokens_used
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MAIN_MODEL,
            messages=oai_messages,
            stream=True,
            max_tokens=2048,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield {"type": "token", "content": delta, "provider": "openai"}
                tokens_used += 1

        yield {"type": "complete", "provider": "openai", "tokens_used": tokens_used}

    async for event in asyncio.wait_for(_inner(), timeout=timeout):
        yield event
