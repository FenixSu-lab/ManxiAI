<!--
  Model provider management page for switching OpenAI-compatible LLMs.
-->
<template>
  <Layout>
    <div class="model-page">
      <div class="page-header">
        <div>
          <p class="eyebrow">Model Operations</p>
          <h1>Model Management</h1>
          <p>Manage DeepSeek, Qwen, OpenAI-compatible, and custom chat model providers.</p>
        </div>
        <div class="header-actions">
          <el-button @click="seedDefaults" :loading="seeding">Seed Chinese presets</el-button>
          <el-button type="primary" @click="openCreateDialog">New provider</el-button>
        </div>
      </div>

      <el-alert
        class="active-alert"
        :type="activeSource === 'database' ? 'success' : 'info'"
        show-icon
        :closable="false"
        :title="activeTitle"
      />

      <el-card shadow="never">
        <el-table v-loading="loading" :data="providers" row-key="id" empty-text="No model providers">
          <el-table-column label="Name" min-width="160">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
              <div class="muted">{{ getProviderLabel(row.provider_type) }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="model" label="Model" min-width="150" />
          <el-table-column prop="base_url" label="Base URL" min-width="260" show-overflow-tooltip />
          <el-table-column prop="masked_api_key" label="API Key" width="140" />
          <el-table-column label="Status" width="150">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : row.is_enabled ? 'info' : 'danger'">
                {{ row.is_active ? 'Active' : row.is_enabled ? 'Enabled' : 'Disabled' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="280" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openEditDialog(row)">Edit</el-button>
              <el-button text @click="activateProvider(row)" :disabled="row.is_active">Activate</el-button>
              <el-button text @click="testProvider(row)">Test</el-button>
              <el-button text type="danger" @click="deleteProvider(row)">Delete</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="dialogVisible" :title="editingProvider ? 'Edit provider' : 'New provider'" width="620px">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="Name" prop="name">
            <el-input v-model="form.name" placeholder="Example: DeepSeek Production" />
          </el-form-item>
          <el-form-item label="Provider" prop="provider_type">
            <el-select v-model="form.provider_type" style="width: 100%" @change="applyProviderPreset">
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="通义千问 Qwen" value="qwen" />
              <el-option label="OpenAI" value="openai" />
              <el-option label="Custom OpenAI Compatible" value="custom" />
              <el-option label="Debug" value="debug" />
            </el-select>
          </el-form-item>
          <el-form-item label="Base URL" prop="base_url">
            <el-input v-model="form.base_url" placeholder="https://api.deepseek.com/v1" />
          </el-form-item>
          <el-form-item label="Model" prop="model">
            <el-input v-model="form.model" placeholder="deepseek-chat / qwen-plus" />
          </el-form-item>
          <el-form-item label="API Key" prop="api_key">
            <el-input v-model="form.api_key" type="password" show-password placeholder="Leave blank to keep existing key when editing" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="Timeout seconds" prop="timeout">
              <el-input-number v-model="form.timeout" :min="5" :max="300" />
            </el-form-item>
            <el-form-item label="Enabled">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </div>
          <el-form-item label="Description">
            <el-input v-model="form.description" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">Cancel</el-button>
          <el-button type="primary" :loading="saving" @click="saveProvider">Save</el-button>
        </template>
      </el-dialog>
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import Layout from '@/components/Layout.vue'
import { api, getApiErrorMessage } from '@/utils/api'

interface LLMProvider {
  id: string
  name: string
  provider_type: string
  base_url: string
  masked_api_key: string
  model: string
  timeout: number
  is_active: boolean
  is_enabled: boolean
  description?: string
}

const providers = ref<LLMProvider[]>([])
const loading = ref(false)
const saving = ref(false)
const seeding = ref(false)
const dialogVisible = ref(false)
const editingProvider = ref<LLMProvider | null>(null)
const activeSource = ref('environment')
const activeFallback = ref<Record<string, string>>({})
const formRef = ref<FormInstance>()

const defaultForm = {
  name: '',
  provider_type: 'deepseek',
  base_url: 'https://api.deepseek.com/v1',
  api_key: '',
  model: 'deepseek-chat',
  timeout: 60,
  is_enabled: true,
  description: ''
}

const form = ref({ ...defaultForm })

const rules: FormRules = {
  name: [{ required: true, message: 'Please enter provider name', trigger: 'blur' }],
  provider_type: [{ required: true, message: 'Please select provider', trigger: 'change' }],
  model: [{ required: true, message: 'Please enter model name', trigger: 'blur' }]
}

const activeTitle = computed(() => {
  const active = providers.value.find((provider) => provider.is_active)
  if (active) return `Active model: ${active.name} / ${active.model}`
  return `Using environment fallback: ${activeFallback.value.provider_type || 'deepseek'} / ${activeFallback.value.model || '-'}`
})

const loadProviders = async () => {
  loading.value = true
  try {
    const [listResponse, activeResponse] = await Promise.all([
      api.get('/model-providers/'),
      api.get('/model-providers/active/')
    ])
    providers.value = listResponse.data.results || listResponse.data || []
    activeSource.value = activeResponse.data.source
    activeFallback.value = activeResponse.data.fallback || {}
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load model providers'))
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingProvider.value = null
  form.value = { ...defaultForm }
  dialogVisible.value = true
}

const openEditDialog = (provider: LLMProvider) => {
  editingProvider.value = provider
  form.value = {
    name: provider.name,
    provider_type: provider.provider_type,
    base_url: provider.base_url,
    api_key: '',
    model: provider.model,
    timeout: provider.timeout,
    is_enabled: provider.is_enabled,
    description: provider.description || ''
  }
  dialogVisible.value = true
}

const applyProviderPreset = () => {
  if (form.value.provider_type === 'deepseek') {
    form.value.base_url = 'https://api.deepseek.com/v1'
    form.value.model = 'deepseek-chat'
  } else if (form.value.provider_type === 'qwen') {
    form.value.base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    form.value.model = 'qwen-plus'
  } else if (form.value.provider_type === 'openai') {
    form.value.base_url = 'https://api.openai.com/v1'
    form.value.model = 'gpt-4o-mini'
  } else if (form.value.provider_type === 'debug') {
    form.value.base_url = 'http://localhost'
    form.value.model = 'debug'
    form.value.api_key = 'debug'
  }
}

const saveProvider = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editingProvider.value && !payload.api_key) {
      delete (payload as any).api_key
    }
    if (editingProvider.value) {
      await api.patch(`/model-providers/${editingProvider.value.id}/`, payload)
      ElMessage.success('Model provider updated')
    } else {
      await api.post('/model-providers/', payload)
      ElMessage.success('Model provider created')
    }
    dialogVisible.value = false
    await loadProviders()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to save model provider'))
  } finally {
    saving.value = false
  }
}

const activateProvider = async (provider: LLMProvider) => {
  try {
    await api.post(`/model-providers/${provider.id}/activate/`)
    ElMessage.success('Active model provider switched')
    await loadProviders()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to activate model provider'))
  }
}

const testProvider = async (provider: LLMProvider) => {
  try {
    const response = await api.post(`/model-providers/${provider.id}/test/`)
    ElMessage.success(`Provider test OK. Reply length: ${response.data.reply_length}`)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Provider test failed'))
  }
}

const deleteProvider = async (provider: LLMProvider) => {
  try {
    await ElMessageBox.confirm(`Delete provider "${provider.name}"?`, 'Confirm', { type: 'warning' })
    await api.delete(`/model-providers/${provider.id}/`)
    ElMessage.success('Model provider deleted')
    await loadProviders()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getApiErrorMessage(error, 'Failed to delete model provider'))
  }
}

const seedDefaults = async () => {
  seeding.value = true
  try {
    await api.post('/model-providers/seed_defaults/')
    ElMessage.success('Provider presets seeded')
    await loadProviders()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to seed provider presets'))
  } finally {
    seeding.value = false
  }
}

const getProviderLabel = (type: string) => ({
  deepseek: 'DeepSeek',
  qwen: '通义千问 Qwen',
  openai: 'OpenAI',
  custom: 'Custom compatible',
  debug: 'Debug'
}[type] || type)

onMounted(() => {
  void loadProviders()
})
</script>

<style scoped lang="scss">
.model-page { padding: 28px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.page-header h1 { margin: 6px 0; font-size: 30px; color: #111827; }
.page-header p { margin: 0; color: #6b7280; }
.eyebrow { margin: 0; color: #2563eb; font-size: 12px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.active-alert { margin-bottom: 16px; }
.muted { color: #6b7280; font-size: 12px; margin-top: 4px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 720px) {
  .page-header,
  .form-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
