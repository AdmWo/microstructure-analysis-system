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

<style scoped>
.stitch-topbar {
  height: 56px;
  border-bottom: 1px solid #1c1c1f;
  background: #121214;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--surface);
  color: var(--text);
  border-color: var(--outline);
}

.brand-wrap {
  display: flex;
  align-items: center;
  gap: 32px;
}

.brand-title {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.92rem;
  font-weight: 800;
}

.top-nav {
  display: flex;
  gap: 8px;
}

.top-nav-item {
  background: transparent;
  border: 0;
  color: #7b8189;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font: 700 11px/1 'Space Grotesk', sans-serif;
  padding: 6px 8px;
  cursor: pointer;
}

.top-nav-item.active {
  color: #00d1ff;
  border-bottom: 2px solid #00d1ff;
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.top-icons {
  display: flex;
  gap: 12px;
  color: #97a3aa;
}

.top-icons .icon-btn {
  border: 1px solid var(--outline);
  background: var(--surface-2);
  color: var(--text);
  padding: 0.35rem 0.6rem;
  border-radius: 4px;
  font: 600 11px/1 'Space Grotesk', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  cursor: pointer;
}

@media (max-width: 480px) {
  .stitch-topbar {
    padding: 0 12px !important;
  }
  .brand-title {
    font-size: 0.75rem !important;
    letter-spacing: 0.04em !important;
  }
  .top-icons {
    gap: 8px !important;
  }
  .top-icons .icon-btn {
    padding: 0.25rem 0.4rem !important;
    font-size: 9px !important;
  }
}
</style>
