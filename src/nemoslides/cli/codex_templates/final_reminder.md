## Reminder — the final check

- `deck.md` contains only the Slidev markdown (no `<think>` tag inside it,
  no surrounding code fences, no prose before or after).
- `think.md` contains only the reasoning trace (no YAML, no Slidev content).
  Length is concise but substantial, structured under the required headings, and
  refers to the user prompt rather than treating the seed as the only surface.
- Theme used in `deck.md` matches the seed's `theme_hint` exactly.
- Every `layout:` value is in the allowed-layouts whitelist.
- No literal `image: https://...` URLs. Use `image-query:` only.
- The first slide is the actual cover slide, not a metadata-only pre-slide.
- Every non-cover slide starts its frontmatter block with `layout:`.
- The deck stays close to `n_slides_target` and does not feel padded.
- No slide is obviously overcrowded, generic, or redundant.
- The final slide feels intentional and resolves the deck's promise.
- `think.md` never claims render feedback, post-hoc fixes, or visual inspection that
  the student model would not actually have.
