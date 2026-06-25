/*
 * Frontend application bootstrap.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/stores/auth'

import 'element-plus/dist/index.css'
import './styles/index.scss'

import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Warm up auth state; the router guard also awaits this when needed.
const authStore = useAuthStore()
void authStore.initialize()

app.mount('#app')
