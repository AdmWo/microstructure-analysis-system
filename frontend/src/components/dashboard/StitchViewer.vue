<template>
  <section class="viewer-shell" @drop="emit('drop', $event)" @dragover="emit('dragover', $event)" @dragleave="emit('dragleave')">

    <!-- STAGE 1: Grid Gallery View -->
    <div v-if="currentStage === 1 && images && images.length > 0" class="viewer-grid-mode">
      <div class="grid-header">
        <h3>Lista obrazów do analizy ({{ images.length }})</h3>
      </div>
      <div class="images-gallery-grid">
        <div
          v-for="(img, index) in images"
          :key="img.id"
          class="gallery-card"
          :class="{ active: index === activeImageIndex }"
          @click="emit('select-image', index)"
        >
          <div class="gallery-preview-wrap">
            <img :src="img.localPreview" class="gallery-img" />
            <div
              v-if="img.params?.roi && img.imageNatural?.width && img.imageNatural?.height"
              class="gallery-roi-outline"
              :style="getRoiOutlineStyle(img, 1.6)"
            ></div>
            <button type="button" class="gallery-card-delete-btn" @click.stop="emit('delete-image', index)" title="Usuń obraz">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            </button>
          </div>
          <div class="gallery-card-info">
            <span class="gallery-card-name" :title="img.name">{{ img.name }}</span>
            <span class="gallery-card-status" :class="{ 'has-result': img.result }">
              {{ img.result ? 'Przeanalizowano' : 'Gotowy do analizy' }}
            </span>
          </div>
        </div>
        <div class="gallery-card add-card" @click="emit('open-file-picker')">
          <span class="add-icon">+</span>
          <span class="add-text">Dodaj zdjęcia</span>
        </div>
      </div>
    </div>

    <!-- Empty Drop-zone Overlay -->
    <div v-else-if="!roiDataUrl" class="viewer-overlay">
      <p>{{ isDragging ? 'Upusc obrazy, aby rozpoczac analize' : 'Wgraj zdjęcia mikroskopowe, aby zaczac' }}</p>
      <button type="button" @click="emit('open-file-picker')">Wybierz obrazy</button>
      <p v-if="error" class="error-text">{{ error }}</p>
    </div>

    <!-- STAGES 2-6: Editor / Result Canvas View -->
    <template v-else>
      <div class="stitch-image-frame-wrap" @wheel.prevent="emit('wheel-image', $event)">
        <div class="stitch-image-frame" :style="frameStyle">
          <img
            :src="mainImageSrc"
            alt="Mikrostruktura"
            class="main-image"
            draggable="false"
            :style="{ filter: baseImageFilter }"
            @load="emit('image-load', $event)"
          />
          <div v-if="displayedRoiBox && !isSwapped" class="roi-live-invert-layer" :style="roiInvertClipStyle">
            <img :src="roiDataUrl" alt="" class="main-image" draggable="false" :style="{ filter: `contrast(${contrastPercent}%)${invertRoi ? ' invert(100%)' : ''}` }" aria-hidden="true" />
          </div>
          <div
            class="roi-overlay"
            :class="overlayClass"
            @mousedown="emit('begin-roi', $event)"
          >
            <div
              v-if="displayedRoiBox"
              class="roi-box"
              :class="roiBoxClass"
              :style="{ left: `${displayedRoiBox.left}px`, top: `${displayedRoiBox.top}px`, width: `${displayedRoiBox.width}px`, height: `${displayedRoiBox.height}px` }"
              @mousedown="handleRoiMouseDown"
            >
              <img
                v-if="isSwapped && maskDataUrl"
                :src="maskDataUrl"
                alt="Maska"
                draggable="false"
                style="position: absolute; inset: 0; width: 100%; height: 100%; object-fit: fill; pointer-events: none; z-index: 1;"
              />
              <span
                v-if="canEditRoi"
                v-for="handle in HANDLES"
                :key="handle"
                class="roi-handle"
                :class="`handle-${handle}`"
                @mousedown.stop="emit('begin-resize-roi', handle, $event)"
              />
            </div>
            <div
              v-if="drawing.active || (drawing.width && drawing.height)"
              class="roi-box drawing"
              :style="{ left: `${drawing.x}px`, top: `${drawing.y}px`, width: `${drawing.width}px`, height: `${drawing.height}px` }"
            />
          </div>

          <!-- Scale Calibration & Measurement SVG Overlay -->
          <svg
            v-if="activeLineGeom || measureLineGeom"
            class="scale-calibration-svg"
            style="position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 10;"
          >
            <!-- Calibration line group -->
            <g v-if="activeLineGeom">
              <line
                :x1="activeLineGeom.line.x1"
                :y1="activeLineGeom.line.y1"
                :x2="activeLineGeom.line.x2"
                :y2="activeLineGeom.line.y2"
                stroke="#00ffff"
                stroke-width="2.5"
              />
              <line
                v-if="activeLineGeom.startTick"
                :x1="activeLineGeom.startTick.x1"
                :y1="activeLineGeom.startTick.y1"
                :x2="activeLineGeom.startTick.x2"
                :y2="activeLineGeom.startTick.y2"
                stroke="#00ffff"
                stroke-width="2.5"
              />
              <line
                v-if="activeLineGeom.endTick"
                :x1="activeLineGeom.endTick.x1"
                :y1="activeLineGeom.endTick.y1"
                :x2="activeLineGeom.endTick.x2"
                :y2="activeLineGeom.endTick.y2"
                stroke="#00ffff"
                stroke-width="2.5"
              />
              <g>
                <rect
                  :x="activeLineGeom.cx - activeLineGeom.labelWidth / 2"
                  :y="activeLineGeom.cy - 22"
                  :width="activeLineGeom.labelWidth"
                  height="18"
                  rx="4"
                  fill="rgba(15, 23, 42, 0.85)"
                  stroke="#00ffff"
                  stroke-width="1"
                />
                <text
                  :x="activeLineGeom.cx"
                  :y="activeLineGeom.cy - 13"
                  fill="#00ffff"
                  font-size="10"
                  font-family="Inter, system-ui, sans-serif"
                  font-weight="600"
                  text-anchor="middle"
                  dominant-baseline="central"
                >
                  {{ activeLineGeom.label }}
                </text>
              </g>
            </g>

            <!-- Measurement line group -->
            <g v-if="measureLineGeom">
              <line
                :x1="measureLineGeom.line.x1"
                :y1="measureLineGeom.line.y1"
                :x2="measureLineGeom.line.x2"
                :y2="measureLineGeom.line.y2"
                stroke="#ff9f00"
                stroke-width="2"
              />
              <line
                v-if="measureLineGeom.startTick"
                :x1="measureLineGeom.startTick.x1"
                :y1="measureLineGeom.startTick.y1"
                :x2="measureLineGeom.startTick.x2"
                :y2="measureLineGeom.startTick.y2"
                stroke="#ff9f00"
                stroke-width="2"
              />
              <line
                v-if="measureLineGeom.endTick"
                :x1="measureLineGeom.endTick.x1"
                :y1="measureLineGeom.endTick.y1"
                :x2="measureLineGeom.endTick.x2"
                :y2="measureLineGeom.endTick.y2"
                stroke="#ff9f00"
                stroke-width="2"
              />
              <g>
                <rect
                  :x="measureLineGeom.cx - measureLineGeom.labelWidth / 2"
                  :y="measureLineGeom.cy - 22"
                  :width="measureLineGeom.labelWidth"
                  height="18"
                  rx="4"
                  fill="rgba(15, 23, 42, 0.85)"
                  stroke="#ff9f00"
                  stroke-width="1"
                />
                <text
                  :x="measureLineGeom.cx"
                  :y="measureLineGeom.cy - 13"
                  fill="#ff9f00"
                  font-size="10"
                  font-family="Inter, system-ui, sans-serif"
                  font-weight="600"
                  text-anchor="middle"
                  dominant-baseline="central"
                >
                  {{ measureLineGeom.label }}
                </text>
              </g>
            </g>
          </svg>

          <!-- Measurement line handles (grab points) -->
          <div
            v-if="displayedMeasureLine"
            class="measure-handle start-handle"
            :style="{ left: `${displayedMeasureLine.startX}px`, top: `${displayedMeasureLine.startY}px` }"
            @mousedown.stop="emit('begin-resize-measure', 'start', $event)"
          />
          <div
            v-if="displayedMeasureLine"
            class="measure-handle end-handle"
            :style="{ left: `${displayedMeasureLine.endX}px`, top: `${displayedMeasureLine.endY}px` }"
            @mousedown.stop="emit('begin-resize-measure', 'end', $event)"
          />
        </div>
      </div>


    </template>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useWorkflowStore } from '../../stores/workflow'

const workflow = useWorkflowStore()

const HANDLES = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

const props = defineProps({
  currentStage: { type: Number, default: 1 },
  roiDataUrl: { type: String, default: null },
  isDragging: { type: Boolean, default: false },
  error: { type: String, default: null },
  frameStyle: { type: Object, required: true },
  contrastPercent: { type: Number, required: true },
  invertRoi: { type: Boolean, default: false },
  canEditRoi: { type: Boolean, default: false },
  displayedRoiBox: { type: Object, default: null },
  drawing: { type: Object, required: true },
  isSwapped: { type: Boolean, default: false },
  maskDataUrl: { type: String, default: null },
  spacePressed: { type: Boolean, default: false },

  // Scale calibration props
  scaleLineCoords: { type: Object, default: null },
  scaleDrawing: { type: Object, default: null },
  scalePhysicalValue: { type: Number, default: 20 },
  scaleUnit: { type: String, default: 'µm' },
  scalePxLength: { type: Number, default: 0 },
  imageNatural: { type: Object, default: null },
  imageRender: { type: Object, default: null },

  // Distance measurement props
  measureLineCoords: { type: Object, default: null },
  measureDrawing: { type: Object, default: null },

  // Multiple images props
  images: { type: Array, default: () => [] },
  activeImageIndex: { type: Number, default: -1 },
})

const emit = defineEmits([
  'drop',
  'dragover',
  'dragleave',
  'wheel-image',
  'image-load',
  'begin-roi',
  'begin-move-roi',
  'begin-resize-roi',
  'begin-resize-measure',
  'open-file-picker',
  'select-image',
  'delete-image',
])

const mainImageSrc = computed(() => {
  if (props.isSwapped && props.maskDataUrl && !props.displayedRoiBox) {
    return props.maskDataUrl
  }
  return props.roiDataUrl
})

const baseImageFilter = computed(() => {
  if (props.isSwapped && props.maskDataUrl && !props.displayedRoiBox) {
    return 'none'
  }
  const shouldApplyWholeImageContrast = !props.displayedRoiBox
  const shouldInvertWholeImage = props.invertRoi && !props.displayedRoiBox
  if (shouldApplyWholeImageContrast) {
    return `contrast(${props.contrastPercent}%)${shouldInvertWholeImage ? ' invert(100%)' : ''}`
  }
  return 'none'
})

const overlayClass = computed(() => {
  if (workflow.interactionMode === 'scale') {
    return 'cursor-pencil-cyan'
  }
  if (workflow.interactionMode === 'measure') {
    return 'cursor-pencil-orange'
  }
  return 'cursor-crosshair'
})

const roiBoxClass = computed(() => {
  if (workflow.interactionMode === 'scale') {
    return 'cursor-pencil-cyan'
  }
  if (workflow.interactionMode === 'measure') {
    return 'cursor-pencil-orange'
  }
  if (props.canEditRoi) {
    return 'cursor-move'
  }
  return 'cursor-crosshair'
})

const roiInvertClipStyle = computed(() => {
  if (!props.displayedRoiBox) return null
  const { left, top, width, height } = props.displayedRoiBox
  const rightInset = `calc(100% - ${left + width}px)`
  const bottomInset = `calc(100% - ${top + height}px)`
  return {
    clipPath: `inset(${top}px ${rightInset} ${bottomInset} ${left}px)`,
  }
})

const displayedScaleLine = computed(() => {
  if (!props.scaleLineCoords || !props.imageNatural?.width || !props.imageNatural?.height || !props.imageRender?.width || !props.imageRender?.height) return null
  const sx = props.imageRender.width / props.imageNatural.width
  const sy = props.imageRender.height / props.imageNatural.height
  return {
    startX: props.scaleLineCoords.startX * sx,
    startY: props.scaleLineCoords.startY * sy,
    endX: props.scaleLineCoords.endX * sx,
    endY: props.scaleLineCoords.endY * sy,
  }
})

const activeLineGeom = computed(() => {
  if (props.currentStage !== 3) return null // Step 3 is scale calibration
  let line = null
  let isDrawing = false
  if (props.scaleDrawing && props.scaleDrawing.active) {
    line = {
      x1: props.scaleDrawing.startX,
      y1: props.scaleDrawing.startY,
      x2: props.scaleDrawing.endX,
      y2: props.scaleDrawing.endY,
    }
    isDrawing = true
  } else if (displayedScaleLine.value) {
    line = {
      x1: displayedScaleLine.value.startX,
      y1: displayedScaleLine.value.startY,
      x2: displayedScaleLine.value.endX,
      y2: displayedScaleLine.value.endY,
    }
  }
  if (!line) return null

  const dx = line.x2 - line.x1
  const dy = line.y2 - line.y1
  const len = Math.sqrt(dx * dx + dy * dy)

  let startTick = null
  let endTick = null
  if (len > 0) {
    const nx = -dy / len
    const ny = dx / len
    const t = 8
    startTick = {
      x1: line.x1 + t * nx,
      y1: line.y1 + t * ny,
      x2: line.x1 - t * nx,
      y2: line.y1 - t * ny,
    }
    endTick = {
      x1: line.x2 + t * nx,
      y1: line.y2 + t * ny,
      x2: line.x2 - t * nx,
      y2: line.y2 - t * ny,
    }
  }

  const cx = (line.x1 + line.x2) / 2
  const cy = (line.y1 + line.y2) / 2

  let label = ''
  if (isDrawing) {
    if (props.imageNatural?.width && props.imageRender?.width) {
      const sx = props.imageNatural.width / props.imageRender.width
      const sy = props.imageNatural.height / props.imageRender.height
      const natDx = (line.x2 - line.x1) * sx
      const natDy = (line.y2 - line.y1) * sy
      const natLen = Math.sqrt(natDx * natDx + natDy * natDy)
      label = `${Math.round(natLen)} px`
    } else {
      label = `${Math.round(len)} px`
    }
  } else {
    label = `${props.scalePhysicalValue} ${props.scaleUnit} (${Math.round(props.scalePxLength)} px)`
  }

  const labelWidth = Math.max(70, label.length * 7.5)

  return {
    line,
    startTick,
    endTick,
    cx,
    cy,
    label,
    labelWidth,
  }
})

const displayedMeasureLine = computed(() => {
  if (!props.measureLineCoords || !props.imageNatural?.width || !props.imageNatural?.height || !props.imageRender?.width || !props.imageRender?.height) return null
  const sx = props.imageRender.width / props.imageNatural.width
  const sy = props.imageRender.height / props.imageNatural.height
  return {
    startX: props.measureLineCoords.startX * sx,
    startY: props.measureLineCoords.startY * sy,
    endX: props.measureLineCoords.endX * sx,
    endY: props.measureLineCoords.endY * sy,
  }
})

const measureLineGeom = computed(() => {
  let line = null
  let isDrawing = false
  if (props.measureDrawing && props.measureDrawing.active) {
    line = {
      x1: props.measureDrawing.startX,
      y1: props.measureDrawing.startY,
      x2: props.measureDrawing.endX,
      y2: props.measureDrawing.endY,
    }
    isDrawing = true
  } else if (displayedMeasureLine.value) {
    line = {
      x1: displayedMeasureLine.value.startX,
      y1: displayedMeasureLine.value.startY,
      x2: displayedMeasureLine.value.endX,
      y2: displayedMeasureLine.value.endY,
    }
  }
  if (!line) return null

  const dx = line.x2 - line.x1
  const dy = line.y2 - line.y1
  const len = Math.sqrt(dx * dx + dy * dy)

  let startTick = null
  let endTick = null
  if (len > 0) {
    const nx = -dy / len
    const ny = dx / len
    const t = 6
    startTick = {
      x1: line.x1 + t * nx,
      y1: line.y1 + t * ny,
      x2: line.x1 - t * nx,
      y2: line.y1 - t * ny,
    }
    endTick = {
      x1: line.x2 + t * nx,
      y1: line.y2 + t * ny,
      x2: line.x2 - t * nx,
      y2: line.y2 - t * ny,
    }
  }

  const cx = (line.x1 + line.x2) / 2
  const cy = (line.y1 + line.y2) / 2

  let label = ''
  let natLen = 0
  if (props.imageNatural?.width && props.imageRender?.width) {
    const sx = props.imageNatural.width / props.imageRender.width
    const sy = props.imageNatural.height / props.imageRender.height
    const natDx = (line.x2 - line.x1) * sx
    const natDy = (line.y2 - line.y1) * sy
    natLen = Math.sqrt(natDx * natDx + natDy * natDy)
  } else {
    natLen = len
  }

  if (props.scalePxLength > 0) {
    const physVal = natLen * (props.scalePhysicalValue / props.scalePxLength)
    label = `${physVal.toFixed(2)} ${props.scaleUnit}`
  } else {
    label = `${Math.round(natLen)} px`
  }

  const labelWidth = Math.max(65, label.length * 7.5)

  return {
    line,
    startTick,
    endTick,
    cx,
    cy,
    label,
    labelWidth,
  }
})

function handleRoiMouseDown(e) {
  if (props.canEditRoi && e.button === 0 && !props.spacePressed) {
    e.stopPropagation()
    emit('begin-move-roi', e)
  }
}

function getRoiOutlineStyle(img, containerAspect = 1.6) {
  if (!img.params || !img.params.roi || !img.imageNatural?.width || !img.imageNatural?.height) return {}
  const { x, y, width, height } = img.params.roi
  const w = img.imageNatural.width
  const h = img.imageNatural.height
  const imgRatio = w / h

  // Initial percentages relative to the image
  const pLeft = x / w
  const pTop = y / h
  const pWidth = width / w
  const pHeight = height / h

  let scaleX = 1
  let scaleY = 1
  let offsetX = 0
  let offsetY = 0

  if (imgRatio > containerAspect) {
    // Image is wider than container aspect ratio (touches left/right, letterbox top/bottom)
    scaleY = containerAspect / imgRatio
    offsetY = (1 - scaleY) / 2
  } else {
    // Image is taller than or equal to container aspect ratio (touches top/bottom, pillarbox left/right)
    scaleX = imgRatio / containerAspect
    offsetX = (1 - scaleX) / 2
  }

  return {
    left: `${(offsetX + pLeft * scaleX) * 100}%`,
    top: `${(offsetY + pTop * scaleY) * 100}%`,
    width: `${(pWidth * scaleX) * 100}%`,
    height: `${(pHeight * scaleY) * 100}%`,
  }
}
</script>

<style scoped>
/* StitchViewer component styles */
.viewer-shell {
  display: flex;
  flex-direction: column;
}

.stitch-image-frame-wrap {
  flex: 1;
  min-height: 0;
}

.viewer-grid-mode {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-2);
}

.grid-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.grid-header h3 {
  margin: 0;
  font: 700 16px 'Space Grotesk', sans-serif;
  color: var(--text);
}

.images-gallery-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-content: start;
  gap: 16px;
  overflow-y: auto;
  padding-bottom: 20px;
  scrollbar-width: thin;
  scrollbar-color: var(--outline) var(--surface-2);
}

.images-gallery-grid::-webkit-scrollbar {
  width: 6px;
}

.images-gallery-grid::-webkit-scrollbar-track {
  background: var(--surface-2);
}

.images-gallery-grid::-webkit-scrollbar-thumb {
  background: var(--outline);
  border-radius: 99px;
}

.images-gallery-grid::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

@media (max-width: 1200px) {
  .images-gallery-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 900px) {
  .images-gallery-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.gallery-card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--outline);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
}

.gallery-card:hover {
  border-color: var(--primary);
  transform: translateY(-2px);
}

.gallery-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
  background: color-mix(in srgb, var(--primary) 5%, var(--surface));
}

.gallery-card.add-card {
  border: 1px dashed var(--outline);
  background: transparent;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: 120px;
  gap: 8px;
}

.gallery-card.add-card:hover {
  border-style: solid;
  border-color: var(--primary);
}

.gallery-card.add-card .add-icon {
  font-size: 24px;
  color: var(--text-soft);
  font-weight: bold;
}

.gallery-card.add-card .add-text {
  font-size: 10px;
  color: var(--text-soft);
  font-weight: bold;
  text-transform: uppercase;
}

.gallery-card.add-card:hover .add-icon,
.gallery-card.add-card:hover .add-text {
  color: var(--primary);
}

.gallery-preview-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16/10;
  background: var(--surface-3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.gallery-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.gallery-roi-outline {
  position: absolute;
  border: 2px solid #ef4444; /* red ROI border */
  background-color: rgba(239, 68, 68, 0.20);
  box-sizing: border-box;
}

.gallery-card-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 10;
}

.gallery-card:hover .gallery-card-delete-btn {
  opacity: 1;
}

.gallery-card-delete-btn:hover {
  background: #ef4444;
}

.gallery-card-info {
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gallery-card-name {
  font-size: 11px;
  color: var(--text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gallery-card-status {
  font-size: 9px;
  color: var(--text-soft);
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 0.05em;
}

.gallery-card-status.has-result {
  color: #10b981;
}
</style>

<style>
.image-workspace {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.image-tools {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.image-tools .btn {
  min-width: 1.55rem;
  height: 1.55rem;
  padding: 0;
  font-size: 0.78rem;
}

.zoom-value {
  min-width: 3rem;
  text-align: center;
  font-size: 0.72rem;
  color: var(--text-soft);
}

.image-stage {
  position: relative;
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  background: var(--image-stage-bg);
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 0.2rem;
}

.viewer-shell {
  position: relative;
  border: 1px solid #3c494e;
  background: #0e0e0f;
  min-height: 0;
  overflow: hidden;
  border-color: var(--outline);
}

.stitch-dashboard.theme-light .viewer-shell {
  background: #f2f4f6;
}

.viewer-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 8px;
  text-align: center;
  color: var(--text-muted);
  color: var(--text-soft);
}

.viewer-overlay button {
  margin: 0 auto;
  border: 1px solid #00d1ff;
  background: transparent;
  color: #00d1ff;
  padding: 8px 12px;
  border-color: var(--primary);
  color: var(--primary);
  cursor: pointer;
}

.main-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
  width: 100%;
  height: 100%;
  object-fit: fill;
}

.empty-image {
  color: #cbd5e1;
}

.roi-overlay {
  position: absolute;
  inset: 0;
  cursor: crosshair;
}

.image-stage:not(.cropEnabled) .roi-overlay {
  cursor: default;
}

.roi-box {
  position: absolute;
  border: 2px dashed #ef4444;
  background: rgba(239, 68, 68, 0.15);
  pointer-events: auto;
}

.roi-box.drawing {
  border-color: #22c55e;
  background: rgba(34, 197, 94, 0.16);
  pointer-events: none;
}

.roi-live-invert-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.roi-handle {
  position: absolute;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999px;
  border: 1px solid #fff;
  background: #2563eb;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.25);
  pointer-events: auto;
  z-index: 3;
}

.handle-nw { left: -0.375rem; top: -0.375rem; cursor: nwse-resize; }
.handle-n  { left: calc(50% - 0.375rem); top: -0.375rem; cursor: ns-resize; }
.handle-ne { right: -0.375rem; top: -0.375rem; cursor: nesw-resize; }
.handle-e  { right: -0.375rem; top: calc(50% - 0.375rem); cursor: ew-resize; }
.handle-se { right: -0.375rem; bottom: -0.375rem; cursor: nwse-resize; }
.handle-s  { left: calc(50% - 0.375rem); bottom: -0.375rem; cursor: ns-resize; }
.handle-sw { left: -0.375rem; bottom: -0.375rem; cursor: nesw-resize; }
.handle-w  { left: -0.375rem; top: calc(50% - 0.375rem); cursor: ew-resize; }

.crop-lock {
  position: absolute;
  right: 0.45rem;
  top: 0.45rem;
  font-size: 0.6rem;
  padding: 0.1rem 0.28rem;
  border-radius: 0.4rem;
  background: rgba(15, 23, 42, 0.72);
  color: #f8fafc;
}

.viewer-meta {
  position: absolute;
  top: 10px;
  left: 10px;
  display: grid;
  gap: 6px;
  pointer-events: none;
}

.viewer-meta > div {
  background: rgba(32, 31, 32, 0.78);
  border: 1px solid #3c494e;
  padding: 4px 8px;
  color: #ffffff;
  font: 500 11px/1.3 'Space Grotesk', sans-serif;
  background: color-mix(in srgb, var(--surface-2) 80%, transparent);
  border-color: var(--outline);
  color: var(--text);
}

.roi-overlay.cursor-pencil-cyan,
.roi-box.cursor-pencil-cyan {
  cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2300d1ff' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'/><path d='m15 5 4 4'/></svg>") 2 22, crosshair;
}
.roi-overlay.cursor-pencil-orange,
.roi-box.cursor-pencil-orange {
  cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23ff9f00' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><path d='M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'/><path d='m15 5 4 4'/></svg>") 2 22, crosshair;
}
.roi-overlay.cursor-crosshair {
  cursor: crosshair;
}

.roi-box.cursor-move {
  cursor: move;
}
.roi-box.cursor-crosshair {
  cursor: crosshair;
}

.measure-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid #ffffff;
  background: #ff9f00;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  cursor: grab;
  transform: translate(-50%, -50%);
  pointer-events: auto;
  z-index: 12;
  transition: transform 0.1s ease, background-color 0.1s ease;
}
.measure-handle:hover {
  transform: translate(-50%, -50%) scale(1.3);
  background: #ffa81a;
  cursor: grabbing;
}

@media (max-width: 1100px) {
  .viewer-shell {
    height: 60vh !important;
    min-height: 480px !important;
  }
}

@media (max-width: 860px) {
  .viewer-shell {
    height: 50vh !important;
    min-height: 380px !important;
  }
}
</style>
