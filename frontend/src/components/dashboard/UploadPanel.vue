<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  isDragging: { type: Boolean, default: false },
  error: { type: String, default: null },
})

const emit = defineEmits(['drop', 'dragover', 'dragleave', 'file-select'])

function onFileChange(e) {
  const f = e.target?.files?.[0]
  if (f) emit('file-select', f)
}
</script>

<template>
  <section class="panel side-panel">
    <h3>Ustawienia</h3>
    <label class="upload-zone" :class="{ dragging: isDragging }" @drop="emit('drop', $event)" @dragover="emit('dragover', $event)" @dragleave="emit('dragleave')">
      <input type="file" accept="image/*" @change="onFileChange" />
      <span v-if="loading" class="upload-loading">Trwa analiza...</span>
      <template v-else>
        <span class="upload-text">Dodaj obraz</span>
        <span class="upload-hint">upuść lub kliknij</span>
      </template>
    </label>
    <p v-if="error" class="upload-error">{{ error }}</p>
    <slot />
  </section>
</template>
