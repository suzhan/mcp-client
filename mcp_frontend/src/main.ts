import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import i18n, { syncLocaleFromBackend } from './i18n';

// Vuetify
import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { aliases, mdi } from 'vuetify/iconsets/mdi';
import '@mdi/font/css/materialdesignicons.css'; // 导入MDI图标字体

// 创建Vuetify实例
const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'light',
  },
});

// 创建Pinia状态管理
const pinia = createPinia();

// 创建Vue应用
const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(vuetify);
app.use(i18n);

// 设置语言
document.querySelector('html')?.setAttribute('lang', i18n.global.locale.value);

// 尝试从后端同步语言设置
syncLocaleFromBackend().finally(() => {
  // 无论同步成功与否，都挂载应用
  app.mount('#app');
}); 