<script setup lang="ts">
defineProps<{
  label: string
  progress: number
  running: boolean
}>()
</script>

<template>
  <div v-if="label" class="status-ribbon panel-card">
    <div class="status-ribbon__top">
      <div>
        <p class="section-title">Workflow</p>
        <strong>{{ label }}</strong>
      </div>
      <span>{{ progress }}%</span>
    </div>
    <el-progress :percentage="progress" :indeterminate="running && progress < 100" :show-text="false" />
  </div>
</template>

<style scoped>
.status-ribbon {
  padding: 16px 18px;
}

.status-ribbon__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-ribbon__top strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
}

.status-ribbon__top span {
  color: var(--accent);
  font-weight: 700;
}
</style>
