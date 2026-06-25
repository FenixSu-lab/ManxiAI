<template>
  <Layout>
    <div class="chat-page">
      <div class="page-header">
        <h1>对话管理</h1>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>

      <div class="chat-list">
        <div class="chat-sidebar">
          <div class="chat-sessions">
            <div
              v-for="session in chatSessions"
              :key="session.id"
              class="chat-session-item"
              :class="{ active: currentSessionId === session.id }"
              @click="selectSession(session.id)"
            >
              <div class="session-header">
                <div class="session-title-group">
                  <h4>{{ session.title || '新对话' }}</h4>
                  <span v-if="session.knowledge_base_name" class="session-kb-tag">
                    {{ session.knowledge_base_name }}
                  </span>
                </div>
                <el-dropdown trigger="click" @command="handleSessionCommand">
                  <el-button type="text" size="small">
                    <el-icon><More /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item :command="{ action: 'rename', session }">
                        重命名
                      </el-dropdown-item>
                      <el-dropdown-item :command="{ action: 'delete', session }">
                        删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
              <div class="session-preview">
                {{ session.last_message || '暂无消息' }}
              </div>
              <div class="session-time">
                {{ formatTime(session.updated_at) }}
              </div>
            </div>
          </div>

          <div v-if="chatSessions.length === 0" class="empty-sessions">
            <el-empty description="暂无对话">
              <el-button type="primary" @click="openCreateDialog">
                创建第一个对话
              </el-button>
            </el-empty>
          </div>
        </div>

        <div class="chat-main">
          <div v-if="currentSessionId" class="chat-container">
            <div class="chat-header">
              <div>
                <h3>{{ getCurrentSession()?.title || '对话' }}</h3>
                <p v-if="getCurrentSession()?.knowledge_base_name" class="session-kb-summary">
                  知识库：{{ getCurrentSession()?.knowledge_base_name }}
                </p>
              </div>
              <el-button type="primary" @click="$router.push(`/chat/${currentSessionId}`)">
                进入对话
              </el-button>
            </div>

            <div class="chat-messages" ref="messagesContainer">
              <div
                v-for="message in currentMessages"
                :key="message.id"
                class="message"
                :class="`message--${message.role}`"
              >
                <div class="message-content">
                  <div class="message-text">{{ message.content }}</div>
                  <div class="message-time">{{ formatTime(message.created_at) }}</div>
                </div>
              </div>
            </div>

            <div class="chat-input">
              <div class="input-container">
                <el-input
                  v-model="newMessage"
                  placeholder="输入您的问题..."
                  @keyup.enter="sendMessage"
                  :disabled="sending"
                />
                <el-button
                  type="primary"
                  @click="sendMessage"
                  :loading="sending"
                  :disabled="!newMessage.trim()"
                >
                  发送
                </el-button>
              </div>
            </div>
          </div>

          <div v-else class="empty-chat">
            <el-empty description="选择一个对话开始聊天">
              <el-button type="primary" @click="openCreateDialog">
                创建新对话
              </el-button>
            </el-empty>
          </div>
        </div>
      </div>

      <el-dialog v-model="showCreateDialog" title="新建对话" width="420px">
        <el-form label-position="top">
          <el-form-item label="对话标题">
            <el-input v-model="newSessionTitle" placeholder="请输入对话标题" />
          </el-form-item>
          <el-form-item label="关联知识库">
            <el-select v-model="newSessionKnowledgeBaseId" placeholder="请选择知识库，可留空" clearable style="width: 100%">
              <el-option
                v-for="knowledgeBase in knowledgeBases"
                :key="knowledgeBase.id"
                :label="knowledgeBase.name"
                :value="knowledgeBase.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="createNewChat">确定</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="showRenameDialog" title="重命名对话" width="400px">
        <el-input v-model="renameTitle" placeholder="请输入对话标题" />
        <template #footer>
          <el-button @click="showRenameDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmRename">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, getApiErrorMessage } from '@/utils/api'
import Layout from '@/components/Layout.vue'
import { Plus, More } from '@element-plus/icons-vue'

interface KnowledgeBaseOption {
  id: string
  name: string
}

interface ChatSessionDto {
  id: string
  title: string
  last_message?: string
  knowledge_base_id?: string
  knowledge_base_name?: string
  updated_at: string
  created_at: string
}

interface ChatMessageDto {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  updated_at?: string
}

interface SessionCommand {
  action: 'rename' | 'delete'
  session: ChatSessionDto
}

const knowledgeBases = ref<KnowledgeBaseOption[]>([])
const chatSessions = ref<ChatSessionDto[]>([])
const currentSessionId = ref<string | null>(null)
const currentMessages = ref<ChatMessageDto[]>([])
const newMessage = ref('')
const sending = ref(false)
const showCreateDialog = ref(false)
const newSessionTitle = ref('')
const newSessionKnowledgeBaseId = ref<string | null>(null)
const showRenameDialog = ref(false)
const renameTitle = ref('')
const renameSessionId = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

const formatTime = (time: string) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const loadKnowledgeBases = async () => {
  try {
    const response = await api.get('/knowledge-bases/')
    knowledgeBases.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载知识库列表失败'))
  }
}

const loadChatSessions = async () => {
  try {
    const response = await api.get('/chat/sessions/')
    chatSessions.value = response.data.results || response.data
    if (chatSessions.value.length > 0 && !currentSessionId.value) {
      currentSessionId.value = chatSessions.value[0].id
      void loadMessages(currentSessionId.value)
    }
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载对话列表失败'))
  }
}

const loadMessages = async (sessionId: string) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionId}/messages/`)
    currentMessages.value = response.data.results || response.data
    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '加载消息失败'))
  }
}

const openCreateDialog = () => {
  newSessionTitle.value = '新对话'
  newSessionKnowledgeBaseId.value = null
  showCreateDialog.value = true
}

const createNewChat = async () => {
  try {
    const payload: Record<string, string> = {
      title: newSessionTitle.value || '新对话'
    }
    if (newSessionKnowledgeBaseId.value) {
      payload.knowledge_base_id = newSessionKnowledgeBaseId.value
    }
    const response = await api.post('/chat/sessions/', payload)
    const newSession: ChatSessionDto = response.data
    chatSessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
    currentMessages.value = []
    showCreateDialog.value = false
    ElMessage.success('创建对话成功')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '创建对话失败'))
  }
}

const selectSession = (sessionId: string) => {
  currentSessionId.value = sessionId
  void loadMessages(sessionId)
}

const getCurrentSession = (): ChatSessionDto | undefined => {
  return chatSessions.value.find((session) => session.id === currentSessionId.value)
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || !currentSessionId.value) return

  const userMessage: ChatMessageDto = {
    id: String(Date.now()),
    role: 'user',
    content: newMessage.value,
    created_at: new Date().toISOString()
  }

  currentMessages.value.push(userMessage)
  const messageContent = newMessage.value
  newMessage.value = ''
  sending.value = true

  try {
    const response = await api.post(`/chat/sessions/${currentSessionId.value}/messages/`, {
      content: messageContent,
      role: 'user'
    })

    currentMessages.value[currentMessages.value.length - 1] = response.data.user_message
    currentMessages.value.push(response.data.assistant_message)
    void loadChatSessions()

    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    currentMessages.value = currentMessages.value.filter((message) => message.id !== userMessage.id)
    ElMessage.error(getApiErrorMessage(error, '发送消息失败'))
  } finally {
    sending.value = false
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const handleSessionCommand = (command: SessionCommand) => {
  const { action, session } = command
  if (action === 'rename') {
    renameSessionId.value = session.id
    renameTitle.value = session.title
    showRenameDialog.value = true
    return
  }
  void deleteSession(session)
}

const confirmRename = async () => {
  try {
    const response = await api.patch(`/chat/sessions/${renameSessionId.value}/`, {
      title: renameTitle.value
    })
    const updatedSession: ChatSessionDto = response.data
    const sessionIndex = chatSessions.value.findIndex((session) => session.id === updatedSession.id)
    if (sessionIndex >= 0) {
      chatSessions.value[sessionIndex] = updatedSession
    }
    showRenameDialog.value = false
    ElMessage.success('重命名成功')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '重命名失败'))
  }
}

const deleteSession = async (session: ChatSessionDto) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.delete(`/chat/sessions/${session.id}/`)
    chatSessions.value = chatSessions.value.filter((item) => item.id !== session.id)

    if (currentSessionId.value === session.id) {
      currentSessionId.value = chatSessions.value.length > 0 ? chatSessions.value[0].id : null
      if (currentSessionId.value) {
        void loadMessages(currentSessionId.value)
      } else {
        currentMessages.value = []
      }
    }

    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(getApiErrorMessage(error, '删除失败'))
    }
  }
}

onMounted(() => {
  void loadKnowledgeBases()
  void loadChatSessions()
})
</script>

<style lang="scss" scoped>
.chat-page {
  padding: 24px;
  height: calc(100vh - 48px);

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    h1 {
      font-size: 28px;
      color: #333;
      margin: 0;
    }
  }
}

.chat-list {
  display: flex;
  height: calc(100vh - 140px);
  gap: 24px;
}

.chat-sidebar {
  width: 300px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;

  .chat-sessions {
    height: 100%;
    overflow-y: auto;

    .chat-session-item {
      padding: 16px;
      border-bottom: 1px solid #f0f0f0;
      cursor: pointer;
      transition: background-color 0.3s;

      &:hover {
        background: #f5f5f5;
      }

      &.active {
        background: #e6f7ff;
        border-right: 3px solid #1890ff;
      }

      .session-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;

        .session-title-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        h4 {
          margin: 0;
          font-size: 14px;
          color: #333;
          font-weight: 600;
        }
      }

      .session-kb-tag {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        font-size: 11px;
        color: #0f766e;
        background: #ccfbf1;
        border-radius: 999px;
        padding: 2px 8px;
      }

      .session-preview {
        font-size: 12px;
        color: #666;
        margin-bottom: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .session-time {
        font-size: 11px;
        color: #999;
      }
    }
  }

  .empty-sessions {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.chat-main {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;

  .chat-container {
    height: 100%;
    display: flex;
    flex-direction: column;

    .chat-header {
      padding: 16px 24px;
      border-bottom: 1px solid #f0f0f0;
      display: flex;
      justify-content: space-between;
      align-items: center;

      h3 {
        margin: 0;
        color: #333;
      }

      .session-kb-summary {
        margin: 6px 0 0;
        font-size: 12px;
        color: #0f766e;
      }
    }

    .chat-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;

      .message {
        margin-bottom: 16px;
        display: flex;

        &--user {
          justify-content: flex-end;

          .message-content {
            background: #1890ff;
            color: #fff;
          }
        }

        &--assistant {
          justify-content: flex-start;

          .message-content {
            background: #f5f5f5;
            color: #333;
          }
        }

        .message-content {
          max-width: 70%;
          padding: 12px 16px;
          border-radius: 8px;

          .message-text {
            margin-bottom: 4px;
            line-height: 1.5;
          }

          .message-time {
            font-size: 11px;
            opacity: 0.7;
          }
        }
      }
    }

    .chat-input {
      padding: 16px;
      border-top: 1px solid #f0f0f0;

      .input-container {
        display: flex;
        gap: 8px;

        .el-input {
          flex: 1;
        }
      }
    }
  }

  .empty-chat {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
