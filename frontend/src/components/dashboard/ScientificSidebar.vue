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
      <h4 class="stage-info-title">{{ stageTitle }}</h4>
      <p class="stage-info-description">{{ stageDescription }}</p>
    </div>

    <div class="control-panel">
      <slot />
    </div>
  </aside>
</template>

<script setup>
defineProps({
  currentStage: { type: Number, required: true },
  steps: { type: Array, required: true },
  activeStep: { type: Number, required: true },
  stageTitle: { type: String, required: true },
  stageDescription: { type: String, required: true },
})

const emit = defineEmits(['step', 'prev', 'next'])
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
  height: 160px;
  min-height: 160px;
  max-height: 160px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--outline);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
}

.stage-info-title {
  margin: 0;
  color: var(--primary);
  font: 700 15px/1.3 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.stage-info-description {
  margin: 0;
  color: var(--text-soft);
  font-size: 13.5px;
  line-height: 1.6;
}

.control-panel {
  margin-top: auto;
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
