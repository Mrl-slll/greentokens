# GreenTokens tools: what to look up

This is an additional learning reference. It does not replace or change the [main README](../README.md) or component guides. Created 20 November 2026.

Each table gives the exact tool name, its category, what it does here, and a search phrase you can copy into a search engine. These phrases are learning aids, not commands to run or instructions to upgrade dependencies. Consult this repository's manifests/lockfiles before following version-specific tutorials.

## First: what the categories mean

| Category | Plain-language meaning | Example here |
| --- | --- | --- |
| Language | The language source code is written in | Python, TypeScript, Rust |
| Runtime | Program that executes code | Python interpreter, Node.js |
| Library | Reusable functions/classes your code calls | Pydantic, boto3 |
| Framework | A structure that organizes your application and calls your code | FastAPI, Next.js |
| Service | A running program other programs communicate with | MySQL, GreenTokens API |
| Protocol | Rules for communication between programs | HTTP, HTTPS |
| Build tool | Transforms source into runnable/distributable output | Vite, TypeScript compiler |
| Package manager | Installs and manages dependencies | npm, pip, Cargo, uv |
| Architecture pattern | A way to organize responsibilities; not necessarily something installed | Control plane, worker polling, reconciliation |

For example: Python is the language, FastAPI is the API framework, Uvicorn runs the API server, and HTTP is how clients call it. They are different layers of the same application.

## 1. Customer website

Read [the web component guide](../app/README.md). Source lives in `app/`, `components/`, and `lib/` at the repository root.

| Tool | Category and role here | Search phrase |
| --- | --- | --- |
| React | UI library; describes pages as reusable components | `React components props state official docs` |
| Next.js | Web framework; routes pages and server-side HTTP handlers | `Next.js App Router route handlers documentation` |
| TypeScript | JavaScript with type checking; describes expected API/UI data | `TypeScript types interfaces handbook` |
| Node.js | JavaScript runtime; runs frontend tooling and server-side web code | `Node.js runtime introduction` |
| Tailwind CSS | Styling framework; utility classes control appearance | `Tailwind CSS utility classes documentation` |
| PostCSS | CSS processing tool used in the styling build | `PostCSS CSS processing introduction` |
| react-markdown | React renderer for Markdown documentation | `react-markdown documentation` |
| remark-gfm | Markdown extension for GitHub-style features such as tables | `remark-gfm tables documentation` |
| npm | Node package manager and script runner | `npm package json scripts package lock` |

Concepts to learn: **component**, **state**, **routing**, **server rendering**, **same-origin proxy**, and **mock adapter**. The API proxy forwards requests; it does not run training. The browser's local storage is not the project database.

## 2. Provider desktop application

Read [the provider guide](../apps/provider_app/README.md). Source lives in `apps/provider_app/`.

| Tool | Category and role here | Search phrase |
| --- | --- | --- |
| React / TypeScript | Desktop interface and typed service calls | `React TypeScript application basics` |
| Vite | Frontend development/build tool; compiles the provider UI | `Vite getting started build development server` |
| Tauri | Desktop application framework; packages a web UI with native capabilities | `Tauri 2 architecture commands IPC` |
| Rust | Language used for native process/hardware operations | `Rust book getting started` |
| Cargo | Rust dependency manager and build tool | `Cargo manifest Cargo.toml build` |
| Webview | Embedded browser component displaying the desktop UI | `Tauri system webview architecture` |
| uv | Provisions the app's private Python environment and packages | `uv Python managed installations virtual environments` |
| Python | Runs the worker that asks for jobs and launches workloads | `Python subprocess environment variables tutorial` |
| sysinfo | Rust library used for system/usage information | `Rust sysinfo crate documentation` |
| NSIS | Windows installer technology used by the current packaging configuration | `Tauri NSIS Windows installer` |

Concepts: **native bridge**, **IPC** (inter-process communication), **subprocess**, **private runtime**, and **CSP** (Content Security Policy). The browser preview and installed native app are different execution environments.

## 3. Backend and authentication

Read [the backend guide](../core/README.md). Main source: `core/api/` and `core/config.py`.

| Tool | Category and role here | Search phrase |
| --- | --- | --- |
| Python | Backend implementation language | `Python tutorial modules virtual environments` |
| FastAPI | API framework; maps HTTP requests to Python functions | `FastAPI path operations dependencies tutorial` |
| Uvicorn | ASGI server; runs the FastAPI application | `Uvicorn ASGI server deployment` |
| Pydantic | Validation library; checks request shape, types and bounds | `Pydantic models validation strict mode` |
| hashlib.scrypt | Python standard-library password-hashing function | `Python hashlib scrypt password hashing salt` |
| secrets | Python standard-library secure random generation | `Python secrets token_urlsafe documentation` |
| httpx | HTTP client dependency used in supporting checks/client-side tooling | `HTTPX Python HTTP client documentation` |

Concepts: **REST-style HTTP API**, **endpoint**, **request/response**, **ASGI**, **authentication**, **authorization**, **bearer token**, **session**, **rate limiting**, and **dependency injection**.

Authentication asks who the caller is. Authorization asks what that caller may do. A checksum is not authentication. A public tunnel does not replace either check. `X-Dev-User` is a development shortcut, not a real login credential.

## 4. Database

Read [the database guide](../core/database/README.md). Source lives in `core/database/`.

| Tool | Category and role here | Search phrase |
| --- | --- | --- |
| MySQL | Relational database service; stores accounts and durable job metadata | `MySQL relational database tables transactions` |
| SQLAlchemy | Python ORM/query library; expresses models and database operations | `SQLAlchemy ORM session transactions tutorial` |
| PyMySQL | Database driver; connects Python to MySQL | `PyMySQL connection cursor documentation` |
| Alembic | Database schema migration tool | `Alembic SQLAlchemy migrations upgrade head` |
| SQLite | Lightweight database used in portions of test coverage | `SQLite in memory database testing` |

Concepts: **table**, **row**, **primary key**, **foreign key**, **transaction**, **row lock**, **unique constraint**, **ORM**, and **migration**.

An ORM maps Python objects to relational data. A migration changes existing database structure in a controlled sequence. Editing an ORM class alone does not upgrade deployed tables. SQLite tests do not reproduce every MySQL behavior.

## 5. Artifact storage

Read [the storage guide](../core/artifacts/README.md). Source: `core/artifacts/storage.py`.

| Tool or standard | Category and role here | Search phrase |
| --- | --- | --- |
| SeaweedFS | Storage service; holds model/log/output objects | `SeaweedFS S3 object storage documentation` |
| S3 API | Object-storage interface; used locally through SeaweedFS | `S3 API buckets object keys explained` |
| boto3 | Python AWS SDK; its S3 client calls the compatible local service | `boto3 S3 endpoint_url put_object get_object` |
| SHA-256 | Cryptographic hash; detects mismatched artifact bytes | `SHA-256 file integrity checksum explained` |

Concepts: **object storage**, **bucket**, **object key**, **artifact**, **checkpoint**, **TTL**, and **checksum**. MySQL stores artifact metadata; SeaweedFS stores the bytes. S3-compatible does not mean data is hosted on Amazon. Expiry does not automatically mean physical deletion.

## 6. Scheduling and workers

Read [execution](../core/jobs/README.md) and [workloads](../core/workloads/README.md).

| Tool or structure | Category and role here | Search phrase |
| --- | --- | --- |
| Ray | Distributed execution framework for the trusted Ray path | `Ray Core tasks actors placement groups` |
| Ray Jobs | Submission interface for a driver running in a Ray cluster | `Ray Jobs API JobSubmissionClient` |
| GreenTokens dispatcher | Project code, not an external product; reconciles jobs and leases | `reconciliation loop distributed systems scheduler` |
| Provider worker | Project Python code; polls HTTPS and runs approved packages | `worker pull model long polling job queue` |
| MySQL-backed queue | Architecture pattern; job rows persist requested work | `database backed job queue skip locked` |

Concepts: **control plane**, **execution plane**, **heartbeat**, **lease**, **long polling**, **idempotency**, **retry**, and **reconciliation**.

Ray workers and independent HTTPS providers are different paths. Connecting multiple providers does not automatically split a model among them. Retries do not automatically resume a checkpoint or guarantee exactly-once execution.

## 7. Machine-learning workloads

Read [workloads](../core/workloads/README.md), [examples](../examples/README.md), and [the four-PC experiment](../experiments/four_pc_cpu/README.md).

| Tool or model | Category and role here | Search phrase |
| --- | --- | --- |
| PyTorch | Tensor/autograd library; computes training updates | `PyTorch tensors autograd training loop tutorial` |
| Hugging Face Transformers | Model/tokenizer library; loads pretrained architectures | `Hugging Face Transformers fine tuning classification` |
| Hugging Face Datasets | Dataset-loading/processing library | `Hugging Face Datasets train test split` |
| NumPy | Numerical array library; used for array operations/transfers | `NumPy arrays introduction` |
| BERT / DistilBERT | Model architectures used by approved sentiment tasks | `BERT DistilBERT sequence classification explained` |
| SST-2 / IMDB | Labeled sentiment datasets, not servers or libraries | `SST-2 IMDB sentiment classification dataset` |
| AdamW | Optimization algorithm updating model parameters | `PyTorch AdamW optimizer explained` |
| CUDA | NVIDIA GPU-computing platform | `PyTorch CUDA availability driver compatibility` |
| safetensors | Model tensor storage format | `Hugging Face safetensors format` |

Concepts: **fine-tuning**, **tokenizer**, **batch**, **epoch**, **gradient**, **optimizer**, **evaluation split**, **data parallelism**, **local SGD**, **FP32**, and **bfloat16**.

The four-PC experiment uses periodic local training and model-change averaging through HTTPS. Do not assume a generic tutorial about Ray Train, NCCL or per-step gradient synchronization describes that experiment's actual implementation.

## 8. Networking and planned Raspberry Pi hosting

Read [the Pi deployment plan](server-migration-plan.md). The following table distinguishes observed use from planned hosting work.

| Tool or concept | Role and status here | Search phrase |
| --- | --- | --- |
| Tailscale | Private overlay network; peer connectivity to the Pi was verified; intended for administration | `Tailscale tailnet private network explained` |
| SSH | Secure remote shell; planned administrative access, not proof access is configured | `OpenSSH remote administration public key authentication` |
| cloudflared / Cloudflare Tunnel | Connector carrying public requests to a local API; current temporary path versus planned persistent path | `Cloudflare Tunnel remotely managed published application` |
| DNS | Maps a stable hostname to its configured destination | `DNS hostname records explained` |
| HTTPS / TLS | Encrypted client-to-server transport | `HTTPS TLS certificates explained` |
| Loopback | Address of the caller's own machine, such as `127.0.0.1` | `localhost loopback 127.0.0.1 explained` |
| Tailscale Serve / Funnel | Private/public service exposure options discussed in the plan; selected deployment not established | `Tailscale Serve versus Funnel` |
| Debian | Linux distribution reported on the Pi | `Debian Linux server administration handbook` |
| systemd | Planned Linux boot/service supervision | `systemd service unit restart dependencies` |

Concepts: **reverse tunnel**, **ingress**, **private network**, **service supervision**, **readiness**, **failover**, and **high availability**.

The connector and API can share a machine while the API listens only on loopback. Providers use the public HTTPS hostname. Tailscale administration is a different route. A permanent hostname does not keep a powered-off machine available; restart supervision does not replace backups or redundant hardware.

## 9. Containers, storage and operational recovery

Read [infrastructure](../infrastructure/README.md) and [operations](../scripts/README.md).

| Tool or concept | Role here | Search phrase |
| --- | --- | --- |
| Docker Engine | Runs containers; proposed server engine on Linux | `Docker Engine containers images volumes` |
| Docker Desktop | Existing developer-machine container environment | `Docker Desktop versus Docker Engine` |
| Docker Compose | Describes the MySQL/storage services and their configuration | `Docker Compose services ports volumes healthcheck` |
| Docker volume | Persistent container data; not a backup by itself | `Docker volumes persistence backup restore` |
| Filesystem mount | Makes the Pi's external drive available at a path; explicit data placement is planned | `Linux persistent mount UUID fstab` |
| Backup / restoration | Separate recoverable copy and the process of restoring it; automation planned | `database backup restore RPO RTO explained` |

Do not run commands from a tutorial that delete volumes, reformat drives or reset a database to troubleshoot this project. Here, accounts and model artifacts must survive migration. Learn the concept first and use the project's actual runbook for operations.

## 10. Clients, tests and delivery

Read [SDK](../sdk/README.md), [Databricks](../databricks/README.md), [tests](../tests/README.md), and [delivery](../.github/README.md).

| Tool or concept | Role here | Search phrase |
| --- | --- | --- |
| Python urllib / argparse / tomllib | Standard-library HTTP client, CLI argument parsing and TOML configuration | `Python urllib argparse tomllib documentation` |
| Databricks notebooks | Optional remote customer interface; not where provider training runs | `Databricks notebooks widgets secrets` |
| unittest | Python test framework | `Python unittest test discovery mocking` |
| Vitest | JavaScript/TypeScript test runner | `Vitest getting started` |
| Testing Library | Tests UI through user-visible behavior | `React Testing Library queries user behavior` |
| jsdom | Simulated DOM environment for tests; not a full installed desktop app | `jsdom testing DOM environment` |
| ESLint | Static JavaScript/TypeScript code checks | `ESLint linting explained` |
| TypeScript compiler / tsc | Checks types and can compile TypeScript | `TypeScript tsc noEmit type checking` |
| Git | Source version-control system | `Git working tree commit branch remote explained` |
| GitHub Actions | Automated checks/build/release workflows | `GitHub Actions workflows artifacts releases` |
| GitHub Pages | Hosts the static installer download page | `GitHub Pages static site hosting` |

Concepts: **unit test**, **integration test**, **acceptance test**, **mock**, **CI/CD**, **build artifact**, and **release**. Passing tests is not deployment; pushing source is not updating an installed app.

## 11. Deferred shared agent knowledge

OpenViking is a proposed shared agent-context service, not a currently installed GreenTokens component. Its planned purpose is to help you and your teammate's agents retrieve selected project knowledge. Search `OpenViking context database team knowledge sharing`, then read the licensing and scope notes in [project memory](roadmap.md) before choosing a version or integration.

## A useful learning order

1. Understand the five architectural parts in the [root guide](../README.md): public entrance, control plane, data layer, execution plane and operations layer.
2. Follow one request from provider app through HTTPS/tunnel to FastAPI.
3. Follow one job from MySQL assignment to a provider subprocess and back to stored artifacts.
4. Learn the tools belonging to the component you are about to edit; you do not need to learn every library first.
5. Check the project's pinned version and scope before applying an online example. A tutorial can be correct for a different version or architecture and still be wrong for this project.
