---
layout: cover
theme: seriph
class: text-center
title: Attention Is All You Need — for Junior Engineers
mdc: true
---
---

---
layout: default
---

# Motivation
- Process whole sequence at once  
- Enable massive parallelism  
- Learn direct relationships between tokens  

---  
layout: image-right
image: https://images.unsplash.com/photo-b5Z3iKwK9x0?w=1200
---

## Q / K / V Intuition
- **Q**: what we’re looking for  
- **K**: what we have to match against  
- **V**: the actual content we retrieve  
- Score = Q·Kᵀ → softmax → weighted V  

---  
layout: two-cols
---

::left::  
Multiple attention heads run **in parallel**  
Each head has its own Q/K/V vectors  

::right::  
Combine head outputs → richer context  
Different heads spot different patterns  

---  
layout: center
---

## Why It Beats RNNs
- All tokens processed **simultaneously** → faster training  
- Unlimited pairwise interactions → stronger representation  
- No long‑range sequential bottlenecks  
- Better handle long‑range dependencies  

---  
layout: quote
---

> **Code Gotcha:**  
> When fine‑tuning, **don’t** crank up the softmax temperature in attention; high temps make scores too uniform and can cause vanishing gradients.

---  
layout: image-left
image: https://images.unsplash.com/photo-9a0jQ9cK5bU?w=1200
---

## Visual Summary
- Arrows from Q → scores → weighted V  
- Multiple heads = multiple arrow streams  
- Result = single context vector per token  

---  
layout: center
---

## Takeaways
- Attention = “match + mix”  
- Multi‑head = multiple match‑mixes at once  
- Simple math ≈ huge lift over RNNs  

---  
layout: center
---

## Thank you!  
Questions?  
Explore: huggingface.co/transformers  

---