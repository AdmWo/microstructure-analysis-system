<script setup>
defineProps({
  currentStage: { type: Number, required: true },
  params: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  hasFile: { type: Boolean, default: false },
})

const emit = defineEmits(['run'])
</script>

<template>
  <div class="panel-block">
    <h4>Parametry</h4>
    <div v-if="currentStage === 1" class="controls-grid single-col">
      <label class="control-inline">
        <input v-model="params.denoise_enabled" type="checkbox" />
        Włącz odszumianie
      </label>
      <label>
        Metoda odszumiania
        <select v-model="params.denoise_method" :disabled="!params.denoise_enabled">
          <option value="median">Filtr medianowy</option>
          <option value="gaussian">Rozmycie Gaussa</option>
        </select>
      </label>
    </div>

    <div v-if="currentStage === 2" class="controls-grid single-col">
      <label>
        Metoda binaryzacji
        <select v-model="params.binarization_method">
          <option value="otsu">Otsu</option>
          <option value="manual">Próg ręczny</option>
        </select>
      </label>
      <label>
        Wartość progu
        <input v-model.number="params.manual_threshold" type="number" min="0" max="255" :disabled="params.binarization_method !== 'manual'" />
      </label>
    </div>

    <div v-if="currentStage === 3" class="controls-grid single-col">
      <label>
        Iteracje otwarcia morfologicznego
        <input v-model.number="params.morph_open_iterations" type="number" min="0" max="10" />
      </label>
      <label>
        Iteracje domknięcia morfologicznego
        <input v-model.number="params.morph_close_iterations" type="number" min="0" max="10" />
      </label>
    </div>

    <div v-if="currentStage === 4" class="stage-note">
      Wynik: stereologiczne <strong>A_A</strong> i <strong>V_V</strong>.
    </div>
  </div>

  <div class="panel-block">
    <button type="button" class="btn primary full-width" :disabled="loading || !hasFile" @click="emit('run')">
      {{ loading ? 'Analiza...' : 'Uruchom analizę' }}
    </button>
  </div>
</template>
