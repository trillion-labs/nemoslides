# NemoSlides · Talk Script (English)

5-minute pitch. Roughly 15–55s per slide. Conversational, not read aloud.
Say numbers and product names only when they carry weight; unpack the rest
in plain English.

---

## Slide 1 · Opener wordplay (~15s)

> Quick note on the name before we start.
>
> In Korean, a slide — a rectangle — is called "ne-mo". So "slides are NeMo"
> is a pun we couldn't resist. NVIDIA NeMo, and the Korean word for the
> shape of a slide.
>
> That is the whole idea of the project in one line. Let's get into it.

**Tone:** Fast. Land the pun, move on. Don't explain it twice.

---

## Slide 2 · Hook + QR (~25s)

> We're Trillion Labs.
>
> We built a model that does one thing well: it makes slides.
>
> The QR on screen opens a live demo. Feel free to scan it and try it
> yourself while I talk.

**Tone:** Short hello, one-line claim, hand them the QR. Don't linger.

---

## Slide 3 · Problem (~40s)

> Ask a frontier LLM to "make me slides" today, and you get one of two
> answers.
>
> The first is **HTML**. It looks fine in a browser tab, but there's no
> pptx, no pdf, no real layout vocabulary — just divs and CSS. You can't
> ship that to anyone.
>
> The second is **images**. This is what Gamma and Nano-Banana do. Pixels
> in, pixels out. Fix a typo, redraw the whole slide.
>
> So here's the gap: **nobody has actually fine-tuned a model for slide
> generation.** Everyone's been routing around the problem.

**Tone:** Two branches, fast. Don't dive into details. End on the gap.

---

## Slide 4 · Why Slidev (~35s)

> We picked **Slidev** as the training target. Slidev is a markdown-based
> slide framework.
>
> Four reasons. It's **text-native** — every token is trainable. It exports
> to **real pptx, pdf, png**, not "open this in a browser." It has the
> **full expressive surface** a real presentation needs — layouts, code
> highlighting, Mermaid, math, animations. And a human can **hand-edit**
> any slide after the fact.
>
> It's the most learnable format for the slide-generation problem.

**Tone:** Four beats, quick. Breath between each, then the summary line.

---

## Slide 5 · What we built (~25s)

> What we built is the **first open model fine-tuned for slide generation**.
>
> Base is NVIDIA's Nemotron Nano 30B. 705 synthetic decks as training data,
> NeMo Automodel for SFT.
>
> Two days, one person. No RL, no DPO — pure SFT on the Nemotron stack.

**Tone:** Weight on "first open model." Ships the rest fast. Light stress on
"two days."

---

## Slide 6 · Aesthetic proof (~55s)

> These are slides our model actually produces. **Same prompt, single
> generation, no human edits.**
>
> You can see a cover slide, an image-right layout, and a dark statement
> slide — layouts mix inside one deck. This is presentation-ready output.
>
> Below are the same prompts fed into the **base model**. The first slide
> leaks YAML frontmatter as body text. The rest are walls of bullets.
>
> **Same 30B weights on both sides.** The gap is the dataset and the
> training — not the parameter count.

**Tone:** Let the image do the work. Talk minimally. Last line is the one
that has to land.

---

## Slide 7 · SlidevBench + numbers (~50s)

> To evaluate this honestly, we built **SlidevBench**. Thirty prompts.
> Each model generates a Slidev deck, we render it, and a vision model
> scores it on content, design, coherence, and visual craft.
>
> The result: our model is **on par with GPT-5.4** — slightly ahead,
> actually — and clearly ahead of Nemotron Super 120B.
>
> Three numbers to remember. **48% lift over the base**. **Four out of
> four dimensions** where our 30B beats the 120B base. **Number one
> overall** on SlidevBench.

**Tone:** Pre-empt "why compare to GPT" by explaining the benchmark first.
Then the numbers.

---

## Slide 8 · Room for improvement (~25s)

> We're not done.
>
> Next, a **DPO pipeline** from SlidesGen-Bench rankings — preference pairs
> where only presentation quality varies. Then we **apply DPO** to close
> the failure modes the judge already catches: overflow, cramped layouts,
> broken KaTeX. Longer term, **RLVR** with the renderer and the VLM judge
> as verifiable reward signals.

**Tone:** Honest about limits. Fast. Signposting, not a detour.

---

## Slide 9 · Everything is open (~15s)

> Everything is public and reproducible. Live demo, gallery of outputs,
> the model on Hugging Face, the dataset on Hugging Face, and the full
> code on GitHub. Five QR codes, one per resource.

**Tone:** Gesture at the wall of QRs. Don't read the URLs out loud.

---

## Slide 10 · Close (~15s)

> To wrap up: **slide generation is a solved problem, if you specialize
> the model for it.**
>
> Thank you.

**Tone:** One line to close. Let the QR do the last bit of work.

---

## Timing

| Slide | Topic | Target | Cumulative |
|---|---|---:|---:|
| 1 | Opener wordplay | 0:15 | 0:15 |
| 2 | Hook + QR | 0:25 | 0:40 |
| 3 | Problem | 0:40 | 1:20 |
| 4 | Why Slidev | 0:35 | 1:55 |
| 5 | What we built | 0:25 | 2:20 |
| 6 | Aesthetic proof | 0:55 | 3:15 |
| 7 | SlidevBench + numbers | 0:50 | 4:05 |
| 8 | Room for improvement | 0:25 | 4:30 |
| 9 | Everything is open | 0:15 | 4:45 |
| 10 | Close | 0:15 | 5:00 |

**On budget.** If you're running hot, compress slide 3 to two sentences, or
drop the image-right callout on slide 6 and just point at the panel.

## Safety notes

- Numbers to not fumble: **48%**, **4/4**, **#1**, **30 prompts**,
  **705 decks**, **30B**, **2 days**.
- Acronyms — SFT, DPO, RLVR, LoRA, FSDP — are fine for a hackathon judge
  audience. For a general audience, say "fine-tuned" instead of "SFT'd".
- On slide 1, don't over-explain the pun. Either it lands or it doesn't;
  moving on fast is the right call either way.
- On slide 9, don't read the URLs. The QRs are the point; the room scans
  what they want.
