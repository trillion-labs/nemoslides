from __future__ import annotations

import unittest

from nemoslides.demo.app import GenerateRequest, _fake_deck_markdown
from nemoslides.demo.prompting import (
    DEFAULT_THEME,
    build_system_prompt,
    build_user_prompt,
    template_context,
)
from nemoslides.eval.generate import parse_deck


class DemoPromptingTests(unittest.TestCase):
    def test_user_prompt_includes_fixed_choices(self) -> None:
        prompt = build_user_prompt(
            prompt="Create a fundraising deck for an AI product design startup.",
            audience="executive",
            tone="professional",
            slide_count=8,
        )
        self.assertIn("Executive", prompt)
        self.assertIn("Tone: Professional", prompt)
        self.assertIn("Target slide count: 8", prompt)
        self.assertIn(f"Theme: `{DEFAULT_THEME}`", prompt)

    def test_system_prompt_keeps_slidev_contract(self) -> None:
        system = build_system_prompt()
        self.assertIn("Output ONLY `<think>...</think>` followed by the deck markdown.", system)
        self.assertIn(f"Use theme `{DEFAULT_THEME}`", system)
        self.assertIn("Do not spend a slide on an agenda, outline, or table of contents", system)

    def test_template_context_matches_default_shape(self) -> None:
        context = template_context()
        self.assertEqual(context["defaults"]["audience"], "general")
        self.assertEqual(context["defaults"]["tone"], "clear")
        self.assertEqual(context["slide_counts"], [6, 8, 10])

    def test_parse_deck_strips_reasoning_block(self) -> None:
        raw = (
            "<think>Reasoning lives here</think>\n"
            "---\n"
            "theme: geist\n"
            "layout: cover\n"
            "---\n"
            "# Demo\n"
        )
        deck = parse_deck(raw)
        self.assertTrue(deck.startswith("---\n"))
        self.assertNotIn("<think>", deck)

    def test_fake_deck_has_slidev_shape(self) -> None:
        deck = _fake_deck_markdown(
            GenerateRequest(
                prompt="Create a judge-facing product pitch for an AI startup.",
                audience="general",
                tone="professional",
                slide_count=8,
            )
        )
        self.assertIn("theme: geist", deck)
        self.assertIn("Audience", deck)
        self.assertIn("This is a fake local deck for smoke testing.", deck)


if __name__ == "__main__":
    unittest.main()
