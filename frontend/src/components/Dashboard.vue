<template>
  <div class="stitch-dashboard" :class="['theme-' + theme, { 'is-roi-dragging': roiDraggingUi }]">
    <DashboardTopBar :theme="theme" @toggle-theme="toggleTheme" @open-help="openHelp" />

    <ScientificSidebar :tool-actions="toolActions" :active-tool="activeTool" @select-tool="activateTool">
      <label>
        <span>Intensywnosc filtru medianowego</span>
        <small>{{ params.denoise_kernel_size }} px</small>
        <input v-model.number="params.denoise_kernel_size" type="range" min="1" max="15" step="1" />
      </label>
      <label>
        <span>Kontrast podgladu</span>
        <small>{{ contrastPercent }}%</small>
        <input v-model.number="contrastPercent" type="range" min="60" max="180" step="5" />
      </label>
      <label>
        <span>Prog binaryzacji</span>
        <small>{{ params.manual_threshold }}</small>
        <input v-model.number="params.manual_threshold" type="range" min="0" max="255" step="1" />
      </label>
      <label>
        <span>Wybor modelu</span>
        <select v-model="selectedModel">
          <option value="DeepMetal-V4.2_ResNet">DeepMetal-V4.2_ResNet</option>
          <option value="DeepMetal-V3.7_EfficientNet">DeepMetal-V3.7_EfficientNet</option>
          <option value="GrainVision-Base">GrainVision-Base</option>
        </select>
      </label>
      <button type="button" class="execute-btn" :disabled="loading || !file" @click="runAnalysis">
        <span class="material-symbols-outlined">play_arrow</span>
        {{ loading ? 'Trwa analiza...' : 'Uruchom analize' }}
      </button>
    </ScientificSidebar>

    <main class="stitch-main">
      <PipelineStepBar :steps="pipelineSteps" :active-step="activePipelineStep" @step="goToPipelineStep" />

      <div class="content-row">
        <StitchViewer
          :roi-data-url="roiDataUrl"
          :is-dragging="isDragging"
          :error="error"
          :frame-style="frameStyle"
          :contrast-percent="contrastPercent"
          :displayed-roi-box="displayedRoiBox"
          :drawing="drawing"
          :roi-meta="params.roi"
          @drop="onDrop"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @wheel-image="onImageWheel"
          @image-load="onImageLoaded"
          @begin-roi="beginRoiSelection"
          @begin-move-roi="beginMoveRoi"
          @begin-resize-roi="beginResizeRoi"
          @zoom-in="zoomIn"
          @zoom-out="zoomOut"
          @reset-view="resetView"
          @clear-roi="clearRoi"
          @open-file-picker="openFilePicker"
        />

        <DashboardMetrics
          :histogram-bins="histogramBins"
          :metric-cards="metricCards"
          :aa-percent="aaPercent"
          :vv-percent="vvPercent"
          :pore-count="poreCount"
          :mask-data-url="maskDataUrl"
          :health-message="health.message"
          @refresh-health="checkHealth"
        />
      </div>
    </main>

    <input ref="fileInputRef" type="file" accept="image/*" @change="onFileInput" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useWorkflowStore } from '../stores/workflow'
import { analyzeImage } from '../api/analyze'
import DashboardTopBar from './dashboard/DashboardTopBar.vue'
import ScientificSidebar from './dashboard/ScientificSidebar.vue'
import PipelineStepBar from './dashboard/PipelineStepBar.vue'
import StitchViewer from './dashboard/StitchViewer.vue'
import DashboardMetrics from './dashboard/DashboardMetrics.vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const workflow = useWorkflowStore()
const file = ref(null)
const result = ref(null)
const error = ref(null)
const loading = ref(false)
const theme = ref('dark')
const isDragging = ref(false)
const localPreview = ref(null)
const fileInputRef = ref(null)
const imageNatural = reactive({ width: 0, height: 0 })
const imageRender = reactive({ width: 0, height: 0 })
const imageStats = reactive({ mean: null, stdDev: null, snr: null })
const histogramBins = ref(Array.from({ length: 24 }, () => 0))
const health = ref({ status: 'checking', message: 'Sprawdzanie polaczenia...' })
const roiDraggingUi = ref(false)

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
const contrastPercent = ref(100)

const currentStage = computed(() => workflow.currentStage)
const maskDataUrl = computed(() => result.value?.mask_b64 ? `data:image/png;base64,${result.value.mask_b64}` : null)
const roiDataUrl = computed(() => localPreview.value)
const aaPercent = computed(() => result.value?.aa_percent ?? null)
const vvPercent = computed(() => result.value?.vv_percent ?? null)
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
const pipelineSteps = computed(() => ([
  { id: 1, label: 'Akwizycja obrazu' },
  { id: 2, label: 'ROI i przetwarzanie wstepne' },
  { id: 3, label: 'Segmentacja (ML)' },
  { id: 4, label: 'Analiza cech' },
  { id: 5, label: 'Wyniki' },
]))
const activePipelineStep = computed(() => {
  if (!file.value) return 1
  if (result.value) return 5
  return Math.min(4, currentStage.value + 1)
})

function goToPipelineStep(step) {
  if (step === 1 || step === 2) workflow.goToStage(1)
  if (step === 3) workflow.goToStage(2)
  if (step === 4) workflow.goToStage(3)
  if (step === 5) workflow.goToStage(4)
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
  if (workflow.currentStage !== 1 || !file.value) return
  if (view.spacePressed || e.button === 1) {
    beginPan(e)
    return
  }
  if (e.button !== 0) return
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
  window.alert('Pomoc: 1) Wgraj obraz, 2) Zaznacz ROI, 3) Ustaw parametry, 4) Kliknij "Uruchom analize".')
}

function activateTool(tool) {
  activeTool.value = tool
  if (tool === 'Przytnij ROI') workflow.goToStage(1)
  if (tool === 'Filtr medianowy') {
    workflow.goToStage(1)
    params.denoise_enabled = true
    params.denoise_method = 'median'
  }
  if (tool === 'Progowanie') {
    workflow.goToStage(2)
    params.binarization_method = 'manual'
  }
  if (tool === 'Kontrast') workflow.goToStage(1)
  if (tool === 'Eksport') exportAnalysis()
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
    params: { ...params, contrast_percent: contrastPercent.value },
    metrics: {
      aa_percent: result.value.aa_percent,
      vv_percent: result.value.vv_percent,
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
    ctx.filter = `contrast(${contrastPercent.value}%)`
    ctx.drawImage(image, 0, 0, width, height)
    const pixels = ctx.getImageData(0, 0, width, height).data
    const bins = Array.from({ length: 24 }, () => 0)
    let sum = 0
    let sumSq = 0
    let count = 0
    for (let i = 0; i < pixels.length; i += 4) {
      const lum = 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2]
      bins[Math.min(23, Math.floor(lum / (256 / 24)))] += 1
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

watch(roiDataUrl, () => {
  computeImageAnalytics()
})

watch(contrastPercent, () => {
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
</script>