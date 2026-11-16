import json
import os
import socket
import sys
from uuid import UUID

import ray
from sqlalchemy import select

from core.api.schemas import BERT_CPUS_PER_WORKER, input_model
from core.training import train_linear
from core.artifacts.storage import Storage
from core.config import Settings
from core.database.models import Artifact, Attempt, Job, now
from core.database.session import database


@ray.remote(max_retries=0)
def calculate(template_id, data):
    value = train_linear(data) if template_id == "linear_regression_v1" else sum(data["values"])
    return {"result": value, "hostname": socket.gethostname(), "pid": os.getpid(),
            "node_id": ray.get_runtime_context().get_node_id()}


def run(attempt_id):
    UUID(attempt_id)
    settings = Settings.from_env()
    engine, sessions = database(settings)
    storage = Storage(settings)
    try:
        with sessions.begin() as db:
            attempt = db.get(Attempt, attempt_id)
            job = db.get(Job, attempt.job_id)
            if job.cancel_requested or job.status in {"FAILED", "CANCELLED", "SUCCEEDED"}:
                return 1
            attempt.started_at = now()
            if job.input_artifact_id:
                artifact = db.get(Artifact, job.input_artifact_id)
                if artifact.organization_id != job.organization_id or artifact.kind != "input":
                    raise ValueError("Unauthorized input")
                data = input_model(job.template_id).model_validate_json(storage.read(artifact)).model_dump()
            else:
                data = input_model(job.template_id).model_validate(job.parameters).model_dump()
            template_id = job.template_id
            requirements = job.requirements
            organization_id, job_id = job.organization_id, job.id
        model_artifact = None
        if template_id == "bert_tiny_ddp_v1":
            # Distributed training across one computer per worker; see core/workloads/ddp.py.
            from ray import cloudpickle
            from core.workloads import bert_tiny, ddp
            for module in (bert_tiny, ddp):
                cloudpickle.register_pickle_by_value(module)  # providers do not have this repository
            metrics, model_bytes = ddp.run_job(bert_tiny.BertTinyRecipe(data), data["workers"], data["steps"],
                                               data["sync_every"], BERT_CPUS_PER_WORKER, requirements["max_runtime_seconds"])
            result = {"result": metrics, "hostname": metrics["computers"][0]["host"], "pid": 0,
                      "node_id": metrics["computers"][0]["host"]}
            model_artifact = storage.put(organization_id, "model", model_bytes, job_id, attempt_id)
        else:
            ray.init(address="auto", logging_level="ERROR")
            ref = calculate.options(num_cpus=requirements["cpu_cores"], num_gpus=0,
                                    memory=int(requirements["ram_gb"] * 1024**3)).remote(template_id, data)
            result = ray.get(ref, timeout=requirements["max_runtime_seconds"])
        payload = json.dumps({"result": result["result"], "job_id": job_id,
                              "attempt_id": attempt_id}, sort_keys=True).encode()
        output = storage.put(organization_id, "output", payload, job_id, attempt_id)
        with sessions.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            attempt = db.get(Attempt, attempt_id)
            if job.cancel_requested or job.status in {"FAILED", "CANCELLED", "SUCCEEDED"}:
                return 1
            if not db.scalar(select(Artifact).where(Artifact.attempt_id == attempt_id, Artifact.kind == "output")):
                db.add(output)
                if model_artifact is not None:
                    db.add(model_artifact)
            attempt.worker_id = result["node_id"]
            attempt.worker_hostname = result["hostname"]
            attempt.worker_pid = result["pid"]
        print(f"Approved pipeline completed; attempt={attempt_id}; host={result['hostname']}", flush=True)
        return 0
    except Exception as exc:
        # Never emit connection URLs, credentials, customer values, or SDK exception text.
        print(f"Approved job failed: {type(exc).__name__} {getattr(exc, 'code', '')} {getattr(exc, 'args', [''])[0] if getattr(exc, 'code', None) else ''}".strip(), flush=True)
        return 1
    finally:
        ray.shutdown()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
