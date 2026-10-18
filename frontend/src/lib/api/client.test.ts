import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiError, api, authenticatedFetch, toApiError } from "./client"

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

  it("preserves Request method and headers used by openapi-fetch", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: "OK", message: "请求成功", data: { id: "project-1" }, request_id: "req-3" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    )
    const request = new Request("http://localhost/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "test" }),
    })

    await authenticatedFetch(request)

    const [input, init] = fetchMock.mock.calls[0]
    expect(input).toBe(request)
    expect(init?.method).toBeUndefined()
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json")
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("test-csrf")
    fetchMock.mockRestore()
  })

  it("preserves openapi-fetch Request headers and method", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: "OK", message: "请求成功", data: { id: "project-1" }, request_id: "req-4" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    )

    await api.POST("/projects", {
      body: {
        title: "test",
        synopsis: "test",
        genre: "都市",
        art_style: "电影感",
        aspect_ratio: "portrait",
      },
    })

    const [input, init] = fetchMock.mock.calls[0]
    expect(input).toBeInstanceOf(Request)
    expect((input as Request).method).toBe("POST")
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json")
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("test-csrf")
    fetchMock.mockRestore()
  })

  it("loads a CSRF token before a Request-based mutation when the cookie is unavailable", async () => {
    document.cookie = "manxu_csrf=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).includes("/auth/csrf")) {
        return new Response(JSON.stringify({
          code: "OK",
          message: "请求成功",
          data: { token: "refreshed-token" },
          request_id: "req-5",
        }), { status: 200, headers: { "content-type": "application/json" } })
      }
      return new Response(JSON.stringify({ code: "OK", message: "请求成功", data: {}, request_id: "req-6" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      })
    })
    const request = new Request("http://localhost/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "test" }),
    })

    await authenticatedFetch(request)

    expect(String(fetchMock.mock.calls[0][0])).toContain("/auth/csrf")
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-CSRF-Token")).toBe("refreshed-token")
    fetchMock.mockRestore()
  })

  it("adds a CSRF header to Request-based deletes", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }))
    const request = new Request("http://localhost/api/v1/projects/project-1", { method: "DELETE" })

    await authenticatedFetch(request)

    const [, init] = fetchMock.mock.calls[0]
    expect(init?.method).toBeUndefined()
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

describe("ApiError", () => {
  it("appends request_id once even when the message already contains it", () => {
    const error = new ApiError({
      code: "CONFLICT",
      message: "请先生成上一话摘要 (request_id: req-dup)",
      requestId: "req-dup",
      status: 409,
    })
    expect(error.message).toBe("请先生成上一话摘要 (request_id: req-dup)")
    expect(error.message.match(/request_id:/gi)?.length).toBe(1)
  })

  it("dedupes via toApiError when wrapping envelope-shaped errors", () => {
    const error = toApiError({
      code: "CONFLICT",
      message: "请先生成上一话摘要 (request_id: req-7)",
      request_id: "req-7",
      status: 409,
    })
    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe("请先生成上一话摘要 (request_id: req-7)")
  })
})
