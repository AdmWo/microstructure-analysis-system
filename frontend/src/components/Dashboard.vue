<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useWorkflowStore } from '../stores/workflow'
import { analyzeImage } from '../api/analyze'
import UploadPanel from './dashboard/UploadPanel.vue'
import StageControls from './dashboard/StageControls.vue'
import ImageWorkspace from './dashboard/ImageWorkspace.vue'
import InterpretationPanel from './dashboard/InterpretationPanel.vue'
import WorkflowTimeline from './dashboard/WorkflowTimeline.vue'

const workflow = useWorkflowStore()
const file = ref(null)
const result = ref(null)
const error = ref(null)
const loading = ref(false)
const isDragging = ref(false)
const localPreview = ref(null)
const imageNatural = reactive({ width: 0, height: 0 })
const imageRender = reactive({ width: 0, height: 0 })
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

function setFile(f) {
  file.value = f
  error.value = null
  result.value = null
  localPreview.value = URL.createObjectURL(f)
  params.roi = null
  workflow.reset()
  resetView()
}

function onImageLoaded(e) {
  imageNatural.width = e.target.naturalWidth
  imageNatural.height = e.target.naturalHeight
  updateImageRenderSize()
}

function updateImageRenderSize() {
  const overlay = document.querySelector('.image-frame .roi-overlay')
  if (!overlay) return
  const rect = overlay.getBoundingClientRect()
  imageRender.width = rect.width
  imageRender.height = rect.height
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
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateImageRenderSize)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
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
  <div class="dashboard">
    <section class="workspace-grid">
      <UploadPanel :loading="loading" :is-dragging="isDragging" :error="error" @drop="onDrop" @dragover="onDragOver" @dragleave="onDragLeave" @file-select="setFile">
        <StageControls :current-stage="currentStage" :params="params" :loading="loading" :has-file="!!file" @run="runAnalysis" />
      </UploadPanel>

      <ImageWorkspace
        :roi-data-url="roiDataUrl"
        :current-stage="currentStage"
        :displayed-roi-box="displayedRoiBox"
        :drawing="drawing"
        :params="params"
        :view="view"
        :view-transform="viewTransform"
        @image-load="onImageLoaded"
        @wheel-image="onImageWheel"
        @zoom-in="zoomIn"
        @zoom-out="zoomOut"
        @reset-view="resetView"
        @begin-roi="beginRoiSelection"
        @begin-move-roi="beginMoveRoi"
        @begin-resize-roi="beginResizeRoi"
        @move-roi="moveRoiSelection"
        @finish-roi="finishRoiSelection"
        @clear-roi="clearRoi"
        @update-manual-roi="updateManualRoi"
      />

      <InterpretationPanel :aa-percent="aaPercent" :vv-percent="vvPercent" :pore-count="poreCount" :mask-data-url="maskDataUrl" />
    </section>

    <WorkflowTimeline
      :stages="workflow.stages"
      :current-stage="currentStage"
      :is-first-stage="workflow.isFirstStage"
      :is-last-stage="workflow.isLastStage"
      @go-stage="workflow.goToStage"
      @prev="workflow.previousStage"
      @next="workflow.nextStage"
    />
  </div>
</template>
