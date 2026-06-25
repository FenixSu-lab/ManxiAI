<template>
  <el-dialog v-model="dialogVisible" title="Document Details" width="960px" @close="resetState">
    <div v-if="document" class="document-detail">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Info" name="info"><el-descriptions :column="2" border><el-descriptions-item label="Name">{{ document.name }}</el-descriptions-item><el-descriptions-item label="Type">{{ document.type_display || getTypeLabel(document.type) }}</el-descriptions-item><el-descriptions-item label="Status"><el-tag :type="getStatusTagType(document.status)">{{ document.status_display || getStatusLabel(document.status) }}</el-tag></el-descriptions-item><el-descriptions-item label="Paragraphs">{{ document.paragraph_count || 0 }}</el-descriptions-item><el-descriptions-item label="Characters">{{ formatNumber(document.char_length || 0) }}</el-descriptions-item><el-descriptions-item label="Hits">{{ document.hit_count || 0 }}</el-descriptions-item><el-descriptions-item label="Created">{{ formatTime(document.created_at) }}</el-descriptions-item><el-descriptions-item label="Updated">{{ formatTime(document.updated_at) }}</el-descriptions-item></el-descriptions></el-tab-pane>
        <el-tab-pane label="Paragraphs" name="paragraphs"><div class="section-header"><span>{{ paragraphs.length }} paragraphs</span><el-button size="small" @click="loadParagraphs" :loading="paragraphsLoading"><el-icon><Refresh /></el-icon>Refresh</el-button></div><div v-loading="paragraphsLoading" class="paragraph-list"><el-empty v-if="paragraphs.length === 0" description="No paragraphs" /><div v-for="paragraph in paragraphs" :key="paragraph.id" class="paragraph-item"><div class="paragraph-title"><strong>{{ paragraph.title || `Paragraph ${paragraph.position + 1}` }}</strong><el-tag size="small" :type="paragraph.is_active ? 'success' : 'info'">{{ paragraph.is_active ? 'Active' : 'Inactive' }}</el-tag></div><p>{{ paragraph.content }}</p><div class="paragraph-meta"><span>{{ paragraph.char_length }} chars</span><span>Position {{ paragraph.position + 1 }}</span><span>{{ getStatusLabel(paragraph.status) }}</span></div></div></div></el-tab-pane>
        <el-tab-pane label="Tasks" name="tasks"><div class="section-header"><span>Task history</span><el-button size="small" @click="loadTasks" :loading="tasksLoading"><el-icon><Refresh /></el-icon>Refresh</el-button></div><div v-loading="tasksLoading" class="task-list"><el-empty v-if="tasks.length === 0" description="No tasks" /><div v-for="task in tasks" :key="task.id" class="task-item"><div class="task-title"><strong>{{ getTaskTypeLabel(task.task_type) }}</strong><el-tag :type="getTaskStatusTagType(task.status)">{{ getTaskStatusLabel(task.status) }}</el-tag></div><el-progress v-if="task.progress" :percentage="task.progress" /><el-alert v-if="task.error_message" type="error" :title="task.error_message" show-icon :closable="false" /><div class="paragraph-meta"><span>Created: {{ formatTime(task.created_at) }}</span><span>Updated: {{ formatTime(task.updated_at) }}</span></div></div></div></el-tab-pane>
        <el-tab-pane label="Settings" name="settings"><el-form :model="settingsForm" label-position="top" class="settings-form"><el-form-item label="Hit handling"><el-radio-group v-model="settingsForm.hit_handling_method"><el-radio label="optimization">Optimize answer</el-radio><el-radio label="directly_return">Return direct hit</el-radio></el-radio-group></el-form-item><el-form-item v-if="settingsForm.hit_handling_method === 'directly_return'" label="Direct return threshold"><el-slider v-model="settingsForm.directly_return_similarity" :min="0" :max="1" :step="0.05" show-input /></el-form-item><el-button type="primary" :loading="savingSettings" @click="saveSettings">Save settings</el-button></el-form></el-tab-pane>
      </el-tabs>
    </div>
    <template #footer><el-button @click="dialogVisible = false">Close</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getDocumentParagraphs, getDocumentTasks, updateDocument } from '@/api/knowledge-base'
import { getApiErrorMessage } from '@/utils/api'
import { formatNumber, formatTime as formatDateTime } from '@/utils/format'
interface DocumentDto { id: string; knowledge_base_id?: string; name: string; type: string; type_display?: string; status: string; status_display?: string; paragraph_count?: number; char_length?: number; hit_count?: number; hit_handling_method?: string; directly_return_similarity?: number; created_at?: string; updated_at?: string }
interface ParagraphDto { id: string; title?: string; content: string; char_length: number; status: string; is_active: boolean; position: number }
interface TaskDto { id: string; task_type: string; status: string; progress: number; error_message?: string; created_at?: string; updated_at?: string }
const props = defineProps<{ modelValue: boolean; document: DocumentDto | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; updated: [] }>()
const dialogVisible = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })
const activeTab = ref('info')
const paragraphs = ref<ParagraphDto[]>([])
const tasks = ref<TaskDto[]>([])
const paragraphsLoading = ref(false)
const tasksLoading = ref(false)
const savingSettings = ref(false)
const settingsForm = ref({ hit_handling_method: 'optimization', directly_return_similarity: 0.9 })
const formatTime = (value?: string) => formatDateTime(value || '')
const requireKnowledgeBaseId = () => { const id = props.document?.knowledge_base_id; if (!id) { ElMessage.error('Missing knowledge base id'); return null } return id }
const loadParagraphs = async () => { if (!props.document) return; const knowledgeBaseId = requireKnowledgeBaseId(); if (!knowledgeBaseId) return; paragraphsLoading.value = true; try { const response = await getDocumentParagraphs(knowledgeBaseId, props.document.id); paragraphs.value = response.data.results || response.data || [] } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Failed to load paragraphs')) } finally { paragraphsLoading.value = false } }
const loadTasks = async () => { if (!props.document) return; const knowledgeBaseId = requireKnowledgeBaseId(); if (!knowledgeBaseId) return; tasksLoading.value = true; try { const response = await getDocumentTasks(knowledgeBaseId, props.document.id); tasks.value = response.data.results || response.data || [] } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Failed to load tasks')) } finally { tasksLoading.value = false } }
const saveSettings = async () => { if (!props.document) return; const knowledgeBaseId = requireKnowledgeBaseId(); if (!knowledgeBaseId) return; savingSettings.value = true; try { await updateDocument(knowledgeBaseId, props.document.id, settingsForm.value); ElMessage.success('Settings saved'); emit('updated') } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Failed to save settings')) } finally { savingSettings.value = false } }
const resetState = () => { activeTab.value = 'info'; paragraphs.value = []; tasks.value = [] }
const getTypeLabel = (type?: string) => ({ base: 'General', web: 'Web', qa: 'QA', table: 'Table', markdown: 'Markdown', text: 'Text' }[type || ''] || type || '-')
const getStatusLabel = (status?: string) => ({ pending: 'Pending', processing: 'Processing', embedding: 'Embedding', completed: 'Completed', failed: 'Failed' }[status || ''] || status || '-')
const getStatusTagType = (status?: string) => ({ pending: 'info', processing: 'warning', embedding: 'warning', completed: 'success', failed: 'danger' }[status || ''] || 'info') as 'info' | 'warning' | 'success' | 'danger'
const getTaskTypeLabel = (type: string) => ({ document_processing: 'Document parsing', web_scraping: 'Web scraping', embedding: 'Embedding', sync: 'Sync' }[type] || type)
const getTaskStatusLabel = (status: string) => getStatusLabel(status)
const getTaskStatusTagType = (status: string) => getStatusTagType(status)
watch(() => props.document, (document) => { if (document) settingsForm.value = { hit_handling_method: document.hit_handling_method || 'optimization', directly_return_similarity: document.directly_return_similarity ?? 0.9 } })
watch(activeTab, (tab) => { if (tab === 'paragraphs' && paragraphs.value.length === 0) void loadParagraphs(); if (tab === 'tasks' && tasks.value.length === 0) void loadTasks() })
</script>
<style scoped lang="scss">.document-detail { min-height: 420px; }.section-header, .paragraph-title, .task-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; }.section-header { margin-bottom: 14px; }.paragraph-list, .task-list { min-height: 260px; }.paragraph-item, .task-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 12px; background: #fff; }.paragraph-item p { color: #374151; line-height: 1.7; margin: 10px 0; white-space: pre-wrap; }.paragraph-meta { display: flex; gap: 14px; flex-wrap: wrap; color: #6b7280; font-size: 12px; }.settings-form { max-width: 520px; }</style>
