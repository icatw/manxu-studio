import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ImageIcon, KeyRound, ScrollText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { api } from '@/lib/api/client'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PROVIDER_NAMES: Record<string, string> = {
  demo: '演示模式',
  deepseek: 'DeepSeek',
  qwen: '通义千问',
  wanx: '通义万相',
  'openai-compatible': 'OpenAI 兼容服务',
}

export function ModelSettingsDialog({ open, onOpenChange }: Props) {
  const query = useQuery({
    queryKey: ['model-config'],
    queryFn: async () => {
      const { data, error } = await api.GET('/model-config')
      if (error || !data) throw new Error('无法读取服务端模型配置')
      return data
    },
    enabled: open,
  })

  const config = query.data
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[min(90vh,640px)] flex-col gap-0 p-0 sm:max-w-xl">
        <DialogHeader className="border-b px-5 py-4">
          <DialogTitle>模型设置</DialogTitle>
          <DialogDescription>模型由 FastAPI 服务端统一配置，密钥不会发送到浏览器。</DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
          {query.isPending && <p className="text-sm text-muted-foreground">正在读取配置…</p>}
          {query.isError && (
            <div className="flex items-center justify-between gap-3 text-sm text-destructive">
              <span>{query.error.message}</span>
              <Button size="sm" variant="outline" onClick={() => void query.refetch()}>重试</Button>
            </div>
          )}
          {config && (
            <>
              <ModelSection
                icon={<ScrollText className="size-4" aria-hidden />}
                title="文本模型"
                provider={config.text_provider}
                model={config.text_model}
                baseUrl={config.text_base_url}
                keyConfigured={config.text_api_key_configured}
                status={config.text_status}
              />
              <ModelSection
                icon={<ImageIcon className="size-4" aria-hidden />}
                title="图像模型"
                provider={config.image_provider}
                model={config.image_model}
                baseUrl={config.image_base_url}
                keyConfigured={config.image_api_key_configured}
                status={config.image_status}
              />
              <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
                配置位于项目根目录的 <code className="font-mono text-foreground">.env</code>，修改后需重启 API。
                当前生成任务仍使用演示结果；真实 provider 适配尚未完成。
              </div>
            </>
          )}
        </div>
        <DialogFooter className="border-t px-5 py-3 sm:justify-end">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ModelSection({
  icon,
  title,
  provider,
  model,
  baseUrl,
  keyConfigured,
  status,
}: {
  icon: ReactNode
  title: string
  provider: string
  model: string
  baseUrl: string
  keyConfigured: boolean
  status: 'demo' | 'not_connected'
}) {
  return (
    <section className="space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-medium">
        <span className="flex size-7 items-center justify-center rounded-md bg-muted text-muted-foreground">{icon}</span>
        {title}
      </h3>
      <dl className="grid grid-cols-[100px_minmax(0,1fr)] gap-x-3 gap-y-2 text-sm">
        <dt className="text-muted-foreground">服务商</dt>
        <dd>{PROVIDER_NAMES[provider] ?? provider}</dd>
        <dt className="text-muted-foreground">模型 ID</dt>
        <dd className="break-all font-mono text-xs">{model || '未配置'}</dd>
        <dt className="text-muted-foreground">Base URL</dt>
        <dd className="break-all font-mono text-xs">{baseUrl || '默认'}</dd>
        <dt className="text-muted-foreground">API 密钥</dt>
        <dd className="flex items-center gap-1.5">
          <KeyRound className="size-3.5" aria-hidden />{keyConfigured ? '已在服务端配置' : '未配置'}
        </dd>
        <dt className="text-muted-foreground">运行状态</dt>
        <dd className={status === 'demo' ? 'text-warning' : 'text-muted-foreground'}>
          {status === 'demo' ? '演示模式' : '已配置，provider 尚未接入'}
        </dd>
      </dl>
    </section>
  )
}
