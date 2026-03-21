<script setup lang="ts">
import { computed } from 'vue'

import { formatDateTime } from '@/utils/time'

const props = defineProps<{
  content: string
  createdAt?: string
}>()

const timeLabel = computed(() => formatDateTime(props.createdAt))
</script>

<template>
  <div class="user-row">
    <div class="user-card">
      <div class="user-card__meta">
        <span>你</span>
        <time>{{ timeLabel }}</time>
      </div>
      <div class="user-bubble">{{ content }}</div>
    </div>
  </div>
</template>

<style scoped>
.user-row {
  display: flex;
  justify-content: flex-end;
}

.user-card {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  max-width: min(760px, 88%);
}

.user-card__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #8aa0b0;
  font-size: 12px;
}

.user-card__meta span {
  font-weight: 700;
  color: #0f5d8c;
}

.user-bubble {
  padding: 16px 18px;
  border-radius: 22px 22px 8px 22px;
  background: linear-gradient(135deg, #0f5d8c 0%, #2b7dae 100%);
  color: white;
  line-height: 1.75;
  white-space: pre-wrap;
  box-shadow: 0 14px 26px rgba(15, 93, 140, 0.2);
}
</style>
