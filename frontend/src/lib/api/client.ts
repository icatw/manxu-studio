import createClient from "openapi-fetch";
import type { paths } from "./schema";

type Envelope = { code: string; message: string; data: unknown; request_id: string };
type UnwrapEnvelope<T> = T extends Envelope ? T["data"] : T;
type UnwrapContent<T> = T extends { content: infer Content }
  ? Omit<T, "content"> & { content: { [K in keyof Content]: UnwrapEnvelope<Content[K]> } }
  : T;
type UnwrapResponses<T> = { [K in keyof T]: UnwrapContent<T[K]> };
type UnwrapOperation<T> = T extends { responses: infer Responses }
  ? Omit<T, "responses"> & { responses: UnwrapResponses<Responses> }
  : T;
type UnwrappedPaths = {
  [Path in keyof paths]: { [Method in keyof paths[Path]]: UnwrapOperation<paths[Path][Method]> };
};

export type ApiErrorDetails = {
  code: string;
  message: string;
  requestId: string;
  status: number;
  errors?: Array<{ field?: string; code?: string; message?: string }>;
};

export class ApiError extends Error {
  readonly code: string;
  readonly requestId: string;
  readonly status: number;
  readonly errors?: ApiErrorDetails["errors"];

  constructor(details: ApiErrorDetails) {
    super(details.requestId ? `${details.message} (request_id: ${details.requestId})` : details.message);
    this.name = "ApiError";
    this.code = details.code;
    this.requestId = details.requestId;
    this.status = details.status;
    this.errors = details.errors;
  }
}

function csrfCookie() {
  if (typeof document === "undefined") return null;
  const part = document.cookie.split(";").map((value) => value.trim()).find((value) => value.startsWith("manxu_csrf="));
  return part ? decodeURIComponent(part.slice("manxu_csrf=".length)) : null;
}

async function refreshCsrfCookie() {
  if (typeof window === "undefined") return null;
  await fetch("/api/v1/auth/csrf", { credentials: "include", headers: { Accept: "application/json" } });
  return csrfCookie();
}

export async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? "GET").toUpperCase()
  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  if (typeof document !== "undefined" && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    let csrf = csrfCookie()
    if (!csrf && typeof input === "string" && !input.includes("/auth/csrf")) csrf = await refreshCsrfCookie()
    if (csrf) headers.set("X-CSRF-Token", csrf)
  }
  const response = await fetch(input, { ...init, headers, credentials: "include" })
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase()
  if (contentType !== "application/json" && !contentType?.endsWith("+json")) return response

  const value: unknown = await response.clone().json().catch(() => null)
  if (!isEnvelope(value)) return response
  if (!response.ok && value.code === "CSRF_INVALID") await refreshCsrfCookie()

  const body = response.ok
    ? value.data
    : {
        ...value,
        status: response.status,
        message: value.request_id ? `${value.message} (request_id: ${value.request_id})` : value.message,
      }
  const responseHeaders = new Headers(response.headers)
  responseHeaders.delete("content-length")
  return new Response(JSON.stringify(body), {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  })
}

export function toApiError(error: unknown, fallback = "请求失败，请稍后重试") {
  if (error instanceof ApiError) return error;
  if (error && typeof error === "object" && "code" in error && "message" in error) {
    const value = error as Partial<Envelope> & { status?: number; errors?: ApiErrorDetails["errors"] };
    return new ApiError({
      code: typeof value.code === "string" ? value.code : "UNKNOWN_ERROR",
      message: typeof value.message === "string" ? value.message : fallback,
      requestId: typeof value.request_id === "string" ? value.request_id : "",
      status: typeof value.status === "number" ? value.status : 0,
      errors: value.errors,
    });
  }
  if (error instanceof Error) return error;
  return new Error(fallback);
}

function isEnvelope(value: unknown): value is Envelope {
  return typeof value === "object" && value !== null &&
    "code" in value && "message" in value && "data" in value && "request_id" in value &&
    typeof value.code === "string" && typeof value.message === "string" &&
    typeof value.request_id === "string"
}

export const api = createClient<UnwrappedPaths>({ baseUrl: "/api/v1", fetch: authenticatedFetch });
