<script setup>
defineProps({
  aaPercent: { type: Number, default: null },
  vvPercent: { type: Number, default: null },
  poreCount: { type: Number, default: null },
  maskDataUrl: { type: String, default: null },
})
</script>

<template>
  <aside class="panel side-panel">
    <h3>Wynik</h3>
    <div class="panel-block">
      <div class="stat-box stat-box-primary">
        <p class="label">Porowatość A_A (%)</p>
        <p class="value">{{ aaPercent ?? '--' }}</p>
      </div>
      <div class="stat-box">
        <p class="label">Porowatość V_V (%)</p>
        <p class="value">{{ vvPercent ?? '--' }}</p>
      </div>
      <div class="stat-box">
        <p class="label">Liczba porów</p>
        <p class="value">{{ poreCount ?? '--' }}</p>
      </div>
    </div>

    <div class="panel-block" v-if="maskDataUrl">
      <h4>Podgląd maski</h4>
      <div class="mask-preview">
        <img :src="maskDataUrl" alt="Maska po binaryzacji i czyszczeniu" />
      </div>
    </div>
  </aside>
</template>
