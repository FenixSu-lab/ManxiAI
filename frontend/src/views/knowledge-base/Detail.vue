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
          <el-table-column label="Actions" width="190" fixed="right" align="center">
            <template #default="{ row }">
              <div class="table-action-group">
                <el-tooltip content="查看详情" placement="top">
                  <el-button class="action-button" type="primary" plain circle @click="openDocument(row)">
                    <el-icon><View /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="canWrite" content="重新处理" placement="top">
                  <el-button class="action-button" plain circle @click="reprocess(row)">
                    <el-icon><RefreshRight /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="canWrite" content="删除数据源" placement="top">
                  <el-button class="action-button action-button--danger" type="danger" plain circle @click="removeDocument(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card v-if="canManage" class="permissions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>权限配置</h2>
              <p v-if="knowledgeBase?.is_public">当前知识库是开放的，所有登录用户都已有读取权限。这里只需要给特定用户增加写入权限。</p>
              <p v-else>为系统内用户授予读取或写入权限。</p>
            </div>
            <el-button @click="loadShares" :loading="sharesLoading"><el-icon><Refresh /></el-icon>刷新</el-button>
          </div>
        </template>

        <el-form class="share-form" inline @submit.prevent>
          <el-form-item label="用户">
            <el-select
              v-model="shareForm.user_email"
              filterable
              remote
              clearable
              reserve-keyword
              placeholder="搜索系统用户"
              :remote-method="searchUserOptions"
              :loading="usersLoading"
              style="width: 280px"
            >
              <el-option v-for="user in userOptions" :key="user.id" :label="user.label" :value="user.email" />
            </el-select>
          </el-form-item>
          <el-form-item label="权限">
            <el-select v-model="shareForm.permission" style="width: 140px">
              <el-option label="读取" value="read" />
              <el-option label="写入" value="write" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="sharing" @click="saveShare">添加 / 更新</el-button>
          </el-form-item>
        </el-form>

        <el-table :data="shares" row-key="id" empty-text="暂无指定用户权限">
          <el-table-column prop="shared_with_email" label="用户" min-width="240" />
          <el-table-column label="权限" width="140">
            <template #default="{ row }"><el-tag :type="row.permission === 'write' ? 'warning' : 'info'">{{ row.permission === 'write' ? '写入' : '读取' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="110" align="center">
            <template #default="{ row }">
              <div class="table-action-group">
                <el-tooltip content="移除权限" placement="top">
                  <el-button class="action-button action-button--danger" type="danger" plain circle @click="removeShare(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card v-if="canManage" class="mcp-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>MCP 导出</h2>
              <p>将当前知识库发布为 Hosted MCP Server，供外部智能体调用。访问令牌只会显示一次。</p>
            </div>
            <div class="document-actions">
              <el-button @click="loadMcpProfiles" :loading="mcpLoading"><el-icon><Refresh /></el-icon>刷新</el-button>
              <el-button type="primary" @click="showMcpDialog = true">新建 MCP 配置</el-button>
            </div>
          </div>
        </template>

        <el-alert
          v-if="newMcpToken"
          type="warning"
          show-icon
          :closable="false"
          class="token-alert"
          title="请立即复制这个令牌。关闭后系统不会再次明文显示。"
        >
          <template #default>
            <div class="token-row">
              <code>{{ newMcpToken }}</code>
              <el-button size="small" @click="copyText(newMcpToken)">复制令牌</el-button>
            </div>
          </template>
        </el-alert>

        <el-table v-loading="mcpLoading" :data="mcpProfiles" row-key="id" empty-text="暂无 MCP 配置">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column label="访问地址" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.endpoint_url }}</span>
            </template>
          </el-table-column>
          <el-table-column label="权限范围" width="150">
            <template #default="{ row }">{{ getMcpScopeLabel(row.permission_scope) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="usage_count" label="调用次数" width="100" />
          <el-table-column label="操作" width="260" fixed="right" align="center">
            <template #default="{ row }">
              <div class="table-action-group">
                <el-tooltip content="复制配置" placement="top">
                  <el-button class="action-button" type="primary" plain circle @click="copyMcpConfig(row)">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="访问日志" placement="top">
                  <el-button class="action-button" plain circle @click="openMcpLogs(row)">
                    <el-icon><Tickets /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip :content="row.is_active ? '停用配置' : '启用配置'" placement="top">
                  <el-button class="action-button" :type="row.is_active ? 'warning' : 'success'" plain circle @click="toggleMcpProfile(row)">
                    <el-icon><SwitchButton /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="轮换令牌" placement="top">
                  <el-button class="action-button" plain circle @click="rotateMcpToken(row)">
                    <el-icon><Key /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除配置" placement="top">
                  <el-button class="action-button action-button--danger" type="danger" plain circle @click="deleteMcp(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="showMcpDialog" title="新建 MCP 配置" width="620px">
        <el-form :model="mcpForm" label-position="top">
          <el-form-item label="名称">
            <el-input v-model="mcpForm.name" placeholder="例如：外部智能体 MCP" />
          </el-form-item>
          <el-form-item label="权限范围">
            <el-select v-model="mcpForm.permission_scope" style="width: 100%">
              <el-option label="只读工具" value="read_only" />
              <el-option label="检索并返回引用" value="citations_only" />
              <el-option label="仅检索" value="search_only" />
            </el-select>
          </el-form-item>
          <el-form-item label="允许调用的工具">
            <el-checkbox-group v-model="mcpForm.allowed_tools">
              <el-checkbox label="search_knowledge" :disabled="!isMcpToolAllowed('search_knowledge')">检索知识库</el-checkbox>
              <el-checkbox label="list_sources" :disabled="!isMcpToolAllowed('list_sources')">列出数据源</el-checkbox>
              <el-checkbox label="get_document" :disabled="!isMcpToolAllowed('get_document')">读取文档</el-checkbox>
              <el-checkbox label="get_paragraph" :disabled="!isMcpToolAllowed('get_paragraph')">读取分段</el-checkbox>
              <el-checkbox label="answer_with_citations" :disabled="!isMcpToolAllowed('answer_with_citations')">带引用回答</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="最大召回数量">
              <el-input-number v-model="mcpForm.max_top_k" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="每分钟限流">
              <el-input-number v-model="mcpForm.rate_limit_per_minute" :min="1" :max="1000" />
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="返回原文内容">
              <el-switch v-model="mcpForm.include_source_content" />
            </el-form-item>
            <el-form-item label="返回元数据">
              <el-switch v-model="mcpForm.include_metadata" />
            </el-form-item>
          </div>
        </el-form>
        <template #footer>
          <el-button @click="showMcpDialog = false">取消</el-button>
          <el-button type="primary" :loading="mcpSaving" @click="createMcp">创建</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="showMcpLogsDialog" title="MCP 访问日志" width="880px">
        <el-table v-loading="mcpLogsLoading" :data="mcpLogs" row-key="id" empty-text="暂无访问日志" max-height="420">
          <el-table-column prop="method" label="方法" width="150" />
          <el-table-column prop="tool_name" label="工具" width="160" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="result_count" label="结果数" width="90" />
          <el-table-column prop="latency_ms" label="耗时 ms" width="110" />
          <el-table-column prop="query" label="查询内容" min-width="180" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-dialog>

      <DocumentUploadDialog v-model="showUploadDialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <QADocumentDialog v-model="showQADialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <WebDocumentDialog v-model="showWebDialog" :knowledge-base-id="knowledgeBaseId" @success="handleDocumentChanged" />
      <DocumentDetailDialog v-model="showDetailDialog" :document="selectedDocument" :can-edit="canWrite" @updated="handleDocumentChanged" />
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ChatDotRound,
  CopyDocument,
  Delete,
  EditPen,
  Key,
  Link,
  Refresh,
  RefreshRight,
  SwitchButton,
  Tickets,
  Upload,
  View
} from '@element-plus/icons-vue'
import Layout from '@/components/Layout.vue'
import DocumentDetailDialog from '@/components/document/DocumentDetailDialog.vue'
import DocumentUploadDialog from '@/components/document/DocumentUploadDialog.vue'
import QADocumentDialog from '@/components/document/QADocumentDialog.vue'
import WebDocumentDialog from '@/components/document/WebDocumentDialog.vue'
import {
  createMcpProfile,
  deleteDocument,
  deleteMcpProfile,
  getDocuments,
  getKnowledgeBase,
  getKnowledgeBaseShares,
  getMcpProfileLogs,
  getMcpProfiles,
  reprocessDocument,
  rotateMcpProfileToken,
  searchUsers,
  shareKnowledgeBase,
  unshareKnowledgeBase,
  updateMcpProfile,
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

interface McpProfileDto {
  id: string
  name: string
  endpoint_url: string
  permission_scope: string
  allowed_tools: string[]
  is_active: boolean
  rate_limit_per_minute: number
  max_top_k: number
  include_source_content: boolean
  include_metadata: boolean
  usage_count: number
  token?: string
}

interface McpLogDto {
  id: string
  method: string
  tool_name: string
  query: string
  status: string
  latency_ms: number
  result_count: number
  created_at?: string
}

const route = useRoute()
const router = useRouter()
const knowledgeBaseId = computed(() => String(route.params.id))
const knowledgeBase = ref<KnowledgeBaseDto | null>(null)
const documents = ref<DocumentDto[]>([])
const selectedDocument = ref<DocumentDto | null>(null)
const shares = ref<ShareDto[]>([])
const userOptions = ref<UserOptionDto[]>([])
const mcpProfiles = ref<McpProfileDto[]>([])
const mcpLogs = ref<McpLogDto[]>([])
const loading = ref(false)
const sharesLoading = ref(false)
const usersLoading = ref(false)
const sharing = ref(false)
const mcpLoading = ref(false)
const mcpSaving = ref(false)
const mcpLogsLoading = ref(false)
const showUploadDialog = ref(false)
const showQADialog = ref(false)
const showWebDialog = ref(false)
const showDetailDialog = ref(false)
const showMcpDialog = ref(false)
const showMcpLogsDialog = ref(false)
const newMcpToken = ref('')
const shareForm = ref({ user_email: '', permission: 'read' as 'read' | 'write' })
const mcpForm = ref({
  name: '',
  permission_scope: 'read_only',
  allowed_tools: ['search_knowledge', 'list_sources', 'get_document', 'get_paragraph'],
  rate_limit_per_minute: 60,
  max_top_k: 5,
  include_source_content: true,
  include_metadata: true
})
const mcpScopeTools: Record<string, string[]> = {
  search_only: ['search_knowledge'],
  citations_only: ['search_knowledge', 'list_sources', 'answer_with_citations'],
  read_only: ['search_knowledge', 'list_sources', 'get_document', 'get_paragraph', 'answer_with_citations']
}

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
    if (knowledgeBase.value?.can_manage) {
      await Promise.all([loadShares(), loadMcpProfiles()])
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, 'Failed to load knowledge base details'))
  } finally {
    loading.value = false
  }
}

const loadMcpProfiles = async () => {
  if (!canManage.value) return
  mcpLoading.value = true
  try {
    const response = await getMcpProfiles(knowledgeBaseId.value)
    mcpProfiles.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载 MCP 配置失败'))
  } finally {
    mcpLoading.value = false
  }
}

const createMcp = async () => {
  if (!mcpForm.value.name.trim()) {
    ElMessage.error('请输入 MCP 配置名称')
    return
  }
  mcpSaving.value = true
  try {
    const response = await createMcpProfile(knowledgeBaseId.value, mcpForm.value)
    newMcpToken.value = response.data.token
    showMcpDialog.value = false
    mcpForm.value = {
      name: '',
      permission_scope: 'read_only',
      allowed_tools: ['search_knowledge', 'list_sources', 'get_document', 'get_paragraph'],
      rate_limit_per_minute: 60,
      max_top_k: 5,
      include_source_content: true,
      include_metadata: true
    }
    ElMessage.success('MCP 配置已创建')
    await loadMcpProfiles()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '创建 MCP 配置失败'))
  } finally {
    mcpSaving.value = false
  }
}

const toggleMcpProfile = async (profile: McpProfileDto) => {
  try {
    await updateMcpProfile(knowledgeBaseId.value, profile.id, { is_active: !profile.is_active })
    ElMessage.success(profile.is_active ? 'MCP 配置已停用' : 'MCP 配置已启用')
    await loadMcpProfiles()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '更新 MCP 配置失败'))
  }
}

const rotateMcpToken = async (profile: McpProfileDto) => {
  try {
    const response = await rotateMcpProfileToken(knowledgeBaseId.value, profile.id)
    newMcpToken.value = response.data.token
    ElMessage.success('MCP 令牌已轮换')
    await loadMcpProfiles()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '轮换 MCP 令牌失败'))
  }
}

const deleteMcp = async (profile: McpProfileDto) => {
  try {
    await ElMessageBox.confirm(`确认删除 MCP 配置“${profile.name}”？`, '确认删除', { type: 'warning' })
    await deleteMcpProfile(knowledgeBaseId.value, profile.id)
    ElMessage.success('MCP 配置已删除')
    await loadMcpProfiles()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(getApiErrorMessage(error, '删除 MCP 配置失败'))
  }
}

const isMcpToolAllowed = (tool: string) => {
  return (mcpScopeTools[mcpForm.value.permission_scope] || mcpScopeTools.read_only).includes(tool)
}

const copyMcpConfig = async (profile: McpProfileDto) => {
  await copyText(JSON.stringify({
    name: profile.name,
    url: profile.endpoint_url,
    authorization: 'Bearer <paste-token-here>',
    protocol: 'mcp-streamable-http'
  }, null, 2))
}

const getMcpScopeLabel = (scope: string) => ({
  read_only: '只读工具',
  citations_only: '检索引用',
  search_only: '仅检索'
}[scope] || scope)

const openMcpLogs = async (profile: McpProfileDto) => {
  showMcpLogsDialog.value = true
  mcpLogsLoading.value = true
  try {
    const response = await getMcpProfileLogs(knowledgeBaseId.value, profile.id)
    mcpLogs.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载 MCP 日志失败'))
  } finally {
    mcpLogsLoading.value = false
  }
}

const copyText = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('已复制')
  } catch (error) {
    ElMessage.error('复制失败')
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

watch(() => mcpForm.value.permission_scope, (scope) => {
  const allowed = new Set(mcpScopeTools[scope] || mcpScopeTools.read_only)
  mcpForm.value.allowed_tools = mcpForm.value.allowed_tools.filter((tool) => allowed.has(tool))
  if (mcpForm.value.allowed_tools.length === 0) {
    mcpForm.value.allowed_tools = [mcpScopeTools[scope]?.[0] || 'search_knowledge']
  }
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
.permissions-card,
.mcp-card { border-radius: 8px; margin-bottom: 16px; }
.permissions-card,
.mcp-card { margin-top: 16px; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-header h2 { margin: 0 0 4px; font-size: 18px; color: #111827; }
.card-header p { margin: 0; color: #6b7280; font-size: 13px; }
.share-form { margin-bottom: 12px; }
.token-alert { margin-bottom: 14px; }
.token-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.token-row code { word-break: break-all; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.status-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.status-error { max-width: 190px; color: #dc2626; font-size: 12px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }
.table-action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 4px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f8fafc;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}
.table-action-group :deep(.el-button + .el-button) { margin-left: 0; }
.action-button {
  width: 30px;
  height: 30px;
  min-height: 30px;
  transition: transform 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease;
}
.action-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
}
.action-button--danger:hover {
  box-shadow: 0 6px 14px rgba(220, 38, 38, 0.16);
}
@media (max-width: 768px) {
  .page-header,
  .card-header {
    flex-direction: column;
  }
  .header-actions,
  .document-actions {
    justify-content: flex-start;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
