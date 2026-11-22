# Customer web application

[System guide](../README.md)

This guide covers the root `app/`, `components/`, and `lib/` directories. This is a Next.js/React web app, separate from the Tauri provider app and from the ignored nested `greentokens/` checkout.

## Purpose and structure

React expresses UI as components; TypeScript defines the client-side contracts; Next.js supplies filesystem routes, server rendering and HTTP route handlers. The **App Router** maps directories to pages and API routes. Tailwind/PostCSS provide styling. These tools present and proxy jobs; they do not schedule workers.

| Source | Responsibility |
| --- | --- |
| `layout.tsx`, `globals.css` | Shared page structure and styling |
| `page.tsx` | Entry/home page |
| `jobs/`, `pipelines/`, `settings/` | Job submission/status, pipeline explanation, mock/live and development identity selection |
| `train/` | Training UI; consult the TrOCR contract before assuming it calls a supported backend template |
| `docs/` | Repository Markdown rendered as documentation |
| `demo/`, `api/demo/predict/route.ts` | Local saved BERT checkpoint inference demo |
| `api/core/[...path]/route.ts` | Fixed upstream API proxy |
| `../components/AppProvider.tsx` | React context containing selected client, identity and mode |
| `../lib/client.ts`, `mockClient.ts`, `types.ts` | Shared client interface, live HTTP adapter, simulator and types |
| `../lib/proxyPolicy.ts` | Allowed paths/methods, body limits, fixed upstream |
| `../lib/recent.ts` | Browser-local job history |
| `../lib/guides.ts` | Allowlisted Markdown files and link rewriting |
| `../lib/demoCheckpoint.ts` | Locate latest valid standalone BERT demo checkpoint |

## Request flow and why there is a proxy

```text
Browser → /api/core/v1/... on Next.js → http://127.0.0.1:8000/v1/... on FastAPI
```

This is a **same-origin backend proxy**: browser requests stay on the website origin, and a server route forwards a constrained set of operations. The upstream is fixed in `lib/proxyPolicy.ts`, not accepted from user input. The route rejects cross-origin requests, filters methods/paths and forwards recognized development identity selectors. Worker administration is deliberately absent from its allowlist.

The proxy reaches the API on the machine hosting Next.js. It is not a remote-provider connection mechanism. Do not expose this development website as a public authenticated customer service: its identity selector is a local stub, and it is not the provider login system.

## Mock mode versus live mode

`AppProvider` defaults to mock mode and restores browser preferences after mount. The shared client interface lets UI components work with either a simulator or live HTTP adapter. This is an **adapter pattern**: same interface, different implementation.

Mock results prove UI behavior only. Live mode needs the backend and matching development identity. Recent job IDs are stored in this browser; they are not a server-side job-list query and will not automatically include all notebook/CLI submissions.

## Documentation and demo boundaries

`lib/guides.ts` only reads listed Markdown paths. New component READMEs are linked by the root guide but are not automatically added to the web documentation route list. Unrecognized repository links currently rewrite to GitHub `main`; local/unpushed guides may not resolve there yet. Read the files locally until published deliberately.

The prediction demo uses a local Python subprocess and a verified standalone checkpoint under `examples/bert_tiny_cpu`. Its inference is not a new provider training job. A clean checkout without generated model files cannot reproduce the demo just by starting Next.js. See [examples](../examples/README.md).

The current subprocess path is specifically `.tools/bert-tiny-venv/Scripts/python.exe`, so this route also assumes this Windows workspace's demo environment. Porting the web UI to another host does not automatically provision that Python executable or model.

## Run and modify

From the outer root: `npm.cmd ci` for initial dependencies, then `npm.cmd run dev`. Default host is loopback port 3000. `npm.cmd run build` builds the application; `npm.cmd start` serves a built app. Use `npm.cmd test`, `npm.cmd run typecheck`, and `npm.cmd run lint` for relevant changes.

Before writing Next.js code, follow `AGENTS.md` and read the relevant installed guides under `node_modules/next/dist/docs/`. Do not apply assumptions from older Next.js versions. When changing an API field, update frontend types/adapters and actual backend contract together. A visual button is not evidence that a backend feature exists.
