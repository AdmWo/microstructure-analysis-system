<script setup>
import { onMounted, ref, watch } from 'vue'
import Dashboard from './components/Dashboard.vue'

const theme = ref('light')

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}

onMounted(() => {
  const saved = localStorage.getItem('mas-theme')
  if (saved === 'dark' || saved === 'light') {
    theme.value = saved
  }
})

watch(theme, (value) => {
  localStorage.setItem('mas-theme', value)
}, { immediate: true })
</script>

<template>
  <div class="app-root" :class="{ 'theme-dark': theme === 'dark' }">
    <header class="app-header">
      <div class="app-header-inner">
        <div>
          <h1>System Analizy Mikrostruktury</h1>
          <p class="subtitle">Nowoczesny workflow: ROI -> Binaryzacja -> Analiza cech -> Interpretacja (A_A / V_V)</p>
        </div>
        <button type="button" class="theme-toggle" :aria-label="theme === 'light' ? 'Włącz tryb ciemny' : 'Włącz tryb jasny'" @click="toggleTheme">
          <span class="theme-icon" aria-hidden="true">{{ theme === 'light' ? '🌙' : '☀️' }}</span>
        </button>
      </div>
    </header>
    <main class="app-main">
      <Dashboard />
    </main>
  </div>
</template>
