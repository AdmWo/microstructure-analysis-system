<template>
  <div class="stitch-dashboard" :class="['theme-' + theme, { 'is-roi-dragging': roiDraggingUi }]">
    <DashboardTopBar :theme="theme" @toggle-theme="toggleTheme" @open-help="openHelp" />

    <ScientificSidebar
      :current-stage="currentStage"
      :steps="pipelineSteps"
      :active-step="activePipelineStep"
      :stage-title="currentStageTitle"
      :stage-description="currentStageDesc"
      :images="images"
      :active-image-index="activeImageIndex"
      @step="goToPipelineStep"
      @prev="handlePrevStage"
      @next="handleNextStage"
      @select-image="setActiveImage"
      @delete-image="deleteImage"
      @open-file-picker="openFilePicker"
    >
      <!-- Step 1: Obraz (List & upload of multiple images) -->
      <template v-if="currentStage === 1">
        <button type="button" class="mini-btn" @click="openFilePicker">Dodaj zdjęcia</button>
        <div class="sidebar-image-list">
          <div
            v-for="(img, idx) in images"
            :key="img.id"
            class="sidebar-image-item"
            :class="{ active: idx === activeImageIndex }"
            @click="setActiveImage(idx)"
          >
            <span class="sidebar-image-name" :title="img.name">{{ img.name }}</span>
            <button type="button" class="sidebar-image-del" @click.stop="deleteImage(idx)">×</button>
          </div>
        </div>
      </template>

      <!-- Step 2: Przetwarzanie Wstępne (ROI & Contrast) -->
      <template v-else-if="currentStage === 2">
        <button type="button" class="mini-btn" @click="openFilePicker">Wgraj nowy obraz</button>
        <label>
          <span>Kontrast analizy (API + podglad)</span>
          <small>{{ params.contrast_percent }}%</small>
          <input v-model.number="params.contrast_percent" type="range" min="50" max="200" step="5" />
        </label>
        <label>
          <span>Intensywnosc filtru medianowego</span>
          <small>{{ params.denoise_kernel_size }} px (OpenCV: nieparzyste >= 3)</small>
          <input v-model.number="params.denoise_kernel_size" type="range" min="3" max="15" step="2" />
        </label>
        <label>
          <span>ROI X / Y / W / H</span>
          <div class="roi-inline-grid">
            <input type="number" min="0" :disabled="!params.roi" :value="params.roi?.x ?? 0" @change="updateManualRoiField({ field: 'x', value: Number($event.target.value || 0) })" />
            <input type="number" min="0" :disabled="!params.roi" :value="params.roi?.y ?? 0" @change="updateManualRoiField({ field: 'y', value: Number($event.target.value || 0) })" />
            <input type="number" min="1" :disabled="!params.roi" :value="params.roi?.width ?? 1" @change="updateManualRoiField({ field: 'width', value: Number($event.target.value || 1) })" />
            <input type="number" min="1" :disabled="!params.roi" :value="params.roi?.height ?? 1" @change="updateManualRoiField({ field: 'height', value: Number($event.target.value || 1) })" />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; margin-top: 0.3rem;">
            <button type="button" class="mini-btn" @click="setRoiToFullImage" style="margin-top: 0;">ROI = cały obraz</button>
            <button type="button" class="mini-btn" @click="clearRoi" :disabled="!params.roi" style="margin-top: 0;">Wyczyść ROI</button>
          </div>
        </label>
        <label class="toggle-row">
          <input type="checkbox" v-model="params.invert_roi" />
          <span>Inwertuj ROI</span>
        </label>
      </template>

      <!-- Step 3: Kalibracja Skali -->
      <template v-else-if="currentStage === 3">
        <div class="scale-calibration-controls" style="display: grid; gap: 0.6rem;">
          <p style="margin: 0 0 0.2rem; font-size: 0.75rem; color: var(--text-soft); line-height: 1.4;">
            Włącz tryb rysowania i przeciągnij linię o znanej długości fizycznej na obrazie. Przytrzymaj <strong>Shift</strong>, aby przyciągać linię do najbliższej osi (pion / poziom).
          </p>
          <button
            type="button"
            class="mini-btn scale-draw-btn"
            :class="{ 'btn-active': workflow.interactionMode === 'scale' }"
            @click="toggleScaleDrawingMode"
            style="width: 100%; text-align: center;"
          >
            {{ workflow.interactionMode === 'scale' ? 'Rysuj linię na obrazie...' : 'Rysuj linię kalibracyjną' }}
          </button>
          
          <label style="margin-top: 0.2rem;">
            <span>Długość w pikselach</span>
            <input type="number" :value="workflow.scalePxLength" readonly disabled style="opacity: 0.7;" />
          </label>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem;">
            <label>
              <span>Wartość</span>
              <input type="number" step="any" min="0.001" v-model.number="workflow.scalePhysicalValue" />
            </label>
            <label>
              <span>Jednostka</span>
              <select v-model="workflow.scaleUnit">
                <option value="µm">µm</option>
                <option value="mm">mm</option>
              </select>
            </label>
          </div>

          <button
            v-if="images.length > 1 && workflow.scalePxLength > 0"
            type="button"
            class="mini-btn scale-copy-btn"
            @click="copyScaleToAll"
            style="width: 100%; text-align: center; margin-top: 4px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa;"
          >
            Kopiuj kalibrację do pozostałych
          </button>
          <p v-if="scaleCopiedStatus" style="font-size: 10px; color: #10b981; margin: 4px 0 0; text-align: center;">
            Pomyślnie skopiowano do wszystkich zdjęć!
          </p>
        </div>
      </template>

      <!-- Step 4: Segmentacja -->
      <template v-else-if="currentStage === 4">
        <label>
          <span>Metoda binaryzacji (API)</span>
          <select id="binarization-method" name="binarization_method" v-model="params.binarization_method">
            <option value="otsu">Otsu — automatyczny prog</option>
            <option value="manual">Reczny prog</option>
            <option value="ml">Machine Learning Segmentation</option>
          </select>
        </label>
        <label v-if="params.binarization_method === 'ml'">
          <span>Model segmentacji ML</span>
          <select id="ml-model-name" name="ml_model_name" v-model="params.ml_model_name">
            <option value="unet_resnet18_baseline">U-Net ResNet18 (Baseline)</option>
          </select>
        </label>
        <label :class="{ disabled: params.binarization_method !== 'manual' }">
          <span>Prog binaryzacji (reczny)</span>
          <small>{{ params.manual_threshold }} / 255</small>
          <input
            v-model.number="params.manual_threshold"
            type="range"
            min="0"
            max="255"
            step="1"
            :disabled="params.binarization_method !== 'manual'"
          />
        </label>
      </template>

      <!-- Step 5: Identyfikacja i Analiza Cech -->
      <template v-else-if="currentStage === 5">
        <label>
          <span>Morfologia — otwarcie (iteracje)</span>
          <small>{{ params.morph_open_iterations }}</small>
          <input v-model.number="params.morph_open_iterations" type="range" min="0" max="10" step="1" />
        </label>
        <label>
          <span>Morfologia — domkniecie (iteracje)</span>
          <small>{{ params.morph_close_iterations }}</small>
          <input v-model.number="params.morph_close_iterations" type="range" min="0" max="10" step="1" />
        </label>
        <label>
          <span>Wybor modelu (roboczo)</span>
          <select id="model-selection" name="model_selection" v-model="selectedModel">
            <option value="DeepMetal-V4.2_ResNet">DeepMetal-V4.2_ResNet</option>
            <option value="DeepMetal-V3.7_EfficientNet">DeepMetal-V3.7_EfficientNet</option>
            <option value="GrainVision-Base">GrainVision-Base</option>
          </select>
        </label>
      </template>

      <template v-else>
        <!-- Brak dodatkowych parametrów dla etapu wyników -->
      </template>

      <button type="button" class="execute-btn" :disabled="loading || images.length === 0" @click="runAnalysis">
        <svg class="execute-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 5v14l11-7z" fill="currentColor" />
        </svg>
        {{ loading ? 'Trwa analiza...' : 'Uruchom analize' }}
      </button>
    </ScientificSidebar>

    <main class="stitch-main">
      <div class="content-row">
        <StitchViewer
          :current-stage="currentStage"
          :roi-data-url="roiDataUrl"
          :is-dragging="isDragging"
          :error="error"
          :frame-style="frameStyle"
          :contrast-percent="params.contrast_percent"
          :invert-roi="params.invert_roi"
          :can-edit-roi="currentStage === 2 && workflow.interactionMode === 'roi'"
          :space-pressed="view.spacePressed"
          :displayed-roi-box="displayedRoiBox"
          :drawing="drawing"
          :is-swapped="isSwapped"
          :mask-data-url="maskDataUrl"
          :scale-enabled="workflow.scalePxLength > 0"
          :scale-line-coords="workflow.scaleLineCoords"
          :scale-drawing="scaleDrawing"
          :scale-physical-value="Number(workflow.scalePhysicalValue) || 0"
          :scale-unit="workflow.scaleUnit"
          :scale-px-length="workflow.scalePxLength"
          :image-natural="imageNatural"
          :image-render="imageRender"
          :measure-line-coords="workflow.measureLineCoords"
          :measure-drawing="measureDrawing"
          :images="images"
          :active-image-index="activeImageIndex"
          @drop="onDrop"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @wheel-image="onImageWheel"
          @image-load="onImageLoaded"
          @begin-roi="beginRoiSelection"
          @begin-move-roi="beginMoveRoi"
          @begin-resize-roi="beginResizeRoi"
          @begin-resize-measure="beginResizeMeasure"
          @open-file-picker="openFilePicker"
          @select-image="setActiveImage"
          @delete-image="deleteImage"
        />

        <DashboardMetrics
          :histogram-bins="histogramBins"
          :threshold-percent="histogramThresholdPercent"
          :threshold-value="activeThresholdValue"
          :ghost-threshold-percent="ghostThresholdPercent"
          :ghost-threshold-value="ghostThresholdValue"
          :histogram-note="histogramNote"
          :min-intensity="histogramMinIntensity"
          :max-intensity="histogramMaxIntensity"
          :metric-cards="metricCards"
          :aa-percent="displayAaPercent"
          :pore-count="displayPoreCount"
          :mask-data-url="maskDataUrl"
          :is-swapped="isSwapped"
          :roi-crop-data-url="roiCropDataUrl"
          :can-swap="activePipelineStep === 6 && !!maskDataUrl"
          :scale-enabled="workflow.scalePxLength > 0"
          :scale-unit="workflow.scaleUnit"
          :total-roi-area-physical="displayTotalRoiArea"
          :average-pore-area-physical="displayAveragePoreArea"
          :pore-density-n-a="displayPoreDensityNA"
          :avg-d1-circularity-perimeter="displayD1"
          :avg-d2-circularity-area="displayD2"
          :avg-edge-indicator="displayEdge"
          :avg-shape-factor-raw="displayShape"
          :avg-roundness-ellipse="displayRoundness"
          :avg-malinowska-factor="displayMalinowska"
          :inference-time-ms="displayInferenceTime"
          :total-execution-time-ms="displayTotalExecutionTime"
          :t-preprocess-ms="displayPreprocessTime"
          :t-segment-ms="displaySegmentTime"
          :t-morphology-ms="displayMorphologyTime"
          :t-stereology-ms="displayStereologyTime"
          :t-encoding-ms="displayEncodingTime"
          :is-thinner="histogramThinner"

          :is-threshold-editable="isThresholdEditable"
          :images-count="images.length"
          :show-averages="showAverages"
          @toggle-swap="toggleSwap"
          @download-mask="downloadMask"
          @download-roi="downloadRoiCrop"
          @update-threshold="onUpdateThreshold"
          @toggle-thickness="toggleHistogramThickness"
          @toggle-display-mode="showAverages = $event"
        />
      </div>

      <div class="bottom-bar">
        <div class="bottom-viewer-controls">
          <button type="button" class="bottom-btn" @click="zoomIn" title="Powiększ">+</button>
          <button type="button" class="bottom-btn" @click="zoomOut" title="Pomniejsz">-</button>
          <button type="button" class="bottom-btn" @click="resetView">Oddal</button>
          
          <!-- Measurement tool button -->
          <button
            v-if="workflow.scalePxLength > 0"
            type="button"
            class="bottom-btn"
            :class="{ 'btn-active': workflow.interactionMode === 'measure' }"
            @click="toggleMeasurementMode"
            title="Zmierz odległość na obrazie"
          >
            <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style="display: inline-block; vertical-align: middle; margin-right: 4px;">
              <path d="M19.5 2H4.5C3.12 2 2 3.12 2 4.5v15C2 20.88 3.12 22 4.5 22h15c1.38 0 2.5-1.12 2.5-2.5v-15C22 3.12 20.88 2 19.5 2zM20 19.5c0 .28-.22.5-.5.5H4.5c-.28 0-.5-.22-.5-.5v-15c0-.28.22-.5.5-.5h15c.28 0 .5.22.5.5v15zM7 6h2v3H7zm0 5h2v3H7zm0 5h2v2H7zm5-10h5v2h-5zm0 5h5v2h-5zm0 5h5v2h-5z"/>
            </svg>
            {{ workflow.interactionMode === 'measure' ? 'Rysuj pomiar...' : 'Zmierz odległość' }}
          </button>
          <button
            v-if="workflow.measureLineCoords"
            type="button"
            class="bottom-btn-mini"
            @click="clearMeasurement"
            title="Wyczyść pomiar"
            style="margin-left: 4px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; border-radius: 4px; font-size: 11px; padding: 2px 6px; cursor: pointer;"
          >
            Usuń pomiar
          </button>

          <button v-if="maskDataUrl && activePipelineStep === 6" type="button" class="bottom-btn" @click="toggleSwap" :class="{ 'btn-active': isSwapped }">
            {{ isSwapped ? 'Pokaż oryginał' : 'Pokaż maskę' }}
          </button>
        </div>

        <div class="bottom-api-status" :class="health.status">
          <span class="status-dot"></span>
          <span class="status-text">{{ health.message }}</span>
          <button type="button" class="bottom-btn-mini" @click="checkHealth">Odśwież</button>
        </div>
      </div>
    </main>

    <input ref="fileInputRef" type="file" accept="image/*" multiple @change="onFileInput" />

    <div v-if="helpOpen" class="help-modal-backdrop" @click.self="closeHelp">
      <section class="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <header class="help-modal-header">
          <h2 id="help-title">Pomoc</h2>
          <button type="button" class="help-close-btn" @click="closeHelp" aria-label="Zamknij pomoc">×</button>
        </header>
        <div class="help-modal-content">
          <p>1) Wgraj jeden lub wiele obrazów.</p>
          <p>2) Ustaw ROI i parametry przetwarzania dla każdego z nich.</p>
          <p>3) Skalibruj skalę i skopiuj ją do pozostałych (jeśli mają tę samą powiększenie).</p>
          <p>4) Wybierz parametry binaryzacji i uruchom analizę.</p>
          <p>5) Wyniki pokażą wartości uśrednione dla całego zbioru oraz szczegóły pojedynczych klatek.</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useWorkflowStore } from '../stores/workflow'
import { analyzeImage } from '../api/analyze'
import DashboardTopBar from './dashboard/DashboardTopBar.vue'
import ScientificSidebar from './dashboard/ScientificSidebar.vue'
import StitchViewer from './dashboard/StitchViewer.vue'
import DashboardMetrics from './dashboard/DashboardMetrics.vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const workflow = useWorkflowStore()

// State for multiple images
const images = ref([])
const activeImageIndex = ref(-1)
const showAverages = ref(true)

const file = ref(null)
const result = ref(null)
const error = ref(null)
const loading = ref(false)
const theme = ref('light')
const isDragging = ref(false)
const localPreview = ref(null)
const fileInputRef = ref(null)
const isSwapped = ref(false)
const imageNatural = reactive({ width: 0, height: 0 })
const imageRender = reactive({ width: 0, height: 0 })
const imageStats = reactive({ mean: null, stdDev: null, snr: null })
const histogramBins = ref([])
const histogramThinner = ref(false)
const isThresholdEditable = computed(() => {
  return activePipelineStep.value === 4 && params.binarization_method === 'manual'
})
const histogramMinIntensity = ref(0)
const histogramMaxIntensity = ref(255)
const localOtsuThreshold = ref(null)
const health = ref({ status: 'checking', message: 'Sprawdzanie polaczenia...' })
const roiDraggingUi = ref(false)
const helpOpen = ref(false)
let savedDocUserSelect = ''
let savedBodyUserSelect = ''
const drawing = reactive({ active: false, x: 0, y: 0, width: 0, height: 0 })
const scaleDrawing = reactive({ active: false, startX: 0, startY: 0, endX: 0, endY: 0 })
const measureDrawing = reactive({ active: false, startX: 0, startY: 0, endX: 0, endY: 0 })
const measureInteraction = reactive({
  active: false,
  handle: null, // 'start' or 'end'
  startX: 0,
  startY: 0,
  originCoords: null,
})
const view = reactive({
  zoom: 1,
  offsetX: 0,
  offsetY: 0,
  panning: false,
  startX: 0,
  startY: 0,
  startOffsetX: 0,
  startOffsetY: 0,
  spacePressed: false,
})
const cropInteraction = reactive({
  active: false,
  mode: 'new',
  handle: null,
  startX: 0,
  startY: 0,
  originBox: null,
})

const params = reactive({
  roi: null,
  invert_roi: false,
  contrast_percent: 100,
  denoise_enabled: true,
  denoise_method: 'median',
  denoise_kernel_size: 5,
  binarization_method: 'ml',
  manual_threshold: 120,
  ml_model_name: 'unet_resnet18_baseline',
  morph_open_iterations: 1,
  morph_close_iterations: 1,
})
const selectedModel = ref('DeepMetal-V4.2_ResNet')
const activeTool = ref('Przytnij ROI')

const currentStage = computed(() => workflow.currentStage)
const maskDataUrl = computed(() => result.value?.mask_b64 ? `data:image/png;base64,${result.value.mask_b64}` : null)
const roiDataUrl = computed(() => localPreview.value)

// Computed metrics displaying either Average or Active Image values
const displayAaPercent = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgAaPercent
  return result.value?.aa_percent ?? null
})
const displayPoreCount = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgPoreCount
  return result.value?.pore_count ?? null
})
const displayTotalRoiArea = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgTotalRoiArea
  return result.value?.total_roi_area_physical ?? null
})
const displayAveragePoreArea = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgPoreArea
  return result.value?.average_pore_area_physical ?? null
})
const displayPoreDensityNA = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgNa
  return result.value?.N_A ?? null
})
const displayD1 = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgD1CircularityPerimeter
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgD1CircularityPerimeter ?? null) : null
})
const displayD2 = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgD2CircularityArea
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgD2CircularityArea ?? null) : null
})
const displayEdge = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgEdgeIndicator
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgEdgeIndicator ?? null) : null
})
const displayShape = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgShapeFactorRaw
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgShapeFactorRaw ?? null) : null
})
const displayRoundness = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgRoundnessEllipse
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgRoundnessEllipse ?? null) : null
})
const displayMalinowska = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgMalinowskaFactor
  return result.value ? (images.value[activeImageIndex.value]?.shapeFactors?.avgMalinowskaFactor ?? null) : null
})
const displayInferenceTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgInferenceTimeMs
  return result.value?.inference_time_ms ?? null
})
const displayTotalExecutionTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgTotalExecutionTimeMs
  return result.value?.total_execution_time_ms ?? null
})
const displayPreprocessTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgPreprocessMs
  return result.value?.t_preprocess_ms ?? null
})
const displaySegmentTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgSegmentMs
  return result.value?.t_segment_ms ?? null
})
const displayMorphologyTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgMorphologyMs
  return result.value?.t_morphology_ms ?? null
})
const displayStereologyTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgStereologyMs
  return result.value?.t_stereology_ms ?? null
})
const displayEncodingTime = computed(() => {
  if (showAverages.value && images.value.length > 1) return workflow.avgEncodingMs
  return result.value?.t_encoding_ms ?? null
})



const displayedRoiBox = computed(() => {
  if (!params.roi || !imageNatural.width || !imageNatural.height || !imageRender.width || !imageRender.height) return null
  const sx = imageRender.width / imageNatural.width
  const sy = imageRender.height / imageNatural.height
  return {
    left: params.roi.x * sx,
    top: params.roi.y * sy,
    width: params.roi.width * sx,
    height: params.roi.height * sy,
  }
})
const viewTransform = computed(() => ({
  transform: `translate(${view.offsetX}px, ${view.offsetY}px) scale(${view.zoom})`,
}))
const frameStyle = computed(() => ({
  width: `${Math.max(1, imageRender.width)}px`,
  height: `${Math.max(1, imageRender.height)}px`,
  ...viewTransform.value,
}))
const metricCards = computed(() => ([
  { label: 'Jasnosc srednia', key: 'mean', value: imageStats.mean !== null ? `${imageStats.mean.toFixed(2)} AU` : 'brak danych' },
  { label: 'Odchylenie standardowe', key: 'stdDev', value: imageStats.stdDev !== null ? `${imageStats.stdDev.toFixed(2)} AU` : 'brak danych' },
  { label: 'Stosunek sygnal/szum', key: 'snr', value: imageStats.snr !== null ? `${imageStats.snr.toFixed(2)} dB` : 'brak danych' },
]))
const activeThresholdValue = computed(() => {
  if (params.binarization_method === 'manual') {
    return params.manual_threshold
  } else {
    return result.value?.used_threshold ?? null
  }
})

const histogramThresholdPercent = computed(() => {
  const val = activeThresholdValue.value
  if (val === null) return null
  const min = histogramMinIntensity.value
  const max = histogramMaxIntensity.value
  if (max === min) return null
  const pct = ((val - min) / (max - min)) * 100
  return Math.max(0, Math.min(100, pct))
})

const ghostThresholdValue = computed(() => {
  if (!result.value || result.value.used_threshold === undefined || result.value.used_threshold === null) return null
  const lastUsed = result.value.used_threshold
  if (lastUsed === activeThresholdValue.value) return null
  return lastUsed
})

const ghostThresholdPercent = computed(() => {
  const val = ghostThresholdValue.value
  if (val === null) return null
  const min = histogramMinIntensity.value
  const max = histogramMaxIntensity.value
  if (max === min) return null
  const pct = ((val - min) / (max - min)) * 100
  return Math.max(0, Math.min(100, pct))
})

const histogramNote = computed(() => {
  if (!roiDataUrl.value) return 'Wgraj obraz, aby zobaczyc histogram ROI.'
  let note = 'Histogram liczony z aktualnego ROI bieżącego obrazu. '
  if (params.binarization_method === 'manual') {
    note += `Linia pokazuje próg ręczny = ${params.manual_threshold}.`
  } else if (activeThresholdValue.value !== null) {
    note += `Linia pokazuje automatyczny próg Otsu = ${activeThresholdValue.value}.`
  } else {
    note += 'Próg Otsu zostanie wyznaczony po uruchomieniu analizy.'
  }
  if (ghostThresholdValue.value !== null) {
    note += ` Linia przerywana ("duch") to próg z ostatniej analizy = ${ghostThresholdValue.value}.`
  }
  return note
})
const roiCropDataUrl = computed(() => result.value?.roi_b64 ? `data:image/png;base64,${result.value.roi_b64}` : null)

const pipelineSteps = computed(() => ([
  { id: 1, label: 'Obraz' },
  { id: 2, label: 'Przetwarzanie Wstepne' },
  { id: 3, label: 'Kalibracja Skali' },
  { id: 4, label: 'Segmentacja (ML)' },
  { id: 5, label: 'Analiza cech' },
  { id: 6, label: 'Wyniki' },
]))
const activePipelineStep = computed(() => {
  if (images.value.length === 0) return 1
  return currentStage.value
})

const currentStageTitle = computed(() => {
  switch (activePipelineStep.value) {
    case 1:
      return 'Obraz'
    case 2:
      return 'Przetwarzanie Wstępne'
    case 3:
      return 'Kalibracja Skali'
    case 4:
      return 'Segmentacja (ML)'
    case 5:
      return 'Analiza cech'
    case 6:
      return 'Wyniki'
    default:
      return ''
  }
})

const currentStageDesc = computed(() => {
  switch (activePipelineStep.value) {
    case 1:
      return 'Etap przygotowania obrazów: wgraj jeden lub wiele plików graficznych z dysku, aby rozpocząć proces zbiorczej analizy struktury porowatej.'
    case 2:
      return 'Etap przygotowania: pozwala na zdefiniowanie obszaru zainteresowania (ROI) na obrazie wejściowym oraz dostosowanie kontrastu i filtrów wygładzających.'
    case 3:
      return 'Etap kalibracji: zdefiniuj linię skali o znanej długości fizycznej, aby przeliczyć piksele na mikrometry (µm) lub milimetry (mm) dla pomiarów stereologicznych.'
    case 4:
      return 'Etap binaryzacji: segmentacja obrazu. Umożliwia dobór progu odcięcia (ręczny suwak lub automatyczna metoda Otsu) w celu odróżnienia porów od tła metalicznego.'
    case 5:
      return 'Etap morfologii: oczyszczanie maski binarnej za pomocą operacji morfologicznego otwarcia (usuwanie drobnych szumów) oraz domknięcia (łączenie pęknięć i luk).'
    case 6:
      return 'Etap wyników: prezentacja obliczonych wskaźników stereologicznych (porowatość powierzchniowa i objętościowa) oraz eksport kompletnego raportu z pomiaru.'
    default:
      return ''
  }
})

function goToPipelineStep(step) {
  if (images.value.length === 0) {
    error.value = 'Najpierw wgraj zdjęcia, aby przejsc dalej w workflow.'
    return
  }
  workflow.goToStage(step)
}

function setRoiToFullImage() {
  if (!imageNatural.width || !imageNatural.height) return
  params.roi = { x: 0, y: 0, width: imageNatural.width, height: imageNatural.height }
}

function onDrop(e) {
  isDragging.value = false
  e.preventDefault()
  const filesList = Array.from(e.dataTransfer?.files || [])
  addFiles(filesList)
}

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

async function onFileInput(event) {
  const selected = Array.from(event.target.files || [])
  await addFiles(selected)
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function openFilePicker() {
  fileInputRef.value?.click()
}

// Helper to load image natural dimensions asynchronously
function loadImageDimensions(fileObj) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => {
      resolve({ width: 0, height: 0 })
    }
    img.src = URL.createObjectURL(fileObj)
  })
}

// Add files to lists
async function addFiles(filesList) {
  const imageFiles = filesList.filter(f => f.type?.startsWith('image/'))
  if (imageFiles.length === 0) return

  error.value = null

  for (const f of imageFiles) {
    const defaultParams = {
      roi: null,
      invert_roi: false,
      contrast_percent: 100,
      denoise_enabled: true,
      denoise_method: 'median',
      denoise_kernel_size: 5,
      binarization_method: 'ml',
      manual_threshold: 120,
      ml_model_name: 'unet_resnet18_baseline',
      morph_open_iterations: 1,
      morph_close_iterations: 1,
    }

    const dims = await loadImageDimensions(f)
    
    const newItem = {
      id: Date.now() + Math.random(),
      file: f,
      name: f.name,
      localPreview: URL.createObjectURL(f),
      imageNatural: dims,
      params: defaultParams,
      scalePxLength: 0.0,
      scalePhysicalValue: 20.0,
      scaleUnit: 'µm',
      scaleLineCoords: null,
      measureLineCoords: null,
      result: null,
      shapeFactors: {
        avgD1CircularityPerimeter: null,
        avgD2CircularityArea: null,
        avgEdgeIndicator: null,
        avgShapeFactorRaw: null,
        avgRoundnessEllipse: null,
        avgMalinowskaFactor: null,
      }
    }

    images.value.push(newItem)
  }

  // Switch to the first uploaded image if no image was active
  if (activeImageIndex.value === -1 && images.value.length > 0) {
    setActiveImage(0)
  }
}

// Active image state management
function setActiveImage(index) {
  if (index < 0 || index >= images.value.length) return

  saveActiveImageState()

  activeImageIndex.value = index
  const img = images.value[index]

  file.value = img.file
  result.value = img.result
  localPreview.value = img.localPreview
  imageNatural.width = img.imageNatural.width
  imageNatural.height = img.imageNatural.height

  Object.assign(params, img.params)

  workflow.scalePxLength = img.scalePxLength
  workflow.scalePhysicalValue = img.scalePhysicalValue
  workflow.scaleUnit = img.scaleUnit
  workflow.scaleLineCoords = img.scaleLineCoords ? { ...img.scaleLineCoords } : null
  workflow.measureLineCoords = img.measureLineCoords ? { ...img.measureLineCoords } : null
  workflow.inferenceTimeMs = img.result?.inference_time_ms ?? null
  workflow.totalExecutionTimeMs = img.result?.total_execution_time_ms ?? null
  workflow.tPreprocessMs = img.result?.t_preprocess_ms ?? null
  workflow.tSegmentMs = img.result?.t_segment_ms ?? null
  workflow.tMorphologyMs = img.result?.t_morphology_ms ?? null
  workflow.tStereologyMs = img.result?.t_stereology_ms ?? null
  workflow.tEncodingMs = img.result?.t_encoding_ms ?? null

  resetView()

  isSwapped.value = false

}

// Delete an image from list
function deleteImage(index) {
  if (index < 0 || index >= images.value.length) return

  const deletedItem = images.value[index]
  if (deletedItem.localPreview) {
    URL.revokeObjectURL(deletedItem.localPreview)
  }

  images.value.splice(index, 1)

  if (images.value.length === 0) {
    activeImageIndex.value = -1
    file.value = null
    result.value = null
    localPreview.value = null
    imageNatural.width = 0
    imageNatural.height = 0
    Object.assign(params, {
      roi: null,
      invert_roi: false,
      contrast_percent: 100,
      denoise_enabled: true,
      denoise_method: 'median',
      denoise_kernel_size: 5,
      binarization_method: 'ml',
      manual_threshold: 120,
      ml_model_name: 'unet_resnet18_baseline',
      morph_open_iterations: 1,
      morph_close_iterations: 1,
    })
    workflow.reset()
  } else {
    if (activeImageIndex.value === index) {
      const nextIdx = Math.min(index, images.value.length - 1)
      activeImageIndex.value = -1
      setActiveImage(nextIdx)
    } else if (activeImageIndex.value > index) {
      activeImageIndex.value--
    }
  }
}

// Save active state fields back to array
function saveActiveImageState() {
  const idx = activeImageIndex.value
  if (idx >= 0 && idx < images.value.length) {
    const img = images.value[idx]
    img.params = { ...params }
    img.file = file.value
    img.result = result.value
    img.localPreview = localPreview.value
    img.imageNatural = { ...imageNatural }
    img.scalePxLength = workflow.scalePxLength
    img.scalePhysicalValue = workflow.scalePhysicalValue
    img.scaleUnit = workflow.scaleUnit
    img.scaleLineCoords = workflow.scaleLineCoords ? { ...workflow.scaleLineCoords } : null
    img.measureLineCoords = workflow.measureLineCoords ? { ...workflow.measureLineCoords } : null
  }
}

// Real-time synchronization watchers
watch(params, (newParams) => {
  const idx = activeImageIndex.value
  if (idx >= 0 && idx < images.value.length) {
    images.value[idx].params = { ...newParams }
  }
}, { deep: true })

watch(() => ({
  scalePxLength: workflow.scalePxLength,
  scalePhysicalValue: workflow.scalePhysicalValue,
  scaleUnit: workflow.scaleUnit,
  scaleLineCoords: workflow.scaleLineCoords,
  measureLineCoords: workflow.measureLineCoords,
}), (newVal) => {
  const idx = activeImageIndex.value
  if (idx >= 0 && idx < images.value.length) {
    const img = images.value[idx]
    img.scalePxLength = newVal.scalePxLength
    img.scalePhysicalValue = newVal.scalePhysicalValue
    img.scaleUnit = newVal.scaleUnit
    img.scaleLineCoords = newVal.scaleLineCoords ? { ...newVal.scaleLineCoords } : null
    img.measureLineCoords = newVal.measureLineCoords ? { ...newVal.measureLineCoords } : null
  }
}, { deep: true })

// Copy calibration parameter to all other files
const scaleCopiedStatus = ref(false)
function copyScaleToAll() {
  if (activeImageIndex.value === -1) return
  const activeImg = images.value[activeImageIndex.value]
  images.value.forEach((img, idx) => {
    if (idx !== activeImageIndex.value) {
      img.scalePxLength = activeImg.scalePxLength
      img.scalePhysicalValue = activeImg.scalePhysicalValue
      img.scaleUnit = activeImg.scaleUnit
      img.scaleLineCoords = activeImg.scaleLineCoords ? { ...activeImg.scaleLineCoords } : null
    }
  })
  scaleCopiedStatus.value = true
  setTimeout(() => {
    scaleCopiedStatus.value = false
  }, 3000)
}

function onImageLoaded(e) {
  imageNatural.width = e.target.naturalWidth
  imageNatural.height = e.target.naturalHeight
  updateImageRenderSize()
  computeImageAnalytics()
}

function updateImageRenderSize() {
  const viewport = document.querySelector('.stitch-image-frame-wrap')
  if (!viewport) return
  const rect = viewport.getBoundingClientRect()
  const maxWidth = rect.width
  const maxHeight = rect.height
  if (!maxWidth || !maxHeight) return

  if (!imageNatural.width || !imageNatural.height) {
    imageRender.width = maxWidth
    imageRender.height = maxHeight
    return
  }

  const imageRatio = imageNatural.width / imageNatural.height
  const viewportRatio = maxWidth / maxHeight
  if (imageRatio > viewportRatio) {
    imageRender.width = maxWidth
    imageRender.height = maxWidth / imageRatio
  } else {
    imageRender.height = maxHeight
    imageRender.width = maxHeight * imageRatio
  }
}

function getRoiOverlayRect() {
  const overlay = document.querySelector('.stitch-image-frame .roi-overlay')
  return overlay?.getBoundingClientRect() ?? null
}

function clampToImageBounds(e) {
  const rect = getRoiOverlayRect()
  if (!rect || !rect.width || !rect.height) return null
  const logicalW = imageRender.width
  const logicalH = imageRender.height
  if (!logicalW || !logicalH) return null
  
  const screenW = Math.max(rect.width, Number.EPSILON)
  const screenH = Math.max(rect.height, Number.EPSILON)
  const cx = Math.min(Math.max(e.clientX, rect.left), rect.right)
  const cy = Math.min(Math.max(e.clientY, rect.top), rect.bottom)
  const x = (cx - rect.left) * (logicalW / screenW)
  const y = (cy - rect.top) * (logicalH / screenH)
  return { x: Math.max(0, Math.min(x, logicalW)), y: Math.max(0, Math.min(y, logicalH)) }
}

let roiGlobalDragAttached = false

function handleRoiGlobalMove(ev) {
  if (view.panning || cropInteraction.active || scaleDrawing.active || measureDrawing.active || measureInteraction.active) ev.preventDefault()
  moveRoiSelection(ev)
}

function handleRoiGlobalEnd() {
  finishRoiSelection()
}

function attachRoiGlobalDragListeners() {
  if (roiGlobalDragAttached) return
  roiGlobalDragAttached = true
  roiDraggingUi.value = true
  savedDocUserSelect = document.documentElement.style.userSelect
  savedBodyUserSelect = document.body.style.userSelect
  document.documentElement.style.userSelect = 'none'
  document.body.style.userSelect = 'none'
  window.getSelection()?.removeAllRanges()
  window.addEventListener('pointermove', handleRoiGlobalMove, { passive: false })
  window.addEventListener('pointerup', handleRoiGlobalEnd, true)
  window.addEventListener('pointercancel', handleRoiGlobalEnd, true)
}

function detachRoiGlobalDragListeners() {
  if (!roiGlobalDragAttached) return
  roiGlobalDragAttached = false
  roiDraggingUi.value = false
  document.documentElement.style.userSelect = savedDocUserSelect
  document.body.style.userSelect = savedBodyUserSelect
  window.removeEventListener('pointermove', handleRoiGlobalMove)
  window.removeEventListener('pointerup', handleRoiGlobalEnd, true)
  window.removeEventListener('pointercancel', handleRoiGlobalEnd, true)
}

function beginRoiSelection(e) {
  if (!file.value) return
  if (view.spacePressed || e.button === 1) {
    beginPan(e)
    return
  }
  if (e.button !== 0) return

  if (workflow.interactionMode === 'scale') {
    e.preventDefault()
    const point = clampToImageBounds(e)
    if (!point) return
    scaleDrawing.active = true
    scaleDrawing.startX = point.x
    scaleDrawing.startY = point.y
    scaleDrawing.endX = point.x
    scaleDrawing.endY = point.y
    attachRoiGlobalDragListeners()
    return
  }
  if (workflow.interactionMode === 'measure') {
    e.preventDefault()
    const point = clampToImageBounds(e)
    if (!point) return
    measureDrawing.active = true
    measureDrawing.startX = point.x
    measureDrawing.startY = point.y
    measureDrawing.endX = point.x
    measureDrawing.endY = point.y
    attachRoiGlobalDragListeners()
    return
  }

  if (workflow.currentStage !== 2) {
    if (view.zoom > 1) beginPan(e)
    return
  }
  if (view.zoom > 1 && params.roi) {
    beginPan(e)
    return
  }
  e.preventDefault()
  const point = clampToImageBounds(e)
  if (!point) return
  cropInteraction.active = true
  cropInteraction.mode = 'new'
  cropInteraction.handle = null
  cropInteraction.startX = point.x
  cropInteraction.startY = point.y
  cropInteraction.originBox = null
  drawing.active = true
  drawing.x = point.x
  drawing.y = point.y
  drawing.width = 0
  drawing.height = 0
  attachRoiGlobalDragListeners()
}

function beginMoveRoi(e) {
  if (workflow.currentStage !== 2 || !displayedRoiBox.value) return
  if (e.button !== 0) return
  e.preventDefault()
  e.stopPropagation()
  const point = clampToImageBounds(e)
  if (!point) return
  cropInteraction.active = true
  cropInteraction.mode = 'move'
  cropInteraction.startX = point.x
  cropInteraction.startY = point.y
  cropInteraction.originBox = { ...displayedRoiBox.value }
  attachRoiGlobalDragListeners()
}

function beginResizeRoi(handle, e) {
  if (workflow.currentStage !== 2 || !displayedRoiBox.value) return
  if (e.button !== 0) return
  e.preventDefault()
  e.stopPropagation()
  const point = clampToImageBounds(e)
  if (!point) return
  cropInteraction.active = true
  cropInteraction.mode = 'resize'
  cropInteraction.handle = handle
  cropInteraction.startX = point.x
  cropInteraction.startY = point.y
  cropInteraction.originBox = { ...displayedRoiBox.value }
  attachRoiGlobalDragListeners()
}

function beginResizeMeasure(handle, e) {
  if (e.button !== 0) return
  e.preventDefault()
  e.stopPropagation()
  const point = clampToImageBounds(e)
  if (!point) return
  measureInteraction.active = true
  measureInteraction.handle = handle
  measureInteraction.startX = point.x
  measureInteraction.startY = point.y
  measureInteraction.originCoords = { ...workflow.measureLineCoords }
  attachRoiGlobalDragListeners()
}

function applyDisplayBoxToRoi(box) {
  const maxW = imageRender.width
  const maxH = imageRender.height
  const clamped = {
    left: Math.max(0, Math.min(box.left, maxW - 1)),
    top: Math.max(0, Math.min(box.top, maxH - 1)),
    width: Math.max(1, Math.min(box.width, maxW)),
    height: Math.max(1, Math.min(box.height, maxH)),
  }
  clamped.width = Math.min(clamped.width, maxW - clamped.left)
  clamped.height = Math.min(clamped.height, maxH - clamped.top)
  const sx = imageNatural.width / imageRender.width
  const sy = imageNatural.height / imageRender.height
  params.roi = {
    x: Math.round(clamped.left * sx),
    y: Math.round(clamped.top * sy),
    width: Math.max(1, Math.round(clamped.width * sx)),
    height: Math.max(1, Math.round(clamped.height * sy)),
  }
}

function beginPan(e) {
  if (e.button !== undefined && e.button !== 0 && e.button !== 1) return
  e.preventDefault()
  const point = clampToImageBounds(e)
  if (!point) return
  view.panning = true
  view.startX = e.clientX
  view.startY = e.clientY
  view.startOffsetX = view.offsetX
  view.startOffsetY = view.offsetY
  attachRoiGlobalDragListeners()
}

function moveRoiSelection(e) {
  if (view.panning) {
    view.offsetX = view.startOffsetX + (e.clientX - view.startX)
    view.offsetY = view.startOffsetY + (e.clientY - view.startY)
    return
  }
  if (measureInteraction.active) {
    const point = clampToImageBounds(e)
    if (!point) return
    const sx = imageNatural.width / imageRender.width
    const sy = imageNatural.height / imageRender.height
    const currentNatX = point.x * sx
    const currentNatY = point.y * sy

    let nextStartX = workflow.measureLineCoords.startX
    let nextStartY = workflow.measureLineCoords.startY
    let nextEndX = workflow.measureLineCoords.endX
    let nextEndY = workflow.measureLineCoords.endY

    if (measureInteraction.handle === 'start') {
      nextStartX = currentNatX
      nextStartY = currentNatY
      if (e.shiftKey) {
        const dx = Math.abs(currentNatX - nextEndX)
        const dy = Math.abs(currentNatY - nextEndY)
        if (dx > dy) {
          nextStartY = nextEndY
        } else {
          nextStartX = nextEndX
        }
      }
    } else {
      nextEndX = currentNatX
      nextEndY = currentNatY
      if (e.shiftKey) {
        const dx = Math.abs(currentNatX - nextStartX)
        const dy = Math.abs(currentNatY - nextStartY)
        if (dx > dy) {
          nextEndY = nextStartY
        } else {
          nextEndX = nextStartX
        }
      }
    }

    workflow.measureLineCoords = {
      startX: Number(nextStartX.toFixed(2)),
      startY: Number(nextStartY.toFixed(2)),
      endX: Number(nextEndX.toFixed(2)),
      endY: Number(nextEndY.toFixed(2)),
    }
    return
  }
  if (workflow.interactionMode === 'scale' && scaleDrawing.active) {
    const point = clampToImageBounds(e)
    if (!point) return
    if (e.shiftKey) {
      const dx = Math.abs(point.x - scaleDrawing.startX)
      const dy = Math.abs(point.y - scaleDrawing.startY)
      if (dx > dy) {
        scaleDrawing.endX = point.x
        scaleDrawing.endY = scaleDrawing.startY
      } else {
        scaleDrawing.endX = scaleDrawing.startX
        scaleDrawing.endY = point.y
      }
    } else {
      scaleDrawing.endX = point.x
      scaleDrawing.endY = point.y
    }
    return
  }
  if (workflow.interactionMode === 'measure' && measureDrawing.active) {
    const point = clampToImageBounds(e)
    if (!point) return
    if (e.shiftKey) {
      const dx = Math.abs(point.x - measureDrawing.startX)
      const dy = Math.abs(point.y - measureDrawing.startY)
      if (dx > dy) {
        measureDrawing.endX = point.x
        measureDrawing.endY = measureDrawing.startY
      } else {
        measureDrawing.endX = measureDrawing.startX
        measureDrawing.endY = point.y
      }
    } else {
      measureDrawing.endX = point.x
      measureDrawing.endY = point.y
    }
    return
  }
  if (!cropInteraction.active) return
  const point = clampToImageBounds(e)
  if (!point) return

  if (cropInteraction.mode === 'new') {
    drawing.x = Math.min(cropInteraction.startX, point.x)
    drawing.y = Math.min(cropInteraction.startY, point.y)
    drawing.width = Math.abs(point.x - cropInteraction.startX)
    drawing.height = Math.abs(point.y - cropInteraction.startY)
    return
  }

  if (!cropInteraction.originBox) return
  const dx = point.x - cropInteraction.startX
  const dy = point.y - cropInteraction.startY
  let left = cropInteraction.originBox.left
  let top = cropInteraction.originBox.top
  let right = cropInteraction.originBox.left + cropInteraction.originBox.width
  let bottom = cropInteraction.originBox.top + cropInteraction.originBox.height

  if (cropInteraction.mode === 'move') {
    const width = right - left
    const height = bottom - top
    left = Math.max(0, Math.min(left + dx, imageRender.width - width))
    top = Math.max(0, Math.min(top + dy, imageRender.height - height))
    applyDisplayBoxToRoi({ left, top, width, height })
    return
  }

  const handle = cropInteraction.handle
  if (!handle) return
  if (handle.includes('n')) top = Math.max(0, Math.min(top + dy, bottom - 8))
  if (handle.includes('s')) bottom = Math.min(imageRender.height, Math.max(bottom + dy, top + 8))
  if (handle.includes('w')) left = Math.max(0, Math.min(left + dx, right - 8))
  if (handle.includes('e')) right = Math.min(imageRender.width, Math.max(right + dx, left + 8))
  applyDisplayBoxToRoi({ left, top, width: right - left, height: bottom - top })
}

function finishRoiSelection() {
  try {
    if (view.panning) {
      view.panning = false
      return
    }
    if (workflow.interactionMode === 'scale' && scaleDrawing.active) {
      const sx = imageNatural.width / imageRender.width
      const sy = imageNatural.height / imageRender.height
      const natStartX = scaleDrawing.startX * sx
      const natStartY = scaleDrawing.startY * sy
      const natEndX = scaleDrawing.endX * sx
      const natEndY = scaleDrawing.endY * sy
      
      const dx = natEndX - natStartX
      const dy = natEndY - natStartY
      const pxLength = Math.sqrt(dx * dx + dy * dy)
      
      if (pxLength >= 1) {
        workflow.scalePxLength = Number(pxLength.toFixed(2))
        workflow.scaleLineCoords = {
          startX: Number(natStartX.toFixed(2)),
          startY: Number(natStartY.toFixed(2)),
          endX: Number(natEndX.toFixed(2)),
          endY: Number(natEndY.toFixed(2)),
        }
      }
      scaleDrawing.active = false
      workflow.interactionMode = 'roi'
      return
    }
    if (workflow.interactionMode === 'measure' && measureDrawing.active) {
      const sx = imageNatural.width / imageRender.width
      const sy = imageNatural.height / imageRender.height
      const natStartX = measureDrawing.startX * sx
      const natStartY = measureDrawing.startY * sy
      const natEndX = measureDrawing.endX * sx
      const natEndY = measureDrawing.endY * sy
      
      const dx = natEndX - natStartX
      const dy = natEndY - natStartY
      const pxLength = Math.sqrt(dx * dx + dy * dy)
      
      if (pxLength >= 1) {
        workflow.measureLineCoords = {
          startX: Number(natStartX.toFixed(2)),
          startY: Number(natStartY.toFixed(2)),
          endX: Number(natEndX.toFixed(2)),
          endY: Number(natEndY.toFixed(2)),
        }
      }
      measureDrawing.active = false
      workflow.interactionMode = 'roi'
      return
    }
    if (measureInteraction.active) {
      measureInteraction.active = false
      measureInteraction.handle = null
      measureInteraction.originCoords = null
      return
    }
    if (!cropInteraction.active) return
    if (cropInteraction.mode === 'new') {
      if (drawing.width >= 8 && drawing.height >= 8 && imageNatural.width && imageNatural.height) {
        applyDisplayBoxToRoi({
          left: drawing.x,
          top: drawing.y,
          width: drawing.width,
          height: drawing.height,
        })
      }
      drawing.active = false
      drawing.x = 0
      drawing.y = 0
      drawing.width = 0
      drawing.height = 0
    }
    cropInteraction.active = false
    cropInteraction.handle = null
    cropInteraction.originBox = null
  } finally {
    detachRoiGlobalDragListeners()
  }
}

function clearRoi() {
  params.roi = null
  drawing.active = false
  drawing.x = 0
  drawing.y = 0
  drawing.width = 0
  drawing.height = 0
}

function updateManualRoiField({ field, value }) {
  if (!params.roi || !imageNatural.width || !imageNatural.height) return
  const next = { ...params.roi }
  if (field === 'x' || field === 'y') {
    next[field] = Math.max(0, Math.round(value))
  } else if (field === 'width' || field === 'height') {
    next[field] = Math.max(1, Math.round(value))
  }
  const x = Math.max(0, Math.min(next.x, imageNatural.width - 1))
  const y = Math.max(0, Math.min(next.y, imageNatural.height - 1))
  params.roi = {
    x,
    y,
    width: Math.max(1, Math.min(next.width, imageNatural.width - x)),
    height: Math.max(1, Math.min(next.height, imageNatural.height - y)),
  }
}

function toggleScaleDrawingMode() {
  if (workflow.interactionMode === 'scale') {
    workflow.interactionMode = 'roi'
  } else {
    workflow.interactionMode = 'scale'
  }
}

function toggleMeasurementMode() {
  if (workflow.interactionMode === 'measure') {
    workflow.interactionMode = 'roi'
  } else {
    workflow.interactionMode = 'measure'
  }
}

function clearMeasurement() {
  workflow.measureLineCoords = null
}

function zoomIn() {
  view.zoom = Math.min(5, +(view.zoom + 0.2).toFixed(2))
  nextTick(updateImageRenderSize)
}

function zoomOut() {
  view.zoom = Math.max(1, +(view.zoom - 0.2).toFixed(2))
  if (view.zoom === 1) {
    view.offsetX = 0
    view.offsetY = 0
  }
  nextTick(updateImageRenderSize)
}

function resetView() {
  view.zoom = 1
  view.offsetX = 0
  view.offsetY = 0
  view.panning = false
  nextTick(updateImageRenderSize)
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function openHelp() {
  helpOpen.value = true
}

function closeHelp() {
  helpOpen.value = false
}

async function checkHealth() {
  health.value = { status: 'checking', message: 'Sprawdzanie polaczenia...' }
  try {
    const res = await fetch(`${API_BASE}/health`)
    if (!res.ok) throw new Error('Brak odpowiedzi')
    const json = await res.json()
    health.value = { status: json.status === 'ok' ? 'ok' : 'error', message: json.status === 'ok' ? 'Polaczono z API' : 'Brak polaczenia z API' }
  } catch {
    health.value = { status: 'error', message: 'Brak polaczenia z API' }
  }
}

// Export aggregate JSON report
function exportAnalysis() {
  if (images.value.length === 0) {
    error.value = 'Brak danych do eksportu.'
    return
  }
  
  const hasResults = images.value.every(img => img.result)
  if (!hasResults) {
    error.value = 'Nie wszystkie obrazy zostały przeanalizowane. Uruchom analizę.'
    return
  }

  const payload = {
    project: 'Microstructure Multiple Image Analysis',
    generated_at: new Date().toISOString(),
    model: selectedModel.value,
    summary_averages: {
      pore_count: workflow.avgPoreCount,
      aa_percent_porosity: workflow.avgAaPercent,
      vv_percent_porosity: workflow.avgAaPercent, // V_V equals A_A in stereology
      average_pore_area_physical: workflow.avgPoreArea,
      pore_density_N_A: workflow.avgNa,
      avg_d1_circularity_perimeter: workflow.avgD1CircularityPerimeter,
      avg_d2_circularity_area: workflow.avgD2CircularityArea,
      avg_edge_indicator: workflow.avgEdgeIndicator,
      avg_shape_factor_raw: workflow.avgShapeFactorRaw,
      avg_roundness_ellipse: workflow.avgRoundnessEllipse,
      avg_malinowska_factor: workflow.avgMalinowskaFactor,
      scale_unit: workflow.scaleUnit,
    },
    images: images.value.map(img => ({
      name: img.name,
      scale: {
        enabled: img.scalePxLength > 0,
        px_length: img.scalePxLength,
        physical_value: img.scalePhysicalValue,
        unit: img.scaleUnit,
      },
      params: {
        roi: img.params.roi,
        invert_roi: img.params.invert_roi,
        contrast_percent: img.params.contrast_percent,
        denoise_enabled: img.params.denoise_enabled,
        denoise_method: img.params.denoise_method,
        denoise_kernel_size: img.params.denoise_kernel_size,
        binarization_method: img.params.binarization_method,
        manual_threshold: img.params.manual_threshold,
        ml_model_name: img.params.ml_model_name || 'unet_resnet18_baseline',
        morph_open_iterations: img.params.morph_open_iterations,
        morph_close_iterations: img.params.morph_close_iterations,
      },
      metrics: {
        pore_count: img.result.pore_count,
        aa_percent: img.result.aa_percent,
        vv_percent: img.result.vv_percent,
        total_roi_area_physical: img.result.total_roi_area_physical,
        average_pore_area_physical: img.result.average_pore_area_physical,
        N_A: img.result.N_A,
        avg_d1_circularity_perimeter: img.result.avg_d1_circularity_perimeter,
        avg_d2_circularity_area: img.result.avg_d2_circularity_area,
        avg_edge_indicator: img.result.avg_edge_indicator,
        avg_shape_factor_raw: img.result.avg_shape_factor_raw,
        avg_roundness_ellipse: img.result.avg_roundness_ellipse,
        avg_malinowska_factor: img.result.avg_malinowska_factor,
      }
    }))
  }
  
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'zbiorczy-raport-analizy.json'
  link.click()
  URL.revokeObjectURL(url)
}

function computeImageAnalytics() {
  if (!roiDataUrl.value) {
    histogramBins.value = Array.from({ length: 24 }, () => 0)
    imageStats.mean = null
    imageStats.stdDev = null
    imageStats.snr = null
    localOtsuThreshold.value = null
    return
  }
  const image = new Image()
  image.onload = () => {
    const canvas = document.createElement('canvas')
    const width = 256
    const height = Math.max(1, Math.round((image.height / image.width) * width))
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const invertPart = params.invert_roi ? ' invert(100%)' : ''
    ctx.filter = `contrast(${params.contrast_percent}%)${invertPart}`
    ctx.drawImage(image, 0, 0, width, height)
    let sx = 0
    let sy = 0
    let sw = width
    let sh = height
    if (params.roi && imageNatural.width > 0 && imageNatural.height > 0) {
      const scaleX = width / imageNatural.width
      const scaleY = height / imageNatural.height
      sx = Math.max(0, Math.min(width - 1, Math.floor(params.roi.x * scaleX)))
      sy = Math.max(0, Math.min(height - 1, Math.floor(params.roi.y * scaleY)))
      sw = Math.max(1, Math.min(width - sx, Math.ceil(params.roi.width * scaleX)))
      sh = Math.max(1, Math.min(height - sy, Math.ceil(params.roi.height * scaleY)))
    }

    const pixels = ctx.getImageData(sx, sy, sw, sh).data
    const hist256 = new Array(256).fill(0)
    let sum = 0
    let sumSq = 0
    let count = 0
    let minLum = 255
    let maxLum = 0
    for (let i = 0; i < pixels.length; i += 4) {
      const lum = Math.round(0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2])
      hist256[Math.min(255, Math.max(0, lum))]++
      sum += lum
      sumSq += lum * lum
      count += 1
      if (lum < minLum) minLum = lum
      if (lum > maxLum) maxLum = lum
    }

    if (count === 0 || minLum > maxLum) {
      minLum = 0
      maxLum = 255
    }
    if (minLum === maxLum) {
      if (minLum > 0) minLum = Math.max(0, minLum - 1)
      else maxLum = Math.min(255, maxLum + 1)
    }

    const minSpan = Math.round(255 * 0.9)
    let minIntensityVal = minLum
    let maxIntensityVal = maxLum
    const currentSpan = maxIntensityVal - minIntensityVal
    if (currentSpan < minSpan) {
      const mid = (minIntensityVal + maxIntensityVal) / 2
      minIntensityVal = Math.max(0, Math.round(mid - minSpan / 2))
      maxIntensityVal = minIntensityVal + minSpan
      if (maxIntensityVal > 255) {
        maxIntensityVal = 255
        minIntensityVal = maxIntensityVal - minSpan
      }
    }

    histogramMinIntensity.value = minIntensityVal
    histogramMaxIntensity.value = maxIntensityVal

    const binCount = histogramThinner.value ? 48 : 24
    const bins = Array.from({ length: binCount }, () => 0)
    const range = maxIntensityVal - minIntensityVal
    for (let lum = minIntensityVal; lum <= maxIntensityVal; lum++) {
      const pxCount = hist256[lum]
      if (pxCount > 0) {
        const binIdx = Math.min(binCount - 1, Math.floor(((lum - minIntensityVal) / (range + 1)) * binCount))
        bins[binIdx] += pxCount
      }
    }
    const mean = count ? sum / count : 0
    const variance = count ? Math.max(0, sumSq / count - mean * mean) : 0
    const stdDev = Math.sqrt(variance)
    const snr = stdDev === 0 ? null : 20 * Math.log10(mean / stdDev)
    const max = Math.max(...bins, 1)
    histogramBins.value = bins.map((v) => (v / max) * 100)
    imageStats.mean = mean
    imageStats.stdDev = stdDev
    imageStats.snr = Number.isFinite(snr) ? snr : null

    // Compute Otsu threshold on the client side
    let totalSum = 0
    for (let i = 0; i < 256; i++) {
      totalSum += i * hist256[i]
    }

    let sumB = 0
    let wB = 0
    let wF = 0
    let varMax = 0
    let threshold = 0

    for (let t = 0; t < 256; t++) {
      wB += hist256[t]
      if (wB === 0) continue
      wF = count - wB
      if (wF === 0) break
      sumB += t * hist256[t]
      const mB = sumB / wB
      const mF = (totalSum - sumB) / wF
      const varBetween = wB * wF * (mB - mF) * (mB - mF)
      if (varBetween > varMax) {
        varMax = varBetween
        threshold = t
      }
    }
    localOtsuThreshold.value = threshold
  }
  image.src = roiDataUrl.value
}

function onImageWheel(e) {
  e.preventDefault()
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

function onKeyDown(e) {
  if (e.code === 'Space') view.spacePressed = true
}

function onKeyUp(e) {
  if (e.code === 'Space') view.spacePressed = false
}

function onUpdateThreshold(val) {
  params.binarization_method = 'manual'
  params.manual_threshold = val
}

function toggleHistogramThickness() {
  histogramThinner.value = !histogramThinner.value
}

onMounted(() => {
  window.addEventListener('resize', updateImageRenderSize)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  const saved = localStorage.getItem('mas-stitch-theme')
  if (saved === 'light' || saved === 'dark') theme.value = saved
  checkHealth()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateImageRenderSize)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
  detachRoiGlobalDragListeners()
})

watch(theme, (value) => {
  localStorage.setItem('mas-stitch-theme', value)
})

watch(activePipelineStep, (newStep) => {
  if (newStep !== 6) {
    isSwapped.value = false
  }
  if (newStep === 3) {
    workflow.interactionMode = 'scale'
  } else if (newStep === 2) {
    workflow.interactionMode = 'roi'
  } else {
    if (workflow.interactionMode === 'scale') {
      workflow.interactionMode = 'roi'
    }
  }
})

watch(roiDataUrl, () => {
  computeImageAnalytics()
})

watch(histogramThinner, () => {
  computeImageAnalytics()
})

watch(() => params.contrast_percent, () => {
  computeImageAnalytics()
})

watch(() => params.roi, () => {
  computeImageAnalytics()
}, { deep: true })

watch(() => params.manual_threshold, () => {
  computeImageAnalytics()
})

watch(() => params.invert_roi, () => {
  computeImageAnalytics()
})

watch(() => view.zoom, () => {
  nextTick(updateImageRenderSize)
})

// Run concurrent analysis for all uploaded images
async function runAnalysis() {
  if (images.value.length === 0) {
    error.value = 'Najpierw wgraj zdjęcia.'
    return
  }
  error.value = null
  loading.value = true
  isSwapped.value = false

  saveActiveImageState()

  try {
    const analysisPromises = images.value.map(async (img) => {
      const res = await analyzeImage(img.file, {
        ...img.params,
        stage: 4,
        scale_enabled: img.scalePxLength > 0,
        scale_px_length: img.scalePxLength,
        scale_physical_value: img.scalePhysicalValue,
        scale_unit: img.scaleUnit,
      })
      img.result = res
      img.shapeFactors = {
        avgD1CircularityPerimeter: res.avg_d1_circularity_perimeter,
        avgD2CircularityArea: res.avg_d2_circularity_area,
        avgEdgeIndicator: res.avg_edge_indicator,
        avgShapeFactorRaw: res.avg_shape_factor_raw,
        avgRoundnessEllipse: res.avg_roundness_ellipse,
        avgMalinowskaFactor: res.avg_malinowska_factor,
      }
      return res
    })

    const results = await Promise.all(analysisPromises)

    // Save result of the currently active image
    if (activeImageIndex.value >= 0 && activeImageIndex.value < images.value.length) {
      const activeRes = images.value[activeImageIndex.value].result
      result.value = activeRes
      workflow.inferenceTimeMs = activeRes?.inference_time_ms ?? null
      workflow.totalExecutionTimeMs = activeRes?.total_execution_time_ms ?? null
      workflow.tPreprocessMs = activeRes?.t_preprocess_ms ?? null
      workflow.tSegmentMs = activeRes?.t_segment_ms ?? null
      workflow.tMorphologyMs = activeRes?.t_morphology_ms ?? null
      workflow.tStereologyMs = activeRes?.t_stereology_ms ?? null
      workflow.tEncodingMs = activeRes?.t_encoding_ms ?? null
    }

    computeAverageMetrics(results)

    workflow.goToStage(6) // go to Wyniki (step 6)
  } catch (e) {
    error.value = e.message || 'Analiza nie powiodła się.'
  } finally {
    loading.value = false
  }
}

function computeAverageMetrics(results) {
  if (!results || results.length === 0) return

  const count = results.length
  let totalAa = 0, totalPoreCount = 0
  let totalRoiArea = 0, totalAvgPoreArea = 0, totalNa = 0
  let totalD1 = 0, totalD2 = 0, totalEdge = 0, totalShape = 0, totalRoundness = 0, totalMalinowska = 0
  let totalInference = 0, totalTotalTime = 0
  let totalPreprocess = 0, totalSegment = 0, totalMorphology = 0, totalStereology = 0, totalEncoding = 0
  let mlCount = 0
  let timeCount = 0
  let prepCount = 0, segCount = 0, morphCount = 0, stereologyCount = 0, encodingCount = 0

  let scaleCount = 0
  results.forEach(res => {
    totalAa += res.aa_percent
    totalPoreCount += res.pore_count
    
    if (res.inference_time_ms !== null && res.inference_time_ms !== undefined) {
      totalInference += res.inference_time_ms
      mlCount++
    }
    if (res.total_execution_time_ms !== null && res.total_execution_time_ms !== undefined) {
      totalTotalTime += res.total_execution_time_ms
      timeCount++
    }
    if (res.t_preprocess_ms !== null && res.t_preprocess_ms !== undefined) {
      totalPreprocess += res.t_preprocess_ms
      prepCount++
    }
    if (res.t_segment_ms !== null && res.t_segment_ms !== undefined) {
      totalSegment += res.t_segment_ms
      segCount++
    }
    if (res.t_morphology_ms !== null && res.t_morphology_ms !== undefined) {
      totalMorphology += res.t_morphology_ms
      morphCount++
    }
    if (res.t_stereology_ms !== null && res.t_stereology_ms !== undefined) {
      totalStereology += res.t_stereology_ms
      stereologyCount++
    }
    if (res.t_encoding_ms !== null && res.t_encoding_ms !== undefined) {
      totalEncoding += res.t_encoding_ms
      encodingCount++
    }

    if (res.total_roi_area_physical !== null && res.total_roi_area_physical !== undefined) {
      totalRoiArea += res.total_roi_area_physical
      totalAvgPoreArea += res.average_pore_area_physical || 0
      totalNa += res.N_A || 0
      totalD1 += res.avg_d1_circularity_perimeter || 0
      totalD2 += res.avg_d2_circularity_area || 0
      totalShape += res.avg_shape_factor_raw || 0
      scaleCount++
    }

    totalEdge += res.avg_edge_indicator || 0
    totalRoundness += res.avg_roundness_ellipse || 0
    totalMalinowska += res.avg_malinowska_factor || 0
  })

  workflow.avgAaPercent = totalAa / count
  workflow.avgPoreCount = totalPoreCount / count
  workflow.avgEdgeIndicator = totalEdge / count
  workflow.avgRoundnessEllipse = totalRoundness / count
  workflow.avgMalinowskaFactor = totalMalinowska / count
  workflow.avgInferenceTimeMs = mlCount > 0 ? totalInference / mlCount : null
  workflow.avgTotalExecutionTimeMs = timeCount > 0 ? totalTotalTime / timeCount : null
  workflow.avgPreprocessMs = prepCount > 0 ? totalPreprocess / prepCount : null
  workflow.avgSegmentMs = segCount > 0 ? totalSegment / segCount : null
  workflow.avgMorphologyMs = morphCount > 0 ? totalMorphology / morphCount : null
  workflow.avgStereologyMs = stereologyCount > 0 ? totalStereology / stereologyCount : null
  workflow.avgEncodingMs = encodingCount > 0 ? totalEncoding / encodingCount : null



  if (scaleCount > 0) {
    workflow.avgTotalRoiArea = totalRoiArea / scaleCount
    workflow.avgPoreArea = totalAvgPoreArea / scaleCount
    workflow.avgNa = totalNa / scaleCount
    workflow.avgD1CircularityPerimeter = totalD1 / scaleCount
    workflow.avgD2CircularityArea = totalD2 / scaleCount
    workflow.avgShapeFactorRaw = totalShape / scaleCount
  } else {
    workflow.avgTotalRoiArea = null
    workflow.avgPoreArea = null
    workflow.avgNa = null
    workflow.avgD1CircularityPerimeter = null
    workflow.avgD2CircularityArea = null
    workflow.avgShapeFactorRaw = null
  }
}

function toggleSwap() {
  isSwapped.value = !isSwapped.value
}

function downloadMask() {
  if (!maskDataUrl.value) return
  const link = document.createElement('a')
  link.href = maskDataUrl.value
  link.download = `maska-segmentacji-${file.value?.name || 'obraz'}.png`
  link.click()
}

function downloadRoiCrop() {
  if (!roiCropDataUrl.value) return
  const link = document.createElement('a')
  link.href = roiCropDataUrl.value
  link.download = `obszar-roi-${file.value?.name || 'obraz'}.png`
  link.click()
}

function handlePrevStage() {
  if (activePipelineStep.value <= 1) {
    openFilePicker()
  } else {
    goToPipelineStep(activePipelineStep.value - 1)
  }
}

function handleNextStage() {
  if (activePipelineStep.value < 6) {
    goToPipelineStep(activePipelineStep.value + 1)
  }
}
</script>

<style scoped>
/* Sidebar image list for stage 1 (Obraz) */
.sidebar-image-list {
  margin-top: 10px;
  display: grid;
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--outline) var(--surface-2);
}

/* Custom premium scrollbar for sidebar image list */
.sidebar-image-list::-webkit-scrollbar {
  width: 5px;
}

.sidebar-image-list::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: 99px;
}

.sidebar-image-list::-webkit-scrollbar-thumb {
  background: var(--outline);
  border-radius: 99px;
}

.sidebar-image-list::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

.sidebar-image-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid var(--outline);
  background: var(--surface-3);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-image-item:hover {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 5%, var(--surface-3));
}

.sidebar-image-item.active {
  border-color: var(--primary);
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, var(--surface-3));
  font-weight: 600;
}

.sidebar-image-name {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  margin-right: 8px;
}

.sidebar-image-del {
  background: transparent;
  border: none;
  color: var(--text-soft);
  font-size: 14px;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.sidebar-image-del:hover {
  color: #ef4444;
}

.metric-toggle-group .toggle-btn {
  font: 700 9px 'Space Grotesk', sans-serif;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  transition: all 0.2s ease;
}

.metric-toggle-group .toggle-btn.active {
  background: var(--primary) !important;
  color: var(--primary-text) !important;
  border-color: var(--primary) !important;
}
</style>

<style>
.workspace-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 260px;
  gap: 0.6rem;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

@media (max-width: 1300px) {
  .workspace-grid {
    grid-template-columns: 280px minmax(0, 1fr);
  }
}

@media (max-width: 980px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

.panel {
  border: 1px solid var(--panel-border);
  border-radius: 0.75rem;
  background: var(--panel-bg);
  padding: 0.7rem;
  min-height: 0;
  box-shadow: var(--panel-shadow);
}

.panel h3 {
  margin: 0 0 0.55rem;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--text-main);
}

.panel h4 {
  margin: 0 0 0.4rem;
  font-size: 0.78rem;
  color: var(--text-soft);
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  overflow: auto;
}

.panel-block {
  display: grid;
  gap: 0.45rem;
}

.upload-zone {
  display: flex;
  min-height: 100px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--upload-border);
  border-radius: 0.75rem;
  background: var(--upload-bg);
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.upload-zone:hover {
  border-color: #94a3b8;
  background: var(--upload-hover);
}

.upload-zone.dragging {
  border-color: #34d399;
  background: #0f2b2c;
}

.upload-zone .upload-text {
  font-size: 0.82rem;
  color: var(--text-main);
}

.upload-zone .upload-hint {
  margin-top: 0.25rem;
  font-size: 0.72rem;
  color: var(--text-soft);
}

.upload-zone .upload-loading {
  color: var(--text-soft);
}

.upload-zone input[type="file"] {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.upload-error {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #fda4af;
}

.app-root.theme-dark .upload-zone.dragging {
  border-color: #34d399;
  background: #0f2b2c;
}

.app-root.theme-dark .upload-error {
  color: #fda4af;
}

.app-root.theme-dark .stage-note {
  background: #0a1220;
  color: #cbd5e1;
}

.app-root.theme-dark .mask-preview img {
  border-color: #334155;
  background: #0f172a;
}

.stitch-main {
  margin-left: 320px;
  height: calc(100vh - 56px);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.content-row {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 12px;
  padding: 6px 12px 12px;
}

.bottom-bar {
  height: 48px;
  min-height: 48px;
  max-height: 48px;
  border-top: 1px solid var(--outline);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-sizing: border-box;
}

.bottom-viewer-controls {
  display: flex;
  gap: 8px;
}

.bottom-btn {
  background: var(--surface-3);
  border: 1px solid var(--outline);
  color: var(--text);
  font: 600 10px/1 'Space Grotesk', sans-serif;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.bottom-btn:hover:not(:disabled) {
  background: var(--primary);
  color: var(--primary-text);
  border-color: var(--primary);
}

.bottom-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.bottom-btn.btn-active {
  border-color: var(--primary);
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 12%, transparent);
}

.bottom-api-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font: 700 9px 'Space Grotesk', sans-serif;
  color: var(--text-soft);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.bottom-api-status.ok .status-dot {
  background: #10b981;
}

.bottom-api-status.error .status-dot {
  background: #ef4444;
}

.bottom-api-status.checking .status-dot {
  background: #f59e0b;
}

.bottom-btn-mini {
  background: transparent;
  border: 1px solid var(--outline);
  color: var(--text-muted);
  font: 600 9px 'Space Grotesk', sans-serif;
  padding: 3px 6px;
  cursor: pointer;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-left: 4px;
}

.bottom-btn-mini:hover {
  border-color: var(--text-soft);
  color: var(--text);
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-soft);
  font: 500 11px/1.2 'Space Grotesk', sans-serif;
  color: var(--text);
}

.status .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #36ffc4;
  box-shadow: 0 0 8px rgba(54, 255, 196, 0.5);
}

.help-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
  background: color-mix(in srgb, #000 55%, transparent);
  display: grid;
  place-items: center;
  padding: 16px;
}

.help-modal {
  width: min(560px, 100%);
  border: 1px solid var(--outline);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.35);
}

.help-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--outline);
}

.help-modal-header h2 {
  margin: 0;
  font: 700 1rem/1.2 'Space Grotesk', sans-serif;
  letter-spacing: 0.02em;
}

.help-close-btn {
  border: 1px solid var(--outline);
  background: var(--surface-2);
  color: var(--text);
  border-radius: 8px;
  width: 32px;
  height: 32px;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.help-modal-content {
  padding: 14px 16px 16px;
  display: grid;
  gap: 10px;
  color: var(--text-soft);
}

.help-modal-content p {
  margin: 0;
  font: 500 13px/1.5 'Inter', sans-serif;
}

.roi-manual-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.45rem;
}

.roi-manual-grid label {
  font-size: 0.66rem;
}

.roi-manual-grid input {
  width: 100%;
}

.stitch-dashboard .roi-overlay {
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}

.stitch-dashboard.is-roi-dragging,
.stitch-dashboard.is-roi-dragging * {
  user-select: none !important;
  -webkit-user-select: none !important;
}

@media (max-width: 1360px) {
  .stitch-main {
    margin-left: 288px;
  }

  .content-row {
    grid-template-columns: minmax(0, 1fr) minmax(220px, 26vw);
  }
}

@media (max-width: 1100px) {
  .stitch-main {
    margin-left: 250px;
  }

  .content-row {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 860px) {
  .stitch-dashboard {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    height: auto;
  }

  .stitch-main {
    margin-left: 0;
    margin-top: 0;
    height: auto;
    min-height: 0;
    flex: 1;
  }

  .content-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
