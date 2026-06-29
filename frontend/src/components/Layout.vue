<!--
  Shared application shell with sidebar navigation and account actions.
-->
<template>
  <div class="layout">
    <aside class="layout__sidebar" :class="{ 'layout__sidebar--collapsed': collapsed }">
      <div class="sidebar-header">
        <h2>{{ collapsed ? 'M' : 'ManxiAI' }}</h2>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>

        <el-menu-item index="/knowledge-base">
          <el-icon><Collection /></el-icon>
          <span>Knowledge Base</span>
        </el-menu-item>

        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>Chat</span>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>Settings</span>
        </el-menu-item>

        <el-menu-item index="/model-management">
          <el-icon><Cpu /></el-icon>
          <span>Model Management</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <main class="layout__main">
      <header class="header">
        <div class="header-left">
          <el-button type="text" class="collapse-btn" @click="collapsed = !collapsed">
            <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
          </el-button>
        </div>

        <div class="header-right">
          <LanguageSwitch />
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :src="authStore.user?.avatar" />
              <span class="username">{{ authStore.user?.username || 'User' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>

            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">Profile</el-dropdown-item>
                <el-dropdown-item command="settings">Settings</el-dropdown-item>
                <el-dropdown-item divided command="logout">Log out</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <section class="content">
        <slot>
          <router-view />
        </slot>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import LanguageSwitch from '@/components/LanguageSwitch.vue'
import {
  House,
  Collection,
  ChatDotRound,
  Setting,
  Cpu,
  Expand,
  Fold,
  ArrowDown
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const collapsed = ref(false)

const activeMenu = computed(() => route.path)

// Handles account menu actions and keeps navigation side effects centralized.
const handleCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('Profile editing is not available yet.')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('Log out of this account?', 'Confirm', {
          confirmButtonText: 'Log out',
          cancelButtonText: 'Cancel',
          type: 'warning'
        })
        authStore.logout()
        router.push('/login')
        ElMessage.success('Logged out.')
      } catch {
        // User canceled the confirmation dialog.
      }
      break
  }
}
</script>

<style lang="scss" scoped>
.layout {
  min-height: 100vh;
  display: flex;
  background: #f5f7fb;
}

.layout__sidebar {
  width: 232px;
  min-height: 100vh;
  background: #001529;
  transition: width 0.2s ease;
  overflow: hidden;

  &--collapsed {
    width: 64px;
  }

  :deep(.el-menu) {
    border-right: 0;
  }
}

.layout__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1f2937;

  h2 {
    color: #fff;
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }
}

.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e8edf5;
  padding: 0 20px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  color: #667085;
  font-size: 18px;

  &:hover {
    color: #1890ff;
  }
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s ease;

  &:hover {
    background: #f2f5fa;
  }

  .username {
    margin: 0 8px;
    color: #344054;
    font-size: 14px;
  }

  .el-icon {
    color: #667085;
    font-size: 12px;
  }
}

.content {
  flex: 1;
  min-width: 0;
}
</style>
