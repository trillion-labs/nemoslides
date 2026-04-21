# Codex Synthesis Task — Slidev Training Deck

You are generating ONE training example for a slide-generation SFT corpus.
Read `seed.json` in the current directory. Produce three files in the same
directory:

1. **`PROMPT.md`** — the final user-side request for this training sample.
   This should read like a realistic user prompt, not internal metadata.

2. **`think.md`** — a concise, standalone, one-way authoring script.
   This file is the primary training signal — the student model will learn
   its slide-authoring strategy from what is written here. Quality bar:

   - **Standalone.** A reader who never saw the seed must be able to understand
     the design intent and all constraints purely from `think.md`.
   - **Design-teaching oriented.** Write as if you are explaining your decisions
     to a novice slide author who must reproduce the same quality in one shot.
     The trace should make the deck generation plausible and understandable.
   - **Forward-looking.** Explain choices before the deck exists. Anticipate how
     slides will likely look and read, but do not write as if you already saw a
     render or repaired the deck after visual feedback.
   - **Slidev-aware.** Name concrete Slidev choices when they matter:
     layout selection, tables vs bullets, `image-right` vs `two-cols`,
     `fact` vs `default`, `v-clicks`, and similar implementation decisions.
   - **Structured prose**, not a flat bullet list. Use short headings like
     `## Reading the user prompt`, `## Theme fit`, `## Narrative arc`,
     `## Key slide mapping`, `## Image & feature choices`, `## Self-review`.
     Under each heading, write in clear, deliberate paragraphs (3–8 sentences
     per section is typical). Short inline bullets are fine where they help;
     pure bullet-dumps are not acceptable.
   - **Length.** Keep it dense and useful. A typical good trace is 350–900
     words. Longer is acceptable only when each section adds concrete design
     value rather than restating the deck.
   - **Self-review section is mandatory.** Before writing `deck.md`, critique
     your own plan in `think.md`: Where might a slide overflow? Which bullet
     is generic and needs replacement? Does the arc actually land for this
     audience? Fix the plan before writing the deck. This is anticipatory review,
     not post-render commentary.

3. **`deck.md`** — a complete, renderable Slidev markdown deck that follows
   ALL the rules below AND executes the plan from `think.md`.

Do **not** write any other files. Do **not** modify `seed.json`,
`INSTRUCTIONS.md`, or `HERO_EXAMPLE.md`.

All required files are already in the current directory. Do not scan sibling
seed folders or parent directories for more task context.

When all three files are present and substantive (not stubs), the folder is done.

The deck quality bar is not "technically valid Slidev." The bar is a deck a real
person would willingly present: visually intentional, easy to scan, theme-faithful,
and narratively coherent from first slide to close.
