<template>
  <aside ref="panelRef" class="metrics-panel">
    <IntensityHistogram
      :histogram-bins="histogramBins"
      :threshold-percent="thresholdPercent"
      :threshold-value="thresholdValue"
      :ghost-threshold-percent="ghostThresholdPercent"
      :ghost-threshold-value="ghostThresholdValue"
      :histogram-note="histogramNote"
      :min-intensity="minIntensity"
      :max-intensity="maxIntensity"
      :is-thinner="isThinner"
      :is-threshold-editable="isThresholdEditable"
      @update-threshold="emit('update-threshold', $event)"
      @toggle-thickness="emit('toggle-thickness')"
    />

    <section class="metric-card">
      <h4>Wyniki analizy</h4>
      
      <!-- Grupa 1: Globalne szacunki -->
      <div class="metric-group">
        <h5 class="metric-group-title">Globalne szacunki</h5>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'aa')" @mouseleave="hideTooltip">Ułamek pow. (A_A)</span>
          <strong>{{ aaPercent !== null ? `${aaPercent.toFixed(2)}%` : 'brak danych' }}</strong>
        </div>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'count')" @mouseleave="hideTooltip">Liczba porów</span>
          <strong>{{ poreCount !== null ? poreCount : 'brak danych' }}</strong>
        </div>
        <template v-if="scaleEnabled && totalRoiAreaPhysical !== null">
          <div class="metric-row">
            <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'roi')" @mouseleave="hideTooltip">Obszar ROI</span>
            <strong>{{ `${totalRoiAreaPhysical.toFixed(2)} ${scaleUnit}²` }}</strong>
          </div>
          <div class="metric-row">
            <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'density')" @mouseleave="hideTooltip">Gęstość p. (N_A)</span>
            <strong>
              {{ poreDensityNA !== null ? poreDensityNA.toFixed(2) : '0.00' }}
              <small style="font-size: 0.75rem; font-weight: normal; opacity: 0.85; margin-left: 2px;">
                {{ scaleUnit === 'µm' ? 'p / 10⁴ µm²' : 'p / mm²' }}
              </small>
            </strong>
          </div>
        </template>
      </div>

      <!-- Grupa 2: Rozkład wielkości porów -->
      <div v-if="scaleEnabled" class="metric-group">
        <h5 class="metric-group-title">Rozkład wielkości porów</h5>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'poreArea')" @mouseleave="hideTooltip">Śr. obszar poru</span>
          <strong>{{ averagePoreAreaPhysical !== null ? `${averagePoreAreaPhysical.toFixed(2)} ${scaleUnit}²` : 'brak danych' }}</strong>
        </div>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'd1')" @mouseleave="hideTooltip">Średnica d_1 (obwód)</span>
          <strong>{{ avgD1CircularityPerimeter !== null ? `${avgD1CircularityPerimeter.toFixed(2)} ${scaleUnit}` : 'brak danych' }}</strong>
        </div>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'd2')" @mouseleave="hideTooltip">Średnica d_2 (pole)</span>
          <strong>{{ avgD2CircularityArea !== null ? `${avgD2CircularityArea.toFixed(2)} ${scaleUnit}` : 'brak danych' }}</strong>
        </div>
      </div>

      <!-- Grupa 3: Wskaźniki kształtu porów -->
      <div class="metric-group">
        <h5 class="metric-group-title">Wskaźniki kształtu porów</h5>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'edge')" @mouseleave="hideTooltip">Współczynnik brzegu</span>
          <strong>{{ avgEdgeIndicator !== null ? avgEdgeIndicator.toFixed(3) : 'brak danych' }}</strong>
        </div>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'roundness')" @mouseleave="hideTooltip">Okrągłość elipsy</span>
          <strong>{{ avgRoundnessEllipse !== null ? avgRoundnessEllipse.toFixed(3) : 'brak danych' }}</strong>
        </div>
        <div class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'malinowska')" @mouseleave="hideTooltip">Współczynnik Malinowskiej</span>
          <strong>{{ avgMalinowskaFactor !== null ? avgMalinowskaFactor.toFixed(3) : 'brak danych' }}</strong>
        </div>
        <div v-if="scaleEnabled" class="metric-row">
          <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'shape')" @mouseleave="hideTooltip">Wskaźnik kształtu</span>
          <strong>
            {{ avgShapeFactorRaw !== null ? avgShapeFactorRaw.toFixed(4) : 'brak danych' }}
            <small v-if="avgShapeFactorRaw !== null" style="font-size: 0.75rem; font-weight: normal; opacity: 0.85; margin-left: 2px;">
              {{ `1/${scaleUnit}` }}
            </small>
          </strong>
        </div>
      </div>
    </section>

    <section class="metric-card">
      <div v-for="metric in metricCards" :key="metric.label" class="metric-row">
        <span class="tooltip-trigger" @mouseenter="showTooltip($event, metric.key)" @mouseleave="hideTooltip">{{ metric.label }}</span>
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
          :disabled="!canSwap"
          style="background: var(--surface-3); border: 1px solid var(--outline); color: var(--text); font-size: 10px; padding: 4px 8px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 6px; transition: all 0.2s;"
          :style="isSwapped ? 'border-color: var(--primary); color: var(--primary); background: color-mix(in srgb, var(--primary) 10%, transparent);' : ''"
        >
          <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true" style="display: block;">
            <path d="M19 8l-4 4h3v6h-6v2h8V12h3L19 8zM5 16l4-4H6V6h6V4H4v8H1l4 4z" />
          </svg>
          Zamień
        </button>
      </div>
      <img
        :src="isSwapped ? roiCropDataUrl : maskDataUrl"
        :alt="isSwapped ? 'Wycięty obszar ROI' : 'Maska segmentacji'"
        class="mask-image"
        @click="canSwap && emit('toggle-swap')"
        :style="{ cursor: canSwap ? 'pointer' : 'not-allowed' }"
      />
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

  <!-- Custom Tooltip Popup -->
  <MetricTooltip
    :visible="tooltip.visible"
    :title="tooltip.title"
    :description="tooltip.description"
    :formula="tooltip.formula"
    :top="tooltip.top"
    :left="tooltip.left"
    @mouseenter="onTooltipMouseEnter"
    @mouseleave="onTooltipMouseLeave"
  />
</template>

<script setup>
import { ref, reactive } from 'vue'
import MetricTooltip from './MetricTooltip.vue'
import IntensityHistogram from './IntensityHistogram.vue'

const emit = defineEmits(['toggle-swap', 'download-mask', 'download-roi', 'update-threshold', 'toggle-thickness'])

defineProps({
  histogramBins: { type: Array, required: true },
  thresholdPercent: { type: Number, default: null },
  thresholdValue: { type: Number, default: null },
  ghostThresholdPercent: { type: Number, default: null },
  ghostThresholdValue: { type: Number, default: null },
  histogramNote: { type: String, default: '' },
  minIntensity: { type: Number, default: 0 },
  maxIntensity: { type: Number, default: 255 },
  isThinner: { type: Boolean, default: false },
  isThresholdEditable: { type: Boolean, default: false },
  metricCards: { type: Array, required: true },
  aaPercent: { type: Number, default: null },
  poreCount: { type: Number, default: null },
  maskDataUrl: { type: String, default: null },
  isSwapped: { type: Boolean, default: false },
  roiCropDataUrl: { type: String, default: null },
  canSwap: { type: Boolean, default: true },

  // Scale calibration props
  scaleEnabled: { type: Boolean, default: false },
  scaleUnit: { type: String, default: 'µm' },
  totalRoiAreaPhysical: { type: Number, default: null },
  averagePoreAreaPhysical: { type: Number, default: null },
  poreDensityNA: { type: Number, default: null },

  // Shape factors
  avgD1CircularityPerimeter: { type: Number, default: null },
  avgD2CircularityArea: { type: Number, default: null },
  avgEdgeIndicator: { type: Number, default: null },
  avgShapeFactorRaw: { type: Number, default: null },
  avgRoundnessEllipse: { type: Number, default: null },
  avgMalinowskaFactor: { type: Number, default: null },
})

const panelRef = ref(null)
const tooltip = reactive({
  visible: false,
  title: '',
  description: '',
  formula: '',
  top: 0,
  left: 0,
})

const TOOLTIP_TEXTS = {
  aa: {
    title: "Ułamek pow. (A_A)",
    description: "Ułamek powierzchniowy porów. Estymuje trójwymiarową porowatość objętościową V_V (zasada Delesse'a).",
    formula: "A_A = \\frac{\\text{Pole porów}}{\\text{Pole ROI}} \\times 100\\%"
  },
  count: {
    title: "Liczba porów",
    description: "Całkowita liczba odrębnych geometrycznie obiektów (porów) zidentyfikowanych w obszarze ROI.",
    formula: ""
  },
  roi: {
    title: "Obszar ROI",
    description: "Całkowita fizyczna powierzchnia zaznaczonego obszaru zainteresowania (ROI).",
    formula: "\\text{Obszar ROI} = N_{\\text{pikseli}} \\times \\left(\\frac{\\text{Skala}_{\\text{fizyczna}}}{\\text{Skala}_{\\text{pikselowa}}}\\right)^2"
  },
  density: {
    title: "Gęstość p. (N_A)",
    description: "Liczba porów przypadająca na znormalizowaną jednostkę powierzchni (10⁴ µm² lub 1 mm²).",
    formula: "N_A = \\frac{N_{\\text{porów}}}{A_{\\text{ROI}}}"
  },
  poreArea: {
    title: "Średni obszar poru",
    description: "Średnia fizyczna powierzchnia pojedynczego poru.",
    formula: "\\bar{A} = \\frac{\\sum A_i}{N_{\\text{porów}}}"
  },
  d1: {
    title: "Średnica d_1 (obwód)",
    description: "Średnica koła o obwodzie równym średniemu obwodowi porów.",
    formula: "d_1 = \\frac{L_{\\text{obwód}}}{\\pi}"
  },
  d2: {
    title: "Średnica d_2 (pole)",
    description: "Średnica koła o polu równym średniemu polu powierzchni porów.",
    formula: "d_2 = 2 \\times \\sqrt{\\frac{A}{\\pi}}"
  },
  edge: {
    title: "Współczynnik brzegu",
    description: "Wskaźnik rozwinięcia linii brzegu poru. Im bliższy 1.0, tym prostsza linia brzegu.",
    formula: "\\text{Współczynnik brzegu} = \\frac{L_{\\text{obwód}}}{2 \\times (w + h)}"
  },
  roundness: {
    title: "Okrągłość elipsy",
    description: "Stosunek małej osi do wielkiej osi elipsy minimalnej wpisanej w por (0.0 - 1.0). Im bliższy 1.0, tym kształt bardziej zbliżony do kołowego.",
    formula: ""
  },
  malinowska: {
    title: "Współczynnik Malinowskiej",
    description: "Miarą regularności i odchyłki kształtu poru od koła. Dla koła wynosi dokładnie 1.0.",
    formula: "W_{\\text{Malinowskiej}} = \\frac{2 \\times \\sqrt{\\pi \\times A}}{L_{\\text{obwód}}}"
  },
  shape: {
    title: "Wskaźnik kształtu",
    description: "Stosunek obwodu poru do jego pola powierzchni w jednostkach fizycznych.",
    formula: "f_{\\text{shape}} = \\frac{L_{\\text{obwód}}}{A}"
  },
  mean: {
    title: "Jasność średnia",
    description: "Średnia jasność pikseli w obszarze ROI w skali szarości (od 0 - czarny do 255 - biały). AU (Arbitrary Units) to jednostka umowna używana w analizie obrazu, gdzie jasność zależy od ustawień mikroskopu/kamery.",
    formula: "\\bar{I} = \\frac{1}{N} \\sum_{i=1}^{N} I_i"
  },
  stdDev: {
    title: "Odchylenie standardowe",
    description: "Miara zróżnicowania jasności pikseli w ROI (kontrastu lokalnego), wyrażona w jednostkach umownych AU. Niskie odchylenie oznacza jednolite tło, wysokie oznacza duże zróżnicowanie.",
    formula: "\\sigma = \\sqrt{\\frac{1}{N} \\sum_{i=1}^{N} (I_i - \\bar{I})^2}"
  },
  snr: {
    title: "Stosunek sygnał/szum (SNR)",
    description: "Stosunek średniej jasności do jej odchylenia standardowego w ROI, wyrażony w decybelach (dB). Określa jakość i czytelność obrazu metalograficznego. Wyższa wartość oznacza łatwiejszą i bardziej wiarygodną segmentację.",
    formula: "\\text{SNR}_{\\text{dB}} = 20 \\times \\log_{10}\\left(\\frac{\\bar{I}}{\\sigma}\\right)"
  }
}

let hideTimeoutId = null

function showTooltip(e, type) {
  if (hideTimeoutId) {
    clearTimeout(hideTimeoutId)
    hideTimeoutId = null
  }
  if (!panelRef.value) return
  const panelRect = panelRef.value.getBoundingClientRect()
  const spanRect = e.target.getBoundingClientRect()
  const data = TOOLTIP_TEXTS[type] || { title: '', description: '', formula: '' }

  tooltip.title = data.title
  tooltip.description = data.description
  tooltip.formula = data.formula
  tooltip.top = spanRect.top + spanRect.height / 2
  tooltip.left = panelRect.left - 12
  tooltip.visible = true
}

function hideTooltip() {
  hideTimeoutId = setTimeout(() => {
    tooltip.visible = false
  }, 250)
}

function onTooltipMouseEnter() {
  if (hideTimeoutId) {
    clearTimeout(hideTimeoutId)
    hideTimeoutId = null
  }
}

function onTooltipMouseLeave() {
  tooltip.visible = false
}
</script>