<script setup lang="ts">
const props = defineProps<{
  label: string
  progress: number
  running: boolean
  failed?: boolean
  stopped?: boolean
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
</style>
