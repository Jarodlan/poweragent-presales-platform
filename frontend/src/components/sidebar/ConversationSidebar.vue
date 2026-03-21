<script setup lang="ts">
import { Plus, Search } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

import { useWorkspaceStore } from '@/stores/workspace'
import { formatDateTime } from '@/utils/time'

const workspace = useWorkspaceStore()
const keyword = ref('')

const groups = computed(() => {
  const normalized = keyword.value.trim().toLowerCase()
  if (!normalized) return workspace.groupedConversations
  return workspace.groupedConversations
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        [item.title, item.last_user_message].join(' ').toLowerCase().includes(normalized),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__top">
      <div>
        <p class="section-title">PowerAgent</p>
        <h1>解决方案工作台</h1>
      </div>
      <el-button type="primary" round @click="workspace.createNewConversation()">
        <el-icon><Plus /></el-icon>
        新建会话
      </el-button>
    </div>

    <el-input v-model="keyword" placeholder="搜索会话" clearable>
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div class="sidebar__groups">
      <section v-for="group in groups" :key="group.label" class="sidebar__group">
        <p class="sidebar__group-title">{{ group.label }}</p>
        <button
          v-for="item in group.items"
          :key="item.conversation_id"
          class="sidebar__item"
          :class="{ 'is-active': item.conversation_id === workspace.currentConversationId }"
          @click="workspace.selectConversation(item.conversation_id)"
        >
          <div class="sidebar__item-top">
            <strong>{{ item.title || '未命名会话' }}</strong>
            <span :class="['sidebar__status', `is-${item.status}`]">{{ item.status }}</span>
          </div>
          <p>{{ item.last_user_message || '等待第一次提问' }}</p>
          <time>{{ formatDateTime(item.last_message_at || item.updated_at) }}</time>
        </button>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 22px 18px;
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(24, 50, 71, 0.08);
}

.sidebar__top {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar__top h1 {
  margin: 8px 0 0;
  font-size: 26px;
  line-height: 1.2;
}

.sidebar__groups {
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-right: 4px;
}

.sidebar__group-title {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
}

.sidebar__item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 20px;
  padding: 14px 14px 12px;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: 0.2s ease;
}

.sidebar__item:hover,
.sidebar__item.is-active {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(15, 93, 140, 0.16);
  box-shadow: 0 12px 22px rgba(15, 38, 56, 0.08);
}

.sidebar__item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sidebar__item strong {
  display: -webkit-box;
  overflow: hidden;
  font-size: 14px;
  line-height: 1.45;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.sidebar__item p {
  margin: 10px 0 10px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--muted);
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.sidebar__item time {
  font-size: 12px;
  color: #8aa0b0;
}

.sidebar__status {
  flex: none;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  text-transform: uppercase;
}

.sidebar__status.is-running {
  background: #eef8ee;
  color: var(--success);
}

.sidebar__status.is-failed {
  background: #fdeeee;
  color: var(--danger);
}

.sidebar__status.is-idle {
  background: #edf3f8;
  color: var(--muted);
}

@media (max-width: 960px) {
  .sidebar {
    display: none;
  }
}
</style>
