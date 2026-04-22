<script setup lang="ts">
import { useNav } from '@slidev/client'
import seedrandom from 'seedrandom'
import { computed, ref, watch } from 'vue'

const { currentSlideRoute } = useNav()

type Range = [number, number]
type Distribution = 'full' | 'top' | 'bottom' | 'left' | 'right' | 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center' | 'topmost'

const formatter = computed(() => (currentSlideRoute.value.meta?.slide as any)?.frontmatter || {})
const distribution = computed(() => (formatter.value.glow || 'full') as Distribution)
const opacity = computed<number>(() => +(formatter.value.glowOpacity ?? 0.4))
const hue = computed<number>(() => +(formatter.value.glowHue || 0))
const seed = computed<string>(() => (formatter.value.glowSeed === 'false' || formatter.value.glowSeed === false)
  ? Date.now().toString()
  : formatter.value.glowSeed || 'default',
)

const overflow = 0.3
const disturb = 0.3
const disturbChance = 0.3

function limits(d: Distribution) {
  const min = -0.2, max = 1.2
  let x: Range = [min, max], y: Range = [min, max]
  const isect = (a: Range, b: Range): Range => [Math.max(a[0], b[0]), Math.min(a[1], b[1])]
  for (const p of d.split('-')) {
    if (p === 'topmost') y = isect(y, [-0.5, 0])
    else if (p === 'top') y = isect(y, [min, 0.6])
    else if (p === 'bottom') y = isect(y, [0.4, max])
    else if (p === 'left') x = isect(x, [min, 0.6])
    else if (p === 'right') x = isect(x, [0.4, max])
    else if (p === 'center') { x = isect(x, [0.25, 0.75]); y = isect(y, [0.25, 0.75]) }
    else if (p === 'full') { x = isect(x, [0, 1]); y = isect(y, [0, 1]) }
  }
  return { x, y }
}

function d2([x1, y1]: Range, [x2, y2]: Range) { return (x2 - x1) ** 2 + (y2 - y1) ** 2 }

function usePoly(n = 16) {
  function gen(): Range[] {
    const L = limits(distribution.value)
    const rng = seedrandom(`${seed.value}-${currentSlideRoute.value.no}`)
    const between = ([a, b]: Range) => rng() * (b - a) + a
    const shake = (r: number) => {
      r = r * (1 + overflow * 2) - overflow
      return rng() < disturbChance ? r + (rng() - 0.5) * disturb : r
    }
    return Array.from({ length: n }, () => [shake(between(L.x)), shake(between(L.y))] as Range)
  }
  const pts = ref(gen())
  const poly = computed(() => pts.value.map(([x, y]) => `${x * 100}% ${y * 100}%`).join(', '))
  watch(currentSlideRoute, () => {
    const next = new Set(gen())
    pts.value = pts.value.map(o => {
      let best = Infinity, closest: Range | undefined
      for (const n of next) {
        const d = d2(o, n)
        if (d < best) { best = d; closest = n }
      }
      if (closest) next.delete(closest)
      return closest!
    })
  })
  return poly
}

const poly1 = usePoly(10)
const poly2 = usePoly(6)
const poly3 = usePoly(3)
</script>

<template>
  <div>
    <div
      class="bg transform-gpu overflow-hidden pointer-events-none"
      :style="{ filter: `blur(70px) hue-rotate(${hue}deg)` }"
      aria-hidden="true"
    >
      <div
        class="clip bg-gradient-to-r from-[#2b5d00] to-[#0a3300]"
        :style="{ 'clip-path': `polygon(${poly1})`, 'opacity': opacity }"
      />
      <div
        class="clip bg-gradient-to-l from-[#76b900] to-[#1e4400]"
        :style="{ 'clip-path': `polygon(${poly2})`, 'opacity': opacity * 0.8 }"
      />
      <div
        class="clip bg-gradient-to-t from-[#aaff4f] to-[#e0ffae]"
        :style="{ 'clip-path': `polygon(${poly3})`, 'opacity': 0.18 }"
      />
    </div>
  </div>
</template>

<style scoped>
.bg, .clip { transition: all 2.5s ease; }
.bg { position: absolute; inset: 0; z-index: -10; }
.clip { clip-path: circle(75%); aspect-ratio: 16 / 9; position: absolute; inset: 0; }
.light .clip { opacity: 1 !important; }
</style>
