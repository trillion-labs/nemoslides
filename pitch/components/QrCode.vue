<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import QRCode from 'qrcode'

const props = withDefaults(defineProps<{
  value: string
  size?: number
  dark?: string
  light?: string
}>(), {
  size: 220,
  dark: '#ffffff',
  light: '#00000000',
})

const svg = ref('')

watchEffect(async () => {
  svg.value = await QRCode.toString(props.value, {
    type: 'svg',
    margin: 0,
    errorCorrectionLevel: 'M',
    color: { dark: props.dark, light: props.light },
  })
})
</script>

<template>
  <div
    class="qr-frame"
    :style="{ width: `${size}px`, height: `${size}px` }"
    v-html="svg"
  />
</template>

<style scoped>
.qr-frame {
  padding: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(170, 255, 79, 0.35);
  border-radius: 14px;
  box-shadow: 0 0 60px rgba(118, 185, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
}
.qr-frame :deep(svg) {
  width: 100%;
  height: 100%;
}
</style>
