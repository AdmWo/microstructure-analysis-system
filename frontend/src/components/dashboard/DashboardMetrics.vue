<template>
  <aside ref="panelRef" class="metrics-panel" @mouseleave="handleMouseLeavePanel">
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
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--outline); padding-bottom: 8px;">
        <h4 style="margin: 0; font: 700 12px/1 'Space Grotesk', sans-serif;">Wyniki analizy</h4>
        <div v-if="imagesCount > 1" class="metric-toggle-group" style="display: flex; gap: 4px;">
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: showAverages }"
            @click="emit('toggle-display-mode', true)"
            style="font-size: 9px; padding: 3px 6px; cursor: pointer; border-radius: 4px; border: 1px solid var(--outline); background: var(--surface-3); color: var(--text);"
          >
            Średnie
          </button>
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: !showAverages }"
            @click="emit('toggle-display-mode', false)"
            style="font-size: 9px; padding: 3px 6px; cursor: pointer; border-radius: 4px; border: 1px solid var(--outline); background: var(--surface-3); color: var(--text);"
          >
            Bieżący
          </button>
        </div>
      </div>
      
      <!-- Grupa 1: Globalne szacunki -->
      <div class="metric-group">
        <h5 class="metric-group-title" @click="toggleGroup('global')" style="cursor: pointer; display: flex; align-items: center; gap: 4px; user-select: none;">
          Globalne szacunki
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: collapsedGroups.global ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </h5>
        <div v-show="!collapsedGroups.global">
          <div class="metric-row">
            <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'aa')" @mouseleave="hideTooltip">Ułamek pow. (A_A)</span>
            <strong>{{ aaPercent !== null ? `${aaPercent.toFixed(2)}%` : 'brak danych' }}</strong>
          </div>
          <div class="metric-row">
            <span class="tooltip-trigger" @mouseenter="showTooltip($event, 'count')" @mouseleave="hideTooltip">Liczba porów</span>
            <strong>{{ poreCount !== null ? (Number.isInteger(poreCount) ? poreCount : poreCount.toFixed(1)) : 'brak danych' }}</strong>
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
      </div>
 
      <!-- Grupa 2: Rozkład wielkości porów -->
      <div v-if="scaleEnabled" class="metric-group">
        <h5 class="metric-group-title" @click="toggleGroup('poreSize')" style="cursor: pointer; display: flex; align-items: center; gap: 4px; user-select: none;">
          Rozkład wielkości porów
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: collapsedGroups.poreSize ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </h5>
        <div v-show="!collapsedGroups.poreSize">
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
      </div>
 
      <!-- Grupa 3: Wskaźniki kształtu porów -->
      <div class="metric-group">
        <h5 class="metric-group-title" @click="toggleGroup('shapeFactors')" style="cursor: pointer; display: flex; align-items: center; gap: 4px; user-select: none;">
          Wskaźniki kształtu porów
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: collapsedGroups.shapeFactors ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </h5>
        <div v-show="!collapsedGroups.shapeFactors">
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
      </div>

      <!-- Grupa 4: Jasność i jakość obrazu -->
      <div class="metric-group">
        <h5 class="metric-group-title" @click="toggleGroup('brightness')" style="cursor: pointer; display: flex; align-items: center; gap: 4px; user-select: none;">
          Jasność i jakość obrazu
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: collapsedGroups.brightness ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </h5>
        <div v-show="!collapsedGroups.brightness">
          <div v-for="metric in metricCards" :key="metric.label" class="metric-row">
            <span class="tooltip-trigger" @mouseenter="showTooltip($event, metric.key)" @mouseleave="hideTooltip">{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
      </div>
    </section>

 
    <div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px;">
      <!-- Performance Statistics -->
      <section v-if="totalExecutionTimeMs !== null" class="metric-card performance-card" style="border-color: color-mix(in srgb, var(--primary) 30%, var(--outline)); padding: 8px 10px; border-radius: 4px; margin-top: 0;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 10.5px; font-family: 'Space Grotesk', sans-serif; color: var(--text-soft); font-weight: 500;">
          <span v-if="inferenceTimeMs !== null && inferenceTimeMs > 0" style="color: #2f76ba; font-weight: 600; display: flex; align-items: center; gap: 3.5px;">
            Inference: {{ inferenceTimeMs.toFixed(0) }} ms
          </span>
          <span v-if="inferenceTimeMs !== null && inferenceTimeMs > 0" style="opacity: 0.3; color: var(--text-muted);">|</span>
          <span style="display: flex; align-items: center; gap: 3.5px; color: #28af4d; font-weight: 600;">
            Total API: {{ totalExecutionTimeMs.toFixed(0) }} ms
          </span>
        </div>
        
        <!-- Detailed Breakdown -->
        <details v-if="tPreprocessMs || tSegmentMs || tMorphologyMs || tStereologyMs || tEncodingMs" style="margin-top: 6px; border-top: 1px dashed var(--outline); padding-top: 4px; font-family: 'Space Grotesk', sans-serif; font-size: 9px; color: var(--text-soft);">
          <summary style="cursor: pointer; text-align: center; list-style: none; outline: none; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); display: flex; align-items: center; justify-content: center; gap: 2px;">
            Rozwiń szczegóły czasu
            <svg viewBox="0 0 24 24" width="8" height="8" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="display: inline-block;">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </summary>
          <div style="display: grid; gap: 4px; margin-top: 6px; padding: 2px 4px; border-radius: 4px; background: var(--surface-3);">
            <div v-if="tPreprocessMs" style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-soft);">Preprocessing & Denoise:</span>
              <strong style="color: var(--text);">{{ tPreprocessMs.toFixed(1) }} ms</strong>
            </div>
            <div v-if="tSegmentMs" style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-soft);">Segmentation / Binarization:</span>
              <strong style="color: var(--text);">{{ tSegmentMs.toFixed(1) }} ms</strong>
            </div>
            <div v-if="tMorphologyMs" style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-soft);">Morphological Cleanup:</span>
              <strong style="color: var(--text);">{{ tMorphologyMs.toFixed(1) }} ms</strong>
            </div>
            <div v-if="tStereologyMs" style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-soft);">Stereology Metrics:</span>
              <strong style="color: var(--text);">{{ tStereologyMs.toFixed(1) }} ms</strong>
            </div>
            <div v-if="tEncodingMs" style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-soft);">Base64 Encoding & API:</span>
              <strong style="color: var(--text);">{{ tEncodingMs.toFixed(1) }} ms</strong>
            </div>
          </div>
        </details>
      </section>

      <!-- Maska segmentacji -->
      <section v-if="maskDataUrl" class="metric-card" style="margin-top: 0;">
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
    </div>



  </aside>
 
  <!-- Custom Tooltip Popup -->
  <MetricTooltip
    ref="submenuRef"
    :visible="tooltip.visible"
    :title="tooltip.title"
    :description="tooltip.description"
    :formula="tooltip.formula"
    :top="tooltip.top"
    :left="tooltip.left"
    @mouseenter="onTooltipMouseEnter"
    @mouseleave="onTooltipMouseLeave"
  />

  <!-- Prediction Cone SVG Debug Overlay for Thesis Screenshots -->
  <teleport to="body">
    <svg
      v-if="debugConeActive && trianglePoints"
      style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 9999;"
    >
      <!-- Draw Cone Polygon -->
      <polygon
        :points="`${trianglePoints.a.x},${trianglePoints.a.y} ${trianglePoints.b.x},${trianglePoints.b.y} ${trianglePoints.c.x},${trianglePoints.c.y}`"
        fill="rgba(0, 209, 255, 0.12)"
        stroke="rgba(0, 209, 255, 0.55)"
        stroke-width="1.5"
        stroke-dasharray="4 3"
      />
      <!-- Draw Vertices -->
      <circle :cx="trianglePoints.a.x" :cy="trianglePoints.a.y" r="4.5" fill="#00d1ff" stroke="#ffffff" stroke-width="1" />
      <circle :cx="trianglePoints.b.x" :cy="trianglePoints.b.y" r="4.5" fill="#00d1ff" stroke="#ffffff" stroke-width="1" />
      <circle :cx="trianglePoints.c.x" :cy="trianglePoints.c.y" r="4.5" fill="#00d1ff" stroke="#ffffff" stroke-width="1" />
    </svg>
  </teleport>
</template>
 
<script setup>
import { ref, reactive } from 'vue'
import MetricTooltip from './MetricTooltip.vue'
import IntensityHistogram from './IntensityHistogram.vue'
import { useMenuAim } from '../../composables/useMenuAim'
 
const emit = defineEmits(['toggle-swap', 'download-mask', 'download-roi', 'update-threshold', 'toggle-thickness', 'toggle-display-mode'])
 
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

  // Multiple images props
  imagesCount: { type: Number, default: 1 },
  showAverages: { type: Boolean, default: true },

  // Performance props
  inferenceTimeMs: { type: Number, default: null },
  totalExecutionTimeMs: { type: Number, default: null },
  tPreprocessMs: { type: Number, default: null },
  tSegmentMs: { type: Number, default: null },
  tMorphologyMs: { type: Number, default: null },
  tStereologyMs: { type: Number, default: null },
  tEncodingMs: { type: Number, default: null },
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

const collapsedGroups = reactive({
  global: false,
  poreSize: false,
  shapeFactors: false,
  brightness: true, // collapsed by default
})

function toggleGroup(key) {
  collapsedGroups[key] = !collapsedGroups[key]
}


const {
  submenuRef,
  onItemHover,
  onMouseLeaveMenu,
  requestClose,
  debugConeActive,
  trianglePoints,
  handleSubmenuMouseEnter,
  handleSubmenuMouseLeave
} = useMenuAim({
  submenuDirection: 'left',
  delay: 300,
  isVisible: () => tooltip.visible
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
  const spanRect = e.target.getBoundingClientRect()
  const anchorCoords = {
    x: spanRect.left + spanRect.width / 2,
    y: spanRect.top + spanRect.height / 2
  }

  onItemHover(type, () => {
    if (hideTimeoutId) {
      clearTimeout(hideTimeoutId)
      hideTimeoutId = null
    }
    if (!panelRef.value) return
    const panelRect = panelRef.value.getBoundingClientRect()
    const data = TOOLTIP_TEXTS[type] || { title: '', description: '', formula: '' }

    tooltip.title = data.title
    tooltip.description = data.description
    tooltip.formula = data.formula
    tooltip.top = spanRect.top + spanRect.height / 2
    tooltip.left = panelRect.left - 12
    tooltip.visible = true
  }, anchorCoords)
}

function handleMouseLeavePanel() {
  onMouseLeaveMenu()
  hideTooltip()
}

function hideTooltip() {
  requestClose(() => {
    tooltip.visible = false
  })
}

function onTooltipMouseEnter() {
  handleSubmenuMouseEnter()
  if (hideTimeoutId) {
    clearTimeout(hideTimeoutId)
    hideTimeoutId = null
  }
}

function onTooltipMouseLeave() {
  handleSubmenuMouseLeave()
  tooltip.visible = false
}
</script>

<style scoped>
.metrics-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--outline);
  border-radius: 6px;
  padding: 8px;
  scrollbar-width: thin;
  scrollbar-color: var(--outline) var(--surface);
}

.metrics-panel::-webkit-scrollbar {
  width: 6px;
}
.metrics-panel::-webkit-scrollbar-track {
  background: var(--surface);
}
.metrics-panel::-webkit-scrollbar-thumb {
  background: var(--outline);
  border-radius: 3px;
}
.metrics-panel::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.metric-card {
  border: 1px solid var(--outline);
  background: var(--surface-2);
  padding: 10px;
}

.metric-card h4 {
  color: var(--text-muted);
  margin: 0 0 8px;
  text-transform: uppercase;
  font: 700 10px/1 'Space Grotesk', sans-serif;
}

.metric-group {
  margin-top: 10px;
  border-top: 1px solid var(--outline);
  padding-top: 10px;
}

.metric-group:first-of-type {
  margin-top: 0;
  border-top: 0;
  padding-top: 0;
}

.metric-group-title {
  margin: 0 0 8px;
  color: var(--primary);
  text-transform: uppercase;
  font: 700 9px/1 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font: 500 12px/1.4 'Space Grotesk', sans-serif;
  color: var(--text-soft);
  margin-bottom: 6px;
}

.metric-row strong {
  color: var(--text);
}

.tooltip-trigger {
  border-bottom: 1px dotted var(--text-muted);
  cursor: help;
  transition: color 0.15s ease, border-bottom-color 0.15s ease;
}

.tooltip-trigger:hover {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.metric-row span[title] {
  border-bottom: 1px dotted var(--text-muted);
  cursor: help;
}

.mask-image {
  width: 100%;
  border: 1px solid var(--outline);
  background: #0e0e0f;
}

.retry-health {
  margin-left: auto;
  border: 1px solid var(--outline);
  background: var(--surface-2);
  color: var(--text);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font: 600 10px/1 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .metrics-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metrics-panel .status {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .metrics-panel {
    grid-template-columns: 1fr;
  }
}
</style>
