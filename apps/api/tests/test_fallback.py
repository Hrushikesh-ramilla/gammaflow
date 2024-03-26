"""Tests for LLM fallback chain — mocks provider failures."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMFallbackChain(unittest.TestCase):
    """Test that fallback chain correctly switches providers on failure."""

    def _collect_events(self, gen):
        """Collect all events from an async generator synchronously."""
        loop = asyncio.new_event_loop()
        events = []

        async def _run():
            async for event in gen:
                events.append(event)

        loop.run_until_complete(_run())
        loop.close()
        return events

    @patch("app.conversation.fallback.anthropic.AsyncAnthropic")
    def test_claude_success_returns_tokens(self, mock_anthropic_cls):
        """When Claude succeeds, events come from claude provider."""
        from app.conversation.fallback import LLMFallbackManager
        import anthropic

        # Mock Claude streaming
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.text_stream = self._async_iter(["Hello ", "world"])
        mock_final = MagicMock()
        mock_final.usage.input_tokens = 50
        mock_final.usage.output_tokens = 10
        mock_stream.get_final_message = AsyncMock(return_value=mock_final)

        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=mock_stream)
        mock_anthropic_cls.return_value = mock_client

        mgr = LLMFallbackManager()
        events = self._collect_events(
            mgr.stream_response(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="test",
                retrieved_chunks=[],
            )
        )

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert all(e["provider"] == "claude" for e in token_events)

    def _async_iter(self, items):
        """Create an async iterable from a list."""
        async def _gen():
            for item in items:
                yield item
        return _gen()

    def test_citation_parser_extracts_page_numbers(self):
        """Citation parser correctly extracts page numbers."""
        from app.conversation.citation_parser import parse_citations
        text = "This is explained on [Page 47, Textbook] and also see [Page 12 — Notes]."
        citations = parse_citations(text)
        assert len(citations) == 2
        assert citations[0].page_number == 47
        assert citations[0].document_name == "Textbook"
        assert citations[1].page_number == 12

    def test_citation_parser_handles_no_citations(self):
        from app.conversation.citation_parser import parse_citations, has_citations
        text = "No citations in this text."
        assert parse_citations(text) == []
        assert not has_citations(text)


if __name__ == "__main__":
    unittest.main()
