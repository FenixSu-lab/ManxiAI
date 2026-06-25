<!--
  Dashboard landing page for quick system status and entry points.
-->
<template>
  <Layout>
    <div class="dashboard">
      <div class="dashboard-header">
        <div>
          <p class="eyebrow">Workspace Overview</p>
          <h1>Dashboard</h1>
          <p>Welcome back, {{ authStore.user?.username || 'user' }}.</p>
        </div>
        <el-button type="primary" @click="$router.push('/knowledge-base')">
          <el-icon><Plus /></el-icon>
          New knowledge base
        </el-button>
      </div>

      <div class="stats-grid">
        <div v-for="item in statItems" :key="item.label" class="stat-card">
          <div class="stat-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ item.value }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </div>
      </div>

      <div class="dashboard-grid">
        <section class="card quick-actions">
          <div class="card__header">
            <h3>Quick Actions</h3>
          </div>
          <div class="card__body action-grid">
            <el-button type="primary" size="large" @click="$router.push('/knowledge-base')">
              <el-icon><Plus /></el-icon>
              Create knowledge base
            </el-button>
            <el-button type="success" size="large" @click="$router.push('/chat')">
              <el-icon><ChatDotRound /></el-icon>
              Start chat
            </el-button>
            <el-button type="info" size="large" @click="$router.push('/settings')">
              <el-icon><Setting /></el-icon>
              System settings
            </el-button>
          </div>
        </section>

        <section class="card">
          <div class="card__header">
            <h3>Runtime Status</h3>
          </div>
          <div class="card__body runtime-status">
            <div class="runtime-status__row">
              <span>Backend</span>
              <el-tag :type="runtimeTagType">{{ runtimeStatus.label }}</el-tag>
            </div>
            <div class="runtime-status__row">
              <span>Database latency</span>
              <strong>{{ runtimeStatus.databaseLatency }}</strong>
            </div>
            <div class="runtime-status__row">
              <span>Total latency</span>
              <strong>{{ runtimeStatus.totalLatency }}</strong>
            </div>
            <p class="runtime-status__message">{{ runtimeStatus.message }}</p>
          </div>
        </section>
      </div>
    </div>
  </Layout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/components/Layout.vue'
import { api } from '@/utils/api'
import {
  Collection,
  Document,
  ChatDotRound,
  User,
  Plus,
  Setting
} from '@element-plus/icons-vue'

const authStore = useAuthStore()

const stats = ref({
  knowledgeBaseCount: 0,
  documentCount: 0,
  chatCount: 0,
  userCount: 0
})

const runtimeStatus = ref({
  label: 'Checking',
  status: 'checking',
  databaseLatency: '...',
  totalLatency: '...',
  message: 'Checking backend and database health.'
})

const statItems = computed(() => [
  { label: 'Knowledge bases', value: stats.value.knowledgeBaseCount, icon: Collection },
  { label: 'Documents', value: stats.value.documentCount, icon: Document },
  { label: 'Chats', value: stats.value.chatCount, icon: ChatDotRound },
  { label: 'Users', value: stats.value.userCount, icon: User }
])

const runtimeTagType = computed(() => {
  if (runtimeStatus.value.status === 'ok') return 'success'
  if (runtimeStatus.value.status === 'degraded') return 'warning'
  if (runtimeStatus.value.status === 'offline') return 'danger'
  return 'info'
})

// Loads summary counters for resources visible to the current user.
const loadStats = async () => {
  try {
    const response = await api.get('/dashboard/summary/')
    stats.value = {
      knowledgeBaseCount: response.data.knowledge_base_count || 0,
      documentCount: response.data.document_count || 0,
      chatCount: response.data.chat_count || 0,
      userCount: response.data.user_count || 0
    }
  } catch (error) {
    console.error('Failed to load dashboard summary:', error)
  }
}

// Loads backend health without triggering global API error messages for degraded responses.
const loadRuntimeStatus = async () => {
  try {
    const response = await api.get('/health/', {
      validateStatus: (status) => status < 600
    })
    const data = response.data
    const databaseLatency = data?.database?.latency_ms
    const totalLatency = data?.latency_ms
    runtimeStatus.value = {
      label: data?.status === 'ok' ? 'Online' : 'Degraded',
      status: data?.status === 'ok' ? 'ok' : 'degraded',
      databaseLatency: typeof databaseLatency === 'number' ? `${databaseLatency} ms` : 'unknown',
      totalLatency: typeof totalLatency === 'number' ? `${totalLatency} ms` : 'unknown',
      message: data?.database?.ok
        ? 'Backend is reachable and the database responded.'
        : `Backend responded, but database health is degraded: ${data?.database?.error || 'unknown error'}`
    }
  } catch {
    runtimeStatus.value = {
      label: 'Offline',
      status: 'offline',
      databaseLatency: 'unavailable',
      totalLatency: 'unavailable',
      message: 'Backend health check failed. Confirm Django is running and the Vite proxy target is correct.'
    }
  }
}

onMounted(() => {
  loadStats()
  loadRuntimeStatus()
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 28px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 28px;

  h1 {
    font-size: 32px;
    color: #111827;
    margin: 0 0 8px;
  }

  p {
    color: #667085;
    font-size: 16px;
    margin: 0;
  }
}

.eyebrow {
  color: #2563eb !important;
  font-size: 12px !important;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px !important;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  border: 1px solid #edf1f7;
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0f766e 0%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;

  .el-icon {
    font-size: 24px;
    color: #fff;
  }
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 14px;
  color: #667085;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 20px;
}

.card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid #edf1f7;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.card__header {
  padding: 20px 22px 0;

  h3 {
    margin: 0;
    color: #111827;
  }
}

.card__body {
  padding: 20px 22px 22px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;

  .el-button {
    height: 58px;
    font-size: 15px;
  }
}

.note-list {
  display: grid;
  gap: 12px;
}

.note-item {
  color: #475467;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 14px;
  line-height: 1.5;
}

.runtime-status {
  display: grid;
  gap: 14px;
}

.runtime-status__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #475467;

  strong {
    color: #111827;
  }
}

.runtime-status__message {
  margin: 4px 0 0;
  color: #667085;
  line-height: 1.5;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 14px;
}

@media (max-width: 900px) {
  .dashboard-grid,
  .dashboard-header {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
