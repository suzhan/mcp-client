import { createI18n } from 'vue-i18n';
import { messages, defaultLocale } from './locales';
import i18nService from './api/i18nService';
import { type SupportedLocales } from './types/i18n';

// 从localStorage获取保存的语言，如果没有则使用默认语言
const savedLocale = localStorage.getItem('locale') as SupportedLocales || defaultLocale;

// 创建i18n实例
const i18n = createI18n({
  legacy: false, // 使用组合式API模式
  locale: savedLocale,
  fallbackLocale: defaultLocale,
  messages,
  silentTranslationWarn: true,  // 在生产环境中隐藏翻译警告
  silentFallbackWarn: true      // 在生产环境中隐藏回退警告
});

// 语言变更函数
export const setLocale = async (locale: SupportedLocales, syncWithBackend: boolean = false) => {
  // 更新前端语言
  i18n.global.locale.value = locale;
  localStorage.setItem('locale', locale);
  document.querySelector('html')?.setAttribute('lang', locale);
  
  // 同步到后端
  if (syncWithBackend) {
    try {
      await i18nService.setCurrentLanguage(locale);
    } catch (error) {
      console.error('同步语言到后端失败:', error);
    }
  }
};

// 从后端同步语言
export const syncLocaleFromBackend = async (): Promise<void> => {
  try {
    const backendLocale = await i18nService.getCurrentLanguage();
    if (backendLocale && backendLocale !== i18n.global.locale.value) {
      await setLocale(backendLocale as SupportedLocales);
    }
  } catch (error) {
    console.error('从后端获取语言设置失败:', error);
  }
};

export default i18n; 