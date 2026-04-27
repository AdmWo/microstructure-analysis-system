<script setup>
defineProps({
  stages: { type: Array, required: true },
  currentStage: { type: Number, required: true },
  isFirstStage: { type: Boolean, default: false },
  isLastStage: { type: Boolean, default: false },
})

const emit = defineEmits(['go-stage', 'prev', 'next'])
</script>

<template>
  <section class="timeline-modern">
    <div class="timeline-steps-row">
      <div class="timeline-line" />
      <div v-for="stage in stages" :key="stage.id" class="timeline-step" :class="{ active: currentStage === stage.id, done: currentStage > stage.id }">
        <button type="button" class="timeline-circle" @click="emit('go-stage', stage.id)">
          <span v-if="currentStage > stage.id">✓</span>
          <span v-else>{{ stage.id }}</span>
        </button>
        <span class="timeline-label">{{ stage.title }}</span>
      </div>
    </div>
    <div class="timeline-nav">
      <button type="button" class="btn ghost" :disabled="isFirstStage" @click="emit('prev')" aria-label="Poprzedni etap">◀</button>
      <button type="button" class="btn ghost" :disabled="isLastStage" @click="emit('next')" aria-label="Następny etap">▶</button>
    </div>
  </section>
</template>
