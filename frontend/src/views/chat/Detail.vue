<template>
  <div class="chat-detail">
    <div class="chat-header">
      <div class="header-left">
        <el-button @click="$router.back()" type="text">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div>
          <h2>{{ chatSession?.title || '对话' }}</h2>
          <p v-if="chatSession?.knowledge_base_name" class="session-kb-summary">
            当前知识库：{{ chatSession.knowledge_base_name }}
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-select
          v-model="selectedKnowledgeBaseId"
          placeholder="切换知识库"
          clearable
          class="knowledge-base-select"
          @change="updateKnowledgeBase"
        >
          <el-option
            v-for="knowledgeBase in knowledgeBases"
            :key="knowledgeBase.id"
            :label="knowledgeBase.name"
            :value="knowledgeBase.id"
          />
        </el-select>
        <el-button :disabled="!writableKnowledgeBases.length || messages.length === 0" @click="openArchiveDialog">
          归档为数据源
        </el-button>
        <el-button type="primary" @click="clearChat">
          <el-icon><Delete /></el-icon>
          清空对话
        </el-button>
      </div>
    </div>

    <el-dialog v-model="archiveDialogVisible" title="归档为数据源" width="720px">
      <el-form label-position="top">
        <el-form-item label="目标知识库">
          <el-select v-model="archiveForm.knowledge_base_id" placeholder="选择可写知识库" style="width: 100%">
            <el-option
              v-for="knowledgeBase in writableKnowledgeBases"
              :key="knowledgeBase.id"
              :label="knowledgeBase.name"
              :value="knowledgeBase.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据源名称">
          <el-input v-model="archiveForm.name" placeholder="例如：对话归档-会议室规则" />
        </el-form-item>
      </el-form>
      <div class="archive-actions">
        <el-button @click="previewArchive" :loading="archivePreviewing">预览归档内容</el-button>
      </div>
      <el-table v-if="archivePreview.length" :data="archivePreview" max-height="260" class="archive-preview">
        <el-table-column prop="question" label="问题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="answer" label="答案" min-width="280" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="archiveDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="archivePreview.length === 0" :loading="archiving" @click="createArchive">确认归档</el-button>
      </template>
    </el-dialog>

    <div class="chat-container">
      <div class="chat-messages" ref="messagesContainer">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="`message--${message.role}`"
        >
          <div class="message-avatar">
            <el-avatar v-if="message.role === 'user'" :src="userAvatar" />
            <div v-else class="ai-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </div>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="message-sender">
                {{ message.role === 'user' ? '您' : 'AI助手' }}
              </span>
              <span class="message-time">{{ formatTime(message.created_at) }}</span>
            </div>
            <div class="message-text">{{ message.content }}</div>
            <div class="message-actions">
              <el-button type="text" size="small" @click="copyMessage(message.content)">
                <el-icon><DocumentCopy /></el-icon>
                复制
              </el-button>
              <el-button v-if="message.role === 'assistant'" type="text" size="small" @click="regenerateMessage(message)">
                <el-icon><Refresh /></el-icon>
                重新生成
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="isTyping" class="message message--assistant">
          <div class="message-avatar">
            <div class="ai-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </div>
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <div class="input-container">
          <el-input
            v-model="newMessage"
            type="textarea"
            :rows="3"
            placeholder="输入您的问题..."
            @keydown.enter.prevent="handleEnterKey"
            :disabled="sending"
            resize="none"
          />
          <div class="input-actions">
            <el-button
              type="primary"
              @click="sendMessage"
              :loading="sending"
              :disabled="!newMessage.trim()"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, getApiErrorMessage } from '@/utils/api'
import { useAuthStore } from '@/stores/auth'
import {
  ArrowLeft,
  Delete,
  ChatDotRound,
  DocumentCopy,
  Refresh,
  Promotion
} from '@element-plus/icons-vue'

const route = useRoute()
const authStore = useAuthStore()
const chatId = route.params.id as string

interface KnowledgeBaseOption {
  id: string
  name: string
  can_write?: boolean
}

interface ChatSessionDto {
  id: string
  title: string
  knowledge_base_id?: string
  knowledge_base_name?: string
  created_at: string
  updated_at: string
}

interface ChatMessageDto {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  updated_at?: string
}

const chatSession = ref<ChatSessionDto | null>(null)
const knowledgeBases = ref<KnowledgeBaseOption[]>([])
const selectedKnowledgeBaseId = ref<string | null>(null)
const messages = ref<ChatMessageDto[]>([])
const newMessage = ref('')
const sending = ref(false)
const isTyping = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const archiveDialogVisible = ref(false)
const archivePreviewing = ref(false)
const archiving = ref(false)
const archivePreview = ref<Array<{ question: string; answer: string }>>([])
const archiveForm = ref({
  knowledge_base_id: '',
  name: ''
})

const userAvatar = computed(() => authStore.user?.avatar)
const writableKnowledgeBases = computed(() => knowledgeBases.value.filter((knowledgeBase) => knowledgeBase.can_write))

const formatTime = (time: string) => {
  if (!time) return ''
  return new Date(time).toLocaleTimeString()
}

const loadKnowledgeBases = async () => {
  try {
    const response = await api.get('/knowledge-bases/')
    knowledgeBases.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载知识库列表失败'))
  }
}

const openArchiveDialog = () => {
  const currentWritable = writableKnowledgeBases.value.find((knowledgeBase) => knowledgeBase.id === selectedKnowledgeBaseId.value)
  archiveForm.value = {
    knowledge_base_id: currentWritable?.id || writableKnowledgeBases.value[0]?.id || '',
    name: `对话归档-${new Date().toLocaleDateString()}`
  }
  archivePreview.value = []
  archiveDialogVisible.value = true
}

const previewArchive = async () => {
  if (!archiveForm.value.knowledge_base_id) {
    ElMessage.error('请选择目标知识库')
    return
  }
  archivePreviewing.value = true
  try {
    const response = await api.post(`/chat/sessions/${chatId}/archive/`, {
      ...archiveForm.value,
      preview: true
    })
    archivePreview.value = response.data.items || []
    if (archivePreview.value.length === 0) {
      ElMessage.warning('当前对话没有可归档的问答对')
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '预览归档失败'))
  } finally {
    archivePreviewing.value = false
  }
}

const createArchive = async () => {
  if (!archiveForm.value.knowledge_base_id) {
    ElMessage.error('请选择目标知识库')
    return
  }
  archiving.value = true
  try {
    await api.post(`/chat/sessions/${chatId}/archive/`, {
      ...archiveForm.value,
      preview: false
    })
    ElMessage.success('对话已归档为数据源，正在向量化')
    archiveDialogVisible.value = false
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '归档失败'))
  } finally {
    archiving.value = false
  }
}

const loadChatSession = async () => {
  try {
    const response = await api.get(`/chat/sessions/${chatId}/`)
    chatSession.value = response.data
    selectedKnowledgeBaseId.value = response.data.knowledge_base_id || null
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载对话信息失败'))
  }
}

const updateKnowledgeBase = async (knowledgeBaseId: string | null) => {
  try {
    const payload = {
      knowledge_base_id: knowledgeBaseId,
      title: chatSession.value?.title || '对话'
    }
    const response = await api.patch(`/chat/sessions/${chatId}/`, payload)
    chatSession.value = response.data
    selectedKnowledgeBaseId.value = response.data.knowledge_base_id || null
    ElMessage.success('知识库已更新')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '更新知识库失败'))
  }
}

const loadMessages = async () => {
  try {
    const response = await api.get(`/chat/sessions/${chatId}/messages/`)
    messages.value = response.data.results || response.data
    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载消息失败'))
  }
}

const sendMessage = async () => {
  if (!newMessage.value.trim()) return

  const userMessage: ChatMessageDto = {
    id: String(Date.now()),
    role: 'user',
    content: newMessage.value,
    created_at: new Date().toISOString()
  }

  messages.value.push(userMessage)
  const messageContent = newMessage.value
  newMessage.value = ''
  sending.value = true
  isTyping.value = true

  nextTick(() => {
    scrollToBottom()
  })

  try {
    const response = await api.post(`/chat/sessions/${chatId}/messages/`, {
      content: messageContent,
      role: 'user'
    })

    messages.value[messages.value.length - 1] = response.data.user_message
    messages.value.push(response.data.assistant_message)

    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    messages.value = messages.value.filter((message) => message.id !== userMessage.id)
    ElMessage.error(getApiErrorMessage(error, '发送消息失败'))
  } finally {
    sending.value = false
    isTyping.value = false
  }
}

const handleEnterKey = (event: KeyboardEvent) => {
  if (event.shiftKey) {
    return
  }
  sendMessage()
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const copyMessage = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const regenerateMessage = async (_message: ChatMessageDto) => {
  ElMessage.info('重新生成功能开发中')
}

const clearChat = async () => {
  try {
    await ElMessageBox.confirm('确定要清空当前对话吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.delete(`/chat/sessions/${chatId}/messages/`)
    messages.value = []
    ElMessage.success('对话已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(getApiErrorMessage(error, '清空失败'))
    }
  }
}

onMounted(() => {
  void loadKnowledgeBases()
  void loadChatSession()
  void loadMessages()
})
</script>

<style lang="scss" scoped>
.chat-detail {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-header {
  min-height: 60px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    h2 {
      margin: 0;
      font-size: 18px;
      color: #333;
    }

    .session-kb-summary {
      margin: 6px 0 0;
      font-size: 12px;
      color: #0f766e;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;

    .knowledge-base-select {
      width: 220px;
    }
  }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.archive-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.archive-preview {
  margin-top: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;

  .message {
    display: flex;
    margin-bottom: 24px;

    &--user {
      justify-content: flex-end;

      .message-content {
        background: #1890ff;
        color: #fff;

        .message-header .message-sender {
          color: rgba(255, 255, 255, 0.8);
        }

        .message-header .message-time {
          color: rgba(255, 255, 255, 0.6);
        }
      }
    }

    &--assistant {
      justify-content: flex-start;

      .message-content {
        background: #fff;
        color: #333;
        border: 1px solid #e8e8e8;
      }
    }

    .message-avatar {
      margin: 0 12px;

      .ai-avatar {
        width: 40px;
        height: 40px;
        background: #1890ff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 18px;
      }
    }

    .message-content {
      max-width: 70%;
      padding: 16px 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .message-sender {
          font-weight: 600;
          font-size: 14px;
        }

        .message-time {
          font-size: 12px;
          opacity: 0.7;
        }
      }

      .message-text {
        line-height: 1.6;
        margin-bottom: 12px;
        word-wrap: break-word;
        white-space: pre-wrap;
      }

      .message-actions {
        display: flex;
        gap: 8px;
        opacity: 0.7;

        .el-button {
          padding: 4px 8px;
          font-size: 12px;
        }
      }
    }
  }
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;

  span {
    width: 8px;
    height: 8px;
    background: #1890ff;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }

    &:nth-child(2) {
      animation-delay: -0.16s;
    }
  }
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.chat-input {
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding: 24px;

  .input-container {
    display: flex;
    gap: 12px;
    align-items: flex-end;

    .el-textarea {
      flex: 1;
    }

    .input-actions {
      display: flex;
      flex-direction: column;

      .el-button {
        height: 40px;
        padding: 0 16px;
      }
    }
  }
}

@media (max-width: 768px) {
  .chat-header {
    flex-direction: column;
    align-items: stretch;

    .header-right {
      .knowledge-base-select {
        width: 100%;
      }
    }
  }

  .chat-messages {
    padding: 16px;

    .message {
      .message-content {
        max-width: 85%;
      }
    }
  }

  .chat-input {
    padding: 16px;
  }
}
</style>
