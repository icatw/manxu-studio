import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query'
import { Bot, ChevronRight, CircleUserRound, KeyRound, Laptop, LoaderCircle, LogOut, Save, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ModelSettingsPanel } from '@/components/studio/model-settings-dialog'
import { api } from '@/lib/api/client'
import { cn } from '@/lib/utils'
import type { components } from '@/lib/api/schema'

type SectionId = 'profile' | 'models' | 'account'
type AccountQuery = UseQueryResult<components['schemas']['Account'], Error>
type IdentityQuery = UseQueryResult<components['schemas']['AuthIdentity'][], Error>
const sections: Array<{ id: SectionId; label: string; description: string; icon: typeof UserRound }> = [
  { id: 'profile', label: '个人资料', description: '昵称与登录方式', icon: UserRound },
  { id: 'models', label: '模型配置', description: '文本与图像服务', icon: Bot },
  { id: 'account', label: '账户与安全', description: '会话与账户状态', icon: ShieldCheck },
]

export function SettingsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedSection = searchParams.get('section') as SectionId | null
  const activeSection: SectionId = sections.some((section) => section.id === requestedSection) ? requestedSection! : 'profile'
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
  const logout = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST('/auth/logout')
      if (error) throw new Error('退出登录失败，请稍后重试')
    },
    onSuccess: () => window.location.assign('/'),
  })
  const selectSection = (section: SectionId) => setSearchParams(section === 'profile' ? {} : { section })

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur sm:px-6">
        <Button variant="ghost" size="icon-sm" aria-label="返回项目库" title="返回项目库" onClick={() => navigate('/projects')}><ChevronRight className="rotate-180" /></Button>
        <a className="flex items-center gap-2 text-sm font-semibold" href="/projects"><span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">漫</span>漫序 Studio</a>
        <span className="border-l pl-3 text-sm text-muted-foreground">设置</span>
        <div className="ml-auto flex items-center gap-2">
          {account.data?.avatar_url ? <img className="size-7 rounded-full border border-border object-cover" src={account.data.avatar_url} alt="" /> : <div className="grid size-7 place-items-center rounded-full bg-muted text-xs font-medium">{account.data?.display_name?.slice(0, 1).toUpperCase() ?? '?'}</div>}
          <span className="hidden max-w-32 truncate text-xs text-muted-foreground sm:inline">{account.data?.display_name ?? '账户'}</span>
          <Button variant="ghost" size="sm" className="text-muted-foreground" disabled={logout.isPending} onClick={() => logout.mutate()}>{logout.isPending ? <LoaderCircle className="animate-spin" /> : <LogOut />}退出登录</Button>
        </div>
      </header>
      <div className="mx-auto grid min-h-[calc(100dvh-3.5rem)] w-full max-w-6xl lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="border-b bg-sidebar/35 p-4 lg:border-r lg:border-b-0 lg:p-5" aria-label="设置导航">
          <div className="mb-5 px-2"><p className="text-lg font-semibold tracking-tight">设置</p><p className="mt-1 text-xs leading-5 text-muted-foreground">管理你的创作环境</p></div>
          <nav className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
            {sections.map(({ id, label, description, icon: Icon }) => { const active = activeSection === id; return <button key={id} type="button" aria-current={active ? 'page' : undefined} onClick={() => selectSection(id)} className={cn('group flex min-w-max flex-1 items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors lg:flex-none', active ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground')}><Icon className={cn('size-4 shrink-0', active ? 'text-primary' : 'text-muted-foreground')} aria-hidden /><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{label}</span><span className="hidden truncate text-[11px] text-muted-foreground lg:block">{description}</span></span><ChevronRight className="hidden size-3.5 lg:block" aria-hidden /></button> })}
          </nav>
          <div className="mt-8 hidden border-t px-2 pt-4 text-xs leading-5 text-muted-foreground lg:block"><div className="mb-2 flex items-center gap-2 text-foreground"><Laptop className="size-3.5" aria-hidden />本地工作区</div>你的模型密钥只会加密保存在服务端，不会出现在浏览器存储中。</div>
        </aside>
        <section className="min-w-0 px-5 py-7 sm:px-8 lg:px-12 lg:py-10"><div className="mx-auto max-w-3xl"><SectionHeader section={activeSection} />{activeSection === 'profile' && <ProfileSection account={account} identities={identities} queryClient={queryClient} />}{activeSection === 'models' && <ModelsSection />}{activeSection === 'account' && <AccountSection account={account.data} onLogout={() => logout.mutate()} logoutPending={logout.isPending} />}</div></section>
      </div>
    </main>
  )
}

function SectionHeader({ section }: { section: SectionId }) { const current = sections.find((item) => item.id === section)!; const Icon = current.icon; return <header className="mb-7 border-b pb-6"><div className="flex items-start gap-3"><span className="grid size-9 place-items-center rounded-md bg-primary/10 text-primary"><Icon className="size-5" aria-hidden /></span><div><h1 className="text-xl font-semibold tracking-tight">{current.label}</h1><p className="mt-1 text-sm text-muted-foreground">{current.description}</p></div></div></header> }

function ProfileSection({ account, identities, queryClient }: { account: AccountQuery; identities: IdentityQuery; queryClient: ReturnType<typeof useQueryClient> }) {
  const [displayName, setDisplayName] = useState(''); const [notice, setNotice] = useState<string | null>(null); const identityItems = Array.isArray(identities.data) ? identities.data : []
  useEffect(() => { if (account.data) setDisplayName(account.data.display_name) }, [account.data])
  const saveProfile = useMutation({ mutationFn: async () => { const { data, error } = await api.PATCH('/auth/me', { body: { display_name: displayName.trim() } }); if (error || !data) throw new Error('保存昵称失败，请重试'); return data }, onSuccess: (data) => { queryClient.setQueryData(['current-account'], data); setNotice('个人资料已保存') }, onError: (error) => setNotice(error.message) })
  function submit(event: FormEvent) { event.preventDefault(); setNotice(null); saveProfile.mutate() }
  return <div className="space-y-6"><SettingBlock title="公开资料" description="这些信息用于识别你的创作工作区。">{account.isPending && <p className="text-sm text-muted-foreground">正在读取账户资料…</p>}{account.isError && <p role="alert" className="text-sm text-destructive">{account.error.message}</p>}{account.data && <form className="grid gap-5 sm:grid-cols-[auto_minmax(0,1fr)]" onSubmit={submit}>{account.data.avatar_url ? <img className="size-16 rounded-full border object-cover" src={account.data.avatar_url} alt="GitHub 头像" /> : <div className="grid size-16 place-items-center rounded-full bg-muted text-xl font-medium">{account.data.display_name.slice(0, 1).toUpperCase()}</div>}<div className="grid min-w-0 gap-4 sm:grid-cols-2"><label className="grid gap-1.5 text-xs font-medium">昵称<Input required minLength={1} maxLength={80} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label><label className="grid gap-1.5 text-xs font-medium">GitHub 账户<Input value={account.data.github_login || '未绑定'} readOnly aria-readonly="true" /></label><div className="flex flex-wrap items-center gap-3 sm:col-span-2"><Button type="submit" size="sm" disabled={!displayName.trim() || saveProfile.isPending || displayName.trim() === account.data.display_name}>{saveProfile.isPending ? <LoaderCircle className="animate-spin" /> : <Save />}保存更改</Button>{notice && <span role="status" className="text-xs text-muted-foreground">{notice}</span>}</div></div></form>}</SettingBlock><SettingBlock title="已验证的登录方式" description="用于登录此账户，不会展示第三方访问令牌。"><div className="divide-y rounded-md border">{identityItems.map((identity) => <div key={identity.id} className="flex items-center gap-3 px-4 py-3 text-sm"><CircleUserRound className="size-4 text-muted-foreground" aria-hidden /><span className="flex-1">{identity.provider === 'email' ? identity.email : 'GitHub'}</span><span className="text-xs text-success">{identity.verified ? '已验证' : '未验证'}</span></div>)}{!identities.isPending && !identities.isError && identityItems.length === 0 && <p className="px-4 py-3 text-sm text-muted-foreground">暂无登录方式信息</p>}</div></SettingBlock></div>
}

function ModelsSection() { return <div className="space-y-5"><div className="rounded-md border border-primary/25 bg-primary/5 px-4 py-3"><div className="flex items-start gap-3"><KeyRound className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden /><div className="min-w-0"><p className="text-sm font-medium">每个账户独立保存模型配置</p><p className="mt-1 text-xs leading-5 text-muted-foreground">配置只对当前账户生效，密钥加密保存在服务端。下方推荐值可以直接填入，再保存并测试连接。</p></div></div></div><ModelSettingsPanel /></div> }

function AccountSection({ account, onLogout, logoutPending }: { account: components['schemas']['Account'] | undefined; onLogout: () => void; logoutPending: boolean }) { return <SettingBlock title="账户与安全" description="查看账户状态并结束当前会话。"><div className="divide-y rounded-md border"><InfoRow label="账户昵称" value={account?.display_name ?? '—'} /><InfoRow label="GitHub 账号" value={account?.github_login ? `@${account.github_login}` : '未绑定'} /><div className="flex items-center justify-between gap-4 px-4 py-4"><div><p className="text-sm font-medium">当前会话</p><p className="mt-1 text-xs text-muted-foreground">浏览器使用 HttpOnly Cookie 保存登录状态。</p></div><Button variant="outline" size="sm" disabled={logoutPending} onClick={onLogout}>{logoutPending ? <LoaderCircle className="animate-spin" /> : <LogOut />}退出登录</Button></div></div></SettingBlock> }
function InfoRow({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-4 px-4 py-3 text-sm"><span className="text-muted-foreground">{label}</span><span className="truncate text-right font-medium">{value}</span></div> }
function SettingBlock({ title, description, children }: { title: string; description: string; children: React.ReactNode }) { return <section className="rounded-md border bg-card/35 p-5 sm:p-6"><div className="mb-5"><h2 className="text-sm font-semibold">{title}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p></div>{children}</section> }
