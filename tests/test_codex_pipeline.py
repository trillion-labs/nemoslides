from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nemoslides.cli import codex_pipeline


class CodexPipelineTests(unittest.TestCase):
    @staticmethod
    def _sample_think() -> str:
        return (
            "## Reading the user prompt\n"
            "The user wants a direct Q3 logistics review for leadership with specific metrics and a tight decision frame.\n"
            "The prompt implies that the audience already knows the operation, so the deck should skip background and move straight to verdict, evidence, and next actions.\n"
            "The hidden constraint is that the content must feel credible enough for an internal review, not like generic business filler.\n"
            "\n"
            "## Theme fit\n"
            "The default theme fits an internal business review because it stays legible and neutral.\n"
            "That matters here because tables and short metric statements need to feel authoritative rather than decorative.\n"
            "\n"
            "## Narrative arc\n"
            "The arc should open with the quarter verdict, move through two evidence moments, and then end with action.\n"
            "This keeps the pacing practical and avoids burying the key message under too much context.\n"
            "\n"
            "## Key slide mapping\n"
            "A statement slide frames the quarter, a default table slide proves the metrics, and an end slide closes with direction.\n"
            "Those are the key slides because they control interpretation, evidence, and the final leadership takeaway.\n"
            "\n"
            "## Image & feature choices\n"
            "No decorative features are needed.\n"
            "One compact table is enough, and avoiding extra visuals keeps the deck sharp for a business review.\n"
            "\n"
            "## Self-review\n"
            "The main risk is overexplaining the quarter instead of showing the metrics fast.\n"
            "I would shorten headings and keep the table compact so the deck stays readable in one shot.\n"
            "I would also make the close more decision-oriented so the final slide resolves the request instead of ending like a generic recap.\n"
        )

    @staticmethod
    def _sample_deck() -> str:
        return (
            "---\n"
            "theme: default\n"
            "title: Q3 Review\n"
            "layout: cover\n"
            "mdc: true\n"
            "---\n\n"
            "# Q3 Review\n\n"
            "### Supply chain leadership update\n\n"
            "---\nlayout: statement\n---\n\n"
            "# The quarter stabilized service.\n\n"
            "### Cost and inventory still need correction.\n\n"
            "---\nlayout: default\n---\n\n"
            "# Scorecard\n\n"
            "| KPI | Target | Q3 | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| OTIF | 96% | 96.1% | Met |\n"
            "| Expedite | $3.0M | $2.9M | Met |\n"
            "| Inventory days | 42 | 44 | Missed |\n"
            "| Forecast accuracy | 78% | 76% | Missed |\n\n"
            "---\nlayout: fact\n---\n\n"
            "# 96.1%\n\n"
            "### OTIF, the best quarter in five periods\n\n"
            "---\nlayout: end\n---\n\n"
            "# Close\n\n"
            "### Back the Q4 reset with weekly review discipline.\n"
        )

    def test_init_creates_prompt_stub_and_shared_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "work"
            seeds = [
                {
                    "id": "seed_00000",
                    "domain": "internal business review",
                    "topic": "Q3 OKR readout for Apex Logistics.",
                    "audience": "Ops leadership",
                    "style_hints": "direct",
                    "theme_hint": "default",
                    "feature_hints": ["data-dense tables"],
                    "n_slides_target": 8,
                }
            ]
            stats = codex_pipeline.init_workspace(seeds, out_dir)
            self.assertEqual(stats["created"], 1)
            seed_dir = out_dir / "seed_00000"
            self.assertTrue((seed_dir / "PROMPT.md").exists())
            self.assertTrue((seed_dir / "PROMPT.md").read_text().startswith("<!--\nCodex:"))
            self.assertTrue((out_dir / "_shared" / "INSTRUCTIONS.md").exists())
            self.assertTrue((seed_dir / "INSTRUCTIONS.md").is_symlink())

    def test_status_requires_prompt_deck_and_think(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "work"
            seeds = [
                {
                    "id": "seed_00000",
                    "domain": "internal business review",
                    "topic": "Q3 OKR readout for Apex Logistics.",
                    "audience": "Ops leadership",
                    "style_hints": "direct",
                    "theme_hint": "default",
                    "feature_hints": [],
                    "n_slides_target": 8,
                }
            ]
            codex_pipeline.init_workspace(seeds, out_dir)
            stats = codex_pipeline.summarize_workspace(out_dir)
            self.assertEqual(stats["complete"], 0)

            seed_dir = out_dir / "seed_00000"
            (seed_dir / "PROMPT.md").write_text("Make a concise 8-slide supply chain Q3 review deck.\n")
            (seed_dir / "think.md").write_text(self._sample_think())
            (seed_dir / "deck.md").write_text(self._sample_deck())
            stats = codex_pipeline.summarize_workspace(out_dir)
            self.assertEqual(stats["prompt_ready"], 1)
            self.assertEqual(stats["complete"], 1)

    def test_pack_uses_prompt_as_user_and_skips_stub_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "work"
            packed_dir = Path(tmp) / "packed"
            seeds = [
                {
                    "id": "seed_00000",
                    "domain": "internal business review",
                    "topic": "Q3 OKR readout for Apex Logistics.",
                    "audience": "Ops leadership",
                    "style_hints": "direct",
                    "theme_hint": "default",
                    "feature_hints": [],
                    "n_slides_target": 8,
                },
                {
                    "id": "seed_00001",
                    "domain": "internal business review",
                    "topic": "Q3 OKR readout for Northwind.",
                    "audience": "Ops leadership",
                    "style_hints": "direct",
                    "theme_hint": "default",
                    "feature_hints": [],
                    "n_slides_target": 8,
                },
            ]
            codex_pipeline.init_workspace(seeds, out_dir)
            seed_dir = out_dir / "seed_00000"
            prompt = "Create a direct 8-slide Q3 logistics OKR deck for supply chain leadership."
            (seed_dir / "PROMPT.md").write_text(prompt + "\n")
            (seed_dir / "think.md").write_text(self._sample_think())
            (seed_dir / "deck.md").write_text(self._sample_deck())

            stats = codex_pipeline.pack_workspace(out_dir, packed_dir)
            self.assertEqual(stats["packed"], 1)
            self.assertEqual(stats["skipped"], 1)
            rec = json.loads((packed_dir / "seed_00000.json").read_text())
            self.assertEqual(rec["chat_messages"][1]["content"], prompt)
            self.assertIn("<think>", rec["assistant_content_with_think"])
            self.assertIn("# Q3 Review", rec["assistant_content_with_think"])


if __name__ == "__main__":
    unittest.main()
