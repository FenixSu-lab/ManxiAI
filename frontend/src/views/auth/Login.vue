<!--
  Login page for account/password authentication.
-->
<template>
  <div class="login-container">
    <LanguageSwitch class="auth-language-switch" />
    <div class="login-box">
      <div class="login-header">
        <h1>ManxiAI</h1>
        <p>Enterprise AI knowledge base system</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="Email or username" size="large" prefix-icon="User" />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="Password"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            class="login-btn"
            @click="handleLogin"
          >
            Log in
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span>No account yet?</span>
        <router-link to="/register">Create one</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import LanguageSwitch from '@/components/LanguageSwitch.vue'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const form = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: 'Please enter an email address or username.', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter a password.', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters.', trigger: 'blur' }
  ]
}

// Extracts the first useful backend validation message from DRF error payloads.
const getErrorMessage = (error: any) => {
  const data = error.response?.data
  if (!data) return 'Login failed. Please try again.'
  if (typeof data === 'string') return data
  if (data.message) return data.message
  if (data.detail) return data.detail

  const fields = ['non_field_errors', 'email', 'password']
  for (const field of fields) {
    const value = data[field]
    if (Array.isArray(value) && value.length > 0) return value[0]
    if (typeof value === 'string') return value
  }

  return 'Login failed. Please try again.'
}

// Validates the form, calls the auth store, and routes to the dashboard on success.
const handleLogin = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    await authStore.login(form)
    ElMessage.success('Logged in.')
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error))
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background:
    radial-gradient(circle at top left, rgba(20, 184, 166, 0.32), transparent 34%),
    linear-gradient(135deg, #102a43 0%, #1f3b57 52%, #0f766e 100%);
}

.auth-language-switch {
  position: absolute;
  top: 22px;
  right: 22px;
}

.login-box {
  width: 400px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;

  h1 {
    font-size: 34px;
    color: #111827;
    margin: 0 0 8px;
  }

  p {
    color: #667085;
    font-size: 14px;
    margin: 0;
  }
}

.login-form {
  .el-form-item {
    margin-bottom: 20px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  color: #667085;
  font-size: 14px;

  a {
    color: #0f766e;
    text-decoration: none;
    margin-left: 8px;
    font-weight: 700;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
