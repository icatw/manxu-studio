import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, useLocation } from "react-router"
import { describe, expect, it, vi } from "vitest"
import { AccountGate } from "./account-gate"

vi.mock("@/lib/api/client", () => ({
  api: {
    GET: vi.fn().mockResolvedValue({ error: { code: "AUTH_REQUIRED" } }),
  },
}))

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}</output>
}

describe("AccountGate", () => {
  it("redirects expired sessions to the login route", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/projects/project-1"]}>
          <LocationProbe />
          <AccountGate><div>protected workspace</div></AccountGate>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole("heading", { name: "漫序 Studio" })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"))
    expect(screen.queryByText("protected workspace")).not.toBeInTheDocument()
  })
})
