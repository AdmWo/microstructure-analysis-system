<script setup>
const props = defineProps({
  roiDataUrl: { type: String, default: null },
  currentStage: { type: Number, required: true },
  displayedRoiBox: { type: Object, default: null },
  drawing: { type: Object, required: true },
  params: { type: Object, required: true },
  view: { type: Object, required: true },
  viewTransform: { type: Object, required: true },
})

const emit = defineEmits(['image-load', 'wheel-image', 'zoom-in', 'zoom-out', 'reset-view', 'begin-roi', 'begin-move-roi', 'begin-resize-roi', 'move-roi', 'finish-roi', 'clear-roi', 'update-manual-roi'])
const handles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']

function onManualChange(field, event) {
  const next = {
    x: props.params.roi?.x ?? 0,
    y: props.params.roi?.y ?? 0,
    width: props.params.roi?.width ?? 1,
    height: props.params.roi?.height ?? 1,
  }
  next[field] = Number(event.target.value || 0)
  emit('update-manual-roi', next)
}
</script>

<template>
  <section class="panel image-workspace">
    <div class="workspace-header">
      <h3>Obszar ROI</h3>
      <div class="image-tools">
        <button type="button" class="btn ghost" @click="emit('zoom-out')">−</button>
        <span class="zoom-value">{{ Math.round(view.zoom * 100) }}%</span>
        <button type="button" class="btn ghost" @click="emit('zoom-in')">+</button>
        <button type="button" class="btn ghost" @click="emit('reset-view')">Dopasuj</button>
      </div>
    </div>
    <div class="image-stage" :class="{ cropEnabled: currentStage === 1 }">
      <div v-if="roiDataUrl" class="image-frame-wrap" @wheel.prevent="emit('wheel-image', $event)">
        <div class="image-frame" :style="viewTransform">
          <img :src="roiDataUrl" alt="Obraz ROI" class="main-image" draggable="false" @load="emit('image-load', $event)" />
        <div class="roi-overlay" @mousedown="emit('begin-roi', $event)" @mousemove="emit('move-roi', $event)" @mouseup="emit('finish-roi')" @mouseleave="emit('finish-roi')">
          <div
            v-if="displayedRoiBox"
            class="roi-box"
            :style="{ left: `${displayedRoiBox.left}px`, top: `${displayedRoiBox.top}px`, width: `${displayedRoiBox.width}px`, height: `${displayedRoiBox.height}px` }"
            @mousedown.stop="emit('begin-move-roi', $event)"
          >
            <span
              v-for="handle in handles"
              :key="handle"
              class="roi-handle"
              :class="`handle-${handle}`"
              @mousedown.stop="emit('begin-resize-roi', handle, $event)"
            />
          </div>
          <div v-if="drawing.active || (drawing.width && drawing.height)" class="roi-box drawing" :style="{ left: `${drawing.x}px`, top: `${drawing.y}px`, width: `${drawing.width}px`, height: `${drawing.height}px` }" />
          <div v-if="currentStage !== 1" class="crop-lock">Edycja ROI tylko na etapie 1</div>
        </div>
        </div>
      </div>
      <div v-if="!roiDataUrl" class="empty-image">Wgraj obraz, aby rozpocząć analizę.</div>
    </div>
    <div class="roi-controls">
      <p>
        ROI:
        <span v-if="params.roi">x={{ params.roi.x }}, y={{ params.roi.y }}, w={{ params.roi.width }}, h={{ params.roi.height }}</span>
        <span v-else>Pełny obraz</span>
      </p>
      <button type="button" class="btn ghost" @click="emit('clear-roi')">Wyczyść ROI</button>
    </div>
    <div v-if="params.roi" class="roi-manual-grid">
      <label>X<input type="number" min="0" :value="params.roi.x" @change="onManualChange('x', $event)" /></label>
      <label>Y<input type="number" min="0" :value="params.roi.y" @change="onManualChange('y', $event)" /></label>
      <label>W<input type="number" min="1" :value="params.roi.width" @change="onManualChange('width', $event)" /></label>
      <label>H<input type="number" min="1" :value="params.roi.height" @change="onManualChange('height', $event)" /></label>
    </div>
  </section>
</template>
