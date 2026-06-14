<template>
  <aside class="stitch-side-nav">
    <div class="tool-header">
      <h3>Postęp pomiaru</h3>
      <p>Etapy workflow</p>
    </div>

    <!-- Vertical Stepper -->
    <div class="vertical-stepper">
      <button
        v-for="step in steps"
        :key="step.id"
        type="button"
        class="vertical-step"
        :class="{ active: activeStep === step.id, done: activeStep > step.id }"
        @click="emit('step', step.id)"
      >
        <div class="step-badge">{{ step.id - 1 }}</div>
        <span class="step-label">{{ step.label }}</span>
      </button>
    </div>

    <!-- Navigation Buttons -->
    <div class="sidebar-nav-buttons">
      <button type="button" class="nav-btn prev-btn" @click="emit('prev')">
        Wstecz
      </button>
      <button type="button" class="nav-btn next-btn" :disabled="activeStep === 5" @click="emit('next')">
        Dalej
      </button>
    </div>

    <!-- Stage Info Description Section -->
    <div class="sidebar-stage-info">
      <!-- Toggle Button (only when in stages 2-6 and we have images) -->
      <button
        v-if="images && images.length > 0 && currentStage > 1"
        type="button"
        class="stage-info-toggle-btn"
        @click="showImagesMode = !showImagesMode"
        :title="showImagesMode ? 'Pokaż opis etapu' : 'Pokaż listę zdjęć'"
      >
        <!-- Info Icon (shows when in Images mode) -->
        <svg v-if="showImagesMode" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <!-- Images Icon (shows when in Info mode) -->
        <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2z"></path>
          <path d="M4 14V6a2 2 0 0 1 2-2h12"></path>
        </svg>
      </button>

      <!-- Mode A: Description -->
      <div v-if="!showImagesMode">
        <h4 class="stage-info-title">{{ stageTitle }}</h4>
        <p class="stage-info-description">{{ stageDescription }}</p>
      </div>

      <!-- Mode B: Images List -->
      <div v-else class="sidebar-images-mode">
        <h5 class="sidebar-mode-title">Zdjęcia ({{ images.length }})</h5>
        <div class="sidebar-thumbnails-container">
          <div
            v-for="(img, index) in images"
            :key="img.id"
            class="sidebar-thumb-card"
            :class="{ active: index === activeImageIndex }"
            @click="emit('select-image', index)"
          >
            <div class="sidebar-thumb-preview">
              <img :src="img.localPreview" class="sidebar-thumb-img" />
              <div
                v-if="img.params?.roi && img.imageNatural?.width && img.imageNatural?.height"
                class="sidebar-thumb-roi"
                :style="getRoiOutlineStyle(img, 70 / 46)"
              ></div>
            </div>
            <span class="sidebar-thumb-name" :title="img.name">{{ img.name }}</span>
            <button type="button" class="sidebar-thumb-del" @click.stop="emit('delete-image', index)" title="Usuń obraz">×</button>
          </div>
          <div class="sidebar-thumb-card add-card" @click="emit('open-file-picker')">
            <span class="add-icon">+</span>
            <span class="add-text">Dodaj</span>
          </div>
        </div>
      </div>
    </div>

    <div class="control-panel">
      <slot />
    </div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  currentStage: { type: Number, required: true },
  steps: { type: Array, required: true },
  activeStep: { type: Number, required: true },
  stageTitle: { type: String, required: true },
  stageDescription: { type: String, required: true },
  images: { type: Array, default: () => [] },
  activeImageIndex: { type: Number, default: 0 },
})

const emit = defineEmits(['step', 'prev', 'next', 'select-image', 'delete-image', 'open-file-picker'])

const showImagesMode = ref(false)

watch(() => props.currentStage, (newStage) => {
  if (newStage === 1) {
    showImagesMode.value = false
  }
})

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
    scaleY = containerAspect / imgRatio
    offsetY = (1 - scaleY) / 2
  } else {
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
.stitch-side-nav {
  position: absolute;
  top: 56px;
  left: 0;
  width: 320px;
  bottom: 0;
  border-right: 1px solid #1c1c1f;
  background: #121214;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: var(--outline) var(--surface);
  border-color: var(--outline);
  background: var(--surface);
  color: var(--text);
}

.stitch-side-nav::-webkit-scrollbar {
  width: 6px;
}
.stitch-side-nav::-webkit-scrollbar-track {
  background: var(--surface);
}
.stitch-side-nav::-webkit-scrollbar-thumb {
  background: var(--outline);
  border-radius: 3px;
}
.stitch-side-nav::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.tool-header {
  border: 1px solid var(--outline);
  background: var(--surface-2);
  padding: 12px 16px;
  margin: 0 16px 12px;
  border-radius: 6px;
}

.tool-header h3 {
  margin: 0;
  text-transform: uppercase;
  color: #859399;
  font: 700 11px/1 'Space Grotesk', sans-serif;
  color: var(--text-muted);
}

.tool-header p {
  margin: 6px 0 0;
  color: #00d1ff;
  font: 500 11px/1.2 'Space Grotesk', sans-serif;
  color: var(--primary);
}

.compact-tool-select-wrap {
  display: none;
  padding: 0 24px;
  margin-bottom: 12px;
  gap: 6px;
}

.compact-tool-select-wrap span {
  color: var(--text-muted);
  text-transform: uppercase;
  font: 700 10px/1 'Space Grotesk', sans-serif;
  letter-spacing: 0.06em;
}

.compact-tool-select {
  border: 1px solid var(--outline);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  padding: 8px 10px;
}

.tool-list {
  display: flex;
  flex-direction: column;
}

.tool-button {
  height: 42px;
  padding: 0 24px;
  border: 0;
  background: transparent;
  color: #97a3aa;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font: 700 10px/1 'Space Grotesk', sans-serif;
  cursor: pointer;
}

.tool-button.active {
  color: #00d1ff;
  border-left: 2px solid #00d1ff;
  background: linear-gradient(90deg, rgba(0, 209, 255, 0.12), transparent);
  color: var(--primary);
  border-left-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 12%, transparent);
}

.vertical-stepper {
  padding: 12px 24px 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-sizing: border-box;
}

.sidebar-nav-buttons {
  display: flex;
  gap: 12px;
  padding: 6px 24px 12px;
  border-bottom: 1px solid var(--outline);
  box-sizing: border-box;
}

.sidebar-nav-buttons .nav-btn {
  flex: 1;
  height: 32px;
  border: 1px solid var(--outline);
  background: var(--surface-2);
  color: var(--text);
  border-radius: 4px;
  font: 700 10px/1 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-nav-buttons .nav-btn:hover:not(:disabled) {
  background: var(--primary);
  color: var(--primary-text);
  border-color: var(--primary);
}

.sidebar-nav-buttons .nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.vertical-step {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-soft);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 4px;
  text-align: left;
  width: 100%;
  transition: all 0.2s;
  opacity: 0.55;
  box-sizing: border-box;
}

.vertical-step:hover {
  opacity: 1;
  background: var(--surface-2);
}

.vertical-step.active {
  opacity: 1;
  color: var(--primary);
  border-color: var(--outline);
  background: var(--surface-2);
}

.vertical-step.done {
  opacity: 0.85;
  color: var(--text);
}

.vertical-step .step-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font: 700 9px/1 'Space Grotesk', sans-serif;
  transition: all 0.2s;
  flex-shrink: 0;
}

.vertical-step.active .step-badge {
  background: var(--primary);
  color: var(--primary-text);
  border-color: var(--primary);
}

.vertical-step.done .step-badge {
  border-color: var(--outline);
  background: var(--surface-3);
}

.vertical-step .step-label {
  font: 700 10px/1 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.sidebar-stage-info {
  flex: 1;
  min-height: 160px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--outline);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  background: var(--surface-2);
  position: relative;
}

.stage-info-title {
  margin: 0;
  color: var(--primary);
  font: 700 15px/1.3 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding-right: 28px;
}

.stage-info-description {
  margin: 8px 0 0 0;
  color: var(--text-soft);
  font-size: 13.5px;
  line-height: 1.6;
}

.stage-info-toggle-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  z-index: 10;
}

.stage-info-toggle-btn:hover {
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
}

.sidebar-images-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-mode-title {
  margin: 0 0 8px 0;
  color: var(--primary);
  font: 700 11px/1.3 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding-right: 28px;
}

.sidebar-thumbnails-container {
  display: grid;
  grid-template-rows: repeat(2, 72px);
  grid-auto-flow: column;
  grid-auto-columns: 80px;
  gap: 6px;
  overflow-x: auto;
  overflow-y: hidden;
  padding-top: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -6px;
  margin-right: -6px;
  height: 168px;
  scrollbar-width: thin;
  scrollbar-color: var(--outline) var(--surface-2);
  box-sizing: border-box;
}

.sidebar-thumbnails-container::-webkit-scrollbar {
  height: 4px;
}

.sidebar-thumbnails-container::-webkit-scrollbar-track {
  background: var(--surface-2);
}

.sidebar-thumbnails-container::-webkit-scrollbar-thumb {
  background: var(--outline);
  border-radius: 99px;
}

.sidebar-thumbnails-container::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

.sidebar-thumb-card {
  position: relative;
  width: 80px;
  height: 72px;
  min-width: 80px;
  background: var(--surface-3);
  border: 1px solid var(--outline);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 4px 5px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.sidebar-thumb-card:hover {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 5%, var(--surface-3));
}

.sidebar-thumb-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary);
  background: color-mix(in srgb, var(--primary) 8%, var(--surface-3));
}

.sidebar-thumb-preview {
  position: relative;
  width: 100%;
  height: 46px;
  background: #000;
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-thumb-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.sidebar-thumb-roi {
  position: absolute;
  border: 1px solid #ef4444;
  background-color: rgba(239, 68, 68, 0.2);
  box-sizing: border-box;
}

.sidebar-thumb-name {
  font-size: 8px;
  color: var(--text);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.sidebar-thumb-del {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  border: 1px solid var(--surface-2);
  font-size: 9px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
  z-index: 10;
}

.sidebar-thumb-del:hover {
  transform: scale(1.15);
  background: #ff4d4d;
}

.sidebar-thumb-card:hover .sidebar-thumb-del {
  opacity: 1;
}

.sidebar-thumb-card.add-card {
  border: 1px dashed var(--outline);
  background: transparent;
  justify-content: center;
  gap: 2px;
}

.sidebar-thumb-card.add-card:hover {
  border-style: solid;
  border-color: var(--primary);
}

.sidebar-thumb-card.add-card .add-icon {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-soft);
  line-height: 1;
}

.sidebar-thumb-card.add-card .add-text {
  font-size: 8px;
  color: var(--text-soft);
  text-transform: uppercase;
  font-weight: bold;
}

.sidebar-thumb-card.add-card:hover .add-icon,
.sidebar-thumb-card.add-card:hover .add-text {
  color: var(--primary);
}

.control-panel {
  border-top: 1px solid var(--outline);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 370px;
  min-height: 370px;
  max-height: 370px;
  box-sizing: border-box;
  border-color: var(--outline);
}

.control-panel label {
  display: grid;
  gap: 6px;
}

.control-panel label.disabled {
  opacity: 0.5;
}

.control-panel span {
  color: var(--text-soft);
  text-transform: uppercase;
  font: 700 10px/1 'Space Grotesk', sans-serif;
  letter-spacing: 0.06em;
}

.control-panel small {
  color: var(--primary);
  font: 500 12px/1.2 'Space Grotesk', sans-serif;
}

.control-panel input,
.control-panel select {
  border: 1px solid #3c494e;
  background: #201f20;
  color: #bbc9cf;
  border-radius: 4px;
  padding: 8px 10px;
  background: var(--surface);
  color: var(--text);
  border-color: var(--outline);
}

.control-panel input[type='range'] {
  accent-color: var(--primary);
  height: 6px;
  padding: 0;
  background: color-mix(in srgb, var(--outline) 35%, transparent);
}

.control-panel input[type='range']::-webkit-slider-runnable-track {
  height: 6px;
  background: color-mix(in srgb, var(--outline) 45%, transparent);
  border-radius: 999px;
}

.control-panel input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  margin-top: -4px;
  border-radius: 999px;
  background: var(--primary);
  border: 1px solid var(--surface);
}

.execute-btn {
  margin-top: auto;
  height: 42px;
  min-height: 42px;
  flex-shrink: 0;
  border: 0;
  background: var(--primary);
  color: var(--primary-text);
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font: 700 11px/1 'Space Grotesk', sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
}

.execute-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
}

.execute-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.toggle-row {
  display: flex !important;
  align-items: center;
  gap: 8px;
}

.swap-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-color: var(--outline) !important;
  color: var(--text-soft) !important;
  background: var(--surface-2) !important;
  box-shadow: none !important;
}

@media (max-width: 1360px) {
  .stitch-side-nav {
    width: 288px;
  }
}

@media (max-height: 900px) and (min-width: 861px) {
  .stitch-side-nav {
    overflow: auto;
  }

  .compact-tool-select-wrap {
    display: grid;
  }

  .tool-list {
    display: none;
  }

  .control-panel {
    margin-top: 0;
  }
}

@media (max-width: 1100px) {
  .stitch-side-nav {
    width: 250px;
  }
}

@media (max-width: 860px) {
  .stitch-side-nav {
    position: static;
    width: 100%;
    max-height: 46vh;
    border-right: 0;
    border-bottom: 1px solid var(--outline);
    overflow: auto;
  }
}
</style>
