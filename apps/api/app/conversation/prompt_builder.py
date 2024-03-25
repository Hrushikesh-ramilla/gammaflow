"""Prompt builder with strict token budget management.

Hard cap: 6,000 tokens total
  System prompt:    ~400 tokens
  Session summary:  ~300 tokens
  Last 5 messages:  ~800 tokens
  Retrieved chunks: ~2,000 tokens
  Current message:  ~100 tokens
  ─────────────────────────────
  Total:            ~3,600 tokens (headroom for response)
"""

from typing import List, Optional

import structlog

from app.config import settings

log = structlog.get_logger()

# Approximate: 1 token ≈ 4 chars
CHARS_PER_TOKEN = 4

SYSTEM_PROMPT_TEMPLATE = """You are SYL, an AI study tutor. You help students understand topics from their uploaded academic materials.

RULES (non-negotiable):
1. Answer ONLY using the provided document chunks below.
2. Every factual claim MUST be followed by a citation: [Page X, DocumentName]
3. If you cannot find the answer in the provided chunks, respond EXACTLY with: "I couldn't find this in your uploaded materials."
4. Never fabricate information or use knowledge outside the provided chunks.
5. Citations must use exact page numbers from the chunks.

Current topic: {topic_name}
Topic depth: {estimated_depth}
Prerequisites covered: {prerequisites}

Retrieved document chunks:
{chunks_text}"""


class PromptBuilder:
    """Assembles LLM prompts with strict token budget enforcement."""

    def __init__(self):
        self.max_total = settings.MAX_TOTAL_TOKENS * CHARS_PER_TOKEN
        self.system_budget = settings.SYSTEM_PROMPT_TOKENS * CHARS_PER_TOKEN
        self.summary_budget = settings.SESSION_SUMMARY_TOKENS * CHARS_PER_TOKEN
        self.messages_budget = settings.LAST_N_MESSAGES
        self.chunks_budget = settings.RETRIEVED_CHUNKS_TOKENS * CHARS_PER_TOKEN

    def build_system_prompt(
        self,
        topic_name: str,
        estimated_depth: str,
        prerequisites: List[str],
        chunks: List[dict],
    ) -> str:
        """Build the system prompt with retrieved chunks embedded."""
        chunks_text = self._format_chunks(chunks)
        return SYSTEM_PROMPT_TEMPLATE.format(
            topic_name=topic_name,
            estimated_depth=estimated_depth,
            prerequisites=", ".join(prerequisites) if prerequisites else "None",
            chunks_text=chunks_text,
        )

    def build_messages(
        self,
        conversation_history: List[dict],
        current_message: str,
        session_summary: Optional[str] = None,
        resume_context: Optional[str] = None,
    ) -> List[dict]:
        """Build the messages array with sliding window history."""
        messages = []

        # Add session summary as first context message if available
        if session_summary:
            summary_text = session_summary[:self.summary_budget]
            messages.append({
                "role": "assistant",
                "content": f"[Session context: {summary_text}]",
            })

        # Add resume context injection if resuming from deviation
        if resume_context:
            messages.append({
                "role": "assistant",
                "content": resume_context,
            })

        # Last N messages (verbatim)
        recent = conversation_history[-self.messages_budget :]
        messages.extend(recent)

        # Current user message
        messages.append({"role": "user", "content": current_message})

        return messages

    def _format_chunks(self, chunks: List[dict]) -> str:
        """Format retrieved chunks into the prompt, respecting token budget."""
        formatted = []
        total_chars = 0

        for chunk in chunks:
            source = "Scanned (OCR)" if chunk.get("source_type") == "OCR" else "Text"
            chunk_text = (
                f"[Page {chunk['page_number']} — {chunk.get('document_role', 'Document')}] "
                f"{{source: {source}}}\n{chunk['text']}\n"
            )
            if total_chars + len(chunk_text) > self.chunks_budget:
                break
            formatted.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n---\n".join(formatted) if formatted else "No relevant content found."
