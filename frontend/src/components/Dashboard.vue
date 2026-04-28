<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useWorkflowStore } from '../stores/workflow'
import { analyzeImage } from '../api/analyze'

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

function clampToImageBounds(e) {
  const target = e.target instanceof Element ? e.target : null
  const current = e.currentTarget instanceof Element ? e.currentTarget : null
  const overlay = target?.closest('.roi-overlay') || current?.closest('.roi-overlay') || current
  const rect = overlay?.getBoundingClientRect()
  if (!rect) return null
  imageRender.width = rect.width
  imageRender.height = rect.height
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))
  return { x, y }
}

function beginRoiSelection(e) {
  if (workflow.currentStage !== 1 || !file.value) return
  if (view.spacePressed || e.button === 1) {
    beginPan(e)
    return
  }
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
}

function beginMoveRoi(e) {
  if (workflow.currentStage !== 1 || !displayedRoiBox.value) return
  e.stopPropagation()
  const point = clampToImageBounds(e)
  if (!point) return
  cropInteraction.active = true
  cropInteraction.mode = 'move'
  cropInteraction.startX = point.x
  cropInteraction.startY = point.y
  cropInteraction.originBox = { ...displayedRoiBox.value }
}

function beginResizeRoi(handle, e) {
  if (workflow.currentStage !== 1 || !displayedRoiBox.value) return
  e.stopPropagation()
  const point = clampToImageBounds(e)
  if (!point) return
  cropInteraction.active = true
  cropInteraction.mode = 'resize'
  cropInteraction.handle = handle
  cropInteraction.startX = point.x
  cropInteraction.startY = point.y
  cropInteraction.originBox = { ...displayedRoiBox.value }
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
  const point = clampToImageBounds(e)
  if (!point) return
  view.panning = true
  view.startX = e.clientX
  view.startY = e.clientY
  view.startOffsetX = view.offsetX
  view.startOffsetY = view.offsetY
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

function updateManualRoi(manualRoi) {
  if (!manualRoi || !imageNatural.width || !imageNatural.height) {
    params.roi = null
    return
  }
  const x = Math.max(0, Math.min(Math.round(manualRoi.x || 0), imageNatural.width - 1))
  const y = Math.max(0, Math.min(Math.round(manualRoi.y || 0), imageNatural.height - 1))
  params.roi = {
    x,
    y,
    width: Math.max(1, Math.min(Math.round(manualRoi.width || 1), imageNatural.width - x)),
    height: Math.max(1, Math.min(Math.round(manualRoi.height || 1), imageNatural.height - y)),
  }
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

<template>
  <div class="stitch-dashboard" :class="`theme-${theme}`">
    <header class="stitch-topbar">
      <div class="brand-wrap">
        <span class="brand-title">System analizy mikrostruktury</span>
      </div>
      <div class="top-icons">
        <button type="button" class="icon-btn" @click="toggleTheme">{{ theme === 'dark' ? 'Tryb jasny' : 'Tryb ciemny' }}</button>
        <button type="button" class="icon-btn" @click="openHelp">Help (?)</button>
      </div>
    </header>

    <aside class="stitch-side-nav">
      <div class="tool-header">
        <h3>Narzedzia naukowe</h3>
        <p>Sterowanie instrumentem</p>
      </div>
      <div class="tool-list">
        <button
          v-for="tool in toolActions"
          :key="tool"
          type="button"
          class="tool-button"
          :class="{ active: activeTool === tool }"
          @click="activateTool(tool)"
        >
          <span>{{ tool }}</span>
        </button>
      </div>

      <div class="control-panel">
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
      </div>
    </aside>

    <main class="stitch-main">
      <div class="pipeline-stepper">
        <button
          v-for="step in pipelineSteps"
          :key="step.id"
          type="button"
          class="pipeline-step"
          :class="{ active: activePipelineStep === step.id, done: activePipelineStep > step.id }"
          @click="goToPipelineStep(step.id)"
        >
          <div class="step-badge">{{ step.id }}</div>
          <span>{{ step.label }}</span>
        </button>
      </div>

      <div class="content-row">
        <section class="viewer-shell" @drop="onDrop" @dragover="onDragOver" @dragleave="onDragLeave">
          <div class="viewer-overlay" v-if="!roiDataUrl">
            <p>{{ isDragging ? 'Upusc obraz, aby rozpoczac analize' : 'Wgraj obraz mikroskopowy, aby zaczac' }}</p>
            <button type="button" @click="openFilePicker">Wybierz obraz</button>
            <p v-if="error" class="error-text">{{ error }}</p>
          </div>

          <div v-else class="stitch-image-frame-wrap" @wheel.prevent="onImageWheel">
            <div class="stitch-image-frame" :style="frameStyle">
              <img :src="roiDataUrl" alt="Mikrostruktura" class="main-image" draggable="false" :style="{ filter: `contrast(${contrastPercent}%)` }" @load="onImageLoaded" />
              <div class="roi-overlay" @mousedown="beginRoiSelection" @mousemove="moveRoiSelection" @mouseup="finishRoiSelection" @mouseleave="finishRoiSelection">
                <div
                  v-if="displayedRoiBox"
                  class="roi-box"
                  :style="{ left: `${displayedRoiBox.left}px`, top: `${displayedRoiBox.top}px`, width: `${displayedRoiBox.width}px`, height: `${displayedRoiBox.height}px` }"
                  @mousedown.stop="beginMoveRoi"
                >
                  <span
                    v-for="handle in ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']"
                    :key="handle"
                    class="roi-handle"
                    :class="`handle-${handle}`"
                    @mousedown.stop="beginResizeRoi(handle, $event)"
                  />
                </div>
                <div v-if="drawing.active || (drawing.width && drawing.height)" class="roi-box drawing" :style="{ left: `${drawing.x}px`, top: `${drawing.y}px`, width: `${drawing.width}px`, height: `${drawing.height}px` }" />
              </div>
            </div>
          </div>

          <div class="viewer-meta">
            <div>MAG: 1000x</div>
            <div>EHT: 20.00 kV</div>
            <div>WD: 8.5 mm</div>
            <div v-if="params.roi">ROI: {{ params.roi.x }}, {{ params.roi.y }} / {{ params.roi.width }}x{{ params.roi.height }}</div>
          </div>
          <div class="viewer-controls">
            <button type="button" @click="zoomIn">+</button>
            <button type="button" @click="zoomOut">-</button>
            <button type="button" @click="resetView">Dopasuj</button>
            <button type="button" @click="clearRoi">Wyczysc ROI</button>
          </div>
        </section>

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
          <section class="metric-card" v-if="maskDataUrl">
            <h4>Maska segmentacji</h4>
            <img :src="maskDataUrl" alt="Maska segmentacji" class="mask-image" />
          </section>
          <section class="metric-card status">
            <span class="dot" />
            {{ health.message }}
            <button type="button" class="retry-health" @click="checkHealth">Odswiez</button>
          </section>
        </aside>
      </div>
    </main>

    <input ref="fileInputRef" type="file" accept="image/*" @change="onFileInput" />
  </div>
</template>
