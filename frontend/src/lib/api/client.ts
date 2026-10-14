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

async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? "GET").toUpperCase()
  if (typeof document !== "undefined" && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("manxu_csrf="))
    if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf.slice("manxu_csrf=".length)))
  }
  const response = await fetch(input, { ...init, headers, credentials: "include" })
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase()
  if (contentType !== "application/json" && !contentType?.endsWith("+json")) return response

  const value: unknown = await response.clone().json().catch(() => null)
  if (!isEnvelope(value)) return response

  const body = response.ok
    ? value.data
    : {
        ...value,
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

function isEnvelope(value: unknown): value is Envelope {
  return typeof value === "object" && value !== null &&
    "code" in value && "message" in value && "data" in value && "request_id" in value &&
    typeof value.code === "string" && typeof value.message === "string" &&
    typeof value.request_id === "string"
}

export const api = createClient<UnwrappedPaths>({ baseUrl: "/api/v1", fetch: authenticatedFetch });
