# Build, release and hosting automation

[System guide](../README.md) · [Provider component](../apps/provider_app/README.md)

GitHub Actions is **CI/CD automation**: workflows respond to repository events, run checks/builds and sometimes publish outputs. A workflow definition is not evidence that a particular build or deployment succeeded.

## Workflows

- `workflows/provider-app.yml`: provider frontend checks, Windows/macOS installer builds and controlled release paths. Builds need Node, Rust/native platform tools and bundled runtime provisioning. `GT_PROVIDER_SERVER` can override the origin used by a build. Read the workflow for exact event, branch, environment and signing conditions.
- `workflows/provider-site.yml`: copies `apps/provider_site/` to `gh-pages`; its job permits `provider-app` or `main`, not every feature branch. GitHub Pages settings remain an external prerequisite.

## Release identity

```text
source commit + build configuration + toolchain
    → compiled app / installer
    → workflow artifact
    → published release asset
    → download-page link
    → user's installed process
```

Each arrow is a separate operation. A new source URL does not rewrite an existing installer. Downloading an unchanged asset cannot fix its old embedded API origin. A workflow artifact is not automatically a public release asset.

Version 0.3.1 is an unsigned preview with a specific exception in the workflow. Future signed release paths require the provisioning described in [Windows distribution](../docs/windows-distribution.md). Do not relabel an unsigned build as signed or instruct users to bypass managed device policy.

For review, capture commit SHA, origin (public, nonsecret), version, build result and installer checksum. Keep signing keys, API keys and session tokens out of the repository and logs. The user authorized this documentation branch push. Push-triggered CI may run under existing workflow rules; this commit does not create a release tag or request publication of installer assets. Other GitHub mutations require their own authorization.
