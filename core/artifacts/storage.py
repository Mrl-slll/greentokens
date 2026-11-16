import hashlib
from datetime import timedelta

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from core.database.models import Artifact, now, uid


# Trained models are large; only this kind may exceed the normal small-artifact limit.
LARGE_KIND_LIMITS = {"model": 64 * 1024 * 1024}


class ArtifactError(Exception):
    pass


class Storage:
    def __init__(self, settings):
        self.settings = settings
        self.client = boto3.client(
            "s3", endpoint_url=settings.s3_endpoint, region_name="us-east-1",
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                          connect_timeout=5, read_timeout=60, retries={"max_attempts": 2}),
        )

    def ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.settings.bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
                raise
            self.client.create_bucket(Bucket=self.settings.bucket)

    def put(self, organization_id, kind, data, job_id=None, attempt_id=None):
        if len(data) > LARGE_KIND_LIMITS.get(kind, self.settings.max_bytes):
            raise ArtifactError("ARTIFACT_TOO_LARGE")
        artifact_id = uid()
        key = f"{organization_id}/{artifact_id}/{kind}"
        self.client.put_object(Bucket=self.settings.bucket, Key=key, Body=data,
                               ContentType={"log": "text/plain", "model": "application/octet-stream"}.get(kind, "application/json"))
        return Artifact(id=artifact_id, organization_id=organization_id,
                        job_id=job_id, attempt_id=attempt_id, object_key=key,
                        kind=kind, sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data),
                        expires_at=now() + timedelta(seconds=self.settings.artifact_ttl_seconds))

    def read(self, artifact):
        if artifact.expires_at <= now():
            raise ArtifactError("ARTIFACT_EXPIRED")
        try:
            response = self.client.get_object(Bucket=self.settings.bucket, Key=artifact.object_key)
            stream = response["Body"]
            try:
                data = stream.read(LARGE_KIND_LIMITS.get(artifact.kind, self.settings.max_bytes) + 1)
            finally:
                stream.close()
        except ClientError as exc:
            raise ArtifactError("ARTIFACT_UNAVAILABLE") from exc
        if len(data) != artifact.size_bytes or hashlib.sha256(data).hexdigest() != artifact.sha256:
            raise ArtifactError("ARTIFACT_INTEGRITY_FAILED")
        return data
