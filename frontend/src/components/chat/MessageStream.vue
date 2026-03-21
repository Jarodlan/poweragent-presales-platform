<script setup lang="ts">
import { ArrowDown } from '@element-plus/icons-vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AssistantMessageCard from './AssistantMessageCard.vue'
import UserMessageBubble from './UserMessageBubble.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { EvidenceCard, MessageItem } from '@/types/conversation'

const props = defineProps<{
  messages: MessageItem[]
}>()

const emit = defineEmits<{
  (e: 'open-evidence', cards: EvidenceCard[]): void
  (e: 'choose-example', text: string): void
  (e: 'retry-message', messageId: string): void
}>()

const examples = [
  '给我提供一个智能电网故障诊断的解决方案',
  '请输出一个分布式储能聚合运营智能体方案',
  '帮我生成一个新能源功率预测方案',
]

const streamRef = ref<HTMLElement | null>(null)
const showScrollToBottom = ref(false)
const messageSignature = computed(() =>
  props.messages
    .map((message) => `${message.message_id}:${message.status}:${message.content?.length || 0}:${message.summary?.length || 0}`)
    .join('|'),
)

function updateScrollState() {
  const element = streamRef.value
  if (!element) return
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight
  showScrollToBottom.value = distance > 120
}

async function scrollToBottom(force = false) {
  await nextTick()
  const element = streamRef.value
  if (!element) return
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight
  if (force || distance < 180) {
    element.scrollTo({
      top: element.scrollHeight,
      behavior: force ? 'auto' : 'smooth',
    })
  }
}

watch(messageSignature, async () => {
  await scrollToBottom()
})

onMounted(() => {
  scrollToBottom(true)
  streamRef.value?.addEventListener('scroll', updateScrollState, { passive: true })
})

onBeforeUnmount(() => {
  streamRef.value?.removeEventListener('scroll', updateScrollState)
})
</script>

<template>
  <div ref="streamRef" class="message-stream">
    <EmptyState
      v-if="!props.messages.length"
      title="把电力场景问题交给 Agent"
      description="输入一个业务需求，系统会结合知识库、模板和工作流，为你生成接近真实项目方案的输出。"
    >
      <div class="message-stream__examples">
        <button v-for="item in examples" :key="item" @click="emit('choose-example', item)">{{ item }}</button>
      </div>
    </EmptyState>

    <template v-else>
      <div v-for="message in props.messages" :key="message.message_id" class="message-stream__item">
        <UserMessageBubble
          v-if="message.role === 'user'"
          :content="message.content || message.query_text"
          :created-at="message.created_at"
        />
        <AssistantMessageCard
          v-else
          :message-id="message.message_id"
          :summary="message.summary"
          :content="message.content"
          :assumptions="message.assumptions"
          :evidence-cards="message.evidence_cards"
          :status="message.status"
          :created-at="message.created_at"
          @open-evidence="emit('open-evidence', $event)"
          @retry="emit('retry-message', $event)"
        />
      </div>

      <button
        v-if="showScrollToBottom"
        class="message-stream__scroll-button"
        @click="scrollToBottom(true)"
      >
        <el-icon><ArrowDown /></el-icon>
        回到底部
      </button>
    </template>
  </div>
</template>

<style scoped>
.message-stream {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100%;
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
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.message-stream__examples button:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 93, 140, 0.28);
  box-shadow: 0 10px 18px rgba(15, 38, 56, 0.08);
}

.message-stream__scroll-button {
  position: sticky;
  align-self: flex-end;
  bottom: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid rgba(15, 93, 140, 0.15);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 20px rgba(15, 38, 56, 0.1);
  color: var(--accent);
  cursor: pointer;
}
</style>
