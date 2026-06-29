<!--
  Public read-only page for viewing a shared chat conversation.
-->
<template>
  <div class="public-chat-share">
    <main class="share-shell">
      <section class="share-header">
        <div>
          <p class="eyebrow">ManxiAI 对话分享</p>
          <h1>{{ shareData?.title || '共享对话' }}</h1>
          <p v-if="shareData?.knowledge_base_name">关联知识库：{{ shareData.knowledge_base_name }}</p>
        </div>
        <el-tag type="info">只读</el-tag>
      </section>

      <el-skeleton v-if="loading" :rows="8" animated />
      <el-result
        v-else-if="loadFailed"
        icon="warning"
        title="分享不可用"
        sub-title="该分享链接不存在、已撤销，或服务暂时不可访问。"
      />
      <section v-else class="message-list">
        <article
          v-for="message in shareData?.messages || []"
          :key="message.id"
          class="message-card"
          :class="`message-card--${message.role}`"
        >
          <div class="message-meta">
            <strong>{{ message.role === 'user' ? '用户' : 'AI 助手' }}</strong>
            <span>{{ formatTime(message.created_at) }}</span>
          </div>
          <p>{{ message.content }}</p>
        </article>
        <el-empty v-if="!shareData?.messages?.length" description="暂无对话内容" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/utils/api'

interface PublicChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

interface PublicChatShare {
  title: string
  knowledge_base_name?: string
  messages: PublicChatMessage[]
  created_at: string
}

const route = useRoute()
const loading = ref(false)
const loadFailed = ref(false)
const shareData = ref<PublicChatShare | null>(null)

const formatTime = (value?: string) => {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

const loadShare = async () => {
  loading.value = true
  loadFailed.value = false
  try {
    const response = await api.get(`/chat/shares/${route.params.token}/`)
    shareData.value = response.data
  } catch (error) {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadShare()
})
</script>

<style scoped lang="scss">
.public-chat-share {
  min-height: 100vh;
  padding: 32px 16px;
  background:
    radial-gradient(circle at 20% 20%, rgba(20, 184, 166, 0.14), transparent 28%),
    linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}

.share-shell {
  width: min(920px, 100%);
  margin: 0 auto;
}

.share-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);

  h1 {
    margin: 4px 0 8px;
    color: #0f172a;
    font-size: 28px;
  }

  p {
    margin: 0;
    color: #64748b;
  }
}

.eyebrow {
  color: #0f766e !important;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message-card {
  max-width: 78%;
  padding: 18px 20px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);

  p {
    margin: 10px 0 0;
    white-space: pre-wrap;
    line-height: 1.7;
    color: #111827;
  }
}

.message-card--user {
  align-self: flex-end;
  background: #0f766e;

  p,
  .message-meta {
    color: #ffffff;
  }

  .message-meta span {
    color: rgba(255, 255, 255, 0.72);
  }
}

.message-card--assistant {
  align-self: flex-start;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: #334155;
  font-size: 13px;

  span {
    color: #94a3b8;
  }
}

@media (max-width: 768px) {
  .share-header {
    flex-direction: column;
  }

  .message-card {
    max-width: 100%;
  }
}
</style>
