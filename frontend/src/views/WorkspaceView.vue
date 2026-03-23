<script setup lang="ts">
import { onMounted } from 'vue'

import ConversationSidebar from '@/components/sidebar/ConversationSidebar.vue'
import MessageComposer from '@/components/composer/MessageComposer.vue'
import MessageStream from '@/components/chat/MessageStream.vue'
import EvidenceDrawer from '@/components/evidence/EvidenceDrawer.vue'
import { useMetaStore } from '@/stores/meta'
import { useWorkspaceStore } from '@/stores/workspace'
import { consumeSolutionHandoffDraft } from '@/utils/solutionHandoff'

const metaStore = useMetaStore()
const workspace = useWorkspaceStore()

onMounted(async () => {
  await metaStore.loadOptions()
  workspace.applyDefaultParams(metaStore.options?.default_params)
  await workspace.loadConversationList()
  const handoffDraft = consumeSolutionHandoffDraft()
  if (handoffDraft) {
    await workspace.applyImportedDraft(handoffDraft)
  } else if (workspace.currentConversationId) {
    await workspace.selectConversation(workspace.currentConversationId)
  }
})

function useExamplePrompt(text: string) {
  workspace.setComposerText(text)
}
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

      <div v-if="workspace.importedDraftNotice" class="workspace-main__imported-banner">
        <span>{{ workspace.importedDraftNotice }}</span>
        <el-button link type="primary" @click="workspace.clearImportedDraftNotice()">知道了</el-button>
      </div>

      <section class="workspace-main__stream">
        <MessageStream
          :messages="workspace.currentMessages"
          :workflow-label="workspace.currentStepLabel"
          :workflow-progress="workspace.currentProgress"
          :workflow-running="workspace.sending"
          :workflow-failed="workspace.currentConversation?.status === 'failed'"
          :workflow-stopped="!workspace.sending && workspace.currentStepLabel === '已停止生成'"
          :workflow-stages="workspace.workflowStages"
          :workflow-anchor-message-id="workspace.workflowAnchorMessageId"
          :show-workflow-ribbon="workspace.showWorkflowRibbon"
          @open-evidence="workspace.openEvidence"
          @choose-example="useExamplePrompt"
          @retry-message="workspace.retryAssistantMessage"
        />
      </section>

      <footer class="workspace-main__composer">
        <div class="workspace-main__composer-inner">
          <MessageComposer />
        </div>
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
  grid-template-rows: auto minmax(0, 1fr) auto;
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
  padding-bottom: 24px;
}

.workspace-main__imported-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(242, 169, 59, 0.12);
  border: 1px solid rgba(242, 169, 59, 0.24);
  color: #7a4a00;
}

.workspace-main__composer {
  position: sticky;
  bottom: 0;
  z-index: 12;
  padding: 8px 0 0;
  background: transparent;
  backdrop-filter: none;
}

.workspace-main__composer-inner {
  max-width: 980px;
  margin: 0 auto;
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
