"""Syllabus parser — extracts topic tree from syllabus text via Claude API.

Uses Claude Sonnet (with OpenAI fallback) to extract structured JSON.
Validates against schema. Retries once with stricter prompt on parse failure.
"""

import json
import re
from typing import Any, Optional

import anthropic
import openai
import structlog

from app.config import settings

log = structlog.get_logger()

EXTRACTION_PROMPT = """Extract all topics from this syllabus text. Return ONLY valid JSON matching this exact schema, no other text:

{
  "topics": [
    {
      "id": "unique_snake_case_id",
      "name": "Topic Name",
      "description": "Brief description of what this topic covers",
      "prerequisites": ["id_of_prereq_topic"],
      "estimated_depth": "introductory" | "intermediate" | "advanced"
    }
  ]
}

Syllabus text:
{syllabus_text}"""

STRICT_EXTRACTION_PROMPT = """You MUST return ONLY a JSON object. No explanation. No markdown. No code blocks.
The JSON must have exactly one key "topics" containing an array.

Parse this syllabus and return the topic structure:
{syllabus_text}"""


class SyllabusParser:
    """Extracts structured topic trees from syllabus text using Claude API."""

    def __init__(self):
        self.claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def parse(self, syllabus_text: str) -> dict[str, Any]:
        """Parse syllabus text into structured topic tree.

        Returns:
            dict with 'topics' key containing list of topic dicts

        Raises:
            ValueError: If parsing fails after retry
        """
        # Attempt 1: normal prompt
        try:
            result = await self._call_claude(syllabus_text, strict=False)
            validated = self._validate_and_assign_ids(result)
            log.info("syllabus_parser.success", topic_count=len(validated["topics"]))
            return validated
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.warning("syllabus_parser.attempt1_failed", error=str(e))

        # Attempt 2: strict prompt
        try:
            result = await self._call_claude(syllabus_text, strict=True)
            validated = self._validate_and_assign_ids(result)
            log.info("syllabus_parser.success_retry", topic_count=len(validated["topics"]))
            return validated
        except Exception as e:
            log.warning("syllabus_parser.claude_failed_trying_openai", error=str(e))

        # Fallback: OpenAI
        try:
            result = await self._call_openai(syllabus_text)
            validated = self._validate_and_assign_ids(result)
            log.info("syllabus_parser.openai_success", topic_count=len(validated["topics"]))
            return validated
        except Exception as e:
            log.error("syllabus_parser.all_attempts_failed", error=str(e))
            raise ValueError(f"Failed to parse syllabus after all attempts: {e}")

    async def _call_claude(self, syllabus_text: str, strict: bool = False) -> dict:
        template = STRICT_EXTRACTION_PROMPT if strict else EXTRACTION_PROMPT
        prompt = template.format(syllabus_text=syllabus_text[:8000])  # cap input

        response = await self.claude.messages.create(
            model=settings.CLAUDE_SONNET_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return self._extract_json(raw)

    async def _call_openai(self, syllabus_text: str) -> dict:
        response = await self.openai.chat.completions.create(
            model=settings.OPENAI_FALLBACK_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": "Extract syllabus topics as JSON. Return ONLY valid JSON."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(syllabus_text=syllabus_text[:8000])},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from potentially markdown-wrapped text."""
        # Strip markdown code blocks
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()
        return json.loads(text)

    def _validate_and_assign_ids(self, data: dict) -> dict:
        """Validate topic structure and ensure all IDs are unique."""
        if "topics" not in data:
            raise ValueError("Missing 'topics' key in parsed result")

        topics = data["topics"]
        if not isinstance(topics, list) or len(topics) == 0:
            raise ValueError("'topics' must be a non-empty list")

        # Ensure all topics have required fields
        seen_ids = set()
        for i, topic in enumerate(topics):
            if "id" not in topic or not topic["id"]:
                topic["id"] = f"topic_{i+1}"
            if topic["id"] in seen_ids:
                topic["id"] = f"{topic['id']}_{i}"
            seen_ids.add(topic["id"])

            if "name" not in topic:
                raise ValueError(f"Topic {i} missing 'name'")
            if "prerequisites" not in topic:
                topic["prerequisites"] = []
            if "estimated_depth" not in topic:
                topic["estimated_depth"] = "intermediate"
            if "description" not in topic:
                topic["description"] = ""

        return {"topics": topics}
