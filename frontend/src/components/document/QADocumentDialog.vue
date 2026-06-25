<template>
  <el-dialog v-model="dialogVisible" title="New QA Document" width="820px" @close="resetForm">
    <el-form ref="formRef" :model="form" label-position="top">
      <el-form-item label="Document name"><el-input v-model="form.name" placeholder="Example: FAQ" /></el-form-item>
      <div class="qa-list"><div v-for="(pair, index) in form.qa_pairs" :key="index" class="qa-item"><div class="qa-item__header"><strong>QA pair {{ index + 1 }}</strong><el-button v-if="form.qa_pairs.length > 1" text type="danger" @click="removePair(index)">Remove</el-button></div><el-form-item label="Question" :prop="`qa_pairs.${index}.question`" :rules="[{ required: true, message: 'Enter a question', trigger: 'blur' }]"><el-input v-model="pair.question" type="textarea" :rows="2" placeholder="Question" /></el-form-item><el-form-item label="Answer" :prop="`qa_pairs.${index}.answer`" :rules="[{ required: true, message: 'Enter an answer', trigger: 'blur' }]"><el-input v-model="pair.answer" type="textarea" :rows="4" placeholder="Answer" /></el-form-item></div></div>
      <el-button class="add-button" @click="addPair"><el-icon><Plus /></el-icon>Add QA pair</el-button>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">Cancel</el-button><el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { createQADocument } from '@/api/knowledge-base'
import { getApiErrorMessage } from '@/utils/api'
interface QAPair { question: string; answer: string }
const props = defineProps<{ modelValue: boolean; knowledgeBaseId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; success: [] }>()
const dialogVisible = computed({ get: () => props.modelValue, set: (value: boolean) => emit('update:modelValue', value) })
const formRef = ref<FormInstance>()
const creating = ref(false)
const form = ref<{ name: string; qa_pairs: QAPair[] }>({ name: '', qa_pairs: [{ question: '', answer: '' }] })
const addPair = () => form.value.qa_pairs.push({ question: '', answer: '' })
const removePair = (index: number) => form.value.qa_pairs.splice(index, 1)
const handleCreate = async () => { if (!formRef.value) return; await formRef.value.validate(); const qaPairs = form.value.qa_pairs.map((pair) => ({ question: pair.question.trim(), answer: pair.answer.trim() })).filter((pair) => pair.question && pair.answer); if (qaPairs.length === 0) { ElMessage.error('Add at least one valid QA pair'); return } creating.value = true; try { await createQADocument(props.knowledgeBaseId, { name: form.value.name.trim(), qa_pairs: qaPairs }); ElMessage.success('QA document created. Embedding is running in the background.'); dialogVisible.value = false; emit('success') } catch (error) { ElMessage.error(getApiErrorMessage(error, 'Failed to create QA document')) } finally { creating.value = false } }
const resetForm = () => { form.value = { name: '', qa_pairs: [{ question: '', answer: '' }] }; formRef.value?.resetFields() }
watch(dialogVisible, (visible) => { if (!visible) resetForm() })
</script>
<style scoped lang="scss">.qa-list { display: flex; flex-direction: column; gap: 14px; max-height: 55vh; overflow-y: auto; padding-right: 4px; }.qa-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; background: #f9fafb; }.qa-item__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }.add-button { width: 100%; margin-top: 14px; }</style>
