import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./lib/api/client", () => ({
  api: {
    GET: vi.fn().mockResolvedValue({ data: { items: [], next_cursor: null } }),
  },
}));

describe("application shell", () => {
  it("renders the project library", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole("heading", { name: "项目" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("还没有项目，先创建一个故事。")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "新建项目" })).toBeInTheDocument();
  });
});
