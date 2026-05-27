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