<template>
  <section class="metric-card">
    <div class="histogram-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <h4 style="margin: 0;">Histogram danych</h4>
      <button
        type="button"
        class="toggle-bars-width-btn"
        @click="emit('toggle-thickness')"
        style="background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 2px; display: flex; align-items: center; justify-content: center; transition: color 0.2s;"
        :title="isThinner ? 'Zmień słupki na grubsze' : 'Zmień słupki na cieńsze'"
      >
        <svg v-if="!isThinner" viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <rect x="2" y="4" width="5" height="16" rx="1" />
          <rect x="9" y="4" width="5" height="16" rx="1" />
          <rect x="16" y="4" width="5" height="16" rx="1" />
        </svg>
        <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <rect x="2" y="4" width="2" height="16" rx="0.5" />
          <rect x="7" y="4" width="2" height="16" rx="0.5" />
          <rect x="12" y="4" width="2" height="16" rx="0.5" />
          <rect x="17" y="4" width="2" height="16" rx="0.5" />
          <rect x="22" y="4" width="2" height="16" rx="0.5" />
        </svg>
      </button>
    </div>
    <div class="histogram-wrap">
      <div
        ref="barsContainerRef"
        class="bars-container"
        :class="{ editable: isThresholdEditable }"
        @mousedown="startDrag"
      >
        <svg
          class="bars-svg"
          :viewBox="isThinner ? '0 0 480 100' : '0 0 240 100'"
          preserveAspectRatio="none"
        >
          <rect
            v-for="(h, idx) in histogramBins"
            :key="idx"
            :x="idx * 10 + 1"
            :y="100 - h"
            width="8"
            :height="h"
            rx="1"
          />
        </svg>
        <div
          v-if="ghostThresholdPercent !== null"
          class="threshold-line ghost-line"
          :style="{ left: `${ghostThresholdPercent}%` }"
          :title="`Ostatni próg: ${ghostThresholdValue}`"
        />
        <div
          v-if="thresholdPercent !== null"
          class="threshold-line"
          :style="{ left: `${thresholdPercent}%` }"
          :title="`Próg: ${thresholdValue}`"
        />
      </div>
    </div>
    <div
      class="histogram-x-labels-wrapper"
      style="position: relative;"
    >
      <!-- Reference absolute bounds, hidden if dynamic bounds overlap them -->
      <span v-if="minIntensity > 35" class="abs-bound left-bound">0</span>
      <span v-if="maxIntensity < 220" class="abs-bound right-bound">255</span>

      <!-- Dynamic labels container aligned with the bars -->
      <div class="histogram-x-labels">
        <span
          v-for="(lbl, idx) in xLabels"
          :key="idx"
          v-show="shouldShowLabel(idx)"
        >{{ lbl }}</span>
      </div>
    </div>
    <p class="histogram-note">{{ histogramNote }}</p>
  </section>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const props = defineProps({
  histogramBins: { type: Array, required: true },
  thresholdPercent: { type: Number, default: null },
  thresholdValue: { type: Number, default: null },
  ghostThresholdPercent: { type: Number, default: null },
  ghostThresholdValue: { type: Number, default: null },
  histogramNote: { type: String, default: '' },
  minIntensity: { type: Number, default: 0 },
  maxIntensity: { type: Number, default: 255 },
  isThinner: { type: Boolean, default: false },
  isThresholdEditable: { type: Boolean, default: false }
})

const emit = defineEmits(['update-threshold', 'toggle-thickness'])

const barsContainerRef = ref(null)
const isDraggingThreshold = ref(false)

function startDrag(e) {
  if (e.button !== 0 || !props.isThresholdEditable || props.thresholdPercent === null) return
  isDraggingThreshold.value = true
  updateThresholdFromEvent(e)
  window.addEventListener('mousemove', handleDrag)
  window.addEventListener('mouseup', stopDrag)
}

function handleDrag(e) {
  if (!isDraggingThreshold.value) return
  updateThresholdFromEvent(e)
}

function stopDrag(e) {
  if (isDraggingThreshold.value) {
    isDraggingThreshold.value = false
    window.removeEventListener('mousemove', handleDrag)
    window.removeEventListener('mouseup', stopDrag)
  }
}

function updateThresholdFromEvent(e) {
  if (!barsContainerRef.value) return
  const rect = barsContainerRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const pct = Math.max(0, Math.min(1, x / rect.width))
  const val = Math.round(props.minIntensity + pct * (props.maxIntensity - props.minIntensity))
  emit('update-threshold', val)
}

const leftOffsetPercent = computed(() => {
  return (props.minIntensity / 255) * 100
})

const widthPercent = computed(() => {
  return ((props.maxIntensity - props.minIntensity) / 255) * 100
})

const xLabels = computed(() => {
  const min = props.minIntensity
  const max = props.maxIntensity
  return [
    min,
    Math.round(min + (max - min) * 0.25),
    Math.round(min + (max - min) * 0.50),
    Math.round(min + (max - min) * 0.75),
    max
  ]
})

function shouldShowLabel(idx) {
  return true
}

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', handleDrag)
  window.removeEventListener('mouseup', stopDrag)
})
</script>

<style scoped>
.metric-card {
  border: 1px solid var(--outline);
  background: var(--surface-2);
  padding: 10px;
}

.metric-card h4 {
  margin: 0 0 8px;
  color: var(--text-muted);
  text-transform: uppercase;
  font: 700 10px/1 'Space Grotesk', sans-serif;
}

.histogram-wrap {
  position: relative;
  background: repeating-linear-gradient(
    45deg,
    rgba(0, 0, 0, 0.05),
    rgba(0, 0, 0, 0.05) 8px,
    rgba(0, 0, 0, 0.12) 8px,
    rgba(0, 0, 0, 0.12) 16px
  );
  border: 1px dashed var(--outline);
  border-radius: 4px;
  overflow: hidden;
  height: 128px;
  box-sizing: border-box;
}

:global(.theme-light) .histogram-wrap {
  background: repeating-linear-gradient(
    45deg,
    rgba(0, 0, 0, 0.02),
    rgba(0, 0, 0, 0.02) 8px,
    rgba(0, 0, 0, 0.06) 8px,
    rgba(0, 0, 0, 0.06) 16px
  );
}

:global(.theme-dark) .histogram-wrap {
  background: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.02),
    rgba(255, 255, 255, 0.02) 8px,
    rgba(0, 0, 0, 0.25) 8px,
    rgba(0, 0, 0, 0.25) 16px
  );
}

.bars-container {
  position: relative;
  height: 100%;
  background: var(--surface-3); /* Solid background to mask the striped wrap background */
  box-sizing: border-box;
  cursor: default;
}

.bars-container.editable {
  cursor: col-resize;
}

.bars-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.bars-svg rect {
  fill: color-mix(in srgb, var(--primary) 65%, transparent);
}

.threshold-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-1px);
  background: #ba1a1a;
  box-shadow: 0 0 4px #ba1a1a;
  pointer-events: none;
}

.threshold-line.ghost-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-1px);
  background: #7c3aed;
  box-shadow: 0 0 4px rgba(124, 58, 237, 0.3);
  pointer-events: none;
  opacity: 0.85;
}

:global(.stitch-dashboard.theme-dark) .threshold-line.ghost-line {
  box-shadow: 0 0 6px rgba(167, 139, 250, 0.5);
}

.histogram-x-labels-wrapper {
  margin-top: 6px;
  height: 12px;
  font: 500 10px/1.1 'Space Grotesk', sans-serif;
  color: var(--text-muted);
}

.abs-bound {
  position: absolute;
  top: 0;
  opacity: 0.4;
}

.left-bound {
  left: 0;
}

.right-bound {
  right: 0;
}

.histogram-x-labels {
  display: flex;
  justify-content: space-between;
  box-sizing: border-box;
}

.histogram-x-labels span {
  text-align: center;
  flex: 1;
}

.histogram-x-labels span:first-child {
  text-align: left;
}

.histogram-x-labels span:last-child {
  text-align: right;
}

.histogram-note {
  margin: 8px 0 0;
  color: var(--text-soft);
  font: 500 10px/1.4 'Space Grotesk', sans-serif;
}
</style>
