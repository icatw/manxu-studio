'use client'

import { useSyncExternalStore } from 'react'

export type TextProviderId = 'demo' | 'deepseek' | 'qwen' | 'openai-compatible'
export type ImageProviderId = 'demo' | 'wanx' | 'openai-compatible'

interface ProviderPreset {
  label: string
  description: string
  models: string[]
  defaultBaseUrl: string
  /** Server-side env var that must hold the API key. Keys never live in the browser. */
  apiKeyEnv: string | null
}

export const TEXT_PROVIDERS: Record<TextProviderId, ProviderPreset> = {
  demo: {
    label: '本地演示模板',
    description: '不调用模型，返回内置的结构化示例剧本',
    models: ['demo-template'],
    defaultBaseUrl: '',
    apiKeyEnv: null,
  },
  deepseek: {
    label: 'DeepSeek',
    description: '适合中文剧本与分镜结构化输出',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    defaultBaseUrl: 'https://api.deepseek.com/v1',
    apiKeyEnv: 'DEEPSEEK_API_KEY',
  },
  qwen: {
    label: '通义千问',
    description: '阿里云百炼 DashScope 兼容模式',
    models: ['qwen-plus', 'qwen-max', 'qwen-turbo'],
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    apiKeyEnv: 'DASHSCOPE_API_KEY',
  },
  'openai-compatible': {
    label: 'OpenAI 兼容接口',
    description: '任何兼容 /chat/completions 的服务',
    models: [],
    defaultBaseUrl: '',
    apiKeyEnv: 'CUSTOM_LLM_API_KEY',
  },
}

export const IMAGE_PROVIDERS: Record<ImageProviderId, ProviderPreset> = {
  demo: {
    label: '前端演示',
    description: '模拟异步任务与进度，返回本地示例图片',
    models: ['demo-placeholder'],
    defaultBaseUrl: '',
    apiKeyEnv: null,
  },
  wanx: {
    label: '通义万相',
    description: '阿里云异步图像生成，支持参考图',
    models: ['wan2.2-t2i-plus', 'wan2.2-t2i-flash', 'wanx2.1-t2i-turbo'],
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/api/v1',
    apiKeyEnv: 'DASHSCOPE_API_KEY',
  },
  'openai-compatible': {
    label: 'OpenAI 兼容接口',
    description: '任何兼容 /images/generations 的服务',
    models: [],
    defaultBaseUrl: '',
    apiKeyEnv: 'CUSTOM_IMAGE_API_KEY',
  },
}

export interface ModelSettings {
  text: {
    provider: TextProviderId
    model: string
    baseUrl: string
    temperature: number
  }
  image: {
    provider: ImageProviderId
    model: string
    baseUrl: string
    concurrency: number
    negativePrompt: string
  }
}

export const DEFAULT_MODEL_SETTINGS: ModelSettings = {
  text: { provider: 'deepseek', model: 'deepseek-chat', baseUrl: 'https://api.deepseek.com/v1', temperature: 0.8 },
  image: {
    provider: 'wanx',
    model: 'wan2.2-t2i-flash',
    baseUrl: '',
    concurrency: 2,
    negativePrompt: 'text, watermark, signature, extra fingers, deformed hands',
  },
}

export const CONCURRENCY_RANGE = { min: 1, max: 4 } as const

const STORAGE_KEY = 'comic-studio:model-settings'
const listeners = new Set<() => void>()
let cached: ModelSettings | null = null

function clampConcurrency(value: number) {
  if (!Number.isFinite(value)) return DEFAULT_MODEL_SETTINGS.image.concurrency
  return Math.min(CONCURRENCY_RANGE.max, Math.max(CONCURRENCY_RANGE.min, Math.round(value)))
}

function normalize(raw: unknown): ModelSettings {
  const value = (raw ?? {}) as Partial<ModelSettings>
  const text = { ...DEFAULT_MODEL_SETTINGS.text, ...value.text }
  const image = { ...DEFAULT_MODEL_SETTINGS.image, ...value.image }
  if (!(text.provider in TEXT_PROVIDERS)) text.provider = 'demo'
  if (!(image.provider in IMAGE_PROVIDERS)) image.provider = 'demo'
  text.temperature = Math.min(2, Math.max(0, Number(text.temperature) || 0))
  image.concurrency = clampConcurrency(Number(image.concurrency))
  return { text, image }
}

function read(): ModelSettings {
  if (cached) return cached
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    cached = raw ? normalize(JSON.parse(raw)) : DEFAULT_MODEL_SETTINGS
  } catch {
    cached = DEFAULT_MODEL_SETTINGS
  }
  return cached
}

export function saveModelSettings(next: ModelSettings) {
  cached = normalize(next)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cached))
  } catch {
    // Storage may be unavailable (private mode); settings still apply for this session.
  }
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useModelSettings() {
  return useSyncExternalStore(subscribe, read, () => DEFAULT_MODEL_SETTINGS)
}

export function getModelSettings() {
  return read()
}

export function describeModel(settings: ModelSettings, kind: 'text' | 'image') {
  const config = settings[kind]
  const preset = kind === 'text' ? TEXT_PROVIDERS[settings.text.provider] : IMAGE_PROVIDERS[settings.image.provider]
  return config.provider === 'demo' ? preset.label : `${preset.label} · ${config.model || '未填写模型'}`
}
