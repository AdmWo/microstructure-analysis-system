<template>
  <div class="stitch-dashboard" :class="['theme-' + theme, { 'is-roi-dragging': roiDraggingUi }]">
    <DashboardTopBar :theme="theme" @toggle-theme="toggleTheme" @open-help="openHelp" />

    <ScientificSidebar
      :current-stage="currentStage"
      :steps="pipelineSteps"
      :active-step="activePipelineStep"
      :stage-title="currentStageTitle"
      :stage-description="currentStageDesc"
      @step="goToPipelineStep"
      @prev="handlePrevStage"
      @next="handleNextStage"
    >
      <template v-if="currentStage === 1">
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
          <button type="button" class="mini-btn" @click="setRoiToFullImage">ROI = caly obraz</button>
        </label>
        <label class="toggle-row">
          <input type="checkbox" v-model="params.invert_roi" />
          <span>Inwertuj ROI (wplywa na API)</span>
        </label>
      </template>

      <template v-else-if="currentStage === 2">
        <label>
          <span>Metoda binaryzacji (API)</span>
          <select id="binarization-method" name="binarization_method" v-model="params.binarization_method">
            <option value="otsu">Otsu — automatyczny prog</option>
            <option value="manual">Reczny prog</option>
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

      <template v-else-if="currentStage === 3">
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
      <button type="button" class="execute-btn" :disabled="loading || !file" @click="runAnalysis">
        <svg class="execute-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 5v14l11-7z" fill="currentColor" />
        </svg>
        {{ loading ? 'Trwa analiza...' : 'Uruchom analize' }}
      </button>
    </ScientificSidebar>

    <main class="stitch-main">
      <div class="content-row">
        <StitchViewer
          :roi-data-url="roiDataUrl"
          :is-dragging="isDragging"
          :error="error"
          :frame-style="frameStyle"
          :contrast-percent="params.contrast_percent"
          :invert-roi="params.invert_roi"
          :can-edit-roi="currentStage === 1"
          :displayed-roi-box="displayedRoiBox"
          :drawing="drawing"
          :is-swapped="isSwapped"
          :mask-data-url="maskDataUrl"
          @drop="onDrop"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @wheel-image="onImageWheel"
          @image-load="onImageLoaded"
          @begin-roi="beginRoiSelection"
          @begin-move-roi="beginMoveRoi"
          @begin-resize-roi="beginResizeRoi"
          @open-file-picker="openFilePicker"
        />

        <DashboardMetrics
          :histogram-bins="histogramBins"
          :threshold-percent="histogramThresholdPercent"
          :threshold-value="activeThresholdValue"
          :ghost-threshold-percent="ghostThresholdPercent"
          :ghost-threshold-value="ghostThresholdValue"
          :histogram-note="histogramNote"
          :metric-cards="metricCards"
          :aa-percent="aaPercent"
          :pore-count="poreCount"
          :mask-data-url="maskDataUrl"
          :is-swapped="isSwapped"
          :roi-crop-data-url="roiCropDataUrl"
          :can-swap="activePipelineStep === 5"
          @toggle-swap="toggleSwap"
          @download-mask="downloadMask"
          @download-roi="downloadRoiCrop"
        />
      </div>

      <div class="bottom-bar">
        <div class="bottom-viewer-controls">
          <button type="button" class="bottom-btn" @click="zoomIn" title="Powiększ">+</button>
          <button type="button" class="bottom-btn" @click="zoomOut" title="Pomniejsz">-</button>
          <button type="button" class="bottom-btn" @click="resetView">Dopasuj</button>
          <button type="button" class="bottom-btn" @click="clearRoi" :disabled="!params.roi">Wyczyść ROI</button>
          <button v-if="maskDataUrl && activePipelineStep === 5" type="button" class="bottom-btn" @click="toggleSwap" :class="{ 'btn-active': isSwapped }">
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

    <input ref="fileInputRef" type="file" accept="image/*" @change="onFileInput" />

    <div v-if="helpOpen" class="help-modal-backdrop" @click.self="closeHelp">
      <section class="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <header class="help-modal-header">
          <h2 id="help-title">Pomoc</h2>
          <button type="button" class="help-close-btn" @click="closeHelp" aria-label="Zamknij pomoc">×</button>
        </header>
        <div class="help-modal-content">
          <p>1) Wgraj obraz.</p>
          <p>2) Ustaw ROI i parametry przetwarzania.</p>
          <p>3) Wybierz binaryzacje i uruchom analize.</p>
          <p>4) Maska wynikowa pokazuje pory jako obszary jasne, a material jako ciemny.</p>
          <p>5) Timeline u gory zmienia etap pracy, a panel po lewej pokazuje sterowanie dla aktualnego etapu.</p>
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
const histogramBins = ref(Array.from({ length: 24 }, () => 0))
const localOtsuThreshold = ref(null)
const health = ref({ status: 'checking', message: 'Sprawdzanie polaczenia...' })
const roiDraggingUi = ref(false)
const helpOpen = ref(false)

let savedDocUserSelect = ''
let savedBodyUserSelect = ''
const drawing = reactive({ active: false, x: 0, y: 0, width: 0, height: 0 })
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
  binarization_method: 'otsu',
  manual_threshold: 120,
  morph_open_iterations: 1,
  morph_close_iterations: 1,
})
const selectedModel = ref('DeepMetal-V4.2_ResNet')
const toolActions = ['Przytnij ROI', 'Filtr medianowy', 'Wybór modelu', 'Progowanie', 'Kontrast', 'Eksport']
const activeTool = ref('Przytnij ROI')

const currentStage = computed(() => workflow.currentStage)
const maskDataUrl = computed(() => result.value?.mask_b64 ? `data:image/png;base64,${result.value.mask_b64}` : null)
const roiDataUrl = computed(() => localPreview.value)
const aaPercent = computed(() => result.value?.aa_percent ?? null)
const poreCount = computed(() => result.value?.pore_count ?? null)
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
  { label: 'Jasnosc srednia', value: imageStats.mean !== null ? `${imageStats.mean.toFixed(2)} AU` : 'brak danych' },
  { label: 'Odchylenie standardowe', value: imageStats.stdDev !== null ? `${imageStats.stdDev.toFixed(2)} AU` : 'brak danych' },
  { label: 'Stosunek sygnal/szum', value: imageStats.snr !== null ? `${imageStats.snr.toFixed(2)} dB` : 'brak danych' },
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
  return val !== null ? (val / 255) * 100 : null
})

const ghostThresholdValue = computed(() => {
  if (!result.value || result.value.used_threshold === undefined || result.value.used_threshold === null) return null
  const lastUsed = result.value.used_threshold
  if (lastUsed === activeThresholdValue.value) return null
  return lastUsed
})

const ghostThresholdPercent = computed(() => {
  const val = ghostThresholdValue.value
  return val !== null ? (val / 255) * 100 : null
})

const histogramNote = computed(() => {
  if (!roiDataUrl.value) return 'Wgraj obraz, aby zobaczyc histogram ROI.'
  let note = 'Histogram liczony z aktualnego ROI. '
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
  { id: 3, label: 'Segmentacja (ML)' },
  { id: 4, label: 'Analiza cech' },
  { id: 5, label: 'Wyniki' },
]))
const activePipelineStep = computed(() => {
  if (!file.value) return 1
  return Math.min(5, currentStage.value + 1)
})

const currentStageTitle = computed(() => {
  switch (activePipelineStep.value) {
    case 1:
      return 'Obraz'
    case 2:
      return 'Przetwarzanie Wstępne'
    case 3:
      return 'Segmentacja (ML)'
    case 4:
      return 'Analiza cech'
    case 5:
      return 'Wyniki'
    default:
      return ''
  }
})

const currentStageDesc = computed(() => {
  switch (activePipelineStep.value) {
    case 1:
      return 'Etap przygotowania obrazu: wgraj plik graficzny z dysku lub przeciągnij go do obszaru roboczego, aby rozpocząć proces analizy struktury porowatej.'
    case 2:
      return 'Etap przygotowania: pozwala na zdefiniowanie obszaru zainteresowania (ROI) na obrazie wejściowym oraz wstępne dostosowanie jasności/kontrastu i filtrów wygładzających.'
    case 3:
      return 'Etap binaryzacji: segmentacja obrazu. Umożliwia dobór progu odcięcia (ręczny suwak lub automatyczna metoda Otsu) w celu odróżnienia porów od tła metalicznego.'
    case 4:
      return 'Etap morfologii: oczyszczanie maski binarnej za pomocą operacji morfologicznego otwarcia (usuwanie drobnych szumów) oraz domknięcia (łączenie pęknięć i luk).'
    case 5:
      return 'Etap wyników: prezentacja obliczonych wskaźników stereologicznych (porowatość powierzchniowa i objętościowa) oraz eksport kompletnego raportu z pomiaru.'
    default:
      return ''
  }
})

function goToPipelineStep(step) {
  if (step === 1) {
    openFilePicker()
    return
  }
  if (!file.value) {
    error.value = 'Najpierw wgraj obraz, aby przejsc dalej w workflow.'
    return
  }
  if (step === 2) workflow.goToStage(1)
  if (step === 3) workflow.goToStage(2)
  if (step === 4) workflow.goToStage(3)
  if (step === 5) workflow.goToStage(4)
}

function setRoiToFullImage() {
  if (!imageNatural.width || !imageNatural.height) return
  params.roi = { x: 0, y: 0, width: imageNatural.width, height: imageNatural.height }
}

function onDrop(e) {
  isDragging.value = false
  e.preventDefault()
  const f = e.dataTransfer?.files?.[0]
  if (f?.type?.startsWith('image/')) {
    setFile(f)
  } else {
    error.value = 'Upuść poprawny plik obrazu (PNG, JPEG itp.).'
  }
}

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onFileInput(event) {
  const selected = event.target.files?.[0]
  if (selected?.type?.startsWith('image/')) {
    setFile(selected)
  }
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function setFile(f) {
  file.value = f
  error.value = null
  result.value = null
  localPreview.value = URL.createObjectURL(f)
  params.roi = null
  workflow.reset()
  resetView()
  isSwapped.value = false
  nextTick(computeImageAnalytics)
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
  /** Po zoomie mapuj proporcjonalnie; gdy kursor jest poza prostokatem obrazu — przyklej do krawedzi overlay. */
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
  if (view.panning || cropInteraction.active) ev.preventDefault()
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
  if (workflow.currentStage !== 1) {
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
  if (workflow.currentStage !== 1 || !displayedRoiBox.value) return
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
  if (workflow.currentStage !== 1 || !displayedRoiBox.value) return
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

function activateTool(tool) {
  activeTool.value = tool
  if (tool === 'Przytnij ROI') return
  if (tool === 'Filtr medianowy') {
    params.denoise_enabled = true
    params.denoise_method = 'median'
  }
  if (tool === 'Progowanie') {
    params.binarization_method = 'manual'
    params.manual_threshold = Math.max(0, Math.min(255, params.manual_threshold))
  }
  if (tool === 'Wybór modelu') return
  if (tool === 'Kontrast') {
    params.contrast_percent = Math.max(50, Math.min(200, params.contrast_percent))
  }
  if (tool === 'Eksport') {
    exportAnalysis()
  }
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

function exportAnalysis() {
  if (!result.value) {
    error.value = 'Brak wyniku do eksportu. Najpierw uruchom analize.'
    return
  }
  const payload = {
    model: selectedModel.value,
      params: { ...params },
    metrics: {
      aa_percent: result.value.aa_percent,
      pore_count: result.value.pore_count,
    },
    generated_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'wynik-analizy.json'
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
    const bins = Array.from({ length: 24 }, () => 0)
    const hist256 = new Array(256).fill(0)
    let sum = 0
    let sumSq = 0
    let count = 0
    for (let i = 0; i < pixels.length; i += 4) {
      const lum = Math.round(0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2])
      bins[Math.min(23, Math.floor(lum / (256 / 24)))] += 1
      hist256[Math.min(255, Math.max(0, lum))]++
      sum += lum
      sumSq += lum * lum
      count += 1
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
  if (newStep !== 5) {
    isSwapped.value = false
  }
})

watch(roiDataUrl, () => {
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

async function runAnalysis() {
  if (!file.value) {
    error.value = 'Najpierw wgraj obraz.'
    return
  }
  error.value = null
  result.value = null
  loading.value = true
  isSwapped.value = false

  try {
    result.value = await analyzeImage(file.value, {
      ...params,
      stage: 4,
    })
    workflow.goToStage(4)
  } catch (e) {
    error.value = e.message || 'Analiza nie powiodła się.'
  } finally {
    loading.value = false
  }
}

function toggleSwap() {
  isSwapped.value = !isSwapped.value
}

function downloadMask() {
  if (!maskDataUrl.value) return
  const link = document.createElement('a')
  link.href = maskDataUrl.value
  link.download = 'maska-segmentacji.png'
  link.click()
}

function downloadRoiCrop() {
  if (!roiCropDataUrl.value) return
  const link = document.createElement('a')
  link.href = roiCropDataUrl.value
  link.download = 'obszar-roi.png'
  link.click()
}

function handlePrevStage() {
  if (activePipelineStep.value <= 2) {
    openFilePicker()
  } else {
    goToPipelineStep(activePipelineStep.value - 1)
  }
}

function handleNextStage() {
  if (activePipelineStep.value < 5) {
    goToPipelineStep(activePipelineStep.value + 1)
  }
}
</script>