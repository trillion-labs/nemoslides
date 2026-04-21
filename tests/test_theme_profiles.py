"""Round-trip: data/theme_profiles.json must stay aligned with nemoslides.pipeline.seeds.THEME_PROFILES.

Either file can drift independently — this test fails loudly if they do.
"""

from __future__ import annotations

import json

from nemoslides._paths import DATA
from nemoslides.pipeline.seeds import THEME_PROFILES, THEMES

PROFILES_JSON = DATA / "theme_profiles.json"


def test_theme_profiles_round_trip() -> None:
    rows = json.loads(PROFILES_JSON.read_text())
    assert {row["theme"] for row in rows} == set(THEMES)
    for row in rows:
        expected = THEME_PROFILES[row["theme"]]
        assert row["vibe"] == expected["vibe"]
        assert row["topic_fit"] == expected["topic_fit"]
        assert row["tone"] == expected["tone"]
