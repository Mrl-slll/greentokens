import { connection } from "next/server";


const API_BASE_URL = "http://127.0.0.1:8000";
const MAX_REQUEST_BYTES = 65_536;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DEVELOPMENT_IDENTITIES = new Set(["alice", "bob", "admin"]);

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function errorResponse(status: number, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function allowedEndpoint(method: string, parts: string[]): string | null {
  if (method === "GET" && parts.length === 1 && parts[0] === "health") {
    return "health";
  }

  if (parts.length === 2 && parts[0] === "v1") {
    if (method === "GET" && parts[1] === "usage") return "v1/usage";
    if (method === "POST" && parts[1] === "jobs") return "v1/jobs";
    if (method === "POST" && parts[1] === "artifacts") return "v1/artifacts";
  }

  if (parts[0] !== "v1" || !["jobs", "artifacts"].includes(parts[1])) {
    return null;
  }

  const id = parts[2];
  if (!id || !UUID_PATTERN.test(id)) return null;

  if (parts.length === 3 && method === "GET") {
    return `v1/${parts[1]}/${id}`;
  }

  if (parts.length === 4 && parts[1] === "jobs") {
    if (method === "GET" && parts[3] === "result") {
      return `v1/jobs/${id}/result`;
    }
    if (method === "POST" && parts[3] === "cancel") {
      return `v1/jobs/${id}/cancel`;
    }
  }

  return null;
}

async function readJsonBody(request: Request): Promise<ArrayBuffer | Response> {
  const contentLength = request.headers.get("content-length");

  if (
    contentLength !== null &&
    (!/^\d+$/.test(contentLength) || Number(contentLength) > MAX_REQUEST_BYTES)
  ) {
    return errorResponse(413, "Request body exceeds the size limit");
  }

  const reader = request.body?.getReader();
  if (!reader) return errorResponse(400, "JSON request body required");

  const buffer = new ArrayBuffer(MAX_REQUEST_BYTES);
  const bytes = new Uint8Array(buffer);
  let size = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (size + value.byteLength > MAX_REQUEST_BYTES) {
        await reader.cancel();
        return errorResponse(413, "Request body exceeds the size limit");
      }

      bytes.set(value, size);
      size += value.byteLength;
    }
  } finally {
    reader.releaseLock();
  }

  return buffer.slice(0, size);
}

async function handleRequest(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const endpoint = allowedEndpoint(request.method, path);
  if (!endpoint) return errorResponse(404, "API route not found");

  const url = new URL(request.url);
  if (url.search) return errorResponse(400, "Query parameters are not supported");

  if (request.method === "POST") {
    const origin = request.headers.get("origin");

    if (origin) {
      const host = request.headers.get("host");
      let sameOrigin = false;

      try {
        const browserOrigin = new URL(origin);
        sameOrigin =
          browserOrigin.protocol === "http:" &&
          (browserOrigin.hostname === "127.0.0.1" ||
            browserOrigin.hostname === "localhost") &&
          browserOrigin.host === host;
      } catch {
        sameOrigin = false;
      }

      if (!sameOrigin) {
        return errorResponse(403, "Cross-origin requests are not allowed");
      }
    }
  }

  const headers = new Headers();

  if (endpoint !== "health") {
    // Development identity selection is not authentication.
    const identity = request.headers.get("x-dev-user");
    if (!identity || !DEVELOPMENT_IDENTITIES.has(identity)) {
      return errorResponse(400, "Invalid development identity");
    }
    headers.set("X-Dev-User", identity);
  }

  let body: ArrayBuffer | undefined;
  if (request.method === "POST" && ["v1/jobs", "v1/artifacts"].includes(endpoint)) {
    const contentType = request.headers.get("content-type") ?? "";
    if (!/^application\/json(?:\s*;|$)/i.test(contentType)) {
      return errorResponse(415, "Content-Type must be application/json");
    }

    const received = await readJsonBody(request);
    if (received instanceof Response) return received;

    body = received;
    headers.set("Content-Type", "application/json");
  }

  try {
    const upstream = await fetch(`${API_BASE_URL}/${endpoint}`, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(30_000)]),
    });

    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      return errorResponse(502, "Unexpected API redirect");
    }

    const responseHeaders = new Headers({
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });

    const contentType = upstream.headers.get("content-type");
    if (contentType) responseHeaders.set("Content-Type", contentType);

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return errorResponse(502, "Local API unavailable");
  }
}

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  await connection();
  return handleRequest(request, context);
}

export async function POST(request: Request, context: RouteContext): Promise<Response> {
  return handleRequest(request, context);
}
