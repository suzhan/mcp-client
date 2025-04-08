<template>
  <div class="not-found">
    <h1>{{ $t('notFound.title') }}</h1>
    <p>{{ $t('notFound.message') }}</p>
    <router-link to="/">{{ $t('notFound.backToHome') }}</router-link>
  </div>
</template>

<script setup lang="ts">
// NotFound 组件逻辑
</script>

<style scoped>
.not-found {
  text-align: center;
  margin-top: 50px;
}
h1 {
  font-size: 2em;
  margin-bottom: 20px;
}
a {
  color: #1976d2;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
</style> 