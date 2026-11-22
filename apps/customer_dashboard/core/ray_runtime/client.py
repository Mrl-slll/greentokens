import subprocess
import sys
from pathlib import Path

from ray.job_submission import JobSubmissionClient


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
        return self.client.submit_job(entrypoint=entrypoint, submission_id=attempt.ray_submission_id,
                                      entrypoint_num_cpus=0)

    def stop(self, submission_id):
        self.client.stop_job(submission_id)

    def logs(self, submission_id):
        return self.client.get_job_logs(submission_id)
