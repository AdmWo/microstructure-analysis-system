import { defineStore } from 'pinia'

const STAGES = [
  { id: 1, key: 'preprocessing', title: 'Przetwarzanie wstępne' },
  { id: 2, key: 'binarization', title: 'Segmentacja (Binaryzacja)' },
  { id: 3, key: 'featureAnalysis', title: 'Identyfikacja i analiza cech' },
  { id: 4, key: 'interpretation', title: 'Interpretacja' },
]

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    currentStage: 1,
    stages: STAGES,
  }),
  getters: {
    isFirstStage: (state) => state.currentStage === 1,
    isLastStage: (state) => state.currentStage === state.stages.length,
  },
  actions: {
    goToStage(stageId) {
      if (stageId >= 1 && stageId <= this.stages.length) {
        this.currentStage = stageId
      }
    },
    nextStage() {
      if (!this.isLastStage) this.currentStage += 1
    },
    previousStage() {
      if (!this.isFirstStage) this.currentStage -= 1
    },
    reset() {
      this.currentStage = 1
    },
  },
})
