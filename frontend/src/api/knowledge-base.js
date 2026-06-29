/**
 * 知识库管理API
 */
import api from '@/utils/api'

// 知识库相关API
export const getKnowledgeBases = (params) => {
  return api({
    url: '/knowledge-bases/',
    method: 'get',
    params
  })
}

export const getKnowledgeBase = (id) => {
  return api({
    url: `/knowledge-bases/${id}/`,
    method: 'get'
  })
}

export const createKnowledgeBase = (data) => {
  return api({
    url: '/knowledge-bases/',
    method: 'post',
    data
  })
}

export const updateKnowledgeBase = (id, data) => {
  return api({
    url: `/knowledge-bases/${id}/`,
    method: 'put',
    data
  })
}

export const deleteKnowledgeBase = (id) => {
  return api({
    url: `/knowledge-bases/${id}/`,
    method: 'delete'
  })
}

// 文档相关API
export const getDocuments = (knowledgeBaseId, params) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/`,
    method: 'get',
    params
  })
}

export const getDocument = (knowledgeBaseId, documentId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/`,
    method: 'get'
  })
}

export const createDocument = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/`,
    method: 'post',
    data
  })
}

export const updateDocument = (knowledgeBaseId, documentId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/`,
    method: 'put',
    data
  })
}

export const deleteDocument = (knowledgeBaseId, documentId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/`,
    method: 'delete'
  })
}

// 文档上传
export const uploadDocument = (knowledgeBaseId, formData) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/upload/`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 创建Web文档
export const createWebDocument = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/create-web/`,
    method: 'post',
    data
  })
}

// 创建问答文档
export const createQADocument = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/create-qa/`,
    method: 'post',
    data
  })
}

// 重新处理文档
export const reprocessDocument = (knowledgeBaseId, documentId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/reprocess/`,
    method: 'post'
  })
}

// 批量操作文档
export const batchOperateDocuments = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/batch/`,
    method: 'post',
    data
  })
}

// 搜索文档
export const searchDocuments = (knowledgeBaseId, params) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/search/`,
    method: 'get',
    params
  })
}

// 获取文档统计
export const getDocumentStats = (knowledgeBaseId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/stats/`,
    method: 'get'
  })
}

// 获取文档段落
export const getDocumentParagraphs = (knowledgeBaseId, documentId, params) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/paragraphs/`,
    method: 'get',
    params
  })
}

// 获取文档处理任务
export const getDocumentTasks = (knowledgeBaseId, documentId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/tasks/`,
    method: 'get'
  })
}

// 段落相关API
export const getParagraphs = (documentId, params) => {
  return api({
    url: `/documents/${documentId}/paragraphs/`,
    method: 'get',
    params
  })
}

export const getParagraph = (documentId, paragraphId) => {
  return api({
    url: `/documents/${documentId}/paragraphs/${paragraphId}/`,
    method: 'get'
  })
}

export const createParagraph = (documentId, data) => {
  return api({
    url: `/documents/${documentId}/paragraphs/`,
    method: 'post',
    data
  })
}

export const updateParagraph = (documentId, paragraphId, data) => {
  return api({
    url: `/documents/${documentId}/paragraphs/${paragraphId}/`,
    method: 'patch',
    data
  })
}

export const deleteParagraph = (documentId, paragraphId) => {
  return api({
    url: `/documents/${documentId}/paragraphs/${paragraphId}/`,
    method: 'delete'
  })
}

// 切换段落激活状态
export const toggleParagraphActive = (documentId, paragraphId) => {
  return api({
    url: `/documents/${documentId}/paragraphs/${paragraphId}/toggle-active/`,
    method: 'post'
  })
}

// 问题相关API
export const getProblems = (knowledgeBaseId, params) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/`,
    method: 'get',
    params
  })
}

export const getProblem = (knowledgeBaseId, problemId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/${problemId}/`,
    method: 'get'
  })
}

export const createProblem = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/`,
    method: 'post',
    data
  })
}

export const updateProblem = (knowledgeBaseId, problemId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/${problemId}/`,
    method: 'put',
    data
  })
}

export const deleteProblem = (knowledgeBaseId, problemId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/${problemId}/`,
    method: 'delete'
  })
}

// 搜索问题
export const searchProblems = (knowledgeBaseId, params) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/problems/search/`,
    method: 'get',
    params
  })
}

// 知识库分享相关API
export const shareKnowledgeBase = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/share/`,
    method: 'post',
    data
  })
}

export const unshareKnowledgeBase = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/unshare/`,
    method: 'delete',
    data
  })
}

export const getKnowledgeBaseShares = (knowledgeBaseId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/shares/`,
    method: 'get'
  })
}

export const searchUsers = (params) => {
  return api({
    url: '/auth/users/search/',
    method: 'get',
    params
  })
}

// 获取公开的知识库
export const getPublicKnowledgeBases = (params) => {
  return api({
    url: '/knowledge-bases/public/',
    method: 'get',
    params
  })
}

// 获取分享给我的知识库
export const getSharedKnowledgeBases = (params) => {
  return api({
    url: '/knowledge-bases/shared-with-me/',
    method: 'get',
    params
  })
}

// 知识库设置相关API
export const getKnowledgeBaseSettings = (knowledgeBaseId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/kb_settings/`,
    method: 'get'
  })
}

export const updateKnowledgeBaseSettings = (knowledgeBaseId, data) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/kb_settings/`,
    method: 'put',
    data
  })
}

// 更新知识库统计信息
export const updateKnowledgeBaseStats = (knowledgeBaseId) => {
  return api({
    url: `/knowledge-bases/${knowledgeBaseId}/update_stats/`,
    method: 'post'
  })
} 
