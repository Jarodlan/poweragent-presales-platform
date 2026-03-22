<script setup lang="ts">
import { Check, Loading } from '@element-plus/icons-vue'

const props = defineProps<{
  label: string
  progress: number
  running: boolean
  failed?: boolean
  stopped?: boolean
  stages?: Array<{
    key: string
    label: string
    status: 'completed' | 'current' | 'failed' | 'stopped'
  }>
}>()
</script>

<template>
  <div v-if="label" class="status-ribbon panel-card">
    <div class="status-ribbon__top">
      <div>
        <p class="section-title">Workflow</p>
        <strong>{{ label }}</strong>
        <small>
          {{
            props.failed
              ? '本次任务中途失败，可以直接在消息卡片里重新生成。'
              : props.stopped
                ? '任务已被手动停止，当前已保留已有内容。'
                : running
                  ? '正在实时推进工作流节点与章节生成。'
                  : '当前会话暂无运行中的生成任务。'
          }}
        </small>
      </div>
      <span>{{ progress }}%</span>
    </div>
    <el-progress
      :percentage="progress"
      :indeterminate="running && progress < 100"
      :show-text="false"
      :status="props.failed ? 'exception' : props.stopped ? 'warning' : undefined"
    />

    <div v-if="props.stages?.length" class="status-ribbon__timeline">
      <div
        v-for="stage in props.stages"
        :key="stage.key"
        :class="['status-ribbon__stage', `is-${stage.status}`]"
      >
        <div class="status-ribbon__stage-icon">
          <el-icon v-if="stage.status === 'completed'"><Check /></el-icon>
          <el-icon v-else-if="stage.status === 'current'" class="is-rotating"><Loading /></el-icon>
          <span v-else-if="stage.status === 'failed'">!</span>
          <span v-else-if="stage.status === 'stopped'">||</span>
        </div>
        <div class="status-ribbon__stage-copy">
          <strong>{{ stage.label }}</strong>
          <small v-if="stage.status === 'completed'">已完成</small>
          <small v-else-if="stage.status === 'current'">进行中</small>
          <small v-else-if="stage.status === 'failed'">失败</small>
          <small v-else-if="stage.status === 'stopped'">已停止</small>
        </div>
      </div>
    </div>
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

.status-ribbon__top small {
  display: block;
  margin-top: 8px;
  color: var(--muted);
  line-height: 1.5;
}

.status-ribbon__top span {
  color: var(--accent);
  font-weight: 700;
}

.status-ribbon__timeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.status-ribbon__stage {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(15, 93, 140, 0.08);
  background: rgba(255, 255, 255, 0.72);
}

.status-ribbon__stage-icon {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  background: #eef3f7;
  color: var(--muted);
}

.status-ribbon__stage-copy {
  min-width: 0;
}

.status-ribbon__stage-copy strong {
  display: block;
  font-size: 13px;
  line-height: 1.45;
  color: var(--text);
}

.status-ribbon__stage-copy small {
  display: block;
  margin-top: 4px;
  color: var(--muted);
}

.status-ribbon__stage.is-completed {
  border-color: rgba(28, 168, 92, 0.18);
  background: rgba(28, 168, 92, 0.06);
}

.status-ribbon__stage.is-completed .status-ribbon__stage-icon {
  background: rgba(28, 168, 92, 0.16);
  color: #13824a;
}

.status-ribbon__stage.is-current {
  border-color: rgba(15, 93, 140, 0.18);
  background: rgba(15, 93, 140, 0.06);
}

.status-ribbon__stage.is-current .status-ribbon__stage-icon {
  background: rgba(15, 93, 140, 0.14);
  color: var(--accent);
}

.status-ribbon__stage.is-failed {
  border-color: rgba(208, 70, 90, 0.18);
  background: rgba(208, 70, 90, 0.06);
}

.status-ribbon__stage.is-failed .status-ribbon__stage-icon {
  background: rgba(208, 70, 90, 0.14);
  color: var(--danger);
}

.status-ribbon__stage.is-stopped {
  border-color: rgba(206, 137, 29, 0.18);
  background: rgba(206, 137, 29, 0.06);
}

.status-ribbon__stage.is-stopped .status-ribbon__stage-icon {
  background: rgba(206, 137, 29, 0.14);
  color: #b76a0d;
}

.is-rotating {
  animation: status-ribbon-rotate 1.2s linear infinite;
}

@keyframes status-ribbon-rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
