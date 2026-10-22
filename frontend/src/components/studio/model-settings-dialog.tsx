import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ImageIcon, KeyRound, LoaderCircle, Save, ScrollText, Sparkles, Wifi } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api, toApiError } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

type ModelMode = components['schemas']['ModelMode']
type ImageBackend = NonNullable<components['schemas']['ModelConfigUpdate']['image_backend']>

const MODE_OPTIONS: { id: ModelMode; label: string; hint: string }[] = [
  { id: 'platform', label: '默认（平台 Agnes）', hint: '使用漫序托管模型，消耗试用额度；无需填写密钥。' },
  { id: 'byok_qwen', label: '自备通义百炼', hint: '使用你的百炼 API Key（文本 + Qwen Image）。' },
  { id: 'byok_agnes', label: '自备 Agnes', hint: '使用你自己的 Agnes API Key；不扣平台额度。' },
]

export function ModelSettingsPanel() {
  const queryClient = useQueryClient()
  const [modelMode, setModelMode] = useState<ModelMode>('platform')
  const [textModel, setTextModel] = useState('')
  const [textBaseUrl, setTextBaseUrl] = useState('')
  const [textKey, setTextKey] = useState('')
  const [imageBackend, setImageBackend] = useState<ImageBackend>('qwen_async')
  const [imageModel, setImageModel] = useState('')
  const [imageBaseUrl, setImageBaseUrl] = useState('')
  const [imageKey, setImageKey] = useState('')
  const [clearTextKey, setClearTextKey] = useState(false)
  const [clearImageKey, setClearImageKey] = useState(false)
  const [notice, setNotice] = useState<{ success: boolean; message: string } | null>(null)

  const query = useQuery({
    queryKey: ['model-config'],
    queryFn: async () => {
      const { data, error } = await api.GET('/model-config')
      if (error || !data) throw toApiError(error, '无法读取模型配置')
      return data
    },
  })

  useEffect(() => {
    if (!query.data) return
    setModelMode(query.data.model_mode)
    setTextModel(query.data.text_model)
    setTextBaseUrl(query.data.text_base_url)
    setImageBackend(query.data.image_backend)
    setImageModel(query.data.image_model)
    setImageBaseUrl(query.data.image_base_url)
    setTextKey('')
    setImageKey('')
    setClearTextKey(false)
    setClearImageKey(false)
  }, [query.data])

  const isByok = modelMode === 'byok_qwen' || modelMode === 'byok_agnes'
  const modelsForBackend = useMemo(() => {
    const backends = query.data?.image_backends ?? []
    const match = backends.find((item) => item.id === imageBackend)
    return match?.models ?? query.data?.image_models ?? []
  }, [query.data, imageBackend])

  useEffect(() => {
    if (!isByok || !modelsForBackend.length) return
    if (!modelsForBackend.includes(imageModel)) {
      setImageModel(modelsForBackend[0] ?? '')
    }
  }, [modelsForBackend, imageModel, isByok])

  useEffect(() => {
    if (modelMode === 'byok_qwen') setImageBackend('qwen_async')
    if (modelMode === 'byok_agnes') setImageBackend('openai_images')
  }, [modelMode])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: components['schemas']['ModelConfigUpdate'] = { model_mode: modelMode }
      if (isByok) {
        body.text_model = textModel.trim()
        body.text_base_url = textBaseUrl.trim()
        body.image_backend = imageBackend
        body.image_model = imageModel
        body.image_base_url = imageBaseUrl.trim()
        if (textKey.trim()) body.text_api_key = textKey
        else if (clearTextKey) body.text_api_key = null
        if (imageKey.trim()) body.image_api_key = imageKey
        else if (clearImageKey) body.image_api_key = null
      }
      const { data, error } = await api.PUT('/model-config', { body })
      if (error || !data) throw toApiError(error, '保存模型配置失败，请检查填写内容')
      return data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['model-config'], data)
      setTextKey('')
      setImageKey('')
      setClearTextKey(false)
      setClearImageKey(false)
      setNotice({ success: true, message: '模型配置已保存' })
    },
    onError: (error) => setNotice({ success: false, message: error.message }),
  })

  const testMutation = useMutation({
    mutationFn: async () => {
      await saveMutation.mutateAsync()
      const { data, error } = await api.POST('/model-config/test')
      if (error || !data) throw toApiError(error, '文本模型连接测试请求失败')
      return data
    },
    onSuccess: (data) => {
      setNotice({ success: data.success, message: data.latency_ms ? `${data.message} · ${data.latency_ms} ms` : data.message })
      void queryClient.invalidateQueries({ queryKey: ['model-config'] })
    },
    onError: (error) => setNotice({ success: false, message: error.message }),
  })

  const testImageMutation = useMutation({
    mutationFn: async () => {
      await saveMutation.mutateAsync()
      const { data, error } = await api.POST('/model-config/test-image')
      if (error || !data) throw toApiError(error, '图像模型连接测试请求失败')
      return data
    },
    onSuccess: (data) => {
      setNotice({ success: data.success, message: data.latency_ms ? `${data.message} · ${data.latency_ms} ms` : data.message })
      void queryClient.invalidateQueries({ queryKey: ['model-config'] })
    },
    onError: (error) => setNotice({ success: false, message: error.message }),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    setNotice(null)
    saveMutation.mutate()
  }

  function selectMode(mode: ModelMode) {
    if (mode === 'platform' && query.data && !query.data.platform_available) {
      setNotice({ success: false, message: '平台默认模型未启用，请选择自备通义或 Agnes' })
      return
    }
    setModelMode(mode)
    const preset = query.data?.system_presets.find((item) =>
      mode === 'byok_qwen' ? item.id === 'dashscope-default' : mode === 'byok_agnes' ? item.id === 'agnes-default' : false,
    )
    if (preset) {
      setTextModel(preset.text_model)
      setTextBaseUrl(preset.text_base_url)
      setImageBackend(preset.image_backend)
      setImageModel(preset.image_model)
      setImageBaseUrl(preset.image_base_url)
    }
  }

  const config = query.data
  const quota = config?.quota
  const backendHelp =
    imageBackend === 'openai_images'
      ? '当前后端使用 OpenAI 风格 `/images/generations`（同步出图）。'
      : '当前后端使用百炼异步 Image API；若地址以 `/compatible-mode/v1` 结尾，服务端会映射到该 Host 的 `/api/v1`。'

  return (
    <form onSubmit={submit} className="space-y-6">
      {query.isPending && <p className="text-sm text-muted-foreground">正在读取配置…</p>}
      {query.isError && <p role="alert" className="text-sm text-destructive">{query.error.message}</p>}
      {config && (
        <>
          <section className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles className="size-4" aria-hidden />
              模型模式
            </h3>
            <div className="grid gap-2" role="radiogroup" aria-label="模型模式">
              {MODE_OPTIONS.map((option) => {
                const disabled = option.id === 'platform' && !config.platform_available
                const selected = modelMode === option.id
                return (
                  <button
                    key={option.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    disabled={disabled}
                    onClick={() => selectMode(option.id)}
                    className={`rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                      selected ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/40'
                    } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    <span className="font-medium">{option.label}</span>
                    <p className="mt-0.5 text-xs text-muted-foreground">{option.hint}</p>
                  </button>
                )
              })}
            </div>
            {quota?.applies && (
              <p className="rounded-md border border-border/80 bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                今日剩余：文本 {quota.text_remaining ?? '不限'} 次 · 图像 {quota.image_remaining ?? '不限'} 张
                {quota.exhausted ? ' · 已用尽，请改用自备模型' : ''}
              </p>
            )}
          </section>

          {modelMode === 'platform' && (
            <p className="text-sm text-muted-foreground">
              当前使用平台 Agnes（{config.text_model} / {config.image_model}）。密钥由服务端托管，不会显示或下载到浏览器。
            </p>
          )}

          {isByok && (
            <>
              <section className="space-y-4">
                <h3 className="flex items-center gap-2 text-sm font-semibold">
                  <ScrollText className="size-4" aria-hidden />
                  文本模型 · OpenAI 兼容
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Base URL">
                    <Input required type="url" placeholder="https://api.example.com/v1" value={textBaseUrl} onChange={(event) => setTextBaseUrl(event.target.value)} />
                  </Field>
                  <Field label="模型 ID">
                    <Input required maxLength={160} placeholder="模型 ID" value={textModel} onChange={(event) => setTextModel(event.target.value)} />
                  </Field>
                  <Field label="API Key">
                    <SecretInput configured={config.text_api_key_configured} value={textKey} onChange={setTextKey} clear={clearTextKey} onClearChange={setClearTextKey} />
                  </Field>
                  <Status label="连接状态" value={statusLabel(config.text_status)} configured={config.text_status === 'connected'} />
                </div>
              </section>

              <section className="space-y-4 border-t pt-5">
                <h3 className="flex items-center gap-2 text-sm font-semibold">
                  <ImageIcon className="size-4" aria-hidden />
                  图像模型
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="图像后端">
                    <select
                      className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm"
                      value={imageBackend}
                      disabled
                      onChange={(event) => setImageBackend(event.target.value as ImageBackend)}
                    >
                      {config.image_backends.map((backend) => (
                        <option key={backend.id} value={backend.id}>
                          {backend.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="模型版本">
                    <select
                      className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm"
                      value={imageModel}
                      onChange={(event) => setImageModel(event.target.value)}
                    >
                      {modelsForBackend.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="图像服务 Base URL">
                    <Input required type="url" maxLength={2048} placeholder="https://api.example.com/v1" value={imageBaseUrl} onChange={(event) => setImageBaseUrl(event.target.value)} />
                  </Field>
                  <Field label="图像 API Key">
                    <SecretInput configured={config.image_api_key_configured} value={imageKey} onChange={setImageKey} clear={clearImageKey} onClearChange={setClearImageKey} />
                  </Field>
                  <Status label="配置状态" value={statusLabel(config.image_status)} configured={config.image_status === 'connected'} />
                </div>
                <p className="text-xs leading-5 text-muted-foreground">{backendHelp}</p>
              </section>
            </>
          )}
        </>
      )}
      {notice && (
        <p
          role="status"
          className={`rounded-md border px-3 py-2 text-sm ${notice.success ? 'border-success/30 bg-success/5 text-success' : 'border-destructive/30 bg-destructive/5 text-destructive'}`}
        >
          {notice.message}
        </p>
      )}
      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <KeyRound className="size-3.5" aria-hidden />
          密钥仅加密保存在服务端
        </span>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" disabled={!config || testMutation.isPending || testImageMutation.isPending || saveMutation.isPending} onClick={() => testMutation.mutate()}>
            {testMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Wifi />}
            测试文本连接
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={!config || testMutation.isPending || testImageMutation.isPending || saveMutation.isPending} onClick={() => testImageMutation.mutate()}>
            {testImageMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Wifi />}
            测试图像连接
          </Button>
          <Button type="submit" size="sm" disabled={!config || saveMutation.isPending || testMutation.isPending || testImageMutation.isPending}>
            {saveMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Save />}
            保存模型配置
          </Button>
        </div>
      </div>
    </form>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid min-w-0 gap-1.5 text-xs font-medium text-foreground">
      {label}
      {children}
    </label>
  )
}

function SecretInput({
  configured,
  value,
  onChange,
  clear,
  onClearChange,
}: {
  configured: boolean
  value: string
  onChange: (value: string) => void
  clear: boolean
  onClearChange: (value: boolean) => void
}) {
  return (
    <div className="space-y-1.5">
      <Input
        type="password"
        autoComplete="new-password"
        value={value}
        placeholder={configured ? '已配置，输入新密钥以替换' : '粘贴 API Key'}
        onChange={(event) => {
          onChange(event.target.value)
          if (event.target.value) onClearChange(false)
        }}
      />
      {configured && (
        <label className="flex items-center gap-1.5 font-normal text-muted-foreground">
          <input
            type="checkbox"
            checked={clear}
            onChange={(event) => {
              onClearChange(event.target.checked)
              if (event.target.checked) onChange('')
            }}
          />
          清除已保存密钥
        </label>
      )}
    </div>
  )
}

function Status({ label, value, configured }: { label: string; value: string; configured: boolean }) {
  return (
    <div className="grid content-start gap-1.5 text-xs font-medium">
      <span>{label}</span>
      <span className="flex h-8 min-w-0 items-center gap-1.5 truncate rounded-md bg-muted/60 px-2 text-muted-foreground">
        {configured && <Check className="size-3.5 shrink-0 text-success" aria-hidden />}
        {value}
      </span>
    </div>
  )
}

function statusLabel(value: string) {
  return { not_configured: '未配置', configured: '已配置，尚未测试', connected: '连接正常', error: '连接失败' }[value] ?? value
}
