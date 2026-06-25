<!--
  Registration page for creating a new local user account.
-->
<template>
  <div class="register-container">
    <div class="register-box">
      <div class="register-header">
        <h1>ManxiAI</h1>
        <p>Create your account</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" class="register-form">
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="Email" size="large" prefix-icon="Message" />
        </el-form-item>

        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="Username" size="large" prefix-icon="User" />
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

        <el-form-item prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="Confirm password"
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
            class="register-btn"
            @click="handleRegister"
          >
            Register
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <span>Already have an account?</span>
        <router-link to="/login">Log in</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormItemRule } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const form = reactive({
  email: '',
  username: '',
  password: '',
  confirm_password: ''
})

// Validates that the confirmation field matches the password field.
const validatePassword = (_rule: FormItemRule, value: string, callback: (error?: Error) => void) => {
  if (value !== form.password) {
    callback(new Error('The two password entries do not match.'))
  } else {
    callback()
  }
}

const rules = {
  email: [
    { required: true, message: 'Please enter an email address.', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address.', trigger: 'blur' }
  ],
  username: [
    { required: true, message: 'Please enter a username.', trigger: 'blur' },
    { min: 3, message: 'Username must be at least 3 characters.', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter a password.', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters.', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: 'Please confirm your password.', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ]
}

// Extracts the first useful backend validation message from DRF error payloads.
const getErrorMessage = (error: any) => {
  const data = error.response?.data
  if (!data) return 'Registration failed. Please try again.'
  if (typeof data === 'string') return data
  if (data.message) return data.message
  if (data.detail) return data.detail

  const fields = ['email', 'username', 'password', 'confirm_password', 'non_field_errors']
  for (const field of fields) {
    const value = data[field]
    if (Array.isArray(value) && value.length > 0) return value[0]
    if (typeof value === 'string') return value
  }

  return 'Registration failed. Please try again.'
}

// Submits registration and sends the user back to the login page on success.
const handleRegister = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    await authStore.register(form)
    ElMessage.success('Registration complete. Please log in.')
    router.push('/login')
  } catch (error: any) {
    ElMessage.error(getErrorMessage(error))
  }
}
</script>

<style lang="scss" scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.3), transparent 32%),
    linear-gradient(135deg, #102a43 0%, #1f3b57 52%, #0f766e 100%);
}

.register-box {
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.register-header {
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

.register-form {
  .el-form-item {
    margin-bottom: 20px;
  }
}

.register-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.register-footer {
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
