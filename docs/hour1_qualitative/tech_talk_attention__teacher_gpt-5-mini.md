---
theme: seriph
class: text-center
title: Attention Is All You Need — for Junior Engineers
mdc: true
layout: cover
---
Attention Is All You Need — for Junior Engineers

Speaker: Your Name · 10-minute tech talk

---

layout: section
---
Why attention? (motivation)
- RNNs process tokens one-by-one. Slow to train.
- Long-range dependencies are hard to learn.
- We wanted a way for every token to "see" every other token, quickly.
- Result: more parallelism and better gradients.

---

layout: image-right
image: https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200
---
Q / K / V — the intuition
- Query: the question you're asking now.
- Key: a label attached to each token.
- Value: the information stored at that token.
- Attention: match Query to Keys → get weights → mix Values.

---

layout: two-cols
---
Analogy: Librarian and cards
::right::
Step-by-step flow (visual)
- Librarian asks (Query).
- Cards have tags (Keys).
- Cards hold pages (Values).
- Matching tags → pick and combine pages.

---

layout: image-left
image: https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200
---
Multi-head attention — why multiple heads?
- Each head is a different "question" or viewpoint.
- Smaller subspaces focus on different patterns.
- Heads run in parallel, then combine results.
- Helps capture syntax, semantics, and position together.

---

layout: default
---
Why it beat RNNs (short)
- Full pairwise connections: tokens attend directly to each other.
- Massive parallelism during training.
- Easier gradient flow (non-sequential).
- Scales better with data and model size.

---

layout: section
---
How attention is computed (intuitive)
- Compute similarity between Query and each Key (dot product).
- Convert similarities to positive weights (softmax).
- Weighted sum of Values gives the attended output.
- Small detail: scale scores so softmax behaves nicely.

---

layout: quote
---
"Attention lets every token look at every other token." — Vaswani et al., summarized

---

layout: default
---
Practical code-level gotcha (one clear trap)
- Forgetting to apply masks:
  - Padding tokens must be masked, or the model will attend to useless pads.
  - For decoders, apply causal (triangular) mask to prevent peeking at future tokens.
- Quick fix checklist:
  - Build mask shaping to match attention score matrix.
  - Add large negative values before softmax where masked.
  - Verify shapes: (batch, heads, seq_q, seq_k) alignment.

---

layout: center
---
Takeaways & next steps
- Attention = Query vs Key → weight Values.
- Multi-heads = parallel viewpoints.
- Advantages: parallel, direct, scalable.
- Try: visualize attention maps on small inputs.
- Resources: "Attention Is All You Need" paper + transformer blogs.