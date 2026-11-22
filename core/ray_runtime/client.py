import json
import os
import subprocess
import time
import sys
from pathlib import Path

from ray.job_submission import JobSubmissionClient


# Settings the runner needs. A group hosted by the provider agent does not inherit the backend's
# environment. They are handed over in a private one-time file on THIS computer (read and deleted by
# scripts/run_job.py), not in the job's runtime_env: a runtime_env is copied to every computer in the job
# and also changes how Ray starts workers (it breaks on a Mac path containing a space).
JOB_ENV_DIR = Path.home() / ".greentokens" / "jobenv"
FORWARDED_ENV = ("GT_MODE", "GT_DATABASE_URL", "GT_S3_ACCESS_KEY", "GT_S3_SECRET_KEY", "GT_S3_ENDPOINT",
                 "GT_RAY_ENDPOINT", "RAY_AUTH_MODE", "RAY_AUTH_TOKEN", "RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER",
                 "RAY_DEFAULT_PYTHON_VERSION_MATCH_LEVEL")


class RayJobs:
    def __init__(self, endpoint):
        self.client = JobSubmissionClient(endpoint)

    def status(self, submission_id):
        try:
            return self.client.get_job_status(submission_id).value
        except RuntimeError as exc:
            if "404" in str(exc):
                return None
            raise

    def submit(self, attempt):
        # Only trusted local code; no customer content is interpolated into this command.
        script = Path(__file__).resolve().parents[2] / "scripts" / "run_job.py"
        JOB_ENV_DIR.mkdir(parents=True, exist_ok=True)
        for stale in JOB_ENV_DIR.glob("*.json"):  # leftovers from jobs that never started
            if time.time() - stale.stat().st_mtime > 3600:
                stale.unlink(missing_ok=True)
        env_file = JOB_ENV_DIR / f"{attempt.id}.json"
        env_file.write_text(json.dumps({n: os.environ[n] for n in FORWARDED_ENV if n in os.environ}), encoding="utf-8")
        entrypoint = subprocess.list2cmdline([sys.executable, str(script), attempt.id, "--env-file", str(env_file)])
        return self.client.submit_job(entrypoint=entrypoint, submission_id=attempt.ray_submission_id,
                                      entrypoint_num_cpus=0)

    def stop(self, submission_id):
        self.client.stop_job(submission_id)

    def logs(self, submission_id):
        return self.client.get_job_logs(submission_id)
