# Raspberry Pi workflow README

How GreenTokens works now that the server is the Raspberry Pi, and how we work with it. Written for anyone on the team: developers, whoever manages the Pi, and testers.

Related: [Pi migration plan](server-migration-plan.md) · [Provider guide](provider-guide.md) · [Windows distribution](windows-distribution.md) · [System README](../README.md)

## 1. The idea in one picture

```
Provider computer (GreenTokens Provider app)
        │  HTTPS requests, outward only
        ▼
https://lurayspi.tail430e22.ts.net      ← the Raspberry Pi (the server)
        ▲
        │  HTTPS requests with a customer key
Customer (Databricks notebooks 00 / 01 / 02)
```

- **The Pi is the server.** It holds accounts, job records and results, and hands out approved jobs.
- **Provider computers** (ordinary PCs and Macs) install the Provider app. The app connects *outward* to the Pi, asks for approved work, runs it, and uploads the result. Providers need no network settings, no firewall changes and no Tailscale.
- **Customers** submit approved training jobs from Databricks. They never touch a provider directly.
- **This laptop is no longer the server.** It is only a development computer.

## 2. The rule: we work with the Pi through requests, never through commands

We **do not log into the Pi or run commands on it** (no SSH) from development or testing. Everything we do from outside is an ordinary HTTPS request, exactly what a real provider app or customer sends.

| | Requests (what we do) | Commands on the Pi (not us) |
|---|---|---|
| Answers | Does it work from outside? Can a provider sign up, sign in and stay online? Are fake developer logins rejected? | Which version is deployed, disk space, backups, service state |
| Can change | Nothing on the Pi | Deploy code, restart services, back up data |
| Risk | Same as any user | Full access to the machine and its data |

Why: privacy, and because outside behaviour is what providers and customers actually experience. Anything that needs the inside of the Pi (section 6) belongs to **whoever manages the Pi**.

## 3. What each part does

| Part | Where it runs | Job |
|---|---|---|
| API (FastAPI) | Pi | Sign-up, sign-in, heartbeats, job assignment, results |
| Database (MySQL) and file storage (SeaweedFS) | Pi | Accounts, jobs, models and logs |
| Job recovery | Pi | A provider that disappears loses its job lease; the job is queued again (up to 3 tries) |
| Public address | Pi | One stable HTTPS address, `https://lurayspi.tail430e22.ts.net` |
| Provider app | Provider computers | Sign in, set up Python and PyTorch inside its own folder, connect, run approved jobs |
| Databricks notebooks | Customer workspace | `00` connect, `01` submit a job, `02` view results |

## 4. Provider workflow (what a computer owner does)

1. Download **GreenTokens Provider** from the [Releases page](https://github.com/Mrl-slll/greentokens/releases). Current: **0.4.0 unsigned preview**. Windows shows "Publisher: Unknown" until code signing is set up.
2. Open the app, **create an account** (any password, no rules) or sign in.
3. Press the power button and choose **Yes, set up & connect**. First time only: it installs what it needs, about 10-20 minutes on NVIDIA computers.
4. It shows **Connected**. Leave the app open while sharing.

What the app does behind the scenes:
- Sends a **heartbeat** to the Pi every few seconds, so the Pi knows it is online.
- Long-polls for work, downloads an approved, checksum-verified workload, runs it, renews its lease, uploads results.
- Retries by itself after a network drop.
- **Stays signed in** after reopening: the session token lives in Windows Credential Manager or the macOS Keychain (never the password) and is renewed on each launch. Sharing never starts by itself; the owner presses Connect.
- **Sign out** removes the saved sign-in and revokes the session on the Pi.

## 5. Customer workflow (Databricks)

1. `00` stores the Pi address and the customer's key as secrets in their workspace and tests the connection.
2. `01_Submit_Training_Job` submits an approved job (for example `text_finetune_v1`).
3. `02_View_Results` shows status, results and the trained model.

Customer keys must exist on the Pi. Only hashes are stored there.

## 6. Who does what

| Task | Owner |
|---|---|
| Write and test code, build and publish the provider app | Developers (from a computer, by Git and GitHub) |
| Check the Pi from outside (health, sign-up, sign-in, heartbeat) | Developers, by requests |
| Put new server code on the Pi, restart services | **Pi manager** |
| Backups, disk mounting, start-on-boot, tunnel service, monitoring | **Pi manager** |
| Create customer keys on the Pi | **Pi manager** |
| Install the app, create an account, press Connect | Provider owners |
| Submit jobs and read results | Customers |

## 7. Safe checks from outside (no Pi access needed)

All of these are plain web requests to `https://lurayspi.tail430e22.ts.net`:

| Check | Expected |
|---|---|
| `GET /health` | `status: ok`, `provider_auth: password-v1` |
| `POST /v1/provider/auth/login` with an empty body | 422 (not 404: the route exists) |
| `GET /v1/usage` with an `X-Dev-User` header | 401 (outside requests cannot pose as a developer) |
| Sign up a throwaway account, sign in, send a heartbeat, sign out | 201, 200, 200, 204; the token stops working after sign-out |
| On a provider computer: the app's status file shows `server` = the Pi address and `state: online` with a fresh `updated` time | Connected to the Pi |

Use throwaway usernames such as `gt-selftest-xxxx`. Never share keys or tokens in chat, logs or Git.

## 8. Current limits

- **Unsigned installers:** Windows warns and Edge may block the download. Use the arrow next to Delete, then Keep. A signed release needs a code-signing identity.
- **New server features need the Pi updated by its manager.** Example: the `refresh` route (30-day sessions) only exists after the Pi runs the 0.4.0 code. Without it the app still works but only remembers a sign-in for 24 hours.
- **One server:** if the Pi is off or its internet or power is down, everyone is offline. There is no failover.
- **Large transfers:** the Pi's public address has bandwidth limits. Normal jobs are fine; very large experiments (such as the four-computer training run) may be slow.
- **The app does not install GPU drivers.**
- **Providers are trusted workers, not sandboxed.** Only approved workloads run, and every package is checksum-verified.

## 9. Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| "Can't reach GreenTokens" | Pi, its power or its internet is down, or the computer is offline | Check the computer's internet, then ask the Pi manager |
| App shows Connected but no jobs arrive | No job has been submitted, or the customer key is not on the Pi | Submit a job from Databricks; ask the Pi manager to check the key |
| Sign-in screen after reopening | Saved sign-in expired or was revoked | Sign in again |
| Windows or Edge blocks the installer | Unsigned preview | Follow the [provider guide](provider-guide.md); do not override managed-device policy |
