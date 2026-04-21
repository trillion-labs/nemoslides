"""Image search with provider chain + disk cache.

Provider order (first configured, non-rate-limited provider wins):
  1. Pexels    (PEXELS_API_KEY)    — 200 req/hr free tier
  2. Unsplash  (UNSPLASH_ACCESS_KEY) — 50 req/hr demo, 5000/hr production
  3. Curated bank fallback (`data/image_bank.json`) — rule-based match

Disk cache at `data/query_cache.json`: normalized query → result dict. Halves
the effective API load for training-data renders, where similar queries repeat
across decks.

Unsplash compliance:
  - Uses `photo.urls.regular` hotlinks (not downloading bytes).
  - Hits `photo.links.download_location` on each pick (download tracking).
  - Attribution strings carry `utm_source=slides-sft&utm_medium=referral`.

Public entry points:
  - `image_search(query) -> ImageResult`
  - `unsplash_search(query) -> ImageResult`  (alias for backward compat)
"""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx

from nemoslides._paths import DATA

_BANK_PATH = DATA / "image_bank.json"
_CACHE_PATH = DATA / "query_cache.json"

_UTM = "utm_source=nemoslides&utm_medium=referral"


@dataclass
class ImageResult:
    url: str
    attribution: str
    source: str  # "pexels_api" | "unsplash_api" | "bank"

    def as_dict(self) -> dict[str, str]:
        return {"url": self.url, "attribution": self.attribution, "source": self.source}


# ─────────────── Cache ───────────────

_cache: dict[str, dict[str, str]] | None = None


def _load_cache() -> dict[str, dict[str, str]]:
    global _cache
    if _cache is None:
        _cache = json.loads(_CACHE_PATH.read_text()) if _CACHE_PATH.exists() else {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(_cache, indent=2, ensure_ascii=False))


def _norm_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


# ─────────────── Providers ───────────────

def _pexels_search(query: str) -> ImageResult | None:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    r = httpx.get(
        "https://api.pexels.com/v1/search",
        params={
            "query": query,
            "per_page": 5,
            "orientation": "landscape",
            "size": "large",
        },
        headers={"Authorization": key},
        timeout=15.0,
    )
    if r.status_code == 429:
        return None
    r.raise_for_status()
    photos = r.json().get("photos") or []
    if not photos:
        return None
    hit = photos[0]
    url = hit["src"].get("large2x") or hit["src"]["large"]
    attr = f"Photo by {hit['photographer']} on Pexels"
    return ImageResult(url=url, attribution=attr, source="pexels_api")


def _unsplash_search(query: str) -> ImageResult | None:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return None
    r = httpx.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": 5, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"},
        timeout=15.0,
    )
    if r.status_code == 429:
        return None
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    hit = results[0]
    url = hit["urls"].get("regular") or hit["urls"]["raw"]

    # Unsplash compliance: hit the download_location to register the pick.
    dl = (hit.get("links") or {}).get("download_location")
    if dl:
        try:
            httpx.get(dl, headers={"Authorization": f"Client-ID {key}"}, timeout=5.0)
        except httpx.HTTPError:
            pass

    user = hit.get("user") or {}
    uname = user.get("username", "")
    name = user.get("name", "Unsplash contributor")
    attr = (
        f"Photo by [{name}](https://unsplash.com/@{uname}?{_UTM}) "
        f"on [Unsplash](https://unsplash.com/?{_UTM})"
    )
    return ImageResult(url=url, attribution=attr, source="unsplash_api")


_UNSPLASH_ROOT = "https://images.unsplash.com"
_BANK_WIDTH = 1600

_bank: list[dict[str, Any]] | None = None


def _load_bank() -> list[dict[str, Any]]:
    global _bank
    if _bank is None:
        _bank = json.loads(_BANK_PATH.read_text())
    return _bank


def _bank_lookup(query: str) -> ImageResult:
    q_tokens = set(re.findall(r"[a-z]+", query.lower()))
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in _load_bank():
        haystack = set(item["themes"]) | set(re.findall(r"[a-z]+", item["desc"].lower()))
        score = len(q_tokens & haystack)
        if score:
            scored.append((score, item))
    if not scored:
        pick = next(i for i in _load_bank() if "office" in i["themes"])
    else:
        scored.sort(key=lambda t: (-t[0], random.random()))
        pick = scored[0][1]
    url = f"{_UNSPLASH_ROOT}/{pick['id']}?w={_BANK_WIDTH}&auto=format&fit=crop&q=80"
    return ImageResult(url=url, attribution="Unsplash curated bank", source="bank")


PROVIDERS: list[Callable[[str], ImageResult | None]] = [
    _pexels_search,
    _unsplash_search,
]


# ─────────────── Public API ───────────────

def image_search(query: str) -> ImageResult:
    """Resolve a query via the provider chain; cache every result on disk."""
    nq = _norm_query(query)
    cache = _load_cache()
    if nq in cache:
        return ImageResult(**cache[nq])

    for provider in PROVIDERS:
        try:
            result = provider(query)
        except httpx.HTTPError:
            result = None
        if result is not None:
            cache[nq] = result.as_dict()
            _save_cache()
            return result

    result = _bank_lookup(query)
    cache[nq] = result.as_dict()
    _save_cache()
    return result


# back-compat alias — existing callers import `unsplash_search`
unsplash_search = image_search


# ─────────────── Tool spec (unchanged signature, new name) ───────────────

OPENAI_TOOL_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "image_search",
        "description": (
            "Search free-use stock photos matching a natural-language query. "
            "Returns a stable image URL usable in Slidev markdown via `image:`. "
            "Query should describe the visual subject in 3–8 words."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language description of the desired image.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def run_image_search(arguments: dict[str, Any]) -> dict[str, str]:
    query = (arguments.get("query") or "").strip()
    if not query:
        return {"error": "empty query", "url": "", "attribution": "", "source": "error"}
    return image_search(query).as_dict()


# back-compat
run_unsplash_search = run_image_search


if __name__ == "__main__":
    for q in [
        "diverse engineering team at laptops",
        "abstract neural network visualization",
        "modern startup office with glass walls",
        "cold email campaign dashboard",
    ]:
        r = image_search(q)
        print(f"{q!r:55s} [{r.source}]")
        print(f"  {r.url}")
