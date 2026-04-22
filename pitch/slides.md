---
theme: default
colorSchema: dark
title: NemoSlides
info: NemoSlides — an open model specialized for slide generation.
transition: fade
mdc: true
routerMode: hash
drawings:
  persist: false
layout: center
class: text-center
---

<div class="text-6xl font-semibold tracking-tight">
  Slides are <span class="text-[#aaff4f]">NeMo</span>.
</div>
<div class="mt-6 text-lg italic opacity-70">
  NeMo means 'rectangle' in Korean.
</div>

<div class="mt-16 text-base font-mono opacity-80">
  Juyoung · Wonsuk · Hyungguk · Hongjoon
</div>

---
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
  <img src="/qr-demo.png" class="w-50 h-50" />
  <div class="text-sm font-mono opacity-70 mt-2">scan → live demo</div>
  <div class="text-xs font-mono opacity-40">nemoslides-production.up.railway.app</div>
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

<div class="mt-10 grid grid-cols-3 gap-5 text-left">

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">base</div>
  <div class="text-2xl font-semibold leading-tight">Nemotron<br/>Nano 30B</div>
  <div class="mt-2 text-xs font-mono opacity-60">MoE · A3B · BF16</div>
</div>

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">data</div>
  <div class="text-2xl font-semibold leading-tight">705<br/>synthetic decks</div>
  <div class="mt-2 text-xs font-mono opacity-60">NeMo Data Designer</div>
</div>

<div>
  <div class="text-xs font-mono opacity-50 uppercase mb-1">training</div>
  <div class="text-2xl font-semibold leading-tight">NeMo Automodel<br/>SFT</div>
  <div class="mt-2 text-xs font-mono opacity-60">FSDP2</div>
</div>

</div>

<div class="mt-12 text-center opacity-85">
  No RL. No DPO. Just the right data and training on the Nemotron stack.
</div>

<div class="mt-6 flex flex-col items-center gap-1.5 text-sm font-mono">
  <a href="https://huggingface.co/datasets/trillionlabs/NemoSlides-SFT-mix-v1.0" target="_blank" class="flex items-center gap-2 opacity-75 hover:opacity-100 hover:text-[#aaff4f] no-underline">
    <logos-hugging-face-icon /> Dataset: trillionlabs/NemoSlides-SFT-mix-v1.0
  </a>
  <a href="https://huggingface.co/trillionlabs/NemoSlides" target="_blank" class="flex items-center gap-2 opacity-75 hover:opacity-100 hover:text-[#aaff4f] no-underline">
    <logos-hugging-face-icon /> Model: trillionlabs/NemoSlides
  </a>
</div>

---
layout: center
class: px-6
---

# Same prompt. Same 30B weights.

<div class="text-center text-xs font-mono opacity-60 -mt-2 mb-5">
  one Slidev prompt → both models → rendered as-is, no edits
</div>

<div class="grid grid-cols-[auto_1fr] gap-4 items-center">

<div class="text-right pr-2">
  <div class="text-[11px] font-mono uppercase opacity-55 leading-tight">base</div>
  <div class="text-xs opacity-60 leading-tight mt-0.5">nemotron-nano 30B</div>
</div>

<div class="grid grid-cols-4 gap-3">
  <img src="/showcase/base_cover.png" class="w-full rounded border border-[#ff6b6b]/30 opacity-65" />
  <img src="/showcase/base_image1.png" class="w-full rounded border border-white/10 opacity-65" />
  <img src="/showcase/base_image2.png" class="w-full rounded border border-white/10 opacity-65" />
  <img src="/showcase/base_dark.png" class="w-full rounded border border-white/10 opacity-65" />
</div>

<div class="text-right pr-2">
  <div class="text-[11px] font-mono uppercase text-[#aaff4f] leading-tight">ours</div>
  <div class="text-xs opacity-80 leading-tight mt-0.5">nemoslides-30b-a3b</div>
</div>

<div class="grid grid-cols-4 gap-3">
  <div class="flow-border"><img src="/showcase/ours_cover.png" /></div>
  <div class="flow-border"><img src="/showcase/ours_image1.png" /></div>
  <div class="flow-border"><img src="/showcase/ours_image2.png" /></div>
  <div class="flow-border"><img src="/showcase/ours_dark.png" /></div>
</div>

</div>

<div class="mt-6 text-center text-sm opacity-85">
  base leaks <span class="font-mono text-[#ff6b6b]/80">frontmatter as body text</span>, produces wall-of-bullets.
  <span class="text-[#aaff4f]">the gap is the dataset, not the parameter count.</span>
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

<table class="w-full border-collapse">
  <thead>
    <tr class="opacity-60 text-xs uppercase">
      <th class="text-left font-normal pb-2">model</th>
      <th class="text-right font-normal pb-2">render</th>
      <th class="text-right font-normal pb-2">overall</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="py-1.5 px-2 flow-row-cell font-semibold rounded-l">nemoslides-30b</td>
      <td class="py-1.5 px-2 flow-row-cell text-right">93%</td>
      <td class="py-1.5 px-2 flow-row-cell text-right font-semibold rounded-r">3.69</td>
    </tr>
    <tr>
      <td class="py-1.5 px-2">nemotron-nano (base)</td>
      <td class="py-1.5 px-2 text-right">87%</td>
      <td class="py-1.5 px-2 text-right">2.50</td>
    </tr>
    <tr>
      <td class="py-1.5 px-2">nemotron-super (120B)</td>
      <td class="py-1.5 px-2 text-right">100%</td>
      <td class="py-1.5 px-2 text-right">2.83</td>
    </tr>
    <tr>
      <td class="py-1.5 px-2">gpt-5.4</td>
      <td class="py-1.5 px-2 text-right">100%</td>
      <td class="py-1.5 px-2 text-right">3.62</td>
    </tr>
    <tr>
      <td class="py-1.5 px-2">glm-5.1</td>
      <td class="py-1.5 px-2 text-right">100%</td>
      <td class="py-1.5 px-2 text-right">3.26</td>
    </tr>
  </tbody>
</table>

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
class: px-16
---

# Room for improvement.

<div class="mt-10 grid grid-cols-3 gap-8 text-left">

<div>

<div class="text-xs font-mono opacity-50 uppercase mb-2">next · 1</div>

### DPO data pipeline

<div class="text-sm opacity-80 mt-2">

571 preference pairs from SlidesGen-Bench rankings, images shared across both sides so only presentation quality varies. Gemini 3.1 Flash Lite writes deep `<think>` for chosen, hurried for rejected.

</div>

</div>

<div>

<div class="text-xs font-mono opacity-50 uppercase mb-2">next · 2</div>

### Apply DPO

<div class="text-sm opacity-80 mt-2">

Close the failure modes the judge already catches — overflow, cramped layouts, broken KaTeX — without training a reward model.

</div>

</div>

<div>

<div class="text-xs font-mono opacity-50 uppercase mb-2">next · 3</div>

### RLVR

<div class="text-sm opacity-80 mt-2">

Verifiable rewards straight from the renderer + VLM judge:

- <span class="font-mono">renderable?</span> — binary, zero-cost
- <span class="font-mono">overlap?</span> — VLM checks the screenshot
- rubric dims → VLM-as-judge dense reward

</div>

</div>

</div>

---
layout: center
class: px-16
---

# Everything is open.

<div class="text-center text-sm opacity-70 -mt-2 mb-8">
  model · dataset · code · gallery · demo — all public, all reproducible
</div>

<div class="grid grid-cols-5 gap-6 justify-items-center">

<div class="flex flex-col items-center gap-2">
  <img src="/qr-demo.png" class="w-32 h-32" />
  <div class="text-xs font-mono uppercase opacity-55 mt-1">demo</div>
  <div class="text-[10px] font-mono opacity-45 break-all text-center max-w-[140px]">nemoslides-production<wbr/>.up.railway.app</div>
</div>

<div class="flex flex-col items-center gap-2">
  <img src="/qr-gallery.png" class="w-32 h-32" />
  <div class="text-xs font-mono uppercase opacity-55 mt-1">gallery</div>
  <div class="text-[10px] font-mono opacity-45 break-all text-center max-w-[140px]">trillion-labs.github.io<wbr/>/nemoslides/gallery</div>
</div>

<div class="flex flex-col items-center gap-2">
  <img src="/qr-hf-model.png" class="w-32 h-32" />
  <div class="text-xs font-mono uppercase opacity-55 mt-1">hf · model</div>
  <div class="text-[10px] font-mono opacity-45 break-all text-center max-w-[140px]">hf.co/trillionlabs<wbr/>/NemoSlides</div>
</div>

<div class="flex flex-col items-center gap-2">
  <img src="/qr-hf-dataset.png" class="w-32 h-32" />
  <div class="text-xs font-mono uppercase opacity-55 mt-1">hf · dataset</div>
  <div class="text-[10px] font-mono opacity-45 break-all text-center max-w-[140px]">hf.co/datasets/trillionlabs<wbr/>/NemoSlides-SFT-mix-v1.0</div>
</div>

<div class="flex flex-col items-center gap-2">
  <img src="/qr-github.png" class="w-32 h-32" />
  <div class="text-xs font-mono uppercase opacity-55 mt-1">github</div>
  <div class="text-[10px] font-mono opacity-45 break-all text-center max-w-[140px]">github.com/trillion-labs<wbr/>/nemoslides</div>
</div>

</div>

---
layout: center
class: text-center
---

# Slide generation is<br/><span class="text-[#aaff4f]">a solved problem</span> —<br/>if you specialize.

<div class="mt-10 flex items-center justify-center gap-10">

<img src="/qr-github.png" class="w-50 h-50" />

<div class="text-left">
  <div class="text-xl font-semibold">See the code.</div>
  <div class="mt-1 text-sm font-mono opacity-70">github.com/trillion-labs/nemoslides</div>
  <div class="mt-4 text-sm font-mono opacity-65">hf.co/trillionlabs/NemoSlides</div>
  <div class="mt-1 text-sm font-mono opacity-65">nemoslides-production.up.railway.app</div>
</div>

</div>

<div class="mt-10 text-xs font-mono opacity-45">
  Nemotron Nano · NeMo Automodel · 705 decks · 2 days
</div>
