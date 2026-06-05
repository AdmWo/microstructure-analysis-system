import { defineStore } from 'pinia'

const STAGES = [
  { id: 1, key: 'preprocessing', title: 'Przetwarzanie wstępne' },
  { id: 2, key: 'calibration', title: 'Kalibracja skali' },
  { id: 3, key: 'binarization', title: 'Segmentacja (Binaryzacja)' },
  { id: 4, key: 'featureAnalysis', title: 'Identyfikacja i analiza cech' },
  { id: 5, key: 'interpretation', title: 'Interpretacja' },
]

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    currentStage: 1,
    stages: STAGES,
    interactionMode: 'roi', // 'roi', 'scale' or 'measure'
    scalePxLength: 0.0,
    scalePhysicalValue: 20.0, // default physical distance, e.g. 20.0
    scaleUnit: 'µm', // 'µm' or 'mm'
    scaleLineCoords: null, // { startX, startY, endX, endY } in natural image space
    measureLineCoords: null, // { startX, startY, endX, endY } in natural image space
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
      this.interactionMode = 'roi'
      this.scalePxLength = 0.0
      this.scalePhysicalValue = 20.0
      this.scaleUnit = 'µm'
      this.scaleLineCoords = null
      this.measureLineCoords = null
    },
  },
})
