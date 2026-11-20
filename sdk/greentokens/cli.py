import argparse
import json
from pathlib import Path
import sys
import tomllib
from uuid import uuid4

from . import Client, GreenTokensError


def load_pipeline(path):
    path = Path(path)
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    allowed = {"template_id", "idempotency_key", "data", "requirements"}
    if set(config) - allowed or config.get("template_id") not in {"sum_numbers_v1", "linear_regression_v1"}:
        raise ValueError("Unknown pipeline or fields. Use greentokens init for a supported configuration")
    data = config.get("data", {})
    if set(data) != {"file"} or not isinstance(data["file"], str):
        raise ValueError("Set [data] file to a local JSON dataset")
    source = path.parent / data["file"]
    if source.stat().st_size > 65536:
        raise ValueError("The MVP dataset limit is 65,536 bytes")
    parameters = json.loads(source.read_text(encoding="utf-8"))
    key = config.get("idempotency_key")
    if not isinstance(key, str) or not key:
        raise ValueError("Set a stable idempotency_key; change it for a new run")
    return config, parameters


def main(argv=None):
    parser = argparse.ArgumentParser(description="GreenTokens: submit approved local CPU pipelines")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--user", choices=["alice", "bob"], default="alice")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a training example without overwriting files")
    init.add_argument("directory", nargs="?", default="greentokens-example")
    commands.add_parser("check", help="Check backend and development identity")
    commands.add_parser("pipelines", help="List supported pipelines")
    for name in ("submit", "explain"):
        sub = commands.add_parser(name)
        sub.add_argument("pipeline")
    for name in ("status", "wait", "logs", "cancel", "result"):
        sub = commands.add_parser(name)
        sub.add_argument("job_id")
        if name == "result":
            sub.add_argument("--output", help="Save output JSON; refuses to overwrite")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            directory = Path(args.directory)
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "dataset.json").write_text('{"x":[0,1,2,3,4],"y":[1,3,5,7,9]}\n', encoding="utf-8")
            (directory / "training.toml").write_text(
                f'template_id = "linear_regression_v1"\nidempotency_key = "{uuid4()}"\n\n'
                '[data]\nfile = "dataset.json"\n\n[requirements]\ncpu_cores = 1\nram_gb = 0.125\ngpus = 0\n'
                'execution_class = "trusted_cpu"\nmax_runtime_seconds = 60\n', encoding="utf-8")
            print("Created training.toml and dataset.json. Run explain, then submit with the pipeline path.")
            return 0
        if args.command == "pipelines":
            print("sum_numbers_v1: connection test (CPU)\nlinear_regression_v1: fit y = slope*x + intercept (CPU)")
            return 0
        client = Client(args.endpoint, args.user)
        if args.command in {"explain", "submit"}:
            config, parameters = load_pipeline(args.pipeline)
            if args.command == "explain":
                print(f"Pipeline: {config['template_id']}\nLocal JSON -> API -> MySQL job input -> Ray CPU worker -> S3 output/logs -> API -> you.\n"
                      "This command sends no data. Submit copies the dataset into the job record.\n"
                      "No direct database credentials needed. Artifacts expire after 24 hours; this does not guarantee physical deletion.\n"
                      "The development backend and client must run on the same computer.")
                return 0
            response = client.submit(config["template_id"], parameters=parameters,
                                     idempotency_key=config["idempotency_key"], requirements=config.get("requirements"))
            print(json.dumps(response, indent=2))
            print(f"Open http://127.0.0.1:3000/jobs/{response['job_id']} in Live mode as {args.user}")
        elif args.command == "logs":
            job = client.status(args.job_id)
            logs = [a for a in job["artifacts"] if a["kind"] == "log"]
            if not logs:
                print("Logs are collected when the attempt finishes; check status first.")
            for artifact in logs:
                print(client.artifact(artifact["artifact_id"]).decode("utf-8", errors="replace"))
        else:
            response = getattr(client, args.command)(*([args.job_id] if hasattr(args, "job_id") else []))
            rendered = json.dumps(response, indent=2)
            if args.command == "result" and args.output:
                with Path(args.output).open("x", encoding="utf-8") as stream:
                    stream.write(rendered + "\n")
                print("Saved result JSON. Model parameters are under result.")
            else:
                print(rendered)
            if args.command == "wait" and response["status"] != "SUCCEEDED":
                return 1
        return 0
    except (GreenTokensError, ValueError, OSError, KeyError, TypeError):
        # Configs and connection errors may contain secrets; do not echo their content.
        print("Command failed. Check the local backend, pipeline syntax, file paths, identity, and job status. Existing files are never overwritten.", file=sys.stderr)
        return 1
