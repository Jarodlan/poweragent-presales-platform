<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Briefcase } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import ConversationSidebar from '@/components/sidebar/ConversationSidebar.vue'
import MessageComposer from '@/components/composer/MessageComposer.vue'
import MessageStream from '@/components/chat/MessageStream.vue'
import EvidenceDrawer from '@/components/evidence/EvidenceDrawer.vue'
import CrmActionButton from '@/components/crm/CrmActionButton.vue'
import CrmSearchDialog from '@/components/crm/CrmSearchDialog.vue'
import CrmWritebackDialog from '@/components/crm/CrmWritebackDialog.vue'
import CrmWritebackHistoryDrawer from '@/components/crm/CrmWritebackHistoryDrawer.vue'
import { bindConversationCrm, writebackConversationCrm } from '@/api/crm'
import { createPresalesTaskFromSolution } from '@/api/presales'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useWorkspaceStore } from '@/stores/workspace'
import { consumeSolutionHandoffDraft } from '@/utils/solutionHandoff'

const metaStore = useMetaStore()
const workspace = useWorkspaceStore()
const authStore = useAuthStore()
const presalesDialogVisible = ref(false)
const creatingPresalesTask = ref(false)
const crmBindDialogVisible = ref(false)
const crmWritebackDialogVisible = ref(false)
const crmHistoryVisible = ref(false)
const crmSubmitting = ref(false)
const presalesForm = reactive({
  task_title: '',
  task_description: '',
  customer_name: '',
  priority: 'medium',
  due_at: '',
  next_follow_up_at: '',
})

const canCreatePresalesTask = computed(() => authStore.hasPermission('presales_task.manage') || authStore.user?.is_superuser)
const canBindCrm = computed(() => authStore.hasPermission('crm.bind') || authStore.user?.is_superuser)
const canWritebackCrm = computed(() => authStore.hasPermission('crm.writeback') || authStore.user?.is_superuser)
const latestCompletedAssistantMessage = computed(() =>
  [...workspace.currentMessages]
    .reverse()
    .find((item) => item.role === 'assistant' && item.status === 'completed' && (item.content || item.summary)),
)

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

function openPresalesDialog() {
  if (!canCreatePresalesTask.value) {
    ElMessage.warning('当前账户没有创建售前任务的权限。')
    return
  }
  if (!workspace.currentConversationId || !latestCompletedAssistantMessage.value) {
    ElMessage.warning('请先完成一轮解决方案生成，再创建售前任务。')
    return
  }
  presalesForm.task_title = `${workspace.currentConversation?.title || '解决方案'}后续推进`
  presalesForm.customer_name = ''
  presalesForm.priority = 'medium'
  presalesForm.due_at = ''
  presalesForm.next_follow_up_at = ''
  presalesForm.task_description = [
    `来源会话：${workspace.currentConversation?.title || '未命名方案会话'}`,
    latestCompletedAssistantMessage.value.summary ? `方案摘要：${latestCompletedAssistantMessage.value.summary}` : '',
    '请基于当前解决方案结果，推进客户沟通、内部评审或演示安排。',
  ]
    .filter(Boolean)
    .join('\n')
  presalesDialogVisible.value = true
}

async function submitPresalesTaskFromSolution() {
  if (!workspace.currentConversationId || !latestCompletedAssistantMessage.value) {
    ElMessage.warning('当前没有可转化的解决方案结果。')
    return
  }
  if (!presalesForm.task_title.trim()) {
    ElMessage.warning('请先填写任务标题。')
    return
  }
  creatingPresalesTask.value = true
  try {
    await createPresalesTaskFromSolution({
      source_id: workspace.currentConversationId,
      source_title: workspace.currentConversation?.title || '解决方案结果',
      customer_name: presalesForm.customer_name.trim(),
      task_title: presalesForm.task_title.trim(),
      task_description: presalesForm.task_description.trim(),
      priority: presalesForm.priority,
      due_at: presalesForm.due_at || null,
      next_follow_up_at: presalesForm.next_follow_up_at || null,
      payload_json: {
        message_id: latestCompletedAssistantMessage.value.message_id,
      },
    })
    presalesDialogVisible.value = false
    ElMessage.success('已创建售前任务，接下来可以去售前闭环中心继续推进。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建售前任务失败')
  } finally {
    creatingPresalesTask.value = false
  }
}

async function refreshConversationContext() {
  await workspace.loadConversationList()
  if (workspace.currentConversationId) {
    await workspace.selectConversation(workspace.currentConversationId)
  }
}

async function handleBindCrm(payload: { crm_customer_record_id: string; crm_opportunity_record_id: string }) {
  if (!workspace.currentConversationId) return
  crmSubmitting.value = true
  try {
    await bindConversationCrm(workspace.currentConversationId, payload)
    await refreshConversationContext()
    ElMessage.success('已绑定飞书 CRM 客户/商机')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '绑定 CRM 失败')
  } finally {
    crmSubmitting.value = false
  }
}

async function handleWritebackCrm() {
  if (!workspace.currentConversationId) return
  crmSubmitting.value = true
  try {
    await writebackConversationCrm(workspace.currentConversationId, {
      confirmed: true,
      write_target: 'followup',
      mode: 'append',
      sync_next_followup: true,
    })
    crmWritebackDialogVisible.value = false
    crmHistoryVisible.value = true
    await refreshConversationContext()
    ElMessage.success('解决方案结果已写回飞书 CRM')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '写回 CRM 失败')
  } finally {
    crmSubmitting.value = false
  }
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
          <el-button
            v-if="canCreatePresalesTask"
            type="warning"
            plain
            :disabled="!latestCompletedAssistantMessage"
            @click="openPresalesDialog"
          >
            <el-icon><Briefcase /></el-icon>
            创建售前任务
          </el-button>
          <span>{{ workspace.currentConversation?.status || 'idle' }}</span>
          <span>{{ workspace.currentMessages.length }} 条消息</span>
        </div>
      </header>

      <div v-if="workspace.importedDraftNotice" class="workspace-main__imported-banner">
        <span>{{ workspace.importedDraftNotice }}</span>
        <el-button link type="primary" @click="workspace.clearImportedDraftNotice()">知道了</el-button>
      </div>

      <CrmActionButton
        :state="workspace.currentConversation"
        :can-bind="canBindCrm"
        :can-writeback="canWritebackCrm"
        title="飞书 CRM 关联"
        description="把当前解决方案会话关联到飞书 CRM 的客户和商机上，后续结果写回和售前推进会更顺。"
        writeback-label="写回解决方案结果"
        @bind="crmBindDialogVisible = true"
        @writeback="crmWritebackDialogVisible = true"
        @history="crmHistoryVisible = true"
      />

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

    <el-dialog
      v-model="presalesDialogVisible"
      title="从解决方案结果创建售前任务"
      width="720px"
      destroy-on-close
    >
      <el-form label-width="96px">
        <el-form-item label="任务标题">
          <el-input v-model="presalesForm.task_title" placeholder="请输入售前任务标题" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="presalesForm.customer_name" placeholder="可选，便于后续在售前闭环中心筛选" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="presalesForm.priority">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="到期时间">
          <el-date-picker v-model="presalesForm.due_at" type="datetime" placeholder="可选" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item label="回访时间">
          <el-date-picker v-model="presalesForm.next_follow_up_at" type="datetime" placeholder="可选" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item label="任务说明">
          <el-input v-model="presalesForm.task_description" type="textarea" :rows="7" resize="vertical" placeholder="补充下一步跟进动作、方案评审或客户沟通计划" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="presalesDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingPresalesTask" @click="submitPresalesTaskFromSolution">
          创建售前任务
        </el-button>
      </template>
    </el-dialog>

    <CrmSearchDialog
      v-model="crmBindDialogVisible"
      @confirm="handleBindCrm"
    />

    <CrmWritebackDialog
      v-model="crmWritebackDialogVisible"
      title="写回解决方案结果到飞书 CRM"
      description="当前会把这轮解决方案结果写入飞书 CRM 跟进记录，适合在准备进入售前推进阶段时执行。"
      :loading="crmSubmitting"
      @confirm="handleWritebackCrm"
    />

    <CrmWritebackHistoryDrawer
      v-model="crmHistoryVisible"
      object-type="solution_result"
      :object-id="latestCompletedAssistantMessage?.message_id || ''"
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
