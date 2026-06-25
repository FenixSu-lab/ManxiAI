<template>
  <el-dialog
    v-model="dialogVisible"
    title="知识库设置"
    width="600px"
    @close="resetForm"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="知识库名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入知识库名称" />
      </el-form-item>
      
      <el-form-item label="描述" prop="description">
        <el-input 
          v-model="form.description" 
          type="textarea" 
          :rows="3"
          placeholder="请输入知识库描述"
        />
      </el-form-item>
      
      <el-form-item label="是否公开" prop="is_public">
        <el-switch 
          v-model="form.is_public"
          active-text="公开"
          inactive-text="私有"
        />
        <div class="form-tip">
          公开的知识库可以被其他用户搜索和访问
        </div>
      </el-form-item>
      
      <el-form-item label="标签" prop="tags">
        <el-tag
          v-for="tag in form.tags"
          :key="tag"
          closable
          @close="removeTag(tag)"
          style="margin-right: 8px; margin-bottom: 8px;"
        >
          {{ tag }}
        </el-tag>
        <el-input
          v-if="inputVisible"
          ref="inputRef"
          v-model="inputValue"
          size="small"
          style="width: 120px;"
          @keyup.enter="handleInputConfirm"
          @blur="handleInputConfirm"
        />
        <el-button v-else size="small" @click="showInput">
          <el-icon><Plus /></el-icon>
          添加标签
        </el-button>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { updateKnowledgeBase } from '@/api/knowledge-base'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  knowledgeBase: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'updated'])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const formRef = ref()
const inputRef = ref()
const saving = ref(false)
const inputVisible = ref(false)
const inputValue = ref('')

const form = ref({
  name: '',
  description: '',
  is_public: false,
  tags: []
})

const rules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 100, message: '名称长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  description: [
    { max: 500, message: '描述长度不能超过 500 个字符', trigger: 'blur' }
  ]
}

const removeTag = (tag) => {
  form.value.tags.splice(form.value.tags.indexOf(tag), 1)
}

const showInput = () => {
  inputVisible.value = true
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const handleInputConfirm = () => {
  if (inputValue.value) {
    if (!form.value.tags.includes(inputValue.value)) {
      form.value.tags.push(inputValue.value)
    }
  }
  inputVisible.value = false
  inputValue.value = ''
}

const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    saving.value = true
    
    await updateKnowledgeBase(props.knowledgeBase.id, form.value)
    
    ElMessage.success('知识库设置保存成功')
    dialogVisible.value = false
    emit('updated')
    
  } catch (error) {
    ElMessage.error('知识库设置保存失败')
  } finally {
    saving.value = false
  }
}

const resetForm = () => {
  if (props.knowledgeBase) {
    form.value = {
      name: props.knowledgeBase.name || '',
      description: props.knowledgeBase.description || '',
      is_public: props.knowledgeBase.is_public || false,
      tags: [...(props.knowledgeBase.tags || [])]
    }
  }
  
  inputVisible.value = false
  inputValue.value = ''
  
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

watch(() => props.knowledgeBase, (newKnowledgeBase) => {
  if (newKnowledgeBase) {
    form.value = {
      name: newKnowledgeBase.name || '',
      description: newKnowledgeBase.description || '',
      is_public: newKnowledgeBase.is_public || false,
      tags: [...(newKnowledgeBase.tags || [])]
    }
  }
}, { immediate: true })

watch(dialogVisible, (newVal) => {
  if (newVal) {
    resetForm()
  }
})
</script>

<style scoped>
.form-tip {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}
</style> 