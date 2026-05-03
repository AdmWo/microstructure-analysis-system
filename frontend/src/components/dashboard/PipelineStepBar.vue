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
      <div class="step-badge">{{ step.id }}</div>
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


