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
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const HANDLES = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

const props = defineProps({
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

function handleRoiMouseDown(e) {
  if (props.canEditRoi) {
    e.stopPropagation()
    emit('begin-move-roi', e)
  }
}
</script>