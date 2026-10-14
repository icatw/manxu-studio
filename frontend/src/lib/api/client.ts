import createClient from "openapi-fetch";
import type { paths } from "./schema";

async function authenticatedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? "GET").toUpperCase()
  if (typeof document !== "undefined" && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("manxu_csrf="))
    if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf.slice("manxu_csrf=".length)))
  }
  return fetch(input, { ...init, headers, credentials: "include" })
}

export const api = createClient<paths>({ baseUrl: "/api/v1", fetch: authenticatedFetch });
