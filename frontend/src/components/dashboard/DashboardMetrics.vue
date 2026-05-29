<template>
  <aside class="metrics-panel">
    <section class="metric-card">
      <h4>Histogram danych</h4>
      <div class="histogram-wrap">
        <div class="bars">
          <span v-for="(h, idx) in histogramBins" :key="idx" :style="{ height: `${h}%` }" />
        </div>
        <div
          v-if="thresholdPercent !== null"
          class="threshold-line"
          :style="{ left: `${thresholdPercent}%` }"
          :title="`Prog: ${thresholdValue}`"
        />
      </div>
      <div class="histogram-x-labels">
        <span>0</span>
        <span>64</span>
        <span>128</span>
        <span>192</span>
        <span>255</span>
      </div>
      <p class="histogram-note">{{ histogramNote }}</p>
    </section>

    <section class="metric-card">
      <h4>Wyniki analizy</h4>
      <div class="metric-row">
        <span>A_A</span>
        <strong>{{ aaPercent !== null ? `${aaPercent.toFixed(2)}%` : 'brak danych' }}</strong>
      </div>
      <div class="metric-row">
        <span>Liczba porow</span>
        <strong>{{ poreCount !== null ? poreCount : 'brak danych' }}</strong>
      </div>
    </section>

    <section class="metric-card">
      <div v-for="metric in metricCards" :key="metric.label" class="metric-row">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
    </section>

    <section v-if="maskDataUrl" class="metric-card" style="margin-top: auto;">
      <div class="metric-card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <h4 style="margin: 0; font: 700 10px/1 'Space Grotesk', sans-serif;">
          {{ isSwapped ? 'Wycięty obszar (ROI)' : 'Maska segmentacji' }}
        </h4>
        <button
          type="button"
          class="swap-btn"
          @click="emit('toggle-swap')"
          style="background: var(--surface-3); border: 1px solid var(--outline); color: var(--text); font-size: 10px; padding: 4px 8px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 6px; transition: all 0.2s;"
          :style="isSwapped ? 'border-color: var(--primary); color: var(--primary); background: color-mix(in srgb, var(--primary) 10%, transparent);' : ''"
        >
          <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true" style="display: block;">
            <path d="M19 8l-4 4h3v6h-6v2h8V12h3L19 8zM5 16l4-4H6V6h6V4H4v8H1l4 4z" />
          </svg>
          Zamień
        </button>
      </div>
      <img :src="isSwapped ? roiCropDataUrl : maskDataUrl" :alt="isSwapped ? 'Wycięty obszar ROI' : 'Maska segmentacji'" class="mask-image" />
      <div style="margin-top: 8px; display: flex;">
        <button
          type="button"
          @click="emit('download-mask')"
          style="flex: 1; background: var(--primary); border: none; color: var(--primary-text); font-size: 11px; padding: 6px; cursor: pointer; border-radius: 4px; font-weight: 700; display: flex; align-items: center; justify-content: center; text-transform: uppercase; letter-spacing: 0.08em; font-family: 'Space Grotesk', sans-serif;"
        >
          Zapisz
        </button>
      </div>
    </section>

  </aside>
</template>

<script setup>
const emit = defineEmits(['toggle-swap', 'download-mask', 'download-roi'])

defineProps({
  histogramBins: { type: Array, required: true },
  thresholdPercent: { type: Number, default: null },
  thresholdValue: { type: Number, default: null },
  histogramNote: { type: String, default: '' },
  metricCards: { type: Array, required: true },
  aaPercent: { type: Number, default: null },
  poreCount: { type: Number, default: null },
  maskDataUrl: { type: String, default: null },
  isSwapped: { type: Boolean, default: false },
  roiCropDataUrl: { type: String, default: null },
})
</script>