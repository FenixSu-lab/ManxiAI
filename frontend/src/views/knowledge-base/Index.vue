<template>
  <Layout>
    <div class="kb-page">
      <div class="page-header">
        <div>
          <h1>Knowledge Bases</h1>
          <p>Manage documents, web pages, and QA content used by RAG chat.</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          New Knowledge Base
        </el-button>
      </div>

      <el-card class="kb-panel" shadow="never">
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="Search knowledge bases" clearable class="search-input">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button @click="loadKnowledgeBases" :loading="loading">
            <el-icon><Refresh /></el-icon>
            Refresh
          </el-button>
        </div>

        <div v-loading="loading" class="kb-content">
          <el-empty v-if="filteredKnowledgeBases.length === 0" description="No knowledge bases">
            <el-button type="primary" @click="openCreateDialog">Create first knowledge base</el-button>
          </el-empty>

          <div v-else class="kb-grid">
            <el-card v-for="kb in filteredKnowledgeBases" :key="kb.id" class="kb-card" shadow="hover" @click="goToDetail(kb.id)">
              <div class="kb-card__header">
                <div class="kb-icon">{{ kb.name.slice(0, 1).toUpperCase() }}</div>
                <div>
                  <h3>{{ kb.name }}</h3>
                  <el-tag size="small" :type="kb.status === 'active' ? 'success' : 'info'">{{ getStatusLabel(kb.status) }}</el-tag>
                </div>
              </div>
              <p class="kb-description">{{ kb.description || 'No description' }}</p>
              <div class="kb-stats">
                <span>{{ kb.documents_count || 0 }} docs</span>
                <span>{{ kb.chunks_count || 0 }} chunks</span>
                <span>{{ formatDate(kb.updated_at || kb.created_at) }}</span>
              </div>
            </el-card>
          </div>
        </div>
      </el-card>

      <el-dialog v-model="showCreateDialog" title="New Knowledge Base" width="460px" @close="resetCreateForm">
        <el-form ref="formRef" :model="newKB" :rules="rules" label-position="top">
          <el-form-item label="Name" prop="name">
            <el-input v-model="newKB.name" placeholder="Example: Meeting room policy" />
          </el-form-item>
          <el-form-item label="Description" prop="description">
            <el-input v-model="newKB.description" type="textarea" :rows="4" placeholder="Optional usage notes" />
          </el-form-item>
          <el-form-item label="Public access">
            <el-switch v-model="newKB.is_public" active-text="Public" inactive-text="Private" />
          </el-form-item>
          <div class="advanced-grid">
            <el-form-item label="Chunk size" prop="chunk_size">
              <el-input-number v-model="newKB.chunk_size" :min="200" :max="4000" :step="100" />
            </el-form-item>
            <el-form-item label="Top K" prop="top_k">
              <el-input-number v-model="newKB.top_k" :min="1" :max="20" />
            </el-form-item>
          </div>
        </el-form>
        <template #footer>
          <el-button @click="showCreateDialog = false">Cancel</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button>
        </template>
      </el-dialog>
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import Layout from '@/components/Layout.vue'
import { api, getApiErrorMessage } from '@/utils/api'

interface KnowledgeBaseDto {
  id: string
  name: string
  description?: string
  status?: string
  documents_count?: number
  chunks_count?: number
  created_at?: string
  updated_at?: string
}

const router = useRouter()
const knowledgeBases = ref<KnowledgeBaseDto[]>([])
const loading = ref(false)
const creating = ref(false)
const searchText = ref('')
const showCreateDialog = ref(false)
const formRef = ref<FormInstance>()
const createDefaults = {
  name: '',
  description: '',
  is_public: false,
  chunk_size: 1000,
  top_k: 5
}
const newKB = ref({ ...createDefaults })

const rules: FormRules = {
  name: [{ required: true, message: 'Please enter a name', trigger: 'blur' }],
  chunk_size: [{ required: true, message: 'Please set a chunk size', trigger: 'blur' }],
  top_k: [{ required: true, message: 'Please set top K', trigger: 'blur' }]
}

const filteredKnowledgeBases = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  if (!keyword) return knowledgeBases.value
  return knowledgeBases.value.filter((kb) => kb.name.toLowerCase().includes(keyword) || (kb.description || '').toLowerCase().includes(keyword))
})

const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    const response = await api.get('/knowledge-bases/')
    knowledgeBases.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load knowledge bases'))
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  showCreateDialog.value = true
}

const resetCreateForm = () => {
  newKB.value = { ...createDefaults }
  formRef.value?.clearValidate()
}

const handleCreate = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  creating.value = true
  try {
    await api.post('/knowledge-bases/', newKB.value)
    ElMessage.success('Knowledge base created')
    showCreateDialog.value = false
    await loadKnowledgeBases()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to create knowledge base'))
  } finally {
    creating.value = false
  }
}

const goToDetail = (id: string) => {
  void router.push(`/knowledge-base/${id}`)
}

const getStatusLabel = (status?: string) => {
  const labels: Record<string, string> = { active: 'Active', inactive: 'Inactive', pending: 'Pending' }
  return labels[status || 'active'] || status || 'Active'
}

const formatDate = (date?: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

onMounted(() => {
  void loadKnowledgeBases()
})
</script>

<style scoped lang="scss">
.kb-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-header h1 { margin: 0 0 6px; font-size: 28px; color: #1f2937; }
.page-header p { margin: 0; color: #6b7280; }
.kb-panel { border-radius: 8px; }
.toolbar { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 20px; }
.search-input { max-width: 360px; }
.advanced-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.kb-content { min-height: 320px; }
.kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.kb-card { cursor: pointer; }
.kb-card :deep(.el-card__body) { display: flex; flex-direction: column; gap: 14px; min-height: 178px; }
.kb-card__header { display: flex; gap: 12px; align-items: center; }
.kb-card__header h3 { margin: 0 0 6px; font-size: 16px; color: #111827; }
.kb-icon { width: 42px; height: 42px; border-radius: 8px; background: #0f766e; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.kb-description { margin: 0; color: #4b5563; line-height: 1.5; min-height: 44px; }
.kb-stats { display: flex; justify-content: space-between; color: #6b7280; font-size: 12px; margin-top: auto; }
@media (max-width: 640px) {
  .advanced-grid,
  .toolbar,
  .page-header {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
