<script setup>
defineProps({
  theme: {
    type: String,
    required: true,
    validator: (v) => ['light', 'dark'].includes(v),
  },
})

const emit = defineEmits(['toggle-theme', 'open-help'])
</script>

<template>
  <header class="stitch-topbar">
    <div class="brand-wrap">
      <span class="brand-title">System analizy mikrostruktury</span>
    </div>
    <div class="top-icons">
      <button type="button" class="icon-btn" @click="emit('toggle-theme')">{{ theme === 'dark' ? 'Tryb jasny' : 'Tryb ciemny' }}</button>
      <button type="button" class="icon-btn" @click="emit('open-help')">Help (?)</button>
    </div>
  </header>
</template>
