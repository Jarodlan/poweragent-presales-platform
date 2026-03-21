<script setup lang="ts">
import { Lock, User as UserIcon } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: authStore.lastUsername,
  password: '',
})
const usernameInputRef = ref()

onMounted(() => {
  window.setTimeout(() => {
    usernameInputRef.value?.focus?.()
  }, 120)
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
    <div class="login-page__grid" />
    <div class="login-page__glow login-page__glow--left" />
    <div class="login-page__glow login-page__glow--right" />
    <div class="login-page__powerlines">
      <span />
      <span />
      <span />
      <span />
    </div>
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
          <el-input
            ref="usernameInputRef"
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            @keyup.enter="submit"
          >
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
        <p>暂不开放自助注册，初始账户由管理员通过脚本或后台创建。登录成功后 access token 默认有效期为 7 天。</p>
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
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 18%, rgba(84, 184, 255, 0.18), transparent 22%),
    radial-gradient(circle at 82% 24%, rgba(70, 255, 211, 0.14), transparent 20%),
    linear-gradient(180deg, #08111a 0%, #0d1d2f 45%, #0f2237 100%);
}

.login-page__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(125, 182, 219, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(125, 182, 219, 0.08) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: radial-gradient(circle at center, black, transparent 88%);
}

.login-page__glow {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
}

.login-page__glow--left {
  left: -110px;
  bottom: -80px;
  background: rgba(31, 165, 255, 0.28);
}

.login-page__glow--right {
  right: -80px;
  top: -100px;
  background: rgba(71, 231, 191, 0.2);
}

.login-page__powerlines {
  position: absolute;
  inset: auto 0 16vh 0;
  height: 220px;
  pointer-events: none;
}

.login-page__powerlines span {
  position: absolute;
  left: -5%;
  right: -5%;
  height: 1px;
  border-top: 1px solid rgba(135, 208, 255, 0.22);
  border-radius: 999px;
}

.login-page__powerlines span:nth-child(1) {
  top: 26px;
  transform: translateY(0) scaleX(1.04);
}

.login-page__powerlines span:nth-child(2) {
  top: 58px;
  transform: translateY(8px) scaleX(1.06);
}

.login-page__powerlines span:nth-child(3) {
  top: 96px;
  transform: translateY(18px) scaleX(1.08);
}

.login-page__powerlines span:nth-child(4) {
  top: 140px;
  transform: translateY(32px) scaleX(1.1);
}

.login-panel {
  width: min(100%, 520px);
  padding: 34px 32px;
  border-radius: 30px;
  position: relative;
  z-index: 2;
  background: rgba(248, 252, 255, 0.92);
  border: 1px solid rgba(131, 202, 241, 0.28);
  box-shadow:
    0 32px 80px rgba(3, 17, 31, 0.36),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
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

.login-form :deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: 16px;
  box-shadow: 0 0 0 1px rgba(15, 93, 140, 0.08) inset;
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
