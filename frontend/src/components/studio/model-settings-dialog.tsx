import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ImageIcon, KeyRound, LoaderCircle, Save, ScrollText, Sparkles, Wifi } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api, toApiError } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

export function ModelSettingsPanel() {
  const queryClient = useQueryClient()
  const [textModel, setTextModel] = useState('')
  const [textBaseUrl, setTextBaseUrl] = useState('')
  const [textKey, setTextKey] = useState('')
  const [imageModel, setImageModel] = useState('qwen-image-3.0')
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
    setTextModel(query.data.text_model)
    setTextBaseUrl(query.data.text_base_url)
    setImageModel(query.data.image_model)
    setImageBaseUrl(query.data.image_base_url)
    setTextKey('')
    setImageKey('')
    setClearTextKey(false)
    setClearImageKey(false)
  }, [query.data])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: components['schemas']['ModelConfigUpdate'] = {
        text_model: textModel.trim(),
        text_base_url: textBaseUrl.trim(),
        image_model: imageModel,
        image_base_url: imageBaseUrl.trim(),
      }
      if (textKey.trim()) body.text_api_key = textKey
      else if (clearTextKey) body.text_api_key = null
      if (imageKey.trim()) body.image_api_key = imageKey
      else if (clearImageKey) body.image_api_key = null
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

  function applySystemPreset() {
    const preset = query.data?.system_presets?.[0]
    if (!preset) return
    setTextModel(preset.text_model)
    setTextBaseUrl(preset.base_url)
    setImageModel(preset.image_model)
    setImageBaseUrl(preset.base_url)
    setNotice({ success: true, message: '已填入系统推荐值，请补充密钥后保存' })
  }

  const config = query.data
  return (
    <form onSubmit={submit} className="space-y-6">
      {query.isPending && <p className="text-sm text-muted-foreground">正在读取配置…</p>}
      {query.isError && <p role="alert" className="text-sm text-destructive">{query.error.message}</p>}
      {config && (
        <>
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="flex items-center gap-2 text-sm font-semibold"><ScrollText className="size-4" aria-hidden />文本模型 · OpenAI 兼容</h3><Button type="button" variant="ghost" size="sm" disabled={!config.system_presets?.length} onClick={applySystemPreset}><Sparkles />填入系统推荐</Button></div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Base URL">
                <Input required type="url" placeholder="https://api.example.com/v1" value={textBaseUrl} onChange={(event) => setTextBaseUrl(event.target.value)} />
              </Field>
              <Field label="模型 ID">
                <Input required maxLength={160} placeholder="qwen-plus" value={textModel} onChange={(event) => setTextModel(event.target.value)} />
              </Field>
              <Field label="API Key">
                <SecretInput configured={config.text_api_key_configured} value={textKey} onChange={setTextKey} clear={clearTextKey} onClearChange={setClearTextKey} />
              </Field>
              <Status label="连接状态" value={statusLabel(config.text_status)} configured={config.text_status === 'connected'} />
            </div>
            <p className="text-xs text-muted-foreground">文本请求会发送到此地址的 `/chat/completions` 接口；仅允许公网 HTTPS 地址。</p>
          </section>

          <section className="space-y-4 border-t pt-5">
            <h3 className="flex items-center gap-2 text-sm font-semibold"><ImageIcon className="size-4" aria-hidden />图像模型 · Qwen Image</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="模型版本">
                <select className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm" value={imageModel} onChange={(event) => setImageModel(event.target.value)}>
                  {config.image_models.map((model) => <option key={model} value={model}>{model}</option>)}
                </select>
              </Field>
              <Field label="图像服务 Base URL">
                <Input required type="url" maxLength={2048} placeholder="https://dashscope.aliyuncs.com/api/v1" value={imageBaseUrl} onChange={(event) => setImageBaseUrl(event.target.value)} />
              </Field>
              <Field label="百炼 API Key">
                <SecretInput configured={config.image_api_key_configured} value={imageKey} onChange={setImageKey} clear={clearImageKey} onClearChange={setClearImageKey} />
              </Field>
              <Status label="配置状态" value={statusLabel(config.image_status)} configured={config.image_status === 'connected'} />
            </div>
            <p className="text-xs leading-5 text-muted-foreground">图像请求使用百炼异步 Image API。可填写官方 API 地址，或已开通图像服务的 Workspace Host；若地址以 `/compatible-mode/v1` 结尾，服务端会映射到该 Host 的 `/api/v1`。</p>
          </section>
        </>
      )}
      {notice && <p role="status" className={`rounded-md border px-3 py-2 text-sm ${notice.success ? 'border-success/30 bg-success/5 text-success' : 'border-destructive/30 bg-destructive/5 text-destructive'}`}>{notice.message}</p>}
      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><KeyRound className="size-3.5" aria-hidden />密钥仅加密保存在服务端</span>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" disabled={!config || testMutation.isPending || testImageMutation.isPending || saveMutation.isPending} onClick={() => testMutation.mutate()}>
            {testMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Wifi />}测试文本连接
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={!config || testMutation.isPending || testImageMutation.isPending || saveMutation.isPending} onClick={() => testImageMutation.mutate()}>
            {testImageMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Wifi />}测试图像连接
          </Button>
          <Button type="submit" size="sm" disabled={!config || saveMutation.isPending || testMutation.isPending || testImageMutation.isPending}>
            {saveMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Save />}保存模型配置
          </Button>
        </div>
      </div>
    </form>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="grid min-w-0 gap-1.5 text-xs font-medium text-foreground">{label}{children}</label>
}

function SecretInput({ configured, value, onChange, clear, onClearChange }: { configured: boolean; value: string; onChange: (value: string) => void; clear: boolean; onClearChange: (value: boolean) => void }) {
  return (
    <div className="space-y-1.5">
      <Input type="password" autoComplete="new-password" value={value} placeholder={configured ? '已配置，输入新密钥以替换' : '粘贴 API Key'} onChange={(event) => { onChange(event.target.value); if (event.target.value) onClearChange(false) }} />
      {configured && <label className="flex items-center gap-1.5 font-normal text-muted-foreground"><input type="checkbox" checked={clear} onChange={(event) => { onClearChange(event.target.checked); if (event.target.checked) onChange('') }} />清除已保存密钥</label>}
    </div>
  )
}

function Status({ label, value, configured }: { label: string; value: string; configured: boolean }) {
  return <div className="grid content-start gap-1.5 text-xs font-medium"><span>{label}</span><span className="flex h-8 min-w-0 items-center gap-1.5 truncate rounded-md bg-muted/60 px-2 text-muted-foreground">{configured && <Check className="size-3.5 shrink-0 text-success" aria-hidden />}{value}</span></div>
}

function statusLabel(value: string) {
  return { not_configured: '未配置', configured: '已配置，尚未测试', connected: '连接正常', error: '连接失败' }[value] ?? value
}
