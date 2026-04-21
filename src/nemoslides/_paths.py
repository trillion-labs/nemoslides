"""Repo-relative path resolution.

All runtime modules import REPO_ROOT from here instead of counting
`Path(__file__).parents[N]`, so moving files around doesn't break paths.
"""

from pathlib import Path


def _find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("could not locate repo root (no pyproject.toml ancestor)")


REPO_ROOT = _find_repo_root()
ASSETS = REPO_ROOT / "assets"
DATA = REPO_ROOT / "data"
RESULTS = REPO_ROOT / "results"
RENDERER = ASSETS / "renderer"
REFERENCE = ASSETS / "reference"
