<template>
  <el-dialog v-model="dialogVisible" title="Create Web Document" width="620px" @close="resetForm">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="Page URL" prop="url"><el-input v-model="form.url" placeholder="https://example.com/article" /></el-form-item>
      <el-form-item label="Document name"><el-input v-model="form.name" placeholder="Default: page URL" /></el-form-item>
      <el-form-item label="CSS selector"><el-input v-model="form.selector" type="textarea" :rows="2" placeholder="Optional, such as article, .content, #main" /><div class="form-tip">Leave empty to extract paragraph, div, and article text.</div></el-form-item>
      <el-form-item label="Crawl depth" prop="depth"><el-input-number v-model="form.depth" :min="1" :max="3" /><div class="form-tip">Depth 1 crawls the current page only. Higher values follow same-domain links with limits.</div></el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">Cancel</el-button><el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createWebDocument } from '@/api/knowledge-base'
import { getApiErrorMessage } from '@/utils/api'
const props = defineProps<{ modelValue: boolean; knowledgeBaseId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; success: [] }>()
const dialogVisible = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })
const formRef = ref<FormInstance>()
const creating = ref(false)
const form = ref({ url: '', name: '', selector: '', depth: 1 })
const rules: FormRules = { url: [{ required: true, message: 'Enter a page URL', trigger: 'blur' }, { type: 'url', message: 'Enter a valid URL', trigger: 'blur' }], depth: [{ required: true, message: 'Select crawl depth', trigger: 'change' }] }
const handleCreate = async () => { if (!formRef.value) return; await formRef.value.validate(); creating.value = true; try { await createWebDocument(props.knowledgeBaseId, { url: form.value.url.trim(), name: form.value.name.trim(), selector: form.value.selector.trim(), depth: form.value.depth }); ElMessage.success('Web document created. Crawling and embedding are running in the background.'); dialogVisible.value = false; emit('success') } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Failed to create web document')) } finally { creating.value = false } }
const resetForm = () => { form.value = { url: '', name: '', selector: '', depth: 1 }; formRef.value?.resetFields() }
watch(dialogVisible, (visible) => { if (!visible) resetForm() })
</script>
<style scoped>.form-tip { margin-top: 4px; color: #6b7280; font-size: 12px; }</style>
