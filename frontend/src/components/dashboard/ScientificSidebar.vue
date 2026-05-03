<template>
  <aside class="stitch-side-nav">
    <div class="tool-header">
      <h3>Narzedzia naukowe</h3>
      <p>Sterowanie instrumentem</p>
    </div>
    <label class="compact-tool-select-wrap" for="tool-select">
      <span>Narzędzie</span>
      <select id="tool-select" class="compact-tool-select" :value="activeTool" @change="emit('select-tool', $event.target.value)">
        <option v-for="tool in toolActions" :key="tool" :value="tool">{{ tool }}</option>
      </select>
    </label>
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

<script setup>
defineProps({
  toolActions: { type: Array, required: true },
  activeTool: { type: String, required: true },
})

const emit = defineEmits(['select-tool'])
</script>