<script setup lang="ts">
import { Lock, User as UserIcon } from '@element-plus/icons-vue'
import { reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})

async function submit() {
  if (!form.username.trim() || !form.password.trim()) {
    ElMessage.warning('请输入用户名和密码。')
    return
  }
  try {
    await authStore.login(form.username.trim(), form.password)
    ElMessage.success('登录成功，正在进入工作台。')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败，请检查账户信息。')
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-panel panel-card">
      <div class="login-panel__intro">
        <p class="section-title">PowerAgent</p>
        <h1>电力行业解决方案工作台</h1>
        <p>
          面向公司内部员工的解决方案生成平台。登录后可访问历史会话、知识证据和多场景模板能力。
        </p>
      </div>

      <el-form label-position="top" class="login-form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" @keyup.enter="submit">
            <template #prefix>
              <el-icon><UserIcon /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            size="large"
            @keyup.enter="submit"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-button type="primary" size="large" round :loading="authStore.loading" @click="submit">
          登录进入工作台
        </el-button>
      </el-form>

      <div class="login-panel__tips">
        <strong>当前阶段说明</strong>
        <p>暂不开放自助注册，初始账户由管理员通过脚本或后台创建。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 18px;
}

.login-panel {
  width: min(100%, 520px);
  padding: 34px 32px;
  border-radius: 30px;
}

.login-panel__intro h1 {
  margin: 10px 0 12px;
  font-size: 34px;
  line-height: 1.15;
}

.login-panel__intro p:last-child {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
}

.login-form {
  margin-top: 24px;
}

.login-form :deep(.el-button) {
  width: 100%;
  margin-top: 8px;
}

.login-panel__tips {
  margin-top: 22px;
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(15, 93, 140, 0.07);
  color: var(--muted);
}

.login-panel__tips strong {
  display: block;
  color: var(--text);
  margin-bottom: 6px;
}

.login-panel__tips p {
  margin: 0;
  line-height: 1.7;
}
</style>
