import os
import subprocess
import sys
from pathlib import Path

from ray.job_submission import JobSubmissionClient


# Settings the runner needs. A group hosted by the provider agent does not inherit the backend's
# environment, so pass these explicitly. Database/storage endpoints are loopback-only, which makes
# the values useless on any other computer in the group.
FORWARDED_ENV = ("GT_MODE", "GT_DATABASE_URL", "GT_S3_ACCESS_KEY", "GT_S3_SECRET_KEY", "GT_S3_ENDPOINT",
                 "GT_RAY_ENDPOINT", "RAY_AUTH_MODE", "RAY_AUTH_TOKEN", "RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER")


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
        entrypoint = subprocess.list2cmdline([sys.executable, str(script), attempt.id])
        env_vars = {name: os.environ[name] for name in FORWARDED_ENV if name in os.environ}
        return self.client.submit_job(entrypoint=entrypoint, submission_id=attempt.ray_submission_id,
                                      entrypoint_num_cpus=0, runtime_env={"env_vars": env_vars})

    def stop(self, submission_id):
        self.client.stop_job(submission_id)

    def logs(self, submission_id):
        return self.client.get_job_logs(submission_id)
