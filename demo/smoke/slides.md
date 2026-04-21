---
theme: seriph
title: Slidev Smoke Test
info: Smoke test covering five named layouts — cover, two-cols, image-right, quote, center.
class: text-center
highlighter: shiki
transition: slide-left
mdc: true
---

# slides-sft smoke test

Validating the Slidev render pipeline across five layouts

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer">
    Nemotron Hackathon 2026 · Track B
  </span>
</div>

---
layout: two-cols
---

# Why this project exists

- Slide generation is a core LLM skill
- Open-source data is scarce and low-aesthetic
- Small open-weight models lag closed slide-gen tools

::right::

# What we are shipping

- A PPTEval-filtered synthetic Slidev dataset
- A Nemotron-3-Nano SFT recipe on NeMo-RL
- A side-by-side base vs finetuned gallery

---
layout: image-right
image: https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200
---

# The pipeline

1. Seed prompts across three domains
2. Teacher model authors Slidev markdown
3. VLM judge filters on PPTEval rubric
4. LoRA SFT on Nemotron-3-Nano-30B-A3B
5. Identical-protocol eval vs baseline

---
layout: quote
---

## "Gamma, but open weights, runs on your laptop, and we're shipping the dataset too."

— the pitch

---
layout: center
class: text-center
---

# Ready to generate

The smoke test renders. Every downstream step rests on this pipeline.
