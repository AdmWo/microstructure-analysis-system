<template>
  <div class="pipeline-stepper">
    <button
      v-for="step in steps"
      :key="step.id"
      type="button"
      class="pipeline-step"
      :class="{ active: activeStep === step.id, done: activeStep > step.id }"
      @click="emit('step', step.id)"
    >
      <div class="step-badge">{{ step.id - 1 }}</div>
      <span>{{ step.label }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  steps: { type: Array, required: true },
  activeStep: { type: Number, required: true },
})

const emit = defineEmits(['step'])
</script>

<style scoped>
.pipeline-stepper {
  height: 56px;
  border-bottom: 1px solid #1c1c1f;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 14px;
  overflow-x: auto;
  border-color: var(--outline);
}

.pipeline-step {
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 6px 8px;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: 0.45;
  white-space: nowrap;
  text-transform: uppercase;
  font: 700 10px/1 'Space Grotesk', sans-serif;
  color: var(--text-muted);
  cursor: pointer;
}

.pipeline-step.active,
.pipeline-step.done {
  opacity: 1;
}

.pipeline-step.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--primary) 25%, transparent);
}

.step-badge {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #859399;
}

.pipeline-step.active .step-badge {
  background: var(--primary);
  color: var(--primary-text);
  border-color: var(--primary);
}

@media (max-width: 860px) {
  .pipeline-stepper {
    height: auto;
    padding: 8px 12px;
    gap: 8px;
  }
}
</style>
