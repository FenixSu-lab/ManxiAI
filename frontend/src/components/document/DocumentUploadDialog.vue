<template>
  <el-dialog v-model="dialogVisible" title="Upload Document" width="620px" @close="resetForm">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="Document name" prop="name"><el-input v-model="form.name" placeholder="Default: file name" /></el-form-item>
      <el-form-item label="Document type" prop="type">
        <el-select v-model="form.type" style="width: 100%">
          <el-option label="General" value="base" /><el-option label="Markdown" value="markdown" /><el-option label="Text" value="text" /><el-option label="Table" value="table" />
        </el-select>
      </el-form-item>
      <el-form-item label="File" prop="file">
        <el-upload ref="uploadRef" drag :auto-upload="false" :show-file-list="true" :limit="1" :before-upload="beforeUpload" :on-change="handleFileChange" :on-remove="handleFileRemove">
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">Drop a file here, or click to select</div>
          <template #tip><div class="el-upload__tip">PDF, Word, Excel, TXT, and Markdown are supported. Max size: 50MB.</div></template>
        </el-upload>
      </el-form-item>
      <el-form-item label="Hit handling" prop="hit_handling_method">
        <el-radio-group v-model="form.hit_handling_method"><el-radio label="optimization">Optimize answer</el-radio><el-radio label="directly_return">Return direct hit</el-radio></el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.hit_handling_method === 'directly_return'" label="Direct return threshold" prop="directly_return_similarity">
        <el-slider v-model="form.directly_return_similarity" :min="0" :max="1" :step="0.05" show-input />
      </el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">Cancel</el-button><el-button type="primary" :loading="uploading" @click="handleUpload">Upload</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile, type UploadInstance, type UploadRawFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadDocument } from '@/api/knowledge-base'
import { getApiErrorMessage } from '@/utils/api'
const props = defineProps<{ modelValue: boolean; knowledgeBaseId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; success: [] }>()
const dialogVisible = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const uploading = ref(false)
const form = ref({ name: '', type: 'base', file: null as File | null, hit_handling_method: 'optimization', directly_return_similarity: 0.9 })
const rules: FormRules = { type: [{ required: true, message: 'Select a document type', trigger: 'change' }], file: [{ required: true, message: 'Select a file', trigger: 'change' }] }
const allowedTypes = new Set(['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain', 'text/markdown'])
const validateFile = (file: File) => { if (file.type && !allowedTypes.has(file.type)) { ElMessage.error('Unsupported file type'); return false } if (file.size > 50 * 1024 * 1024) { ElMessage.error('File size must be below 50MB'); return false } return true }
const beforeUpload = (file: UploadRawFile) => validateFile(file)
const handleFileChange = (file: UploadFile) => { const rawFile = file.raw; if (!rawFile || !validateFile(rawFile)) { uploadRef.value?.clearFiles(); form.value.file = null; return } form.value.file = rawFile; if (!form.value.name) form.value.name = rawFile.name; formRef.value?.validateField('file') }
const handleFileRemove = () => { form.value.file = null }
const handleUpload = async () => { if (!formRef.value) return; await formRef.value.validate(); if (!form.value.file) { ElMessage.error('Select a file'); return } uploading.value = true; try { const formData = new FormData(); formData.append('file', form.value.file); if (form.value.name) formData.append('name', form.value.name); formData.append('type', form.value.type); formData.append('hit_handling_method', form.value.hit_handling_method); formData.append('directly_return_similarity', String(form.value.directly_return_similarity)); await uploadDocument(props.knowledgeBaseId, formData); ElMessage.success('Document uploaded. Parsing and embedding are running in the background.'); dialogVisible.value = false; emit('success') } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Upload failed')) } finally { uploading.value = false } }
const resetForm = () => { form.value = { name: '', type: 'base', file: null, hit_handling_method: 'optimization', directly_return_similarity: 0.9 }; formRef.value?.resetFields(); uploadRef.value?.clearFiles() }
watch(dialogVisible, (visible) => { if (!visible) resetForm() })
</script>
<style scoped>.el-upload__tip { color: #6b7280; font-size: 12px; }</style>
