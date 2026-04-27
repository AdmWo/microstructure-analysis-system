<script setup>
import Dashboard from './components/Dashboard.vue'
</script>

<template>
  <div class="app-root">
    <header class="app-header">
      <div class="app-header-inner">
        <h1>Microstructure Segmentation & Analysis</h1>
        <p class="subtitle">Upload an image to detect pores (Otsu thresholding)</p>
      </div>
    </header>
    <main class="app-main">
      <Dashboard />
    </main>
  </div>
</template>
