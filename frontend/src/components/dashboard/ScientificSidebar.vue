<script setup>
defineProps({
  toolActions: { type: Array, required: true },
  activeTool: { type: String, required: true },
})

const emit = defineEmits(['select-tool'])
</script>

<template>
  <aside class="stitch-side-nav">
    <div class="tool-header">
      <h3>Narzedzia naukowe</h3>
      <p>Sterowanie instrumentem</p>
    </div>
    <div class="tool-list">
      <button
        v-for="tool in toolActions"
        :key="tool"
        type="button"
        class="tool-button"
        :class="{ active: activeTool === tool }"
        @click="emit('select-tool', tool)"
      >
        <span>{{ tool }}</span>
      </button>
    </div>

    <div class="control-panel">
      <slot />
    </div>
  </aside>
</template>
