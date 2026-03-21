<script setup lang="ts">
import { ArrowUp, Setting, VideoPause } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'

import { useMetaStore } from '@/stores/meta'
import { useWorkspaceStore } from '@/stores/workspace'

const metaStore = useMetaStore()
const workspace = useWorkspaceStore()
const expanded = ref(false)

const canSubmit = computed(() => workspace.composerText.trim().length > 0 && !workspace.sending)
</script>

<template>
  <div class="composer panel-card">
    <div class="composer__header">
      <el-button text @click="expanded = !expanded">
        <el-icon><Setting /></el-icon>
        参数配置
      </el-button>
      <span>当前参数仅对本次发送生效</span>
    </div>

    <div v-if="expanded && metaStore.options" class="composer__params">
      <el-form label-position="top">
        <el-form-item label="电网场景">
          <el-select v-model="workspace.composerParams.grid_environment" placeholder="选择电网场景">
            <el-option
              v-for="item in metaStore.options.grid_environment_options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="诊断对象">
          <el-select v-model="workspace.composerParams.equipment_type" placeholder="选择对象">
            <el-option
              v-for="item in metaStore.options.equipment_type_options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="数据基础">
          <el-select v-model="workspace.composerParams.data_basis" multiple collapse-tags>
            <el-option
              v-for="item in metaStore.options.data_basis_options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="目标能力">
          <el-select v-model="workspace.composerParams.target_capability" multiple collapse-tags>
            <el-option
              v-for="item in metaStore.options.target_capability_options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <el-input
      v-model="workspace.composerText"
      type="textarea"
      :autosize="{ minRows: 4, maxRows: 10 }"
      resize="none"
      placeholder="输入你的电力业务场景需求，例如：请给我生成一个配电网故障诊断智能体解决方案。"
      @keydown.ctrl.enter.prevent="workspace.submitCurrentMessage()"
      @keydown.meta.enter.prevent="workspace.submitCurrentMessage()"
    />

    <div class="composer__actions">
      <span>支持 `Ctrl/Command + Enter` 发送</span>
      <div class="composer__buttons">
        <el-button v-if="workspace.sending" type="danger" plain @click="workspace.stopCurrentTask()">
          <el-icon><VideoPause /></el-icon>
          停止
        </el-button>
        <el-button type="primary" round :disabled="!canSubmit" @click="workspace.submitCurrentMessage()">
          <el-icon><ArrowUp /></el-icon>
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.composer {
  padding: 16px;
}

.composer__header,
.composer__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer__header {
  margin-bottom: 12px;
}

.composer__header span,
.composer__actions span {
  font-size: 12px;
  color: var(--muted);
}

.composer__params {
  margin-bottom: 14px;
  padding: 12px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.composer__buttons {
  display: flex;
  gap: 8px;
}

:deep(.el-form) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

:deep(.el-form-item) {
  margin-bottom: 0;
}

@media (max-width: 760px) {
  :deep(.el-form) {
    grid-template-columns: 1fr;
  }

  .composer__actions,
  .composer__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
