<!--
  Account and API-key settings page.
-->
<template>
  <Layout>
    <div class="settings-page">
      <div class="page-header">
        <p class="eyebrow">Administration</p>
        <h1>Settings</h1>
      </div>

      <div class="settings-content">
        <el-tabs v-model="activeTab" tab-position="left">
          <el-tab-pane label="Profile" name="profile">
            <section class="setting-section">
              <h3>Profile</h3>
              <el-form :model="profileForm" label-width="110px">
                <el-form-item label="Email">
                  <el-input v-model="profileForm.email" disabled />
                </el-form-item>
                <el-form-item label="Username">
                  <el-input v-model="profileForm.username" />
                </el-form-item>
                <el-form-item label="First name">
                  <el-input v-model="profileForm.first_name" />
                </el-form-item>
                <el-form-item label="Last name">
                  <el-input v-model="profileForm.last_name" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="updateProfile">Save profile</el-button>
                </el-form-item>
              </el-form>
            </section>
          </el-tab-pane>

          <el-tab-pane label="Password" name="password">
            <section class="setting-section">
              <h3>Change Password</h3>
              <el-form :model="passwordForm" label-width="130px">
                <el-form-item label="Current password">
                  <el-input v-model="passwordForm.old_password" type="password" show-password />
                </el-form-item>
                <el-form-item label="New password">
                  <el-input v-model="passwordForm.new_password" type="password" show-password />
                </el-form-item>
                <el-form-item label="Confirm password">
                  <el-input v-model="passwordForm.confirm_password" type="password" show-password />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="changePassword">Change password</el-button>
                </el-form-item>
              </el-form>
            </section>
          </el-tab-pane>

          <el-tab-pane label="API Keys" name="api-keys">
            <section class="setting-section setting-section--wide">
              <div class="section-header">
                <h3>API Keys</h3>
                <el-button type="primary" @click="showCreateApiKeyDialog = true">
                  Create API key
                </el-button>
              </div>

              <el-table :data="apiKeys" style="width: 100%">
                <el-table-column prop="name" label="Name" />
                <el-table-column prop="key" label="Key" show-overflow-tooltip />
                <el-table-column prop="created_at" label="Created at" />
                <el-table-column label="Actions" width="210">
                  <template #default="scope">
                    <el-button type="primary" size="small" @click="regenerateApiKey(scope.row)">
                      Regenerate
                    </el-button>
                    <el-button type="danger" size="small" @click="deleteApiKey(scope.row)">
                      Delete
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </section>
          </el-tab-pane>
        </el-tabs>
      </div>

      <el-dialog v-model="showCreateApiKeyDialog" title="Create API Key" width="420px">
        <el-form :model="apiKeyForm" label-width="80px">
          <el-form-item label="Name">
            <el-input v-model="apiKeyForm.name" placeholder="API key name" />
          </el-form-item>
        </el-form>

        <template #footer>
          <el-button @click="showCreateApiKeyDialog = false">Cancel</el-button>
          <el-button type="primary" @click="createApiKey">Create</el-button>
        </template>
      </el-dialog>
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/utils/api'
import Layout from '@/components/Layout.vue'

interface ApiKey {
  id: string
  name: string
  key: string
  created_at: string
}

const authStore = useAuthStore()
const activeTab = ref('profile')
const showCreateApiKeyDialog = ref(false)

const profileForm = ref({
  email: '',
  username: '',
  first_name: '',
  last_name: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const apiKeyForm = ref({
  name: ''
})

const apiKeys = ref<ApiKey[]>([])

// Sends profile edits to the backend and refreshes the local auth store.
const updateProfile = async () => {
  try {
    await api.put('/auth/users/me/', profileForm.value)
    ElMessage.success('Profile updated.')
    authStore.getUserInfo()
  } catch {
    ElMessage.error('Failed to update profile.')
  }
}

// Validates and submits a password change request.
const changePassword = async () => {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    ElMessage.error('The two password entries do not match.')
    return
  }

  try {
    await api.post('/auth/users/change_password/', passwordForm.value)
    ElMessage.success('Password changed.')
    passwordForm.value = {
      old_password: '',
      new_password: '',
      confirm_password: ''
    }
  } catch {
    ElMessage.error('Failed to change password.')
  }
}

// Loads API keys when the backend endpoint is available.
const loadApiKeys = async () => {
  try {
    const response = await api.get('/auth/api-keys/')
    apiKeys.value = response.data.results || response.data
  } catch {
    apiKeys.value = []
  }
}

// Creates a named API key and refreshes the table.
const createApiKey = async () => {
  try {
    await api.post('/auth/api-keys/', apiKeyForm.value)
    ElMessage.success('API key created.')
    showCreateApiKeyDialog.value = false
    apiKeyForm.value.name = ''
    loadApiKeys()
  } catch {
    ElMessage.error('Failed to create API key.')
  }
}

// Regenerates a selected API key after explicit confirmation.
const regenerateApiKey = async (apiKey: ApiKey) => {
  try {
    await ElMessageBox.confirm(`Regenerate API key "${apiKey.name}"?`, 'Confirm', {
      confirmButtonText: 'Regenerate',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })

    await api.post(`/auth/api-keys/${apiKey.id}/regenerate/`)
    ElMessage.success('API key regenerated.')
    loadApiKeys()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to regenerate API key.')
    }
  }
}

// Deletes a selected API key after explicit confirmation.
const deleteApiKey = async (apiKey: ApiKey) => {
  try {
    await ElMessageBox.confirm(`Delete API key "${apiKey.name}"?`, 'Confirm', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })

    await api.delete(`/auth/api-keys/${apiKey.id}/`)
    ElMessage.success('API key deleted.')
    loadApiKeys()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete API key.')
    }
  }
}

onMounted(() => {
  if (authStore.user) {
    profileForm.value = {
      email: authStore.user.email,
      username: authStore.user.username,
      first_name: authStore.user.first_name,
      last_name: authStore.user.last_name
    }
  }
  loadApiKeys()
})
</script>

<style lang="scss" scoped>
.settings-page {
  padding: 28px;
}

.page-header {
  margin-bottom: 28px;

  h1 {
    font-size: 32px;
    color: #111827;
    margin: 0;
  }
}

.eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 8px;
}

.settings-content {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #edf1f7;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.setting-section {
  max-width: 640px;
  padding-left: 20px;

  &--wide {
    max-width: 100%;
  }

  h3 {
    margin: 0 0 24px;
    color: #111827;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;

  h3 {
    margin: 0;
  }
}
</style>
