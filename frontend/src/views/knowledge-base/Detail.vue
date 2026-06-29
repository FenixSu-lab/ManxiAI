<!--
  Knowledge base detail page with data-source maintenance and owner permissions.
-->
<template>
  <Layout>
    <div class="kb-detail-page">
      <div class="page-header">
        <div>
          <el-button text @click="router.back()"><el-icon><ArrowLeft /></el-icon>Back</el-button>
          <h1>{{ knowledgeBase?.name || 'Knowledge Base Details' }}</h1>
          <p>{{ knowledgeBase?.description || 'Manage data sources and processing status for this knowledge base.' }}</p>
          <div v-if="knowledgeBase" class="role-row">
            <el-tag>{{ roleLabel }}</el-tag>
            <el-tag v-if="knowledgeBase.is_public" type="success">Open: all signed-in users can read</el-tag>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="openChat" :disabled="!knowledgeBase"><el-icon><ChatDotRound /></el-icon>Open Chat</el-button>
          <el-button v-if="canWrite" type="primary" @click="showUploadDialog = true"><el-icon><Upload /></el-icon>Upload Document</el-button>
        </div>
      </div>

      <el-row :gutter="16" class="summary-row">
        <el-col :xs="24" :sm="8"><el-card shadow="never"><div class="summary-item"><span>Documents</span><strong>{{ knowledgeBase?.documents_count || documents.length }}</strong></div></el-card></el-col>
        <el-col :xs="24" :sm="8"><el-card shadow="never"><div class="summary-item"><span>Chunks</span><strong>{{ knowledgeBase?.chunks_count || totalParagraphs }}</strong></div></el-card></el-col>
        <el-col :xs="24" :sm="8"><el-card shadow="never"><div class="summary-item"><span>Updated</span><strong>{{ formatTime(knowledgeBase?.updated_at || knowledgeBase?.created_at) }}</strong></div></el-card></el-col>
      </el-row>

      <el-card class="documents-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>Data Sources</h2>
              <p>Uploaded files, crawled pages, QA entries, and chat archives are parsed and embedded in the background.</p>
            </div>
            <div class="document-actions">
              <el-button v-if="canWrite" @click="showQADialog = true"><el-icon><EditPen /></el-icon>New QA</el-button>
              <el-button v-if="canWrite" @click="showWebDialog = true"><el-icon><Link /></el-icon>Crawl Web</el-button>
              <el-button @click="loadData" :loading="loading"><el-icon><Refresh /></el-icon>Refresh</el-button>
            </div>
          </div>
        </template>
        <el-table v-loading="loading" :data="documents" row-key="id" empty-text="No documents">
          <el-table-column prop="name" label="Document" min-width="220" />
          <el-table-column label="Type" width="140">
            <template #default="{ row }">{{ row.type_display || getTypeLabel(row.type) }}</template>
          </el-table-column>
          <el-table-column label="Status" width="220">
            <template #default="{ row }">
              <div class="status-cell">
                <el-tag :type="getStatusTagType(row.status)">{{ row.status_display || getStatusLabel(row.status) }}</el-tag>
                <el-tooltip v-if="row.latest_error" :content="row.latest_error" placement="top">
                  <span class="status-error">{{ row.latest_error }}</span>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="paragraph_count" label="Chunks" width="90" />
          <el-table-column label="Updated" width="180">
            <template #default="{ row }">{{ formatTime(row.updated_at || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="Actions" width="230" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openDocument(row)">View</el-button>
              <el-button v-if="canWrite" text @click="reprocess(row)">Reprocess</el-button>
              <el-button v-if="canWrite" text type="danger" @click="removeDocument(row)">Delete</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card v-if="canManage" class="permissions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>Permissions</h2>
              <p v-if="knowledgeBase?.is_public">This knowledge base is open, so all signed-in users already have read access. Add users here only when they need write access.</p>
              <p v-else>Grant read or write access to users in this system.</p>
            </div>
            <el-button @click="loadShares" :loading="sharesLoading"><el-icon><Refresh /></el-icon>Refresh</el-button>
          </div>
        </template>

        <el-form class="share-form" inline @submit.prevent>
          <el-form-item label="User">
            <el-select
              v-model="shareForm.user_email"
              filterable
              remote
              clearable
              reserve-keyword
              placeholder="Search users"
              :remote-method="searchUserOptions"
              :loading="usersLoading"
              style="width: 280px"
            >
              <el-option v-for="user in userOptions" :key="user.id" :label="user.label" :value="user.email" />
            </el-select>
          </el-form-item>
          <el-form-item label="Permission">
            <el-select v-model="shareForm.permission" style="width: 140px">
              <el-option label="Read" value="read" />
              <el-option label="Write" value="write" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="sharing" @click="saveShare">Add / Update</el-button>
          </el-form-item>
        </el-form>

        <el-table :data="shares" row-key="id" empty-text="No assigned users">
          <el-table-column prop="shared_with_email" label="User" min-width="240" />
          <el-table-column prop="permission" label="Permission" width="140">
            <template #default="{ row }"><el-tag :type="row.permission === 'write' ? 'warning' : 'info'">{{ row.permission }}</el-tag></template>
          </el-table-column>
          <el-table-column label="Actions" width="120">
            <template #default="{ row }">
              <el-button text type="danger" @click="removeShare(row)">Remove</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <DocumentUploadDialog v-model="showUploadDialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <QADocumentDialog v-model="showQADialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <WebDocumentDialog v-model="showWebDialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <DocumentDetailDialog v-model="showDetailDialog" :document="selectedDocument" :can-edit="canWrite" @updated="handleDocumentChanged" />
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ChatDotRound, EditPen, Link, Refresh, Upload } from '@element-plus/icons-vue'
import Layout from '@/components/Layout.vue'
import DocumentDetailDialog from '@/components/document/DocumentDetailDialog.vue'
import DocumentUploadDialog from '@/components/document/DocumentUploadDialog.vue'
import QADocumentDialog from '@/components/document/QADocumentDialog.vue'
import WebDocumentDialog from '@/components/document/WebDocumentDialog.vue'
import {
  deleteDocument,
  getDocuments,
  getKnowledgeBase,
  getKnowledgeBaseShares,
  reprocessDocument,
  searchUsers,
  shareKnowledgeBase,
  unshareKnowledgeBase,
  updateKnowledgeBaseStats
} from '@/api/knowledge-base'
import { getApiErrorMessage } from '@/utils/api'

interface KnowledgeBaseDto {
  id: string
  name: string
  description?: string
  documents_count?: number
  chunks_count?: number
  is_public?: boolean
  user_role?: 'owner' | 'write' | 'read' | 'none'
  can_write?: boolean
  can_manage?: boolean
  created_at?: string
  updated_at?: string
}

interface DocumentDto {
  id: string
  knowledge_base_id?: string
  name: string
  type: string
  type_display?: string
  status: string
  status_display?: string
  latest_error?: string
  paragraph_count: number
  char_length?: number
  hit_count?: number
  created_at?: string
  updated_at?: string
}

interface ShareDto {
  id: string
  shared_with_email: string
  permission: 'read' | 'write'
}

interface UserOptionDto {
  id: string
  email: string
  username: string
  label: string
}

const route = useRoute()
const router = useRouter()
const knowledgeBaseId = computed(() => String(route.params.id))
const knowledgeBase = ref<KnowledgeBaseDto | null>(null)
const documents = ref<DocumentDto[]>([])
const selectedDocument = ref<DocumentDto | null>(null)
const shares = ref<ShareDto[]>([])
const userOptions = ref<UserOptionDto[]>([])
const loading = ref(false)
const sharesLoading = ref(false)
const usersLoading = ref(false)
const sharing = ref(false)
const showUploadDialog = ref(false)
const showQADialog = ref(false)
const showWebDialog = ref(false)
const showDetailDialog = ref(false)
const shareForm = ref({ user_email: '', permission: 'read' as 'read' | 'write' })

const canWrite = computed(() => Boolean(knowledgeBase.value?.can_write))
const canManage = computed(() => Boolean(knowledgeBase.value?.can_manage))
const totalParagraphs = computed(() => documents.value.reduce((sum, item) => sum + (item.paragraph_count || 0), 0))
const roleLabel = computed(() => `Role: ${knowledgeBase.value?.user_role || 'none'}`)

const loadData = async () => {
  loading.value = true
  try {
    const [kbResponse, docsResponse] = await Promise.all([
      getKnowledgeBase(knowledgeBaseId.value),
      getDocuments(knowledgeBaseId.value)
    ])
    knowledgeBase.value = kbResponse.data
    documents.value = docsResponse.data.results || docsResponse.data || []
    if (knowledgeBase.value?.can_manage) await loadShares()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load knowledge base details'))
  } finally {
    loading.value = false
  }
}

const loadShares = async () => {
  if (!canManage.value) return
  sharesLoading.value = true
  try {
    const response = await getKnowledgeBaseShares(knowledgeBaseId.value)
    shares.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load permissions'))
  } finally {
    sharesLoading.value = false
  }
}

const searchUserOptions = async (query: string) => {
  usersLoading.value = true
  try {
    const response = await searchUsers({ q: query })
    const assigned = new Set(shares.value.map((share) => share.shared_with_email))
    userOptions.value = (response.data.results || response.data || []).filter((user: UserOptionDto) => !assigned.has(user.email))
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to search users'))
  } finally {
    usersLoading.value = false
  }
}

const saveShare = async () => {
  if (!shareForm.value.user_email) {
    ElMessage.error('Please select a user')
    return
  }
  sharing.value = true
  try {
    await shareKnowledgeBase(knowledgeBaseId.value, shareForm.value)
    ElMessage.success('Permission saved')
    shareForm.value = { user_email: '', permission: 'read' }
    userOptions.value = []
    await loadShares()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to save permission'))
  } finally {
    sharing.value = false
  }
}

const removeShare = async (share: ShareDto) => {
  try {
    await ElMessageBox.confirm(`Remove permission for "${share.shared_with_email}"?`, 'Confirm', { type: 'warning' })
    await unshareKnowledgeBase(knowledgeBaseId.value, { user_email: share.shared_with_email })
    ElMessage.success('Permission removed')
    await loadShares()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getApiErrorMessage(error, 'Failed to remove permission'))
  }
}

const handleDocumentChanged = async () => {
  showUploadDialog.value = false
  showQADialog.value = false
  showWebDialog.value = false
  if (canWrite.value) {
    try {
      await updateKnowledgeBaseStats(knowledgeBaseId.value)
    } catch (error) {}
  }
  await loadData()
}

const openDocument = (document: DocumentDto) => {
  selectedDocument.value = { ...document, knowledge_base_id: document.knowledge_base_id || knowledgeBaseId.value }
  showDetailDialog.value = true
}

const reprocess = async (document: DocumentDto) => {
  try {
    await reprocessDocument(knowledgeBaseId.value, document.id)
    ElMessage.success('Reprocessing started')
    await loadData()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to reprocess document'))
  }
}

const removeDocument = async (document: DocumentDto) => {
  try {
    await ElMessageBox.confirm(`Delete document "${document.name}"?`, 'Confirm delete', { type: 'warning', confirmButtonText: 'Delete', cancelButtonText: 'Cancel' })
    await deleteDocument(knowledgeBaseId.value, document.id)
    ElMessage.success('Document deleted')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getApiErrorMessage(error, 'Failed to delete document'))
  }
}

const openChat = () => {
  void router.push('/chat')
}

const getTypeLabel = (type: string) => ({
  base: 'General',
  web: 'Web',
  qa: 'QA',
  chat_archive: 'Chat Archive',
  table: 'Table',
  markdown: 'Markdown',
  text: 'Text'
}[type] || type)

const getStatusLabel = (status: string) => ({ pending: 'Pending', processing: 'Processing', embedding: 'Embedding', completed: 'Completed', failed: 'Failed' }[status] || status)
const getStatusTagType = (status: string) => ({ pending: 'info', processing: 'warning', embedding: 'warning', completed: 'success', failed: 'danger' }[status] || 'info') as 'info' | 'warning' | 'success' | 'danger'
const formatTime = (value?: string) => value ? new Date(value).toLocaleString() : '-'

onMounted(() => {
  void loadData()
})
</script>

<style scoped lang="scss">
.kb-detail-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.page-header h1 { margin: 8px 0 6px; font-size: 28px; color: #111827; }
.page-header p { margin: 0; color: #6b7280; }
.role-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.header-actions,
.document-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.summary-row { margin-bottom: 16px; }
.summary-item { display: flex; flex-direction: column; gap: 8px; }
.summary-item span { color: #6b7280; font-size: 13px; }
.summary-item strong { color: #111827; font-size: 22px; }
.documents-card,
.permissions-card { border-radius: 8px; margin-bottom: 16px; }
.permissions-card { margin-top: 16px; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-header h2 { margin: 0 0 4px; font-size: 18px; color: #111827; }
.card-header p { margin: 0; color: #6b7280; font-size: 13px; }
.share-form { margin-bottom: 12px; }
.status-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.status-error { max-width: 190px; color: #dc2626; font-size: 12px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }
@media (max-width: 768px) {
  .page-header,
  .card-header {
    flex-direction: column;
  }
  .header-actions,
  .document-actions {
    justify-content: flex-start;
  }
}
</style>
