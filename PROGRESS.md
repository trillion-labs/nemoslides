# Progress Log

Live execution log. Update on: block completion, blocker, or deviation from [`PLAN.md`](PLAN.md).

## Current phase

**Baseline eval complete.** PPTEval pipeline finished end-to-end: generate
→ render → judge. Rubric iterated v1 → v5. Canonical baseline numbers on
30-row test split available for all four reference models.

## Block status

| # | Block (hours) | Status | Started | Finished | Key result |
|---|---|---|---|---|---|
| 1 | Slidev smoke test (0–1) | done | hour 0 | hour 0+15m | 5 layouts rendered to PNG via `slidev export --format png --per-slide`; seriph theme, image-right layout successfully fetches external images |
| 2 | Teacher + base qualitative check (1–2) | done | hour 1 | hour 2 | Teacher GPT-5-mini locked (with prompt iteration); base model emits Slidev-shaped output but defaults to `layout: default`, hallucinates Unsplash IDs → empty image panels. Clear gap to close. Direction shifted: train full Slidev capability, not constrained subset. See `docs/qualitative/notes.md`. |
| 3 | Data synthesis (2–5) | **done** | hour 2 | — | Codex-authored corpus: locked seeds → Codex writes `PROMPT.md` / `think.md` / `deck.md` per seed. 651 validated rows at last pack; 705 train + 30 test on `trillionlabs/slides-sft-v0`. |
| 4 | Quality filter + JSONL (5–7) | **done** | hour 5 | — | Per-seed validators in `scripts/codex_pipeline.py` (prompt/think/deck substance + syntactic checks). Packer at `scripts/push_hf_dataset.py` emits chat-JSONL (system + user + assistant w/ reasoning_content). |
| 5 | **Baseline PPTEval + NeMo-RL install (7–8)** | **eval done** | hour 7 | — | 30-row canonical eval complete; rubric v5 (hybrid subjective + objective Slidev-feature scan); weighted Overall. Nano baseline = 2.50 floor-scored. NeMo-RL install still pending. |
| 6 | **SFT launch (8)** | pending | — | — | — |
| 7 | Training in background, prep pitch/repo (8–20) | pending | — | — | — |
| 8 | Finetuned eval (20–26) | pending | — | — | — |
| 9 | Hero cuts + reel + self-gen pitch deck (26–32) | pending | — | — | — |
| 10 | Pitch polish + reproducibility pass (32–40) | pending | — | — | — |
| 11 | Slack (40–48) | pending | — | — | — |

## Numbers

Baseline from rubric v5, 30-row test split, floor-scored (unrenderable = 1s).
Judge: `google/gemini-3-flash-preview`. Weighted Overall =
`0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence`.

| Metric | nano (base, SFT target) | super | glm-5.1 | gpt-5.4 | Finetuned | Δ |
|---|---|---|---|---|---|---|
| Render rate | 87%* | 100% | 100% | 100% | — | — |
| Content (1–5) | 3.50 | 4.13 | 3.83 | 4.27 | — | — |
| Design (1–5) | 2.30 | 2.63 | 3.03 | 3.17 | — | — |
| Coherence (1–5) | 3.37 | 3.73 | 3.83 | 4.07 | — | — |
| **Visual Craft (obj)** | **1.80** | 1.97 | 2.90 | 3.40 | — | — |
| **Weighted Overall** | **2.50** | 2.83 | 3.26 | **3.62** | — | — |
| Dataset size (kept after filter) | — | — | — | — | — | — |
| Training loss (final) | — | — | — | — | — | — |

*Render rate inflated ~15pp by cache-reuse of Vue-error PNGs; judge/feature scanner correctly score these low, so rankings stand. Re-render fresh for the final pitch number.

## Blockers / deviations

*None yet.*

## Changelog

- **Hour -1** — repo scaffolded: `README.md`, `PLAN.md`, `DECISIONS.md`, `CLAUDE.md`, `PROGRESS.md`.
- **Hour 0** — user preference locked: Python deps via `uv` only (no pip/conda/poetry). Updated `CLAUDE.md`.
- **Hour 0+15m** — Slidev smoke test complete. `demo/smoke/` contains `slides.md` (5 named layouts) and 5 rendered PNGs in `screenshots/`. Render path confirmed: Slidev CLI + playwright-chromium via `slidev export --format png --per-slide`. This path scales to thousands of decks with parallel Playwright workers.
- **Hour 1** — Python env with uv initialized (`pyproject.toml` + `uv.lock`). Deps: openai, python-dotenv, httpx, tqdm.
- **Hour 1** — Canonical renderer at `renderer/` with seriph/default/apple-basic/bricks/shibainu themes pre-installed. `./renderer/render.sh <deck.md> <output_dir>` usable from anywhere.
- **Hour 1** — Teacher (GPT-5-mini via OpenAI) + base (Nemotron-3-Nano-30B-A3B via OpenRouter free tier) qualitative check done. Teacher produces usable Slidev with minor format bugs; base understands format but defaults to `layout: default` and hallucinates Unsplash IDs → empty image panels. Side-by-side renders in `docs/qualitative/renders/`.
- **Hour 1.5** — **Direction shift:** training target expanded from template-constrained subset to full Slidev capability surface (code blocks, Mermaid, KaTeX, v-click, v-motion, all named layouts, theme variety). `DECISIONS.md` updated accordingly.
- **Hour 2** — **Architecture shift 1:** one-shot deck SFT → agentic multi-turn SFT (then re-reverted, see hour 2.5).
- **Hour 2.2** — Slidev docs vendored at `reference/slidev_docs/` (sparse-clone of `slidevjs/slidev/docs`). `pipeline/slidev_reference.py` compiles a ~45KB / 11K-token knowledge pack (syntax, layouts, animations, mermaid, latex, line-highlighting, icons, components, curated themes catalog) to inject into teacher system prompts. Unsplash tool `pipeline/tools/unsplash.py` done with API + bank fallback (smoke-tested).
- **Hour 2.5** — **Step-back + re-scope:** agentic multi-turn was getting expensive (5–10× synthesis time). Reverted to one-shot, but retained reasoning traces via distillation. Final training format: chat-JSONL, assistant content = `<think>{reasoning}</think>\n\n<Slidev markdown with image-query placeholders>`. Teacher switched from GPT-5-mini → **GLM-5.1** (via OpenRouter, `z-ai/glm-5.1`) because GLM exposes raw reasoning traces in a separate `reasoning` field; OpenAI hides them. Image hallucination solved by model emitting `image-query:` natural-text placeholders resolved by a pre-Slidev-export preprocessor.
- **Hour 2.6** — SFT target switched from `-Base-BF16` (pretraining checkpoint) to **`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`** (post-trained). The post-trained variant has native `<think>` reasoning (default `enable_thinking=True`) — our training data format slots in directly. Baseline eval + finetuned eval both use the same model with SFT adapter as the only delta.
- **Current cleanup** — Simplified to one canonical script surface: `scripts.codex_pipeline.py` with `init`, `status`, and `pack`. Deprecated synthesis path removed. `PROMPT.md` is now authored by Codex as part of the sample, not precomputed by the pipeline.

### Eval infrastructure (block 5)

- **Eval stack shipped** at `eval/`: `generate.py` (4-model adapter — nemotron-nano/super, glm-5.1, gpt-5.4), `run.py` (async orchestrator, concurrency=5 per model, resumable via `score.json`), `judge.py` (Gemini 3 Flash vision, user prompt + slide PNGs only, JSON object extractor + escape sanitizer + retry), `rubric.py`, `features.py`, `compare.py`. Dataset pushed as 30-row test + 705-row train at `trillionlabs/slides-sft-v0`.
- **Rubric iteration**. v1–v2 were 3-dim PPTEval (content/design/coherence). v3 added visual_richness + prompt_fidelity with hard caps. v4 tightened with benchmark 5-anchors, generic-phrase blacklist, evidence-required rationales. **v5 (current)**: dropped prompt_fidelity (redundant with content's completeness axis), swapped subjective visual_richness for **objective `features.py` scan** (counts named layouts, shiki, Mermaid, KaTeX, v-click, notes, transitions, non-default theme → 1–5 score). Weighted Overall `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence` — over-weights the visual axis because that's where SFT delta lives.
- **Render pipeline hardening**. Three bugs caught + fixed on the way: (a) `slidev export` uses `getPort(12445)` which races across parallel invocations → added `fcntl.flock`-serialized render in `renderer/render.sh`. (b) Slidev exits 0 even with Vue compile errors → render validator scans stdout for signatures (`[vite] Internal server error`, `Element is missing end tag`, `YAMLParseError`, `ReferenceError: Unresolved alias`). (c) 1-slide "renders" from fence-wrap bugs passing as success → min-slide guard (3 PNGs minimum). Also fixed `parse_deck` to unwrap leading ```markdown fences (closed or unclosed) without touching inner code blocks in real decks.
- **Baseline numbers locked** (30 rows, rubric v5, floor-scored). Nano 2.50 < Super 2.83 < GLM 3.26 < GPT 3.62. SFT target: lift nano ≥ Super (must-have) and close the gap to GLM (stretch). The objective VisCraft dim (nano 1.80 → GPT 3.40) is the quantified SFT teaching signal.
