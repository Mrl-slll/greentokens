"""Store the GreenTokens server address as the Databricks secret greentokens/url (your own workspace).

Uses your Databricks login in ~/.databrickscfg (created by the VS Code Databricks extension).
    python scripts/set_databricks_url.py https://<address>.trycloudflare.com
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("Usage: python scripts/set_databricks_url.py https://<server address>")
    cfg = Path.home() / ".databrickscfg"
    if not cfg.is_file():
        sys.exit("No ~/.databrickscfg found: set the secret greentokens/url in Databricks yourself.")
    lines = cfg.read_text(encoding="utf-8").splitlines()
    get = lambda k: next((l.split("=", 1)[1].strip() for l in lines if l.startswith(k + "=")), "")
    host, token = get("host").rstrip("/"), get("token")
    if not host or not token:
        sys.exit("~/.databrickscfg has no host/token: set the secret greentokens/url in Databricks yourself.")
    request = urllib.request.Request(host + "/api/2.0/secrets/put", method="POST",
                                     data=json.dumps({"scope": "greentokens", "key": "url", "string_value": sys.argv[1]}).encode(),
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as exc:
        sys.exit(f"Databricks refused the update (HTTP {exc.code}). Set greentokens/url by hand.")
    print("Databricks secret greentokens/url updated.")


if __name__ == "__main__":
    main()
