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
          :src="roiDataUrl"
          alt="Mikrostruktura"
          class="main-image"
          draggable="false"
          :style="{ filter: `contrast(${contrastPercent}%)` }"
          @load="emit('image-load', $event)"
        />
        <div
          class="roi-overlay"
          @mousedown="emit('begin-roi', $event)"
        >
          <div
            v-if="displayedRoiBox"
            class="roi-box"
            :style="{ left: `${displayedRoiBox.left}px`, top: `${displayedRoiBox.top}px`, width: `${displayedRoiBox.width}px`, height: `${displayedRoiBox.height}px` }"
            @mousedown.stop="emit('begin-move-roi', $event)"
          >
            <span
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

    <div class="viewer-meta">
      <div>MAG: 1000x</div>
      <div>EHT: 20.00 kV</div>
      <div>WD: 8.5 mm</div>
      <div v-if="roiMeta">ROI: {{ roiMeta.x }}, {{ roiMeta.y }} / {{ roiMeta.width }}x{{ roiMeta.height }}</div>
    </div>
    <div class="viewer-controls">
      <button type="button" @click="emit('zoom-in')">+</button>
      <button type="button" @click="emit('zoom-out')">-</button>
      <button type="button" @click="emit('reset-view')">Dopasuj</button>
      <button type="button" @click="emit('clear-roi')">Wyczysc ROI</button>
    </div>
  </section>
</template>

<script setup>
const HANDLES = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

defineProps({
  roiDataUrl: { type: String, default: null },
  isDragging: { type: Boolean, default: false },
  error: { type: String, default: null },
  frameStyle: { type: Object, required: true },
  contrastPercent: { type: Number, required: true },
  displayedRoiBox: { type: Object, default: null },
  drawing: { type: Object, required: true },
  roiMeta: { type: Object, default: null },
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
  'zoom-in',
  'zoom-out',
  'reset-view',
  'clear-roi',
  'open-file-picker',
])
</script>