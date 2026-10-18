import { useEffect, useId, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { FolderOpen, LogOut, Settings } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { useCurrentAccount } from "@/hooks/use-current-account";
import { cn } from "@/lib/utils";

type AccountMenuProps = {
  className?: string;
  /** Hide “作品库” when the current page already is the library. */
  showLibraryLink?: boolean;
  /** Hide “设置” when already on the settings page. */
  showSettingsLink?: boolean;
};

export function AccountMenu({
  className,
  showLibraryLink = true,
  showSettingsLink = true,
}: AccountMenuProps) {
  const navigate = useNavigate();
  const account = useCurrentAccount();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);

  const logout = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/auth/logout");
      if (error) throw new Error("退出登录失败，请稍后重试");
    },
    onSuccess: () => window.location.assign("/login"),
    onError: (error) => toast.error("退出登录失败", { description: error.message }),
  });

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const displayName = account.data?.display_name ?? "账户";
  const login = account.data?.github_login;
  const initial = (displayName || login || "?").slice(0, 1).toUpperCase();

  return (
    <div className={cn("relative", className)} ref={wrapRef}>
      <Button
        variant="ghost"
        size="icon-sm"
        className="rounded-full"
        aria-label="账户菜单"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        title="账户"
        onClick={() => setOpen((value) => !value)}
      >
        {account.data?.avatar_url ? (
          <img src={account.data.avatar_url} alt="" className="size-7 rounded-full object-cover" />
        ) : (
          <span className="grid size-7 place-items-center rounded-full bg-muted text-xs font-medium">
            {initial}
          </span>
        )}
      </Button>
      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label="账户"
          className="absolute right-0 z-50 mt-1 w-56 rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        >
          <div className="border-b px-2.5 py-2">
            <p className="truncate text-sm font-medium">{displayName}</p>
            {login ? (
              <p className="truncate text-[11px] text-muted-foreground">@{login}</p>
            ) : null}
          </div>
          {showSettingsLink ? (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent"
              onClick={() => {
                setOpen(false);
                navigate("/settings");
              }}
            >
              <Settings className="size-4 text-muted-foreground" aria-hidden />
              设置
            </button>
          ) : null}
          {showLibraryLink ? (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm hover:bg-accent"
              onClick={() => {
                setOpen(false);
                navigate("/projects");
              }}
            >
              <FolderOpen className="size-4 text-muted-foreground" aria-hidden />
              作品库
            </button>
          ) : null}
          <div className="my-1 h-px bg-border" aria-hidden />
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50"
            disabled={logout.isPending}
            onClick={() => {
              setOpen(false);
              logout.mutate();
            }}
          >
            <LogOut className="size-4" aria-hidden />
            {logout.isPending ? "退出中…" : "退出登录"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
