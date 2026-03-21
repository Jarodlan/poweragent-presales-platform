<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <div class="user-row">
    <div class="user-bubble">{{ content }}</div>
  </div>
</template>

<style scoped>
.user-row {
  display: flex;
  justify-content: flex-end;
}

.user-bubble {
  max-width: min(720px, 88%);
  padding: 16px 18px;
  border-radius: 22px 22px 8px 22px;
  background: linear-gradient(135deg, #0f5d8c 0%, #2b7dae 100%);
  color: white;
  line-height: 1.75;
  white-space: pre-wrap;
  box-shadow: 0 14px 26px rgba(15, 93, 140, 0.2);
}
</style>
