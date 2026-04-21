# Workflow contract

Read these four files before writing:

1. `seed.json` — the structured source record behind the prompt
2. `INSTRUCTIONS.md` — this rulebook
3. `HERO_EXAMPLE.md` — the quality target for pacing, density, and visual intent
4. `PROMPT.md` — initially a stub; you replace it with the final user-side prompt

Then write exactly three files in the current folder:

1. `PROMPT.md`
2. `think.md`
3. `deck.md`

All required inputs are already in the current folder. Do not search sibling
seed folders, parent directories, or the wider repository for additional task context.

## `PROMPT.md` requirements

`PROMPT.md` is the user-side input for the training sample.

- Write a realistic user request that could plausibly produce this deck.
- Base it on `seed.json`, but make it read like an actual user prompt rather
  than a mechanical field dump.
- Keep it concise and natural.
- Do not mention chain-of-thought, training, or internal pipeline details.

## `think.md` requirements

`think.md` is the planning artifact. It should explain how the deck earns clarity,
not just summarize the request or source record. Use the required headings from `think_stub.md` and
write structured prose, not a bullet dump.

- Start from the final `PROMPT.md` as the canonical user request and refer to it directly.
- Restate the presentation goal, audience, and hidden constraints in your own words.
- Decide the narrative arc before writing slides.
- Explain the reasoning like a one-way script a novice could follow.
- Stay Slidev-aware: connect design intent to concrete authoring choices.
- Map the key slides, not every slide, unless more detail is truly necessary.
- Record rejected options when they were plausible.
- You may speculate about likely final visual appearance, balance, rhythm, and
  readability, but only as a prediction from the seed and plan.
- Do not describe render feedback, post-hoc fixes, or fake iteration history.
- End with a self-critique that catches overflow, repetition, weak transitions,
  generic bullets, and theme mismatch before you write `deck.md`.
- Keep the trace compact. Prefer compressed, information-dense paragraphs over
  long explanations that restate the same point.

## `deck.md` requirements

`deck.md` must be a complete, renderable Slidev deck with no extra commentary.

- The theme in the first slide frontmatter matches `seed.theme_hint` exactly.
- The first slide is the cover. Use a single top frontmatter block; do not emit a
  separate global YAML block and then another cover slide block.
- Every slide declares `layout:` from the allowed set.
- For every non-cover slide, start the frontmatter block with `layout:` as the
  first key. Keep the frontmatter block tight and parser-friendly.
- Slides are separated with `---` on its own line.
- Use `image-query:` for visuals. Do not use `image:` URLs anywhere.
- Respect `seed.n_slides_target` closely. Aim for the target; `±1` is preferred,
  `±2` is the outer limit.

## Narrative rules

Build a presentation, not a document dump.

- Start with a clean promise: what this deck is about and why the audience should care.
- Give the middle a shape: context, evidence, comparison, mechanism, implication.
- Land on a close that resolves the opening promise; do not just stop after the last fact.
- If `outline_hint` exists, treat it as the primary structure unless it would clearly
  create a bad deck. Preserve its order and intent when possible.
- Treat `feature_hints` as optional cues, not mandatory decorations. Use a feature only
  when it improves understanding.

## Visual composition rules

- One dominant idea per slide. If two ideas compete, split the slide or demote one.
- Alternate heavy and light slides so the deck breathes.
- Use `statement`, `fact`, `center`, or `section` slides to reset pacing between denser slides.
- Prefer short, concrete bullets over paragraphs.
- Use tables only when comparison across rows or columns matters. If a table is not being
  scanned, it should probably be bullets or a `fact` slide instead.
- Use Mermaid, code blocks, or math only when the topic truly needs them.
- Pick one or two hero moments in the deck where the visual treatment is intentionally stronger
  than the surrounding slides.
- If a heading or bullet will likely overrun at presentation scale, shorten it before writing.

## Layout heuristics

- `cover`: title, subtitle, optional one-line context only
- `section`: chapter break or act shift
- `statement` / `fact` / `center`: bold punctuation, key thesis, or headline result
- `two-cols`: compare, contrast, before/after, pros/cons, market vs product, treatment vs control
- `image-right` / `image-left`: image carries explanatory value and text can stay tight
- `image`: the visual itself is the point
- `default`: only when no more specific layout communicates better
- `end`: close, CTA, summary, or discussion prompt

## Image-query rules

Write image queries as art direction, not search-engine mush.

- Name the real subject, setting, and mood the slide needs.
- Prefer compositionally useful scenes over generic stock phrases.
- Match the deck topic: enterprise dashboards for enterprise decks, lab settings for research,
  infrastructure diagrams or server rooms for systems talks, not random smiling teams.
- Avoid text-in-image dependencies. The slide text should carry the wording.
