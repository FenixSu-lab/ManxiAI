/*
 * Application router with token-aware authentication guards.
 */
import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/Index.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/knowledge-base',
      name: 'KnowledgeBase',
      component: () => import('@/views/knowledge-base/Index.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/knowledge-base/:id',
      name: 'KnowledgeBaseDetail',
      component: () => import('@/views/knowledge-base/Detail.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/chat/Index.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/chat/:id',
      name: 'ChatDetail',
      component: () => import('@/views/chat/Detail.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/settings/Index.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/error/404.vue')
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  NProgress.start()

  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false

  // A persisted token is enough to try restoring the user before redirecting.
  if (authStore.token && !authStore.user) {
    try {
      await authStore.getUserInfo()
    } catch {
      // getUserInfo clears invalid auth state; the redirect below handles it.
    }
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (!requiresAuth && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
