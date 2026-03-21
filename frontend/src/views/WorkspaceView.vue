<script setup lang="ts">
import { onMounted } from 'vue'

import ConversationSidebar from '@/components/sidebar/ConversationSidebar.vue'
import MessageComposer from '@/components/composer/MessageComposer.vue'
import MessageStream from '@/components/chat/MessageStream.vue'
import StatusRibbon from '@/components/chat/StatusRibbon.vue'
import EvidenceDrawer from '@/components/evidence/EvidenceDrawer.vue'
import { useMetaStore } from '@/stores/meta'
import { useWorkspaceStore } from '@/stores/workspace'

const metaStore = useMetaStore()
const workspace = useWorkspaceStore()

onMounted(async () => {
  await metaStore.loadOptions()
  workspace.applyDefaultParams(metaStore.options?.default_params)
  await workspace.loadConversationList()
  if (workspace.currentConversationId) {
    await workspace.selectConversation(workspace.currentConversationId)
  }
})
</script>

<template>
  <div class="workspace-shell">
    <ConversationSidebar />

    <main class="workspace-main">
      <header class="workspace-main__header">
        <div>
          <p class="section-title">Conversation</p>
          <h2>{{ workspace.currentConversation?.title || '新的解决方案会话' }}</h2>
        </div>
        <div class="workspace-main__meta">
          <span>{{ workspace.currentConversation?.status || 'idle' }}</span>
          <span>{{ workspace.currentMessages.length }} 条消息</span>
        </div>
      </header>

      <StatusRibbon
        :label="workspace.currentStepLabel"
        :progress="workspace.currentProgress"
        :running="workspace.sending"
      />

      <section class="workspace-main__stream">
        <MessageStream :messages="workspace.currentMessages" @open-evidence="workspace.openEvidence" />
      </section>

      <footer class="workspace-main__composer">
        <MessageComposer />
      </footer>
    </main>

    <EvidenceDrawer
      v-model="workspace.evidenceDrawerVisible"
      :items="workspace.activeEvidenceCards"
    />
  </div>
</template>

<style scoped>
.workspace-main {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 18px;
  padding: 22px;
  min-width: 0;
}

.workspace-main__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.workspace-main__header h2 {
  margin: 6px 0 0;
  font-size: 30px;
  line-height: 1.2;
}

.workspace-main__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.workspace-main__meta span {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(15, 93, 140, 0.12);
  color: var(--muted);
  font-size: 12px;
}

.workspace-main__stream {
  min-height: 0;
  overflow: auto;
  padding-right: 6px;
}

.workspace-main__composer {
  position: sticky;
  bottom: 0;
}

@media (max-width: 960px) {
  .workspace-main {
    padding: 16px;
  }

  .workspace-main__header {
    flex-direction: column;
  }
}
</style>
