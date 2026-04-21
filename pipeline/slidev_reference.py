"""Curated Slidev references injected into synthesis prompts.

Two string exports:

- `TASK_INSTRUCTIONS`  —  short, always-on constraints: output format, the
  `<think>` reasoning tag, the `image-query:` convention, theme/layout
  whitelists. Included in 100% of teacher calls.

- `SLIDEV_CHEATSHEET`  —  a compact Slidev feature reference (layouts, code
  highlighting, Mermaid, KaTeX, v-click, icons, images). Included in ~20% of
  teacher calls so the student learns to generate good Slidev both with and
  without explicit reference context — a form of prompt dropout.

The old ~45KB doc-concatenation pack is replaced by this curated version.
Larger packs made every call expensive and produced student models that
over-relied on always having the reference in context.
"""

from __future__ import annotations

from textwrap import dedent

ALLOWED_LAYOUTS: list[str] = [
    "cover",
    "default",
    "center",
    "section",
    "statement",
    "fact",
    "intro",
    "end",
    "two-cols",
    "image-right",
    "image-left",
    "image",
    "quote",
    "full",
]

ALLOWED_THEMES: list[str] = [
    # official
    "default",
    "seriph",
    "apple-basic",
    # community (professional)
    "geist",
    "academic",
    "the-unnamed",
    "nord",
    "penguin",
    "dracula",
    "frankfurt",
    "scholarly",
    "takahashi",
]


TASK_INSTRUCTIONS: str = dedent(
    r"""
    # Task — generate a Slidev deck with a reasoning trace

    You will be given a slide-deck seed (domain, topic, audience, style, theme hint,
    feature hints, target slide count, optionally outline_hint). Produce:

    1. A concise, **standalone**, one-way reasoning trace inside
       `<think>...</think>`. This is the primary training signal — the student
       model learns its slide-authoring strategy from this trace. It must:
         - anchor itself to the user prompt/request, not just the structured seed,
         - stand on its own (a reader who never saw the seed should understand
           the design intent and constraints from the trace alone),
         - explain decisions the way you would teach a novice slide author,
         - think forward from the seed and planned deck, not backward from an
           already-rendered result,
         - cover: interpretation of the seed, theme-choice rationale, overall
           narrative arc and why that arc fits the audience, key-slide mapping
           with layout + image + feature decisions and their reasoning, visual
           predictions that are inferable before rendering, tradeoffs considered
           and rejected, and a final self-review pass,
         - stay Slidev-aware: mention concrete layouts or features when they
           materially affect execution or readability,
         - never claim render feedback, post-hoc repair, or visual inspection
           that would only be available after generation,
         - use structured prose with short headings where helpful
           (`## Reading the user prompt`, `## Narrative arc`, `## Key slide mapping`,
           `## Self-review`) — not a flat bullet list.
         - stay compact and information-dense; avoid repeating obvious facts or
           restating the deck without adding reasoning value.

    2. A complete, renderable Slidev deck in markdown, RIGHT AFTER the `</think>` tag.

    ## Hard output rules (non-negotiable)

    ### 1. Single top frontmatter = first slide = cover
    The FIRST slide IS the cover slide. Put all global settings (theme, title,
    mdc, class, layout) in its frontmatter. DO NOT create an empty standalone
    global-frontmatter block followed by a separate `---` cover slide.

    Correct:
    ```
    ---
    theme: bricks
    title: FarmStack — Series A
    class: text-center
    layout: cover
    mdc: true
    image-query: "aerial view of midwest farmland at golden hour"
    ---

    # FarmStack

    ### Predictive Yields. Precise Fertilizer.

    ---
    layout: two-cols
    ---
    ...
    ```

    WRONG (empty first slide, do NOT do this):
    ```
    ---
    theme: bricks
    title: ...
    mdc: true
    ---

    ---
    layout: cover
    ---
    # FarmStack
    ```

    ### 2. Layouts & themes
    - Allowed layouts: LAYOUTS_LIST
    - Allowed themes: THEMES_LIST
    - Every slide declares `layout:` from the allowed list.
    - For every non-cover slide, the slide frontmatter block starts with `layout:`.

    ### 3. Slide separators
    Slides separated by `---` on its own line. Per-slide frontmatter is a YAML block
    `---\n<yaml>\n---` at the top of the slide, with NO blank lines inside the block.

    ### 4. Images — query placeholders, never URLs
    Use `image-query:` with a natural-language description, not `image:` with a URL.
    A render-time preprocessor resolves queries to real Unsplash/Pexels URLs.
    Example: `image-query: "diverse engineering team collaborating at laptops"`.
    Applies to `layout: image-right | image-left | image`, cover background images,
    and any inline references. NO literal URLs anywhere.

    ### 5. Mermaid — code fence, NOT a Vue component
    Correct:
    ````
    ```mermaid
    graph LR
      A[Ingest] --> B[Transform] --> C[Load]
    ```
    ````
    WRONG (do NOT emit these):
    - `<Mermaid chart={...} />`  — this is not a Slidev component
    - `<mermaid>...</mermaid>`
    Only the fenced ` ```mermaid ` code-block form works.

    ### 6. KaTeX math
    Inline: `$e^{i\pi} = -1$`. Block: `$$ ... $$` on its own lines.

    ### 7. v-click progressive reveal
    Use `<v-click>...</v-click>` or `<v-clicks>\n- bullet\n- bullet\n</v-clicks>`.
    Do not invent other tag names.

    ### 8. Length, fences, scope
    - Respect the seed's `n_slides_target` (±2 slide is fine).
    - No surrounding markdown code fences around the entire deck output.
    - Output ONLY `<think>...</think>` followed by the deck markdown.
    """
).strip().replace(
    "LAYOUTS_LIST", ", ".join(f"`{x}`" for x in ALLOWED_LAYOUTS)
).replace(
    "THEMES_LIST", ", ".join(f"`{x}`" for x in ALLOWED_THEMES)
)


SLIDEV_CHEATSHEET: str = dedent(
    r"""
    # Slidev cheat sheet (optional context)

    Reference this only if useful. The examples are authoritative — follow the exact
    syntax shown. When a feature isn't covered here, rely on what you already know.

    ## Deck skeleton

    ```md
    ---
    theme: seriph
    title: Smart Cities Briefing
    class: text-center
    mdc: true
    layout: cover
    ---

    # Title

    Subtitle

    ---
    layout: two-cols
    ---

    # Left column heading

    Left content

    ::right::

    # Right column heading

    Right content

    ---
    layout: image-right
    image-query: "satellite view of a dense city at night"
    ---

    # Slide title

    Bullet content on the left, image fills the right.
    ```

    ## Layouts — when to use which

    | layout | purpose | required / key frontmatter |
    |---|---|---|
    | `cover` | opening title slide | `class: text-center` |
    | `default` | generic content slide | — |
    | `center` | center-align a focal message | — |
    | `section` | section divider inside a deck | — |
    | `statement` | single bold statement | — |
    | `fact` | one large number or fact | — |
    | `intro` | presenter / team intro | — |
    | `end` | closing slide | — |
    | `two-cols` | two columns; use `::right::` divider | — |
    | `image-right` | content left, image right | `image-query:` |
    | `image-left` | content right, image left | `image-query:` |
    | `image` | image occupies the full slide | `image-query:` |
    | `quote` | pull-quote | — |
    | `full` | full-bleed custom content | — |

    ## Themes — vibe and fit

    | theme | best for | vibe |
    |---|---|---|
    | `default` | generic business/tech updates | neutral, minimal blue |
    | `seriph` | editorial, long-form keynotes, essays | elegant serif |
    | `apple-basic` | consumer launches, crisp pitches | Apple-keynote minimalism |
    | `geist` | startup pitches, dev-tool launches, SaaS | Vercel-clean, monospace accents |
    | `academic` | research talks, conference papers, lectures | formal serif, figure-heavy |
    | `the-unnamed` | dev talks, engineering deep-dives | VS Code dark, purple accents |
    | `nord` | dev talks, infra/systems topics | cool blue-gray Nord palette |
    | `penguin` | Vue/JS ecosystem, product demos | warm, modern, gradient accents |
    | `dracula` | dev talks, dark-mode presentations | classic dark, high contrast |
    | `frankfurt` | academic/formal talks, Beamer feel | navy + cream, structured |
    | `scholarly` | research talks (oxford/cambridge/princeton styles) | traditional academic |
    | `takahashi` | minimalist talks, single-idea slides | oversized type, high impact |

    ## Code blocks with line highlighting

    Default highlighting on specific lines:

    ````md
    ```ts {2,3}
    function add(a: Ref<number> | number, b: Ref<number> | number) {
      return computed(() => unref(a) + unref(b))
    }
    ```
    ````

    Stepped highlighting across clicks (`|` separates stages):

    ````md
    ```ts {2-3|5|all}
    // line 1
    const x = 1
    const y = 2
    // line 4
    const z = x + y
    ```
    ````

    ## Mermaid diagrams

    ````md
    ```mermaid
    graph LR
      A[Ingest] --> B[Transform] --> C[Load]
    ```
    ````

    Supports `graph`, `flowchart`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `gantt`, `pie`, `stateDiagram-v2`, `journey`, `mindmap`.

    ## Math (KaTeX)

    Inline: `$e^{i\pi} + 1 = 0$`

    Block:
    ```md
    $$
    \mathrm{Attention}(Q, K, V) = \mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V
    $$
    ```

    ## Progressive reveal (v-click)

    ```md
    <v-click>Appears on first click</v-click>

    <div v-click>Appears on next click</div>

    <v-clicks>

    - Each bullet
    - Appears
    - One click at a time

    </v-clicks>

    <v-after>Shows with the previous v-click</v-after>
    ```

    Hide after clicking: `<v-click hide>disappears next click</v-click>` or `v-click.hide` directive.

    ## Icons (Iconify)

    Inline as components, hyphenated collection-name:

    ```md
    <mdi-rocket-launch class="text-4xl text-blue-500" />
    <logos-typescript-icon class="text-2xl" />
    <carbon-ai class="text-3xl" />
    ```

    Common collections: `mdi` (Material Design), `carbon` (IBM Carbon), `logos` (brand logos), `tabler`, `ph` (Phosphor), `heroicons`, `twemoji`.

    ## Transitions

    Per-slide, in frontmatter:

    ```yaml
    ---
    transition: slide-left
    ---
    ```

    Options: `slide-left`, `slide-right`, `slide-up`, `slide-down`, `fade`, `fade-out`, `view-transition`.

    ## Presenter notes

    HTML comment at the END of a slide:

    ```md
    # Slide content

    - Bullet

    <!-- Speak for ~30s here; emphasize the RL-fine-tuning angle. -->
    ```

    ## Block frontmatter directive

    You can place YAML after content too, via a fenced HTML comment:

    ```md
    # Slide

    ---
    layout: image-right
    image-query: "abstract data streams"
    ---
    ```

    (Prefer the standard per-slide frontmatter at the top.)
    """
).strip()


if __name__ == "__main__":
    # usage check
    import sys

    print(f"TASK_INSTRUCTIONS  : {len(TASK_INSTRUCTIONS):,} chars / ~{len(TASK_INSTRUCTIONS) // 4:,} tok")
    print(f"SLIDEV_CHEATSHEET  : {len(SLIDEV_CHEATSHEET):,} chars / ~{len(SLIDEV_CHEATSHEET) // 4:,} tok")
    if "--dump" in sys.argv:
        print()
        print("=== TASK_INSTRUCTIONS ===")
        print(TASK_INSTRUCTIONS)
        print()
        print("=== SLIDEV_CHEATSHEET ===")
        print(SLIDEV_CHEATSHEET)
