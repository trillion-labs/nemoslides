# Eval comparison

Test set: 30 rows. Judge: `google/gemini-3-flash-preview` (vision).

**Rubric v5:** Content / Design / Coherence (judge) + Visual Craft (objective Slidev-feature scan). 1–5 each.
**Weighted Overall:** `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence`
**Render-fail accounting:** floor-scored = unrenderable rows count as 1 across all dims.

## Headline (floor-scored, ranked by weighted Overall)

| Model | Render | Content | Design | Coherence | VisCraft | **Overall** |
|---|---|---|---|---|---|---|
| `nano-local` | 93% | 4.03 | 3.53 | 4.00 | 3.50 | **3.69** |
| `gpt-5.4` | 100% | 4.27 | 3.17 | 4.07 | 3.40 | **3.62** |
| `glm-5.1` | 100% | 3.83 | 3.03 | 3.83 | 2.90 | **3.26** |
| `nemotron-super` | 100% | 4.13 | 2.63 | 3.73 | 1.97 | **2.83** |
| `nemotron-nano` | 87% | 3.50 | 2.30 | 3.37 | 1.80 | **2.50** |

## Mean over renderable only (ranked by weighted Overall)

| Model | Render | Content | Design | Coherence | VisCraft | **Overall** |
|---|---|---|---|---|---|---|
| `nano-local` | 93% | 4.37 | 3.81 | 4.33 | 3.78 | **3.99** |
| `gpt-5.4` | 100% | 4.27 | 3.17 | 4.07 | 3.40 | **3.62** |
| `glm-5.1` | 100% | 3.93 | 3.10 | 3.93 | 2.97 | **3.34** |
| `nemotron-super` | 100% | 4.13 | 2.63 | 3.73 | 1.97 | **2.83** |
| `nemotron-nano` | 87% | 3.88 | 2.50 | 3.73 | 1.92 | **2.73** |

## Model slugs

- `nano-local` → `nemotron-slide`
- `gpt-5.4` → `gpt-5.4`
- `glm-5.1` → `z-ai/glm-5.1`
- `nemotron-super` → `nvidia/nemotron-3-super-120b-a12b`
- `nemotron-nano` → `nvidia/nemotron-3-nano-30b-a3b`
