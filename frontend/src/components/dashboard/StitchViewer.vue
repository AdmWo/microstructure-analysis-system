<template>
  <section class="viewer-shell" @drop="emit('drop', $event)" @dragover="emit('dragover', $event)" @dragleave="emit('dragleave')">
    <div v-if="!roiDataUrl" class="viewer-overlay">
      <p>{{ isDragging ? 'Upusc obraz, aby rozpoczac analize' : 'Wgraj obraz mikroskopowy, aby zaczac' }}</p>
      <button type="button" @click="emit('open-file-picker')">Wybierz obraz</button>
      <p v-if="error" class="error-text">{{ error }}</p>
    </div>

    <div v-else class="stitch-image-frame-wrap" @wheel.prevent="emit('wheel-image', $event)">
      <div class="stitch-image-frame" :style="frameStyle">
        <img
          :src="mainImageSrc"
          alt="Mikrostruktura"
          class="main-image"
          draggable="false"
          :style="{ filter: baseImageFilter }"
          @load="emit('image-load', $event)"
        />
        <div v-if="invertRoi && displayedRoiBox && !isSwapped" class="roi-live-invert-layer" :style="roiInvertClipStyle">
          <img :src="roiDataUrl" alt="" class="main-image" draggable="false" :style="{ filter: `contrast(${contrastPercent}%) invert(100%)` }" aria-hidden="true" />
        </div>
        <div
          class="roi-overlay"
          @mousedown="emit('begin-roi', $event)"
        >
          <div
            v-if="displayedRoiBox"
            class="roi-box"
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
  </section>
</template>

<script setup>
import { computed } from 'vue'

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
  const shouldInvertWholeImage = props.invertRoi && !props.displayedRoiBox
  return `contrast(${props.contrastPercent}%)${shouldInvertWholeImage ? ' invert(100%)' : ''}`
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
  if (props.currentStage !== 2) return null
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
  if (props.canEditRoi) {
    e.stopPropagation()
    emit('begin-move-roi', e)
  }
}
</script>