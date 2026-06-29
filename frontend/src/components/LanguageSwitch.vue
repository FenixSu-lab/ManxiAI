<!--
  Global language switcher for English and Chinese UI text.
-->
<template>
  <el-button class="language-switch" size="small" @click="toggleLanguage">
    {{ languageState.current === 'zh' ? 'English' : '中文' }}
  </el-button>
</template>

<script setup lang="ts">
import { languageState, toggleLanguage } from '@/utils/i18n'
</script>

<style scoped>
.language-switch {
  font-weight: 700;
}
</style>
