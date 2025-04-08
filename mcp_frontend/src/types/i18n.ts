// 定义支持的语言类型
export type SupportedLocales = 'en-US' | 'zh-CN';

// 扩展Window接口，添加Vue-i18n需要的类型
declare module 'vue-i18n' {
  // 定义消息模式，确保类型安全
  export interface DefineLocaleMessage {
    common: {
      appName: string;
      ok: string;
      cancel: string;
      save: string;
      delete: string;
      edit: string;
      add: string;
      create: string;
      refresh: string;
      loading: string;
      search: string;
      noData: string;
      error: string;
      success: string;
      warning: string;
      info: string;
    };
    menu: {
      home: string;
      servers: string;
      providers: string;
      settings: string;
      newChat: string;
      chat: string;
      configManagement: string;
      sessions: string;
    };
    servers: {
      title: string;
      addServer: string;
      editServer: string;
      deleteServer: string;
      serverName: string;
      serverUrl: string;
      serverType: string;
      serverStatus: string;
      connectionStatus: string;
      connected: string;
      disconnected: string;
      connecting: string;
      errorConnecting: string;
      stdioServer: string;
      httpServer: string;
      sseServer: string;
      command: string;
      arguments: string;
      environmentVariables: string;
      deleteConfirm: string;
      testing: string;
      testSuccess: string;
      testFailed: string;
    };
    providers: {
      title: string;
      addProvider: string;
      editProvider: string;
      deleteProvider: string;
      providerName: string;
      apiKey: string;
      apiUrl: string;
      defaultModel: string;
      models: string;
      deleteConfirm: string;
      testing: string;
      testSuccess: string;
      testFailed: string;
    };
    chat: {
      newChat: string;
      title: string;
      send: string;
      typing: string;
      regenerate: string;
      clear: string;
      copyToClipboard: string;
      copiedToClipboard: string;
      deleteMessage: string;
      selectServer: string;
      selectProvider: string;
      selectModel: string;
      sessionName: string;
      saveSession: string;
      loadingTools: string;
      loadingResources: string;
      noToolsAvailable: string;
      noResourcesAvailable: string;
      executingTool: string;
      toolExecutionResult: string;
      approveToolExecution: string;
      denyToolExecution: string;
      toolRequestedBy: string;
      with: string;
    };
    settings: {
      title: string;
      language: string;
      theme: string;
      dark: string;
      light: string;
      advanced: string;
      logging: string;
      debugMode: string;
      clearCache: string;
      clearCacheConfirm: string;
      restartRequired: string;
    };
    errors: {
      connectionFailed: string;
      authenticationFailed: string;
      serverError: string;
      clientError: string;
      networkError: string;
      unknownError: string;
      invalidInput: string;
      missingRequiredField: string;
      timeoutError: string;
      serviceUnavailable: string;
      tooManyRequests: string;
      permissionDenied: string;
    };
    notFound: {
      title: string;
      message: string;
      backToHome: string;
    };
  }
} 