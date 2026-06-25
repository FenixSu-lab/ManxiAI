<!--
  Not-found page for unmatched routes.
-->
<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-code">404</div>
      <div class="error-message">Page not found</div>
      <div class="error-description">
        The page you requested does not exist or has been removed.
      </div>
      <div class="error-actions">
        <el-button type="primary" @click="$router.push('/')">Go home</el-button>
        <el-button @click="$router.back()">Go back</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Static 404 page.
</script>

<style lang="scss" scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at center, rgba(37, 99, 235, 0.12), transparent 36%),
    #f5f7fb;
}

.error-content {
  text-align: center;
  background: #fff;
  border-radius: 20px;
  padding: 48px 56px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);

  .error-code {
    font-size: 120px;
    font-weight: 800;
    color: #2563eb;
    line-height: 1;
    margin-bottom: 20px;
  }

  .error-message {
    font-size: 24px;
    color: #111827;
    margin-bottom: 12px;
    font-weight: 700;
  }

  .error-description {
    font-size: 16px;
    color: #667085;
    margin-bottom: 32px;
  }

  .error-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
  }
}
</style>
