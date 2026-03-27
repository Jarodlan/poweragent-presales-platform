<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  title?: string
  description?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  confirm: []
}>()

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog :model-value="modelValue" :title="title || '写回飞书 CRM'" width="560px" destroy-on-close @close="close">
    <div class="crm-writeback-dialog">
      <div class="crm-writeback-dialog__intro">
        <strong>确认写回飞书 CRM</strong>
        <p>{{ description || '当前操作会将平台里的最新结果写入飞书 CRM 跟进记录或附件索引，便于后续统一查看和闭环推进。' }}</p>
      </div>
      <el-alert title="建议在结果内容确认无误后再执行写回，避免 CRM 主档被重复或错误信息污染。" type="warning" :closable="false" />
    </div>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" @click="emit('confirm')">确认写回</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.crm-writeback-dialog {
  display: grid;
  gap: 14px;
}

.crm-writeback-dialog__intro {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(248, 252, 255, 0.96), rgba(238, 247, 255, 0.9));
  border: 1px solid rgba(15, 93, 140, 0.08);
}

.crm-writeback-dialog__intro strong {
  display: block;
  margin-bottom: 8px;
}

.crm-writeback-dialog__intro p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}
</style>
