# Progress Log

Live execution log. Update on: block completion, blocker, or deviation from [`PLAN.md`](PLAN.md).

## Current phase

**Codex-authored corpus pipeline.** Deprecated synthesis code removed. The
active path is: locked seeds → Codex writes `PROMPT.md` / `think.md` /
`deck.md` → workspace pack to training records.

## Block status

| # | Block (hours) | Status | Started | Finished | Key result |
|---|---|---|---|---|---|
| 1 | Slidev smoke test (0–1) | done | hour 0 | hour 0+15m | 5 layouts rendered to PNG via `slidev export --format png --per-slide`; seriph theme, image-right layout successfully fetches external images |
| 2 | Teacher + base qualitative check (1–2) | done | hour 1 | hour 2 | Teacher GPT-5-mini locked (with prompt iteration); base model emits Slidev-shaped output but defaults to `layout: default`, hallucinates Unsplash IDs → empty image panels. Clear gap to close. Direction shifted: train full Slidev capability, not constrained subset. See `docs/hour1_qualitative/notes.md`. |
| 3 | Data synthesis (2–5) | pending | — | — | — |
| 4 | Quality filter + JSONL (5–7) | pending | — | — | — |
| 5 | **Baseline PPTEval + NeMo-RL install (7–8)** | pending | — | — | — |
| 6 | **SFT launch (8)** | pending | — | — | — |
| 7 | Training in background, prep pitch/repo (8–20) | pending | — | — | — |
| 8 | Finetuned eval (20–26) | pending | — | — | — |
| 9 | Hero cuts + reel + self-gen pitch deck (26–32) | pending | — | — | — |
| 10 | Pitch polish + reproducibility pass (32–40) | pending | — | — | — |
| 11 | Slack (40–48) | pending | — | — | — |

## Numbers

To be filled after the relevant block completes.

| Metric | Baseline (block 5) | Finetuned (block 8) | Δ |
|---|---|---|---|
| PPTEval Content (1–5) | — | — | — |
| PPTEval Design (1–5) | — | — | — |
| PPTEval Coherence (1–5) | — | — | — |
| Pairwise win rate vs base | — | — | — |
| Dataset size (kept after filter) | — | — | — |
| Training loss (final) | — | — | — |

## Blockers / deviations

*None yet.*

## Changelog

- **Hour -1** — repo scaffolded: `README.md`, `PLAN.md`, `DECISIONS.md`, `CLAUDE.md`, `PROGRESS.md`.
- **Hour 0** — user preference locked: Python deps via `uv` only (no pip/conda/poetry). Updated `CLAUDE.md`.
- **Hour 0+15m** — Slidev smoke test complete. `demo/smoke/` contains `slides.md` (5 named layouts) and 5 rendered PNGs in `screenshots/`. Render path confirmed: Slidev CLI + playwright-chromium via `slidev export --format png --per-slide`. This path scales to thousands of decks with parallel Playwright workers.
- **Hour 1** — Python env with uv initialized (`pyproject.toml` + `uv.lock`). Deps: openai, python-dotenv, httpx, tqdm.
- **Hour 1** — Canonical renderer at `renderer/` with seriph/default/apple-basic/bricks/shibainu themes pre-installed. `./renderer/render.sh <deck.md> <output_dir>` usable from anywhere.
- **Hour 1** — Teacher (GPT-5-mini via OpenAI) + base (Nemotron-3-Nano-30B-A3B via OpenRouter free tier) qualitative check done. Teacher produces usable Slidev with minor format bugs; base understands format but defaults to `layout: default` and hallucinates Unsplash IDs → empty image panels. Side-by-side renders in `docs/hour1_qualitative/renders/`.
- **Hour 1.5** — **Direction shift:** training target expanded from template-constrained subset to full Slidev capability surface (code blocks, Mermaid, KaTeX, v-click, v-motion, all named layouts, theme variety). `DECISIONS.md` updated accordingly.
- **Hour 2** — **Architecture shift 1:** one-shot deck SFT → agentic multi-turn SFT (then re-reverted, see hour 2.5).
- **Hour 2.2** — Slidev docs vendored at `reference/slidev_docs/` (sparse-clone of `slidevjs/slidev/docs`). `pipeline/slidev_reference.py` compiles a ~45KB / 11K-token knowledge pack (syntax, layouts, animations, mermaid, latex, line-highlighting, icons, components, curated themes catalog) to inject into teacher system prompts. Unsplash tool `pipeline/tools/unsplash.py` done with API + bank fallback (smoke-tested).
- **Hour 2.5** — **Step-back + re-scope:** agentic multi-turn was getting expensive (5–10× synthesis time). Reverted to one-shot, but retained reasoning traces via distillation. Final training format: chat-JSONL, assistant content = `<think>{reasoning}</think>\n\n<Slidev markdown with image-query placeholders>`. Teacher switched from GPT-5-mini → **GLM-5.1** (via OpenRouter, `z-ai/glm-5.1`) because GLM exposes raw reasoning traces in a separate `reasoning` field; OpenAI hides them. Image hallucination solved by model emitting `image-query:` natural-text placeholders resolved by a pre-Slidev-export preprocessor.
- **Hour 2.6** — SFT target switched from `-Base-BF16` (pretraining checkpoint) to **`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`** (post-trained). The post-trained variant has native `<think>` reasoning (default `enable_thinking=True`) — our training data format slots in directly. Baseline eval + finetuned eval both use the same model with SFT adapter as the only delta.
- **Current cleanup** — Simplified to one canonical script surface: `scripts.codex_pipeline.py` with `init`, `status`, and `pack`. Deprecated synthesis path removed. `PROMPT.md` is now authored by Codex as part of the sample, not precomputed by the pipeline.
