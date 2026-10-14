import { beforeEach, describe, expect, it, vi } from "vitest"
import { authenticatedFetch } from "./client"

describe("authenticatedFetch", () => {
  beforeEach(() => {
    document.cookie = "manxu_csrf=test-csrf; path=/"
  })

  it("adds JSON and CSRF headers to mutation requests", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: "OK", message: "请求成功", data: { ok: true }, request_id: "req-1" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    await authenticatedFetch("/api/v1/projects", { method: "POST", body: JSON.stringify({ title: "test" }) })

    const [, init] = fetchMock.mock.calls[0]
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json")
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("test-csrf")
    fetchMock.mockRestore()
  })

  it("preserves stable API error fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: "NOT_FOUND", message: "资源不存在", data: null, request_id: "req-2" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    )

    const response = await authenticatedFetch("/api/v1/projects/missing")
    const body = await response.json()
    expect(body.code).toBe("NOT_FOUND")
    expect(body.request_id).toBe("req-2")
    expect(body.status).toBe(404)
  })
})
