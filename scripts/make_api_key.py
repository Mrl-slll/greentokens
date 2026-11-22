"""Create an API key for an existing GreenTokens user.

Usage: python scripts/make_api_key.py alice

Prints the key ONCE (store it in the Databricks secret scope 'greentokens', key 'token')
and the GT_API_KEYS value for the backend. Only the SHA-256 hash goes to the server.
"""
import hashlib
import json
import secrets
import sys

if len(sys.argv) != 2 or sys.argv[1] not in {"alice", "bob"}:
    sys.exit("Usage: python scripts/make_api_key.py alice|bob")
key = "gt_" + secrets.token_urlsafe(32)
print("API key (shown once, keep it secret):", key)
print("Backend env var (hash only):")
print("GT_API_KEYS=" + json.dumps({hashlib.sha256(key.encode()).hexdigest(): sys.argv[1]}))
