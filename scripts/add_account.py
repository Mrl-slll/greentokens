"""Create a GreenTokens account and print its key ONCE (only a hash is stored).

    python -m scripts.add_account <name> --provider --server https://<tunnel-or-server-address>
        -> prints an INVITE CODE for a provider computer (server address + key in one line)
    python -m scripts.add_account <name> --customer
        -> prints a customer key for Databricks (secret scope "greentokens", key "token")

Each account gets its own organization, so customers never see each other's jobs and provider
accounts cannot submit or read customer jobs. Keys are added to ~/.greentokens/api_keys.json
(hashes only); the running backend picks them up without a restart.
"""
import argparse
import base64
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

KEYS_FILE = Path.home() / ".greentokens" / "api_keys.json"


def invite_code(server, key, name):
    payload = json.dumps({"u": server.rstrip("/"), "k": key, "n": name}, separators=(",", ":")).encode()
    return "gtinv1." + base64.urlsafe_b64encode(payload).decode().rstrip("=")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="lowercase letters, digits and dashes, e.g. rtx-pc-1")
    role = parser.add_mutually_exclusive_group(required=True)
    role.add_argument("--provider", action="store_true")
    role.add_argument("--customer", action="store_true")
    parser.add_argument("--server", help="public https address of the GreenTokens server (needed for --provider)")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", args.name) or args.name in {"alice", "bob", "admin"}:
        sys.exit("Choose a name of 3-32 lowercase letters, digits or dashes (not alice/bob/admin).")
    if args.provider and not (args.server or "").startswith("https://"):
        sys.exit("--provider needs --server https://... (the address provider computers will connect to).")

    from scripts.local_stack import configure, services
    from core.database.models import Organization, User
    configure()
    _, engine, sessions, _ = services()
    with sessions.begin() as db:
        if db.get(User, args.name):
            sys.exit(f"Account {args.name} already exists. Pick another name.")
        org = f"org-{args.name}"
        db.add(Organization(id=org, name=f"{'Provider' if args.provider else 'Customer'} {args.name}"))
        db.flush()
        db.add(User(id=args.name, organization_id=org, role="provider" if args.provider else "customer"))
    engine.dispose()

    key = "gt_" + secrets.token_urlsafe(32)
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    keys = json.loads(KEYS_FILE.read_text(encoding="utf-8")) if KEYS_FILE.is_file() else {}
    keys[hashlib.sha256(key.encode()).hexdigest()] = args.name
    KEYS_FILE.write_text(json.dumps(keys, indent=1), encoding="utf-8")

    print(f"Created {'provider' if args.provider else 'customer'} account '{args.name}'. Shown once, keep it private:\n")
    if args.provider:
        print("Invite code for the provider computer (paste it into the GreenTokens Provider app):")
        print(invite_code(args.server, key, args.name))
    else:
        print("Customer key (store in Databricks as secret greentokens/token):")
        print(key)


if __name__ == "__main__":
    main()
