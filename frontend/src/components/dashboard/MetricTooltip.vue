<template>
  <Transition name="fade">
    <div
      v-if="visible"
      ref="tooltipRef"
      class="custom-tooltip-popup"
      :style="{ top: `${top}px`, left: `${left}px` }"
      @mouseenter="emit('mouseenter')"
      @mouseleave="emit('mouseleave')"
    >
      <div class="tooltip-header">{{ title }}</div>
      <div class="tooltip-body">{{ description }}</div>
      <div v-if="formula" class="tooltip-formula">
        <span class="formula-label">Równanie:</span>
        <div class="formula-latex" v-html="renderedFormula" />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const emit = defineEmits(['mouseenter', 'mouseleave'])

const tooltipRef = ref(null)

defineExpose({
  el: tooltipRef
})

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  formula: { type: String, default: '' },
  top: { type: Number, default: 0 },
  left: { type: Number, default: 0 }
})

const renderedFormula = computed(() => {
  if (!props.formula) return ''
  try {
    return katex.renderToString(props.formula, {
      displayMode: true,
      throwOnError: false
    })
  } catch (err) {
    console.error('KaTeX rendering error:', err)
    return props.formula
  }
})
</script>

<style scoped>
.custom-tooltip-popup {
  position: fixed;
  z-index: 1000;
  min-width: 260px;
  max-width: 450px;
  width: max-content;
  background: rgba(32, 31, 32, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 209, 255, 0.25);
  color: var(--text);
  padding: 12px 14px;
  border-radius: 8px;
  font-family: 'Space Grotesk', sans-serif;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  transform: translate(-100%, -50%);
  pointer-events: auto; /* Allow mouse hover to copy text */
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-sizing: border-box;
}

.tooltip-header {
  font-weight: 700;
  font-size: 13px;
  color: var(--primary);
  margin: 0;
}

.tooltip-body {
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-soft);
  margin: 0;
  white-space: normal;
}

.tooltip-formula {
  background: rgba(0, 209, 255, 0.08);
  border: 1px solid rgba(0, 209, 255, 0.15);
  border-radius: 4px;
  padding: 6px 10px;
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.formula-label {
  font-size: 9px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 0.05em;
}

.formula-latex {
  margin-top: 2px;
  overflow: visible; /* Remove ugly and useless scrollbar */
}

.formula-latex :deep(.katex-display) {
  margin: 2px 0;
  text-align: left;
}

.formula-latex :deep(.katex) {
  font-size: 1.15em;
}

/* Light mode overrides */
:global(.theme-light .custom-tooltip-popup) {
  background: #ffffff;
  border: 1px solid rgba(0, 72, 141, 0.2);
  color: #191c1e;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
}

:global(.theme-light .tooltip-body) {
  color: #2c3e50;
}

:global(.theme-light .tooltip-formula) {
  background: #f4f7fa;
  border-color: #dbe3eb;
}

:global(.theme-light .formula-label) {
  color: #5a6a85;
}

:global(.theme-light .formula-latex .katex) {
  color: #00488d; /* Force high-contrast primary color for LaTeX formulas in light mode */
}

/* Fade Transition for smooth entry/exit */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-102%, -50%) scale(0.96);
}
</style>
