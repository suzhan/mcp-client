/// <reference types="vite/client" />

// 声明Vue单文件组件类型
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 声明导入元数据类型
interface ImportMeta {
  readonly env: Record<string, string>
} 