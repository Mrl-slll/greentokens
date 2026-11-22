import { UPSTREAM, asDevUser, match } from "@/lib/proxyPolicy";

async function handle(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const origin = req.headers.get("origin");
  // Next.js can normalize req.url to localhost even when the browser uses 127.0.0.1.
  const requestUrl = new URL(req.url);
  const expectedOrigin = `${requestUrl.protocol}//${req.headers.get("host") ?? requestUrl.host}`;
  if ((origin && origin !== expectedOrigin) || req.headers.get("sec-fetch-site") === "cross-site") {
    return Response.json({ detail: "Cross-origin request denied" }, { status: 403 });
  }
  const { path } = await ctx.params;
  const limit = match(req.method, path);
  if (limit === null) return Response.json({ detail: "Not found" }, { status: 404 });
  const user = asDevUser(req.headers.get("x-dev-user"));
  const headers: Record<string, string> = {};
  if (user) headers["X-Dev-User"] = user;
  let body: ArrayBuffer | undefined;
  if (limit > 0) {
    body = await req.arrayBuffer();
    if (body.byteLength > limit) return Response.json({ detail: "Request too large" }, { status: 413 });
    headers["Content-Type"] = "application/json";
  }
  try {
    const up = await fetch(`${UPSTREAM}/${path.join("/")}`, { method: req.method, headers, body, signal: req.signal, cache: "no-store" });
    return new Response(up.body, { status: up.status, headers: { "Content-Type": up.headers.get("content-type") ?? "application/json" } });
  } catch {
    return Response.json({ detail: "GreenTokens API unreachable (is the local stack running?)" }, { status: 502 });
  }
}
export { handle as GET, handle as POST };
