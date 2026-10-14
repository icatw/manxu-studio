import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, LoaderCircle, LogOut, Save, UserRound } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api/client'
import { ModelSettingsPanel } from '@/components/studio/model-settings-dialog'

export function SettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const account = useQuery({
    queryKey: ['current-account'],
    queryFn: async () => {
      const { data, error } = await api.GET('/auth/me')
      if (error || !data) throw new Error('无法读取账户资料')
      return data
    },
  })
  const identities = useQuery({
    queryKey: ['auth-identities'],
    queryFn: async () => {
      const { data, error } = await api.GET('/auth/identities')
      if (error || !data) throw new Error('无法读取登录方式')
      return data
    },
  })
  const [displayName, setDisplayName] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const identityItems = Array.isArray(identities.data) ? identities.data : []
  const logout = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST('/auth/logout')
      if (error) throw new Error('退出登录失败，请稍后重试')
    },
    onSuccess: () => window.location.assign('/'),
    onError: (error) => setNotice(error.message),
  })

  useEffect(() => {
    if (account.data) setDisplayName(account.data.display_name)
  }, [account.data])

  const saveProfile = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.PATCH('/auth/me', { body: { display_name: displayName.trim() } })
      if (error || !data) throw new Error('保存昵称失败，请重试')
      return data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['current-account'], data)
      setNotice('个人资料已保存')
    },
    onError: (error) => setNotice(error.message),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    setNotice(null)
    saveProfile.mutate()
  }

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b px-4 sm:px-6">
        <Button variant="ghost" size="icon-sm" aria-label="返回项目库" title="返回项目库" onClick={() => navigate('/projects')}><ArrowLeft /></Button>
        <a className="flex items-center gap-2 text-sm font-semibold" href="/projects">
          <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">漫</span>漫序 Studio
        </a>
        <span className="border-l pl-3 text-sm text-muted-foreground">设置</span>
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto text-muted-foreground"
          disabled={logout.isPending}
          onClick={() => logout.mutate()}
        >
          <LogOut aria-hidden />退出登录
        </Button>
      </header>
      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8">
        <h1 className="text-xl font-semibold">设置</h1>
        <section className="mt-6 border-t pt-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold"><UserRound className="size-4" aria-hidden />个人资料</h2>
          {account.isPending && <p className="mt-4 text-sm text-muted-foreground">正在读取账户资料…</p>}
          {account.isError && <p role="alert" className="mt-4 text-sm text-destructive">{account.error.message}</p>}
          {account.data && <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
            {account.data.avatar_url
              ? <img className="size-14 rounded-full border object-cover" src={account.data.avatar_url} alt="GitHub 头像" />
              : <div className="grid size-14 place-items-center rounded-full bg-muted text-lg font-medium">{account.data.github_login.slice(0, 1).toUpperCase()}</div>}
            <form className="grid min-w-0 flex-1 gap-4 sm:grid-cols-2" onSubmit={submit}>
              <label className="grid gap-1.5 text-xs font-medium">昵称
                <Input required minLength={1} maxLength={80} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label className="grid gap-1.5 text-xs font-medium">GitHub 账户
                <Input value={account.data.github_login || '未绑定'} readOnly aria-readonly="true" />
              </label>
              <div className="grid gap-1.5 text-xs font-medium sm:col-span-2">登录方式
                <div className="flex flex-wrap gap-2 text-sm font-normal">
                  {identityItems.map((identity) => (
                    <span key={identity.id} className="border px-2.5 py-1.5">
                      {identity.provider === 'email' ? identity.email : 'GitHub'}{identity.provider === 'email' && identity.verified ? ' · 已验证' : ''}
                    </span>
                  ))}
                  {!identities.isPending && !identities.isError && identityItems.length === 0 && <span className="text-muted-foreground">暂无登录方式信息</span>}
                  {identities.isError && <span className="text-destructive">{identities.error.message}</span>}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
                <Button type="submit" size="sm" disabled={!displayName.trim() || saveProfile.isPending || displayName.trim() === account.data.display_name}>
                  {saveProfile.isPending ? <LoaderCircle className="animate-spin" /> : <Save />}保存昵称
                </Button>
                {notice && <span role="status" className={`text-xs ${saveProfile.isError ? 'text-destructive' : 'text-muted-foreground'}`}>{notice}</span>}
              </div>
            </form>
          </div>}
        </section>
        <section className="mt-8 border-t pt-5">
          <h2 className="mb-4 text-sm font-semibold">模型配置</h2>
          <ModelSettingsPanel />
        </section>
      </div>
    </main>
  )
}
