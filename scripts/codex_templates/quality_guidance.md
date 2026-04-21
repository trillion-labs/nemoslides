## Quality bar (read before writing)

Look at `HERO_EXAMPLE.md` — that is the quality target. Notes:

- **Density.** Each content slide has ≤ 5 bullets, each bullet ≤ 12 words.
  A 1920×1080 slide cannot comfortably hold more — overflow makes the deck
  useless. Prefer fewer, punchier bullets over comprehensive ones.
- **Syntax robustness.** Fragile Slidev markdown is a hard failure. Avoid blank
  lines inside frontmatter blocks, do not invent components, and keep non-cover
  slide frontmatter predictable.
- **Cover slide.** Title + short subtitle + (optional) one-line footer —
  nothing else. Use the cover layout.
- **Variety.** Mix layouts across the deck. A deck that is 8 `default`
  slides in a row is a failure. Use `two-cols` for comparison, `image-right`
  for content + visual, `statement`/`fact` for punctuation, `center` for
  focal messages, `section` for act shifts, `end` for the close.
- **Specificity.** Every bullet names a concrete thing — a number, a product
  name, a technique, a metric. Generic phrases ("scalable", "innovative",
  "leveraging synergies") are forbidden.
- **Coherence.** Each slide must earn its place in the arc. Remove any slide
  that repeats a point without escalating it, clarifying it, or reframing it.
- **Rhythm.** Sequence slides so visual weight changes over time: do not stack
  multiple dense default/table slides without a lighter punctuation slide.
- **Image quality.** Images should clarify tone, domain, or mechanism. Generic
  corporate stock, vague "innovation" imagery, and decorative filler weaken the deck.
- **Feature restraint.** Mermaid, code, math, tables, and v-clicks are tools,
  not trophies. If a feature does not make the slide easier to understand, omit it.
- **Reasoning style.** `think.md` should sound like pre-generation design
  reasoning, not a render critique or a post-hoc explanation after the deck exists.
- **Reasoning density.** `think.md` should be concise by default. Cut repetition,
  avoid narrating obvious facts twice, and focus on decisions that actually improve the deck.
- **Close with intent.** The last slide should feel like a conclusion, decision,
  or invitation, not just "questions?" unless the seed clearly implies that style.
- **Speaker notes.** Use `<!-- ... -->` at the end of a slide ONLY when it
  actually adds value (1–2 decks per 10 slides, max).
