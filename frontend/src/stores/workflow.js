import { defineStore } from 'pinia'

const STAGES = [
  { id: 1, key: 'image', title: 'Obraz' },
  { id: 2, key: 'preprocessing', title: 'Przetwarzanie wstępne' },
  { id: 3, key: 'calibration', title: 'Kalibracja skali' },
  { id: 4, key: 'binarization', title: 'Segmentacja (Binaryzacja)' },
  { id: 5, key: 'featureAnalysis', title: 'Identyfikacja i analiza cech' },
  { id: 6, key: 'interpretation', title: 'Interpretacja / Wyniki' },
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
    // Average values across all images
    avgAaPercent: null,
    avgPoreCount: null,
    avgTotalRoiArea: null,
    avgPoreArea: null,
    avgNa: null,
    avgInferenceTimeMs: null,
    avgTotalExecutionTimeMs: null,
    avgPreprocessMs: null,
    avgSegmentMs: null,
    avgMorphologyMs: null,
    avgStereologyMs: null,
    avgEncodingMs: null,
    // Active image or single image metrics
    avgD1CircularityPerimeter: null,
    avgD2CircularityArea: null,
    avgEdgeIndicator: null,
    avgShapeFactorRaw: null,
    avgRoundnessEllipse: null,
    avgMalinowskaFactor: null,
    inferenceTimeMs: null,
    totalExecutionTimeMs: null,
    tPreprocessMs: null,
    tSegmentMs: null,
    tMorphologyMs: null,
    tStereologyMs: null,
    tEncodingMs: null,

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
      this.avgAaPercent = null
      this.avgPoreCount = null
      this.avgTotalRoiArea = null
      this.avgPoreArea = null
      this.avgNa = null
      this.avgInferenceTimeMs = null
      this.avgTotalExecutionTimeMs = null
      this.avgPreprocessMs = null
      this.avgSegmentMs = null
      this.avgMorphologyMs = null
      this.avgStereologyMs = null
      this.avgEncodingMs = null
      this.avgD1CircularityPerimeter = null
      this.avgD2CircularityArea = null
      this.avgEdgeIndicator = null
      this.avgShapeFactorRaw = null
      this.avgRoundnessEllipse = null
      this.avgMalinowskaFactor = null
      this.inferenceTimeMs = null
      this.totalExecutionTimeMs = null
      this.tPreprocessMs = null
      this.tSegmentMs = null
      this.tMorphologyMs = null
      this.tStereologyMs = null
      this.tEncodingMs = null
    },
  },
})

