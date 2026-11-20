# Provider installer download site

[System guide](../../README.md) · [Provider app](../provider_app/README.md) · [Delivery](../../.github/README.md)

`index.html` is a static download page. Static means a web server can serve these files without running FastAPI, a database or the training worker. The page explains the preview and links to release assets; it does not operate the provider API.

The current Windows/Mac links point to `provider-v0.3.1` GitHub release assets. Updating `provider-server.json` or starting another tunnel does not change those downloads. Changing this page also does not rebuild an installer.

`.github/workflows/provider-site.yml` copies this directory into a generated `gh-pages` branch, subject to its branch/event conditions. GitHub Pages must be configured for that branch. Do not assume any feature-branch edit publishes automatically.

When releasing: build/verify the installer first, publish the intended release when authorized, then align links/checksums and explanatory text. Verify the bytes actually served by the link. The website can remain online while the development PC's API is offline, because they are different services.
