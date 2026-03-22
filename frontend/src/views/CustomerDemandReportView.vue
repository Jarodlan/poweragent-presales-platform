<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { ArrowLeft, Download, Refresh } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

import EmptyState from '@/components/common/EmptyState.vue'
import { useCustomerDemandStore } from '@/stores/customerDemand'
import { renderMarkdown } from '@/utils/markdown'
import { formatDateTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const demandStore = useCustomerDemandStore()

const sessionId = computed(() => String(route.params.sessionId || ''))
const report = computed(() => demandStore.currentReport)

async function loadReportContext() {
  if (!sessionId.value) return
  await demandStore.selectSession(sessionId.value)
}

onMounted(loadReportContext)
watch(sessionId, async () => {
  await loadReportContext()
})
</script>

<template>
  <div class="customer-demand-report-shell">
    <header class="customer-demand-report-header panel-card">
      <div class="customer-demand-report-header__left">
        <el-button plain @click="router.push('/customer-demand')">
          <el-icon><ArrowLeft /></el-icon>
          返回会中工作台
        </el-button>
        <div>
          <p class="section-title">Demand Report</p>
          <h1>{{ report?.report_title || demandStore.currentSession?.session_title || '客户需求分析报告' }}</h1>
          <p>
            {{ demandStore.currentSession?.customer_name || '未选中客户' }}
            <span v-if="demandStore.currentSession?.region"> · {{ demandStore.currentSession?.region }}</span>
            <span v-if="report?.updated_at"> · 更新于 {{ formatDateTime(report.updated_at) }}</span>
          </p>
        </div>
      </div>
      <div class="customer-demand-report-header__actions">
        <el-button plain @click="loadReportContext">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :loading="demandStore.exporting" @click="demandStore.exportCurrentReport()">
          <el-icon><Download /></el-icon>
          导出 Markdown
        </el-button>
      </div>
    </header>

    <div v-if="demandStore.loadingDetail" class="customer-demand-report-loading panel-card">
      正在加载报告内容...
    </div>

    <template v-else-if="report">
      <section class="customer-demand-report-grid">
        <article class="panel-card report-main">
          <div class="report-main__head">
            <h2>正式需求分析报告</h2>
            <p>适合会后阅读、导出和流转，不再挤在会中辅助工作台的小卡片里。</p>
          </div>
          <div class="markdown-view" v-html="renderMarkdown(report.report_markdown || '')"></div>
        </article>

        <aside class="report-side">
          <section class="panel-card report-side__card">
            <h3>需求挖掘方向建议</h3>
            <div class="markdown-view" v-html="renderMarkdown(report.digging_suggestions_markdown || '暂无建议')"></div>
          </section>

          <section class="panel-card report-side__card">
            <h3>推荐追问问题</h3>
            <div class="markdown-view" v-html="renderMarkdown(report.recommended_questions_markdown || '暂无推荐问题')"></div>
          </section>

          <section class="panel-card report-side__card">
            <h3>报告元信息</h3>
            <ul class="report-meta-list">
              <li>
                <strong>模型</strong>
                <span>{{ report.llm_model || '未记录' }}</span>
              </li>
              <li>
                <strong>版本</strong>
                <span>V{{ report.report_version }}</span>
              </li>
              <li>
                <strong>知识库开关</strong>
                <span>{{ report.knowledge_enabled ? '已开启' : '未开启' }}</span>
              </li>
              <li>
                <strong>创建时间</strong>
                <span>{{ formatDateTime(report.created_at) }}</span>
              </li>
            </ul>
          </section>
        </aside>
      </section>
    </template>

    <div v-else class="customer-demand-report-empty">
      <EmptyState
        title="还没有正式需求分析报告"
        description="你可以先回到会中工作台，点击“会后生成正式报告”，生成完成后再回来查看。"
      />
    </div>
  </div>
</template>

<style scoped>
.customer-demand-report-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100vh;
  padding: 22px;
}

.customer-demand-report-header,
.report-main,
.report-side__card,
.customer-demand-report-loading {
  padding: 20px 22px;
}

.customer-demand-report-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.customer-demand-report-header__left {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.customer-demand-report-header__left h1 {
  margin: 8px 0 0;
  line-height: 1.2;
}

.customer-demand-report-header__left p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.customer-demand-report-header__actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.customer-demand-report-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  gap: 18px;
}

.report-main__head h2,
.report-side__card h3 {
  margin: 0;
}

.report-main__head p {
  margin: 8px 0 16px;
  color: var(--muted);
  line-height: 1.6;
}

.report-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.report-meta-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.report-meta-list li {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: var(--muted);
}

.report-meta-list strong {
  color: var(--text);
}

.markdown-view {
  line-height: 1.85;
  color: var(--text);
}

.markdown-view :deep(h1),
.markdown-view :deep(h2),
.markdown-view :deep(h3),
.markdown-view :deep(h4) {
  margin-top: 0.9em;
  margin-bottom: 0.35em;
}

.markdown-view :deep(p) {
  margin: 0.55em 0;
}

.markdown-view :deep(ul),
.markdown-view :deep(ol) {
  padding-left: 22px;
}

@media (max-width: 1080px) {
  .customer-demand-report-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 768px) {
  .customer-demand-report-shell {
    padding: 16px;
  }

  .customer-demand-report-header {
    flex-direction: column;
  }

  .customer-demand-report-header__left {
    flex-direction: column;
  }

  .customer-demand-report-header__actions {
    flex-wrap: wrap;
  }
}
</style>
