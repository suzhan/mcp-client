<template>
  <v-menu>
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        icon
        variant="text"
        size="small"
      >
        <v-icon>mdi-translate</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="locale in availableLocales"
        :key="locale.code"
        :value="locale.code"
        @click="changeLocale(locale.code)"
      >
        <v-list-item-title>{{ locale.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
  
  <!-- 语言切换中的加载指示器 -->
  <v-dialog
    v-model="loading"
    persistent
    width="300"
  >
    <v-card>
      <v-card-text class="pt-4">
        {{ $t('common.loading') }}
        <v-progress-linear
          indeterminate
          color="primary"
          class="mt-2"
        ></v-progress-linear>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { availableLocales } from '../locales';
import { setLocale } from '../i18n';
import { type SupportedLocales } from '../types/i18n';

const loading = ref(false);

const changeLocale = async (locale: SupportedLocales) => {
  loading.value = true;
  try {
    // 更新前端语言并同步到后端
    await setLocale(locale, true);
  } catch (error) {
    console.error('语言切换失败:', error);
  } finally {
    loading.value = false;
  }
};
</script> 