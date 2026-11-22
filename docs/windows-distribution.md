# Windows distribution: unsigned test releases (0.3.1, 0.4.0) and future signing

Versions 0.3.1 and 0.4.0 have an unsigned preview path for testing before identity verification. It does not establish SmartScreen reputation or bypass a security block. Future public release tags still require Windows signing and a permanent server address. The app, provider authentication, worker, FastAPI, Ray and MySQL are unchanged.

## Findings

- GitHub builds for commit `e5d1cb1` succeeded. The official 0.3.0 Windows asset is present; a combined artifact/download check is recorded in the task report.
- The provider download page and guides target 0.3.1. These links work only after its release is published.
- The release workflow creates a draft, uploads both installers plus SHA256SUMS.txt, checks uploaded digests, then publishes. Failed uploads remain private drafts. Existing versions are never overwritten. Only the tags listed in `UNSIGNED_PREVIEW_TAGS` (0.3.1, 0.4.0) are labeled unsigned; other tags still require signing.
- The observed uncommon-download warning is consistent with the confirmed unsigned installer. The separate Edge failure is not proven to be caused by the app. Defender history was inaccessible in the earlier inspection; organizational policy and network/browser failures have not been ruled out. Signing cannot override them.

## Options and costs (checked November 17, 2026)

| Option | Published price | Fit |
| --- | --- | --- |
| Microsoft Artifact Signing Basic | US $9.99/account/month; 5,000 signatures; $0.005/additional signature | Recommended service to evaluate, subject to eligibility and identity approval. Azure/GitHub OIDC integration requires provisioning and an approved signing-client dependency; not activated here. |
| DigiCert Software Trust Manager Essentials | Starts at $83/month, billed as a $1,000 annual subscription; confirm current signature allowance/terms | Managed HSM/CI option, higher cost; no purchase or SDK integration performed. |
| Existing CA-issued Authenticode certificate with HSM-backed Windows key provider | No additional certificate purchase if already owned; runner/HSM/renewal costs depend on your provider | Implemented integration uses Windows SDK SignTool and the CurrentUser certificate store. No private key export or new application dependency. |

Sources: [Microsoft pricing](https://learn.microsoft.com/azure/artifact-signing/how-to-change-sku), [Microsoft setup](https://learn.microsoft.com/azure/artifact-signing/quickstart), [DigiCert comparison](https://www.digicert.com/content/dam/digicert/pdfs/digicert-code-signing-cert-options-comparison.pdf). Prices exclude taxes and may vary. Do not purchase until the owner approves a provider, cost and legal publisher identity.

## Configure the implemented certificate-store signing path

1. Obtain a publicly trusted **code-signing** certificate for the verified legal publisher. A self-signed certificate or an HTTPS certificate is not suitable. Provision the non-exportable private key in the provider-approved HSM/token. Install its key provider on a dedicated Windows release runner so the certificate appears in `Cert:\CurrentUser\My` for the runner service account. Do not export keys or put PFX/passwords in this repository or logs.
2. Restrict that runner group to this repository's reviewed release workflow and protected tag refs. Do not expose a signing runner to PRs or untrusted branch code. Require review of release commits and protect creation of `provider-v*` tags. Use an isolated/ephemeral runner where possible.
3. Create protected GitHub environments `provider-signing` and `provider-release`, requiring a release-owner review and permitting only protected release tags. Ordinary branch builds use `provider-build` on hosted runners. No signing credentials are needed for branch builds.
4. Set repository variable `WINDOWS_SIGNING_RUNNER` to the runner labels as JSON, e.g. `["self-hosted","Windows","X64","provider-signing"]`. Set `WINDOWS_CERT_THUMBPRINT` in the signing environment to the certificate's public 40-character fingerprint. Set `WINDOWS_PUBLISHER` in both signing and release environments to the certificate's exact legal publisher CN. The runner needs Node, Rust/build tools and the Windows SDK. Hardware-provider credentials stay in its protected service configuration, not source files.
5. Set `GT_PROVIDER_SERVER` to a permanent HTTPS origin pointing to the backend. Signed release builds reject expiring `trycloudflare.com` quick tunnels. The backend can remain on this PC, but hostname ownership/tunnel configuration is a separate prerequisite; no domain has been purchased.
6. Increment package.json, its lockfile metadata, Cargo.toml, Cargo.lock as applicable, and tauri.conf.json together. Use a new signed-release tag, such as `provider-v0.3.2`, only after the matching version is reviewed.
7. Except for the listed unsigned previews, tag builds invoke Tauri's `signCommand` for the app executable and installer, using SHA-256 and an RFC3161 timestamp. Signature trust, configured signer and timestamp are required before upload. Any signing failure blocks publishing. The uploaded Windows checksum is generated **after** signing. Both platform jobs must succeed before publication.

The signing hook uses [Tauri 2's custom sign command](https://v2.tauri.app/distribute/sign/windows/), checked against the installed CLI 2.12.4 schema, and [Windows SDK SignTool](https://learn.microsoft.com/windows/win32/seccrypto/signtool). GitHub environments, certificate access and paid accounts have not been provisioned automatically.

## Installer behavior and remaining validation

Windows packaging remains NSIS, `currentUser`, Windows 10/11 **x64**. It does not request machine-wide installation. WebView2 setup is now visible rather than silent. Training setup remains an explicit consent step and installs into the app's private directory; code inspection found no GPU-driver installation. Uninstall uses Windows Settings → Apps. Publisher metadata is set to the certificate identity for signed builds.

Installation/uninstallation on clean Windows 10/11 machines and actual signing have **not** been exercised in this task. Only the requested release artifact/download-link check was run. Existing CI tests remain configured for future builds, but no CI run was triggered here. Do not advertise signed-release readiness until provisioning and a signed build succeed. Bundled third-party executables and downloaded runtimes may have separate reputation/policy requirements.

## Troubleshooting policy

Record Edge's exact error, release version, SHA-256, Windows/Edge versions and any Defender detection name. Use Ctrl+J and Windows Security → Protection history. Administrators approve managed-device installations. Report suspected false detections through Microsoft's official submission process after reviewing the file; never disable protection or ask users to override a block. [Microsoft download troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/microsoft-edge/development/download-failures).

Signing establishes publisher identity and integrity, not instant reputation: [Microsoft SmartScreen guidance](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation).
