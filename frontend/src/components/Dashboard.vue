<script setup>
import { ref, computed } from 'vue'
import { analyzeImage } from '../api/analyze'

const file = ref(null)
const result = ref(null)
const error = ref(null)
const loading = ref(false)
const isDragging = ref(false)
const uploadedMimeType = ref('image/png')

const originalDataUrl = computed(() => {
  if (!result.value?.original_b64) return null
  return `data:${uploadedMimeType.value};base64,${result.value.original_b64}`
})

const maskDataUrl = computed(() => {
  if (!result.value?.mask_b64) return null
  return `data:image/png;base64,${result.value.mask_b64}`
})

const porosityPercent = computed(() => result.value?.porosity_percent ?? null)
const poreCount = computed(() => result.value?.pore_count ?? null)

function onDrop(e) {
  isDragging.value = false
  e.preventDefault()
  const f = e.dataTransfer?.files?.[0]
  if (f?.type?.startsWith('image/')) {
    file.value = f
    uploadedMimeType.value = f.type || 'image/png'
    runAnalysis(f)
  } else {
    error.value = 'Please drop an image file (PNG, JPEG, etc.).'
  }
}

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onFileSelect(e) {
  const f = e.target?.files?.[0]
  if (f) {
    file.value = f
    uploadedMimeType.value = f.type || 'image/png'
    runAnalysis(f)
  }
}

async function runAnalysis(f) {
  error.value = null
  result.value = null
  loading.value = true
  try {
    result.value = await analyzeImage(f)
  } catch (e) {
    error.value = e.message || 'Analysis failed.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="dashboard">
    <!-- Upload zone -->
    <section>
      <label
        class="upload-zone"
        :class="{ dragging: isDragging }"
        @drop="onDrop"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
      >
        <input
          type="file"
          accept="image/*"
          @change="onFileSelect"
        />
        <span v-if="loading" class="upload-loading">Analyzing…</span>
        <template v-else>
          <span class="upload-text">Drag & drop an image here</span>
          <span class="upload-hint">or click to choose</span>
        </template>
      </label>
      <p v-if="error" class="upload-error">{{ error }}</p>
    </section>

    <!-- Statistics card -->
    <section v-if="porosityPercent != null" class="results-card">
      <h2>Results</h2>
      <div class="results-stats">
        <div class="stat-box">
          <p class="label">Detected Porosity (%)</p>
          <p class="value">{{ porosityPercent }}%</p>
        </div>
        <div class="stat-box">
          <p class="label">Pore count</p>
          <p class="value">{{ poreCount }}</p>
        </div>
      </div>
    </section>

    <!-- Side-by-side images -->
    <section v-if="originalDataUrl && maskDataUrl" class="images-grid">
      <div class="image-card">
        <h3>Original Image</h3>
        <img
          :src="originalDataUrl"
          alt="Original microstructure"
        />
      </div>
      <div class="image-card image-card-mask">
        <h3>Processed Mask</h3>
        <img
          :src="maskDataUrl"
          alt="Processed mask (pores)"
        />
      </div>
    </section>
  </div>
</template>
