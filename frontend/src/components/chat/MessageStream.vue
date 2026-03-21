<script setup lang="ts">
import AssistantMessageCard from './AssistantMessageCard.vue'
import UserMessageBubble from './UserMessageBubble.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { EvidenceCard, MessageItem } from '@/types/conversation'

const props = defineProps<{
  messages: MessageItem[]
}>()

const emit = defineEmits<{
  (e: 'open-evidence', cards: EvidenceCard[]): void
}>()

const examples = [
  '给我提供一个智能电网故障诊断的解决方案',
  '请输出一个分布式储能聚合运营智能体方案',
  '帮我生成一个新能源功率预测方案',
]
</script>

<template>
  <div class="message-stream">
    <EmptyState
      v-if="!props.messages.length"
      title="把电力场景问题交给 Agent"
      description="输入一个业务需求，系统会结合知识库、模板和工作流，为你生成接近真实项目方案的输出。"
    >
      <div class="message-stream__examples">
        <button v-for="item in examples" :key="item">{{ item }}</button>
      </div>
    </EmptyState>

    <template v-else>
      <div v-for="message in props.messages" :key="message.message_id" class="message-stream__item">
        <UserMessageBubble v-if="message.role === 'user'" :content="message.content || message.query_text" />
        <AssistantMessageCard
          v-else
          :summary="message.summary"
          :content="message.content"
          :assumptions="message.assumptions"
          :evidence-cards="message.evidence_cards"
          :status="message.status"
          @open-evidence="emit('open-evidence', $event)"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-stream {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.message-stream__examples {
  margin-top: 24px;
  display: grid;
  gap: 12px;
}

.message-stream__examples button {
  text-align: left;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(15, 93, 140, 0.16);
  background: white;
  color: var(--text);
}
</style>
