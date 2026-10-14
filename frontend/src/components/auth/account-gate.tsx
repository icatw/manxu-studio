import { useQuery } from "@tanstack/react-query"
import { Github, LoaderCircle, ShieldCheck } from "lucide-react"
import { useSearchParams } from "react-router"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

const AUTH_ERRORS: Record<string, string> = {
  oauth_unconfigured: "服务端尚未配置 GitHub OAuth，请联系部署管理员。",
  denied: "GitHub 授权已取消。",
  invalid_callback: "登录回调信息不完整，请重新尝试。",
  state: "登录校验已过期，请重新尝试。",
  github: "无法验证 GitHub 账户，请稍后重试。",
  account_locked: "此 GitHub 账户不在已启用账户中。",
  setup_required: "服务尚未完成账户初始化，请联系部署管理员。",
}

export function AccountGate({ children }: { children: React.ReactNode }) {
  const [searchParams] = useSearchParams()
  const auth = useQuery({
    queryKey: ["current-account"],
    queryFn: async () => {
      const { data, error } = await api.GET("/auth/me")
      if (error || !data) return null
      return data
    },
    retry: false,
    staleTime: 60_000,
  })

  if (auth.isPending) {
    return <main className="grid min-h-dvh place-items-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 size-4 animate-spin" />正在验证账户…</main>
  }
  if (auth.data) return children

  const error = searchParams.get("auth_error")
  return (
    <main className="grid min-h-dvh place-items-center bg-background px-5 py-10">
      <section className="w-full max-w-sm border-t-2 border-primary pt-6">
        <div className="mb-6 flex size-10 items-center justify-center rounded-md bg-primary text-base font-bold text-primary-foreground" aria-hidden>漫</div>
        <h1 className="text-xl font-semibold">漫序 Studio</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">使用已启用的 GitHub 账户登录创作工作区。</p>
        {error && <p role="alert" className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{AUTH_ERRORS[error] ?? "登录未能完成，请重试。"}</p>}
        <Button className="mt-6 w-full" onClick={() => window.location.assign("/api/v1/auth/github/start")}>
          <Github aria-hidden />使用 GitHub 登录
        </Button>
        <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-3.5 shrink-0" aria-hidden />仅首个成功登录的 GitHub 账户可访问此工作区。</p>
      </section>
    </main>
  )
}
