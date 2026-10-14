import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./lib/api/client", () => ({
  api: {
    GET: vi.fn((path: string) => Promise.resolve(path === "/auth/me"
      ? { data: { id: "acct-1", github_login: "creator", display_name: "creator", avatar_url: null } }
      : path === "/model-config"
        ? { data: {
            text_provider: "openai-compatible", text_model: "qwen-plus", text_base_url: "https://example.com/v1",
            text_api_key_configured: false, text_status: "not_configured", image_provider: "qwen",
            image_model: "qwen-image-3.0-pro", image_base_url: "https://dashscope.aliyuncs.com/api/v1",
            image_api_key_configured: false, image_concurrency: 1, image_negative_prompt: "",
            image_status: "not_configured", image_models: ["qwen-image-3.0-pro"],
          } }
        : { data: { items: [], next_cursor: null } })),
    PATCH: vi.fn(),
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

    expect(await screen.findByRole("heading", { name: "项目" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("还没有项目，先创建一个故事。")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "新建项目" })).toBeInTheDocument();
  });

  it("shows editable image service URL in account settings", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/settings"]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const imageUrl = await screen.findByLabelText("图像服务 Base URL") as HTMLInputElement;
    expect(imageUrl.value).toBe("https://dashscope.aliyuncs.com/api/v1");
    fireEvent.change(imageUrl, { target: { value: "https://workspace.example.com/api/v1" } });
    expect(imageUrl.value).toBe("https://workspace.example.com/api/v1");
    expect(screen.getByRole("heading", { name: "个人资料" })).toBeInTheDocument();
  });
});
