import { useQuery } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { ArrowLeft, Github, LoaderCircle, Mail, ShieldCheck } from "lucide-react"
import { useSearchParams } from "react-router"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api/client"

const AUTH_ERRORS: Record<string, string> = {
  oauth_unconfigured: "服务端尚未配置 GitHub OAuth，请联系部署管理员。",
  denied: "GitHub 授权已取消。",
  invalid_callback: "登录回调信息不完整，请重新尝试。",
  state: "登录校验已过期，请重新尝试。",
  github: "无法验证 GitHub 账户，请稍后重试。",
  account: "无法创建或读取账户，请稍后重试。",
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
  const [email, setEmail] = useState("")
  const [code, setCode] = useState("")
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState("")
  const [resendIn, setResendIn] = useState(0)

  useEffect(() => {
    if (resendIn <= 0) return
    const timer = window.setTimeout(() => setResendIn((value) => value - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [resendIn])

  async function requestCode() {
    const normalizedEmail = email.trim()
    if (!normalizedEmail || !normalizedEmail.includes("@")) {
      setNotice("请输入有效的邮箱地址")
      return
    }
    setBusy(true)
    setNotice("")
    try {
      const result = await api.POST("/auth/email/code", { body: { email: normalizedEmail } })
      if (result.error || !result.data) {
        setNotice(readErrorMessage(result.error, "验证码发送失败，请稍后重试"))
        return
      }
      setSent(true)
      setResendIn(60)
      setNotice("验证码已发送，请检查邮箱")
    } catch {
      setNotice("验证码发送失败，请稍后重试")
    } finally {
      setBusy(false)
    }
  }

  async function verifyCode() {
    const normalizedEmail = email.trim()
    if (!normalizedEmail || code.length !== 6) {
      setNotice("请输入邮箱和 6 位验证码")
      return
    }
    setBusy(true)
    setNotice("")
    try {
      const result = await api.POST("/auth/email/verify", { body: { email: normalizedEmail, code } })
      if (result.error || !result.data) {
        setNotice(readErrorMessage(result.error, "验证码无效或已过期"))
        return
      }
      window.location.assign("/")
    } catch {
      setNotice("登录失败，请稍后重试")
    } finally {
      setBusy(false)
    }
  }

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
        <p className="mt-2 text-sm leading-6 text-muted-foreground">使用邮箱验证码登录或注册创作工作区。</p>
        {error && <p role="alert" className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{AUTH_ERRORS[error] ?? "登录未能完成，请重试。"}</p>}
        <div className="mt-6 space-y-3">
          <Input type="email" placeholder="邮箱地址" value={email} disabled={sent} onChange={(event) => setEmail(event.target.value)} />
          {!sent ? (
            <Button className="w-full" disabled={busy || !email.trim()} onClick={() => void requestCode()}><Mail aria-hidden />获取验证码</Button>
          ) : (
            <>
              <Input inputMode="numeric" maxLength={6} placeholder="6 位验证码" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} />
              <Button className="w-full" disabled={busy || code.length !== 6} onClick={() => void verifyCode()}>{busy ? <LoaderCircle className="animate-spin" aria-hidden /> : <Mail aria-hidden />}登录或注册</Button>
              <div className="flex items-center justify-between text-sm">
                <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => { setSent(false); setCode(""); setResendIn(0); setNotice("") }}><ArrowLeft aria-hidden />修改邮箱</Button>
                <Button type="button" variant="ghost" size="sm" disabled={busy || resendIn > 0} onClick={() => void requestCode()}>{resendIn > 0 ? `${resendIn} 秒后重发` : "重新发送验证码"}</Button>
              </div>
            </>
          )}
        </div>
        {notice && <p role="status" className="mt-3 text-sm text-muted-foreground">{notice}</p>}
        <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />或<span className="h-px flex-1 bg-border" /></div>
        <Button className="w-full" variant="outline" onClick={() => window.location.assign("/api/v1/auth/github/start")}><Github aria-hidden />使用 GitHub 继续</Button>
        <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-3.5 shrink-0" aria-hidden />登录凭据由服务端安全处理。</p>
      </section>
    </main>
  )
}

function readErrorMessage(error: unknown, fallback: string) {
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === "string") return message
  }
  return fallback
}
