import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { AccountMenu } from "./account-menu"

vi.mock("@/hooks/use-current-account", () => ({
  useCurrentAccount: () => ({
    data: {
      id: "acct-1",
      github_login: "creator",
      display_name: "创作者",
      avatar_url: null,
    },
    isPending: false,
    isError: false,
  }),
}))

vi.mock("@/lib/api/client", () => ({
  api: {
    POST: vi.fn(async () => ({ error: undefined })),
  },
}))

function renderMenu(props?: { showLibraryLink?: boolean; showSettingsLink?: boolean }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AccountMenu {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("AccountMenu", () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("opens a menu with settings and logout", () => {
    renderMenu()
    fireEvent.click(screen.getByRole("button", { name: "账户菜单" }))
    expect(screen.getByRole("menu", { name: "账户" })).toBeInTheDocument()
    expect(screen.getByRole("menuitem", { name: "设置" })).toBeInTheDocument()
    expect(screen.getByRole("menuitem", { name: "作品库" })).toBeInTheDocument()
    expect(screen.getByRole("menuitem", { name: "退出登录" })).toBeInTheDocument()
    expect(screen.getByText("创作者")).toBeInTheDocument()
  })

  it("can hide the library and settings links", () => {
    renderMenu({ showLibraryLink: false, showSettingsLink: false })
    fireEvent.click(screen.getByRole("button", { name: "账户菜单" }))
    expect(screen.queryByRole("menuitem", { name: "作品库" })).not.toBeInTheDocument()
    expect(screen.queryByRole("menuitem", { name: "设置" })).not.toBeInTheDocument()
  })
})
