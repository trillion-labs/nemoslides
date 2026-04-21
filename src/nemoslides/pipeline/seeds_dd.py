"""NeMo Data Designer port of the seed generator.

Replaces the hand-rolled 12-theme round-robin in `pipeline.seeds` with a
Data Designer pipeline:

  theme (category, 12) → vibe/topic_fit/tone (subcategory on theme)
                       ↓
                 domain (category, 35)
                 n_slides_target (uniform int 6..14)
                 include_outline (bernoulli p=0.35)
                       ↓
                 seed (LLM structured: topic, audience, style_hints,
                       feature_hints, outline_hint?)

Output JSON schema is byte-identical to `data/seeds.json` so downstream
(`scripts.codex_pipeline init --seeds`) keeps working unchanged.

Shards are written to `<out>.d/batch_NNNN.json` and merged via the same
pattern as the legacy generator so crashes resume cleanly.

Requires:
  - `uv add data-designer`
  - OPENROUTER_API_KEY in .env
  - `~/.data-designer/model_providers.yaml` with `default: openrouter` and
    an `openrouter` provider entry (bootstrapped by `dd_smoke.py`).

Usage:
    uv run python -m nemoslides.pipeline.seeds_dd --n 10000 --shard-size 50 --out data/seeds.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from tqdm import tqdm

from data_designer.config.exports import (
    BernoulliSamplerParams,
    CategorySamplerParams,
    ChatCompletionInferenceParams,
    DataDesignerConfigBuilder,
    LLMStructuredColumnConfig,
    ModelConfig,
    SamplerColumnConfig,
    SamplerType,
    SubcategorySamplerParams,
    UniformSamplerParams,
)
from data_designer.interface.data_designer import DataDesigner

from nemoslides.pipeline.seeds import DOMAINS, FEATURE_BUCKETS, THEMES, THEME_PROFILES

load_dotenv()


TEACHER_MODEL = "z-ai/glm-5.1"
MODEL_ALIAS = "glm"

DEFAULT_ARTIFACT_DIR = Path(".data-designer-artifacts")


GLM_MODEL = ModelConfig(
    alias=MODEL_ALIAS,
    model=TEACHER_MODEL,
    provider="openrouter",
    inference_parameters=ChatCompletionInferenceParams(
        temperature=1.0,
        top_p=1.0,
        max_tokens=2048,
    ),
)


class SlideSeedOutput(BaseModel):
    """LLM-authored half of the seed (the rest is sampled)."""

    topic: str = Field(
        description=(
            "One to two sentences. Concrete and specific; use named "
            "(possibly fictional) products, people, places, or projects. "
            "Must fit the theme profile."
        ),
    )
    audience: str = Field(description="Short phrase describing the audience.")
    style_hints: str = Field(description="Short phrase of style/tone, aligned with theme tone.")
    feature_hints: list[str] = Field(
        default_factory=list,
        description=(
            "0 to 3 items drawn from the allowed feature bucket list. "
            "Empty list is fine."
        ),
        max_length=3,
    )
    outline_hint: list[str] | None = Field(
        default=None,
        description=(
            "Per-slide summary strings. Populate ONLY if include_outline is 1. "
            "When populated, length must match n_slides_target."
        ),
    )


SYSTEM_PROMPT = (
    "You are a creative strategist helping build a training corpus for a "
    "slide-generation model. Each row you produce is a realistic slide-deck "
    "seed a real presenter would deliver. Topics must be concrete, specific, "
    "and ON-theme for the theme profile you are given. Do not copy example "
    "phrasings; invent fresh topics."
)


def _feature_bucket_list() -> str:
    return "\n".join(f"  - {bucket}" for bucket in FEATURE_BUCKETS)


USER_PROMPT = (
    "Produce one Slidev seed for a deck built on theme `{{ theme }}`.\n"
    "\n"
    "Theme profile for `{{ theme }}`:\n"
    "- Vibe: {{ vibe }}\n"
    "- Topic fit: {{ topic_fit }}\n"
    "- Tone: {{ tone }}\n"
    "\n"
    "Context for this seed:\n"
    "- Domain: {{ domain }}\n"
    "- Target slide count: {{ n_slides_target }}\n"
    "- Include outline_hint? {{ include_outline }}   (1 = yes, 0 = no)\n"
    "\n"
    "Allowed feature_hints (pick 0 to 3, or none):\n"
    f"{_feature_bucket_list()}\n"
    "\n"
    "Constraints:\n"
    "- `topic` must genuinely fit the theme profile above. Off-theme topics are rejected.\n"
    "- `topic` must match the domain. Domain and theme together constrain what you write.\n"
    "- `audience`, `style_hints`: short phrases aligned with the theme tone.\n"
    "- `feature_hints`: zero to three items from the allowed list; pick only what genuinely helps the topic.\n"
    "- `outline_hint`:\n"
    "  * If include_outline = 1, provide exactly {{ n_slides_target }} short slide-summary strings (title + 1-2 key bullets each).\n"
    "  * If include_outline = 0, set to null.\n"
    "- Do not reference this prompt or these instructions in the output.\n"
)


def build_config() -> DataDesignerConfigBuilder:
    cb = DataDesignerConfigBuilder(model_configs=[GLM_MODEL])

    cb.add_column(
        SamplerColumnConfig(
            name="theme",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=list(THEMES)),
        )
    )

    for field in ("vibe", "topic_fit", "tone"):
        cb.add_column(
            SamplerColumnConfig(
                name=field,
                sampler_type=SamplerType.SUBCATEGORY,
                params=SubcategorySamplerParams(
                    category="theme",
                    values={theme: [profile[field]] for theme, profile in THEME_PROFILES.items()},
                ),
            )
        )

    cb.add_column(
        SamplerColumnConfig(
            name="domain",
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=list(DOMAINS)),
        )
    )

    cb.add_column(
        SamplerColumnConfig(
            name="n_slides_target",
            sampler_type=SamplerType.UNIFORM,
            params=UniformSamplerParams(low=6, high=14, decimal_places=0),
        )
    )

    cb.add_column(
        SamplerColumnConfig(
            name="include_outline",
            sampler_type=SamplerType.BERNOULLI,
            params=BernoulliSamplerParams(p=0.35),
        )
    )

    cb.add_column(
        LLMStructuredColumnConfig(
            name="seed",
            model_alias=MODEL_ALIAS,
            system_prompt=SYSTEM_PROMPT,
            prompt=USER_PROMPT,
            output_format=SlideSeedOutput,
        )
    )

    return cb


def _emit_record(row: dict[str, Any], seed_idx: int) -> dict[str, Any]:
    """Flatten DD row → legacy seed-JSON shape."""
    payload = row["seed"]
    if not isinstance(payload, dict):
        payload = json.loads(payload) if isinstance(payload, str) else dict(payload)

    include_outline = int(row["include_outline"]) == 1
    outline_hint = payload.get("outline_hint") if include_outline else None
    feature_hints = payload.get("feature_hints") or []
    if not isinstance(feature_hints, list):
        feature_hints = []

    record: dict[str, Any] = {
        "domain": row["domain"],
        "topic": payload.get("topic", ""),
        "audience": payload.get("audience", ""),
        "style_hints": payload.get("style_hints", ""),
        "theme_hint": row["theme"],
        "feature_hints": feature_hints,
        "n_slides_target": int(float(row["n_slides_target"])),
        "id": f"seed_{seed_idx:05d}",
    }
    if outline_hint:
        record["outline_hint"] = list(outline_hint)
    return record


def _shard_path(batch_dir: Path, idx: int) -> Path:
    return batch_dir / f"batch_{idx:04d}.json"


def _shard_done(batch_dir: Path, idx: int) -> bool:
    p = _shard_path(batch_dir, idx)
    if not p.exists():
        return False
    try:
        payload = json.loads(p.read_text())
        return isinstance(payload, list) and len(payload) > 0
    except (json.JSONDecodeError, OSError):
        return False


def _run_shard(dd: DataDesigner, shard_size: int, dataset_name: str) -> list[dict[str, Any]]:
    cb = build_config()
    results = dd.create(cb, num_records=shard_size, dataset_name=dataset_name)
    df = results.load_dataset()
    records = df.to_dict(orient="records")
    return records


def _merge_shards(batch_dir: Path, out_path: Path) -> int:
    merged: list[dict[str, Any]] = []
    for shard in sorted(batch_dir.glob("batch_*.json")):
        try:
            rows = json.loads(shard.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for row in rows:
            row["id"] = f"seed_{len(merged):05d}"
            merged.append(row)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    return len(merged)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000, help="total seeds to generate")
    ap.add_argument("--shard-size", type=int, default=50)
    ap.add_argument("--out", type=Path, default=Path("data/seeds.json"))
    ap.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACT_DIR)
    ap.add_argument(
        "--preview-only",
        action="store_true",
        help="run one preview() of size 10 and exit; no artifacts written",
    )
    args = ap.parse_args()

    dd = DataDesigner(artifact_path=args.artifacts)

    if args.preview_only:
        cb = build_config()
        result = dd.preview(cb, num_records=10)
        df = result.dataset
        cols = [c for c in df.columns if not c.endswith("__reasoning_trace")]
        print(df[cols].to_string())
        return

    batch_dir = args.out.with_suffix(".d")
    batch_dir.mkdir(parents=True, exist_ok=True)

    n_shards = (args.n + args.shard_size - 1) // args.shard_size
    todo = [i for i in range(n_shards) if not _shard_done(batch_dir, i)]
    done = n_shards - len(todo)

    print(
        f"shards: {n_shards} total | done {done} | running {len(todo)} "
        f"| shard-size {args.shard_size} | out {args.out}"
    )

    rng = random.Random(42)

    for idx in tqdm(todo, desc="shards"):
        try:
            rows = _run_shard(dd, args.shard_size, dataset_name=f"shard_{idx:04d}")
        except Exception as e:
            tqdm.write(f"  ! shard {idx:04d} failed: {type(e).__name__}: {e}")
            continue

        records: list[dict[str, Any]] = []
        for offset, row in enumerate(rows):
            try:
                rec = _emit_record(row, seed_idx=idx * args.shard_size + offset)
            except Exception as exc:
                tqdm.write(f"  ! shard {idx:04d} row {offset} malformed: {exc}")
                continue
            if not rec["topic"]:
                continue
            records.append(rec)
        if records:
            _shard_path(batch_dir, idx).write_text(
                json.dumps(records, indent=2, ensure_ascii=False)
            )
            tqdm.write(f"  + shard {idx:04d}: {len(records)}/{len(rows)} kept")
        else:
            tqdm.write(f"  ! shard {idx:04d}: 0 valid rows — not writing")
        _ = rng.random()  # reserved for future jitter/backoff hooks

    total = _merge_shards(batch_dir, args.out)
    print(f"merged {total} seeds → {args.out}")
    print(f"shard files at {batch_dir}/")


if __name__ == "__main__":
    main()
