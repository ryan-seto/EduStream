import json
import logging

import anthropic
import google.generativeai as genai
from app.config import get_settings
from app.services.scenario_pool import scenario_pool

logger = logging.getLogger(__name__)
settings = get_settings()


PROBLEM_PROMPT_TEMPLATE = """You are creating a short-form educational video about {category} for social media.

Topic: {topic}
{description_section}

Create a PROBLEM/QUIZ video that:
1. Hooks viewers with "Can you solve this?" or similar
2. Presents a clear engineering/physics problem with specific numbers
3. Shows 4 multiple choice answer options (A, B, C, D)
4. Encourages viewers to comment their answer

IMPORTANT: Return ONLY valid JSON, no other text. Use this exact structure:
{{
  "type": "problem",
  "hook_text": "Can you solve this beam problem?",
  "diagram_description": "Detailed description for drawing: beam type, supports, loads with exact values and positions",
  "content_steps": [
    {{"text": "Given: describe the setup with numbers", "highlight": "what to emphasize"}},
    {{"text": "Find: what to calculate", "highlight": "target variable"}}
  ],
  "answer_options": ["A: 5 kN", "B: 10 kN", "C: 15 kN", "D: 20 kN"],
  "correct_answer": "A",
  "explanation": "Brief explanation of why A is correct",
  "cta_text": "Comment A, B, C, or D!"
}}

The diagram_description MUST include:
- Type of structure (beam, truss, etc.)
- Support types and positions (pin, roller, fixed)
- Load types, magnitudes, and positions
- Any dimensions needed

Make the problem solvable in ~30 seconds mentally or with simple math.
Return ONLY the JSON object, no markdown formatting."""


class AIGenerator:
    """
    Generates educational scripts using Claude API (primary) or Gemini API (fallback).
    """

    def __init__(self):
        self.claude_client = None
        self.gemini_model = None

        # Try Claude first (primary)
        if settings.anthropic_api_key:
            self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Gemini as fallback
        if settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key":
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate_problem_script(
        self,
        topic: str,
        category: str = "engineering",
        description: str | None = None,
        recent_template_ids: list[str] | None = None,
    ) -> dict:
        """
        Generate a problem/quiz script for short-form video.

        Returns:
            dict with structured script data for video generation
        """
        # PRIMARY: Use hardcoded scenario pool (no API cost)
        try:
            result = scenario_pool.generate(
                topic=topic,
                category=category,
                description=description or "",
                recent_template_ids=recent_template_ids,
            )
            logger.info("Used scenario pool for: %s", topic)
            return result
        except Exception as e:
            logger.warning("Scenario pool error: %s, falling back to AI APIs", e)

        description_section = f"Additional context: {description}" if description else ""
        prompt = PROBLEM_PROMPT_TEMPLATE.format(
            topic=topic,
            category=category,
            description_section=description_section,
        )

        # Try Claude API first
        if self.claude_client:
            try:
                response = self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return self._parse_json_response(response.content[0].text)
            except Exception as e:
                logger.error("Claude API error: %s", e)

        # Try Gemini as fallback
        if self.gemini_model:
            try:
                response = await self.gemini_model.generate_content_async(prompt)
                return self._parse_json_response(response.text)
            except Exception as e:
                logger.error("Gemini API error: %s", e)

        # Fall back to mock data
        logger.warning("No AI API available, using mock data")
        return self._get_mock_problem_script(topic, category)

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON response from AI, handling common formatting issues."""
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}\nResponse: {text[:500]}")

    def _get_mock_problem_script(self, topic: str, category: str) -> dict:
        """Return mock problem data for testing without API key."""
        return {
            "type": "problem",
            "hook_text": f"Can you solve this {topic} problem?",
            "diagram_description": f"Simply supported beam, 6m length. Pin support at left end (A), roller support at right end (B). Point load of 12 kN applied at center (3m from each end). Show reaction forces Ra at A and Rb at B as upward arrows.",
            "content_steps": [
                {"text": "Given: 6m beam with 12 kN center load", "highlight": "load"},
                {"text": "Find: Reaction forces at A and B", "highlight": "supports"},
            ],
            "answer_options": [
                "A: Ra = 6 kN, Rb = 6 kN",
                "B: Ra = 12 kN, Rb = 0 kN",
                "C: Ra = 8 kN, Rb = 4 kN",
                "D: Ra = 4 kN, Rb = 8 kN",
            ],
            "correct_answer": "A",
            "explanation": "By symmetry, each support carries half the load: 12 kN ÷ 2 = 6 kN each",
            "cta_text": "Comment A, B, C, or D!",
        }


# Singleton instance
ai_generator = AIGenerator()
