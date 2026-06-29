/*
 * Lightweight runtime language support for the Vue SPA.
 *
 * The current frontend was built with literal UI strings across many pages.
 * This module provides a pragmatic language switch without forcing a large
 * component-by-component i18n rewrite.
 */
import { reactive } from 'vue'

export type Language = 'en' | 'zh'

const STORAGE_KEY = 'manxiai_language'

export const languageState = reactive({
  current: (localStorage.getItem(STORAGE_KEY) === 'zh' ? 'zh' : 'en') as Language
})

const enToZh: Record<string, string> = {
  'Dashboard': '仪表盘',
  'Knowledge Base': '知识库',
  'Chat': '对话',
  'Settings': '设置',
  'Model Management': '模型管理',
  'Model Operations': '模型运维',
  'Manage DeepSeek, Qwen, OpenAI-compatible, and custom chat model providers.': '管理 DeepSeek、通义千问、OpenAI 兼容和自定义聊天模型供应商。',
  'Seed Chinese presets': '生成国产模型预设',
  'New provider': '新建供应商',
  'No model providers': '暂无模型供应商',
  'Provider': '供应商',
  'Base URL': '基础地址',
  'API Key': 'API 密钥',
  'Enabled': '已启用',
  'Disabled': '已禁用',
  'Edit': '编辑',
  'Activate': '设为当前',
  'Test': '测试',
  'Edit provider': '编辑供应商',
  'Example: DeepSeek Production': '示例：DeepSeek 生产环境',
  'Custom OpenAI Compatible': '自定义 OpenAI 兼容',
  'Timeout seconds': '超时时间（秒）',
  'Leave blank to keep existing key when editing': '编辑时留空则保留原密钥',
  'Active model:': '当前模型：',
  'Using environment fallback:': '使用环境变量回退：',
  'Model provider updated': '模型供应商已更新',
  'Model provider created': '模型供应商已创建',
  'Active model provider switched': '当前模型供应商已切换',
  'Model provider deleted': '模型供应商已删除',
  'Provider presets seeded': '模型预设已生成',
  'Failed to load model providers': '加载模型供应商失败',
  'Failed to save model provider': '保存模型供应商失败',
  'Failed to activate model provider': '切换模型供应商失败',
  'Provider test failed': '供应商测试失败',
  'Failed to delete model provider': '删除模型供应商失败',
  'Failed to seed provider presets': '生成模型预设失败',
  'Please enter provider name': '请输入供应商名称',
  'Please select provider': '请选择供应商',
  'Please enter model name': '请输入模型名称',
  'Profile': '个人资料',
  'Log out': '退出登录',
  'User': '用户',
  'Confirm': '确认',
  'Cancel': '取消',
  'Delete': '删除',
  'Create': '创建',
  'Save': '保存',
  'Back': '返回',
  'Refresh': '刷新',
  'Actions': '操作',
  'Name': '名称',
  'Status': '状态',
  'Type': '类型',
  'Updated': '更新时间',
  'Created': '创建时间',
  'Created at': '创建时间',
  'Key': '密钥',
  'Regenerate': '重新生成',
  'Workspace Overview': '工作区概览',
  'Welcome back,': '欢迎回来，',
  'New knowledge base': '新建知识库',
  'Knowledge bases': '知识库',
  'Documents': '文档',
  'Chats': '对话',
  'Users': '用户',
  'Quick Actions': '快捷操作',
  'Create knowledge base': '创建知识库',
  'Start chat': '开始对话',
  'System settings': '系统设置',
  'Runtime Status': '运行状态',
  'Backend': '后端服务',
  'Database latency': '数据库延迟',
  'Total latency': '总延迟',
  'Checking': '检查中',
  'Online': '在线',
  'Degraded': '异常',
  'Offline': '离线',
  'unknown': '未知',
  'unavailable': '不可用',
  'Checking backend and database health.': '正在检查后端和数据库状态。',
  'Backend is reachable and the database responded.': '后端可访问，数据库已响应。',
  'Backend health check failed. Confirm Django is running and the Vite proxy target is correct.': '后端健康检查失败。请确认 Django 正在运行，且 Vite 代理目标正确。',
  'Enterprise AI knowledge base system': '企业级 AI 知识库系统',
  'Email or username': '邮箱或用户名',
  'Email': '邮箱',
  'Username': '用户名',
  'Password': '密码',
  'Confirm password': '确认密码',
  'Log in': '登录',
  'Create one': '创建账号',
  'No account yet?': '还没有账号？',
  'Create your account': '创建你的账号',
  'Register': '注册',
  'Already have an account?': '已有账号？',
  'Administration': '管理',
  'First name': '名',
  'Last name': '姓',
  'Save profile': '保存资料',
  'Change Password': '修改密码',
  'Current password': '当前密码',
  'New password': '新密码',
  'Change password': '修改密码',
  'API Keys': 'API 密钥',
  'Create API key': '创建 API 密钥',
  'Create API Key': '创建 API 密钥',
  'API key name': 'API 密钥名称',
  'Manage data sources and processing status for this knowledge base.': '管理该知识库的数据源和处理状态。',
  'Data Sources': '数据源',
  'Uploaded files, crawled pages, and QA entries are parsed and embedded in the background.': '上传文件、网页抓取和问答条目会在后台解析并向量化。',
  'New QA': '新建问答',
  'Crawl Web': '抓取网页',
  'Upload Document': '上传文档',
  'Document': '文档',
  'Chunks': '分块',
  'View': '查看',
  'Reprocess': '重新处理',
  'Document Details': '文档详情',
  'Info': '信息',
  'Paragraphs': '段落',
  'Characters': '字符数',
  'Hits': '命中次数',
  'Tasks': '任务',
  'Task history': '任务历史',
  'No tasks': '暂无任务',
  'No paragraphs': '暂无段落',
  'Settings saved': '设置已保存',
  'Close': '关闭',
  'Hit handling': '命中处理',
  'Optimize answer': '优化回答',
  'Return direct hit': '直接返回命中',
  'Direct return threshold': '直接返回阈值',
  'Pending': '待处理',
  'Processing': '处理中',
  'Embedding': '向量化中',
  'Completed': '已完成',
  'Failed': '失败',
  'General': '通用',
  'Web': '网页',
  'QA': '问答',
  'Table': '表格',
  'Markdown': 'Markdown',
  'Text': '文本',
  'Active': '启用',
  'Inactive': '停用',
  'Position': '位置',
  'Document parsing': '文档解析',
  'Web scraping': '网页抓取',
  'Sync': '同步',
  'Knowledge Bases': '知识库',
  'Manage documents, web pages, and QA content used by RAG chat.': '管理用于 RAG 对话的文档、网页和问答内容。',
  'New Knowledge Base': '新建知识库',
  'Search knowledge bases': '搜索知识库',
  'No knowledge bases': '暂无知识库',
  'Create first knowledge base': '创建第一个知识库',
  'No description': '暂无描述',
  'Example: Meeting room policy': '示例：会议室制度',
  'Optional usage notes': '可选的使用说明',
  'Public': '公开',
  'Private': '私有',
  'Please enter a name': '请输入名称',
  'Please set a chunk size': '请设置分块大小',
  'Please set top K': '请设置 Top K',
  'Knowledge base created': '知识库已创建',
  'Failed to load knowledge bases': '加载知识库失败',
  'Failed to create knowledge base': '创建知识库失败',
  'Create Knowledge Base': '创建知识库',
  'Description': '描述',
  'Public access': '公开访问',
  'Chunk size': '分块大小',
  'Top K': 'Top K',
  'Open Chat': '打开对话',
  'Send': '发送',
  'New chat': '新建对话',
  'Chat Sessions': '对话会话',
  'Messages': '消息',
  'Rename': '重命名',
  'Language': '语言',
  'English': '英文',
  'Chinese': '中文',
  '中文': '中文',
  'Logged in.': '登录成功。',
  'Logged out.': '已退出登录。',
  'Registration complete. Please log in.': '注册完成，请登录。',
  'Profile updated.': '个人资料已更新。',
  'Password changed.': '密码已修改。',
  'API key created.': 'API 密钥已创建。',
  'API key regenerated.': 'API 密钥已重新生成。',
  'API key deleted.': 'API 密钥已删除。',
  'Reprocessing started': '已开始重新处理',
  'Document deleted': '文档已删除'
}

const zhToEn = Object.fromEntries(Object.entries(enToZh).map(([en, zh]) => [zh, en]))
let isTranslating = false
let translateScheduled = false

export function setLanguage(language: Language): void {
  languageState.current = language
  localStorage.setItem(STORAGE_KEY, language)
  scheduleTranslate()
}

export function toggleLanguage(): void {
  setLanguage(languageState.current === 'zh' ? 'en' : 'zh')
}

export function t(text: string): string {
  return translateText(text)
}

export function installRuntimeTranslator(): void {
  scheduleTranslate()
  const observer = new MutationObserver(() => {
    if (isTranslating || languageState.current !== 'zh') {
      return
    }
    scheduleTranslate()
  })
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ['placeholder', 'title', 'aria-label']
  })
}

function translateText(value: string): string {
  const source = value.trim()
  if (!source) return value

  const dictionary = languageState.current === 'zh' ? enToZh : zhToEn
  const direct = dictionary[source]
  if (direct) return preserveWhitespace(value, direct)

  for (const [from, to] of Object.entries(dictionary)) {
    if (source.startsWith(from)) {
      return preserveWhitespace(value, source.replace(from, to))
    }
  }
  if (languageState.current === 'zh') {
    if (/^\d+\s+docs$/.test(source)) return preserveWhitespace(value, source.replace('docs', '个文档'))
    if (/^\d+\s+chunks$/.test(source)) return preserveWhitespace(value, source.replace('chunks', '个分块'))
    if (/^\d+\s+chars$/.test(source)) return preserveWhitespace(value, source.replace('chars', '个字符'))
  } else {
    if (/^\d+\s+个文档$/.test(source)) return preserveWhitespace(value, source.replace('个文档', 'docs'))
    if (/^\d+\s+个分块$/.test(source)) return preserveWhitespace(value, source.replace('个分块', 'chunks'))
    if (/^\d+\s+个字符$/.test(source)) return preserveWhitespace(value, source.replace('个字符', 'chars'))
  }
  return value
}

function translateDocument(): void {
  if (isTranslating) return
  isTranslating = true
  try {
    translateTextNodes(document.body)
    translateAttributes(document.body)
  } finally {
    isTranslating = false
  }
}

function scheduleTranslate(): void {
  if (translateScheduled) return
  translateScheduled = true
  window.requestAnimationFrame(() => {
    translateScheduled = false
    translateDocument()
  })
}

function translateTextNodes(root: HTMLElement): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const nodes: Text[] = []
  while (walker.nextNode()) {
    const node = walker.currentNode as Text
    if (node.parentElement?.closest('script,style,code,pre')) continue
    nodes.push(node)
  }
  for (const node of nodes) {
    const current = node.nodeValue || ''
    const translated = translateText(current)
    if (translated !== current) {
      node.nodeValue = translated
    }
  }
}

function translateAttributes(root: HTMLElement): void {
  const elements = root.querySelectorAll<HTMLElement>('[placeholder],[title],[aria-label]')
  for (const element of elements) {
    for (const attr of ['placeholder', 'title', 'aria-label']) {
      const value = element.getAttribute(attr)
      if (!value) continue
      const translated = translateText(value)
      if (translated !== value) {
        element.setAttribute(attr, translated)
      }
    }
  }
}

function preserveWhitespace(original: string, translated: string): string {
  const prefix = original.match(/^\s*/)?.[0] || ''
  const suffix = original.match(/\s*$/)?.[0] || ''
  return `${prefix}${translated}${suffix}`
}
