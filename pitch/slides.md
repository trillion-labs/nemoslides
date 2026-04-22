---
theme: default
colorSchema: dark
title: NemoSlides
info: NemoSlides — an open model specialized for slide generation.
transition: fade
mdc: true
drawings:
  persist: false
layout: center
class: text-center
---

<div class="text-xs font-mono opacity-60 mb-6">
  NVIDIA Nemotron Hackathon 2026 · Track B
</div>

# Nemo<span class="text-[#aaff4f]">Slides</span>

<div class="mt-4 text-2xl opacity-90">
  SOTA LLMs can't make slides.
</div>
<div class="text-2xl">
  <span class="text-[#aaff4f] font-semibold">This one can.</span>
</div>

<div class="mt-12 flex flex-col items-center gap-2">
  <QrCode value="https://nemoslides.up.railway.app" :size="200" />
  <div class="text-sm font-mono opacity-70 mt-2">scan → live demo</div>
  <div class="text-xs font-mono opacity-40">nemoslides.up.railway.app</div>
</div>

<div class="absolute bottom-6 right-8 text-xs opacity-55 font-mono">
  Trillion Labs
</div>

---
layout: center
class: px-16
---

# Frontier models can't ship a deck.

<div class="mt-8 grid grid-cols-2 gap-8 text-left">

<div>

### HTML route

<div class="text-xs font-mono opacity-50 mb-2">GPT, Claude, Gemini, …</div>

They emit `<div>` presentations.

- no `.pptx` / `.pdf` export
- locked to a browser tab
- no layout vocabulary, just CSS
- unshareable offline

</div>

<div>

### Image route

<div class="text-xs font-mono opacity-50 mb-2">Gamma, Nano-Banana, …</div>

Pixels in, pixels out.

- typos → redraw from scratch
- no structure, no reflow
- can't diff, can't version
- opaque to every tool downstream

</div>

</div>

<div class="mt-10 text-center text-[#aaff4f]">
  → nobody has SFT'd a model <em>for</em> slide generation
</div>

---
layout: center
class: px-16
---

# Slidev is the right training target.

<div class="mt-6 grid grid-cols-2 gap-8 items-start">

<div>

```md
---
layout: two-cols
transition: slide-left
---

# Why Slidev

- text DSL → trainable
- real exports (pptx, pdf, png)
- rich layout vocabulary
- editable forever
```

</div>

<div class="text-left space-y-4 pt-2">

<div>
  <div class="font-semibold">Text-native DSL</div>
  <div class="text-sm opacity-75">Markdown + YAML + Vue. Every token is trainable.</div>
</div>

<div>
  <div class="font-semibold">Real exports</div>
  <div class="text-sm opacity-75"><code>.pptx · .pdf · .png</code> — not "open this in a browser."</div>
</div>

<div>
  <div class="font-semibold">Full capability surface</div>
  <div class="text-sm opacity-75">Layouts, Shiki, Mermaid, KaTeX, <code>v-click</code>, themes.</div>
</div>

<div>
  <div class="font-semibold">Editable forever</div>
  <div class="text-sm opacity-75">Diff it, grep it, version it, hand-tweak it.</div>
</div>

</div>

</div>

---
layout: center
class: px-16
---

# The first open model<br/><span class="text-[#aaff4f]">SFT'd for slide generation.</span>

<div class="mt-10 grid grid-cols-4 gap-5 text-left">

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">base</div>
  <div class="text-2xl font-semibold leading-tight">Nemotron<br/>Nano 30B</div>
  <div class="mt-2 text-xs font-mono opacity-60">MoE · A3B · BF16</div>
</div>

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">data</div>
  <div class="text-2xl font-semibold leading-tight">705<br/>synthetic decks</div>
  <div class="mt-2 text-xs font-mono opacity-60">Slidev · Codex pipeline</div>
</div>

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">training</div>
  <div class="text-2xl font-semibold leading-tight">NeMo-RL<br/>SFT</div>
  <div class="mt-2 text-xs font-mono opacity-60">LoRA · FSDP2</div>
</div>

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">effort</div>
  <div class="text-2xl font-semibold leading-tight">2 days<br/>solo</div>
  <div class="mt-2 text-xs font-mono opacity-60">one practitioner</div>
</div>

</div>

<div class="mt-12 text-center opacity-85">
  No RL. No DPO. Just the right data and <code>run_sft.py</code>.
</div>

---
layout: center
class: px-8
---

# This is what our model produces.

<div class="text-center text-xs font-mono opacity-60 -mt-2 mb-4">
  one prompt → one deck → no human edits · cover, image-right, section, dark statement
</div>

<div class="grid grid-cols-4 gap-3">
  <img src="/showcase/ours_cover.png" class="w-full rounded border border-white/10 shadow-lg" />
  <img src="/showcase/ours_image1.png" class="w-full rounded border border-white/10 shadow-lg" />
  <img src="/showcase/ours_image2.png" class="w-full rounded border border-white/10 shadow-lg" />
  <img src="/showcase/ours_dark.png" class="w-full rounded border-2 border-[#aaff4f]/50 shadow-lg" />
</div>

<div class="mt-8 grid grid-cols-[1fr_auto_1.5fr] gap-6 items-center">

<div class="text-right">
  <div class="text-xs font-mono opacity-60 uppercase mb-1">base model · same prompt</div>
  <div class="text-xs opacity-60 italic">emits literal "Slide 1 – Title" placeholder</div>
</div>

<img src="/showcase/base_broken.png" class="w-48 rounded border border-[#ff6b6b]/40 opacity-75" />

<div class="text-left">
  <div class="text-sm font-semibold text-[#aaff4f]">+48% overall · same 30B weights</div>
  <div class="text-xs opacity-70">the gap is the dataset, not the parameter count</div>
</div>

</div>

---
layout: center
class: px-16
---

# On par with GPT-5.4. Ahead of 120B.

<div class="text-center text-sm opacity-80 -mt-2 mb-1">
  We built <span class="text-[#aaff4f] font-semibold">SlidevBench</span> — 30 prompts, rendered decks, a vision model judges each on content, design, coherence, and visual craft.
</div>
<div class="text-center text-xs font-mono opacity-55 mb-6">
  floor-scored · unrenderable = 1/5 across all dims
</div>

<div class="grid grid-cols-2 gap-10 items-center">

<div class="font-mono text-sm">

| model | render | overall |
|---|---:|---:|
| **nemoslides-30b** | 93% | **3.69** |
| gpt-5.4 | 100% | 3.62 |
| glm-5.1 | 100% | 3.26 |
| nemotron-super (120B) | 100% | 2.83 |
| nemotron-nano (base) | 87% | 2.50 |

</div>

<div class="space-y-5">

<div>
  <div class="text-5xl font-semibold text-[#aaff4f] leading-none">+48%</div>
  <div class="text-sm opacity-80 mt-1">overall lift from pure SFT (2.50 → 3.69)</div>
</div>

<div>
  <div class="text-5xl font-semibold text-[#aaff4f] leading-none">4 / 4</div>
  <div class="text-sm opacity-80 mt-1">dimensions where 30B SFT beats 120B base</div>
</div>

<div>
  <div class="text-5xl font-semibold text-[#aaff4f] leading-none">#1</div>
  <div class="text-sm opacity-80 mt-1">overall on SlidevBench</div>
</div>

</div>

</div>

---
layout: center
class: text-center
---

# Slide generation is<br/><span class="text-[#aaff4f]">a solved problem</span> —<br/>if you specialize.

<div class="mt-10 flex items-center justify-center gap-10">

<QrCode value="https://nemoslides.up.railway.app" :size="200" />

<div class="text-left">
  <div class="text-xl font-semibold">Try it now.</div>
  <div class="mt-1 text-sm font-mono opacity-70">nemoslides.up.railway.app</div>
  <div class="mt-4 text-sm font-mono opacity-65">github.com/trillion-labs/nemoslides</div>
  <div class="mt-1 text-sm font-mono opacity-65">hf.co/trillion-labs/nemoslides-30b-a3b</div>
</div>

</div>

<div class="mt-10 text-xs font-mono opacity-45">
  Nemotron Nano · NeMo-RL · 705 decks · 2 days
</div>
