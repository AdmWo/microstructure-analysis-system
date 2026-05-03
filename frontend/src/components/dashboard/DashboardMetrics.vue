<template>
  <aside class="metrics-panel">
    <section class="metric-card">
      <h4>Histogram danych</h4>
      <div class="bars">
        <span v-for="(h, idx) in histogramBins" :key="idx" :style="{ height: `${h}%` }" />
      </div>
    </section>

    <section class="metric-card">
      <h4>Wyniki analizy</h4>
      <div class="metric-row">
        <span>A_A</span>
        <strong>{{ aaPercent !== null ? `${aaPercent.toFixed(2)}%` : 'brak danych' }}</strong>
      </div>
      <div class="metric-row">
        <span>V_V</span>
        <strong>{{ vvPercent !== null ? `${vvPercent.toFixed(2)}%` : 'brak danych' }}</strong>
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

    <section v-if="maskDataUrl" class="metric-card">
      <h4>Maska segmentacji</h4>
      <img :src="maskDataUrl" alt="Maska segmentacji" class="mask-image" />
    </section>

    <section class="metric-card status">
      <span class="dot" />
      {{ healthMessage }}
      <button type="button" class="retry-health" @click="emit('refresh-health')">Odswiez</button>
    </section>
  </aside>
</template>

<script setup>
const emit = defineEmits(['refresh-health'])

defineProps({
  histogramBins: { type: Array, required: true },
  metricCards: { type: Array, required: true },
  aaPercent: { type: Number, default: null },
  vvPercent: { type: Number, default: null },
  poreCount: { type: Number, default: null },
  maskDataUrl: { type: String, default: null },
  healthMessage: { type: String, required: true },
})
</script>