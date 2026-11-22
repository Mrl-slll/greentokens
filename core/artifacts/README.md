# Artifacts: object storage, checksums and expiry

[System guide](../../README.md) · [Backend](../README.md)

`storage.py:Storage` wraps boto3's S3 client. The server is SeaweedFS in Docker; the interface is S3-compatible. This is the **metadata/blob separation** pattern: MySQL knows who owns an artifact and where it is, while object storage holds its bytes.

Why use it: model archives can be much larger than status rows, and a consistent object API isolates most storage operations from the rest of the backend. Configuration currently requires a loopback S3 endpoint, so changing to remote managed storage is not just editing a URL.

## Write and read paths

1. `put()` checks the kind-specific limit, creates an opaque artifact ID and organization-scoped key, and uploads bytes.
2. It returns an `Artifact` metadata object containing key, SHA-256, byte count and expiry; the caller persists that object in its database transaction.
3. API ownership checks occur before `read()`.
4. `read()` rejects expired records, fetches bounded bytes, and verifies length and checksum before returning them.

The object upload and SQL transaction are not one atomic distributed transaction. Failed metadata commits or replaced uploads can leave orphaned objects; there is no automatic garbage collector.

## Limits and formats

| Kind | Typical content | Storage code limit |
| --- | --- | --- |
| `input` | Approved JSON input | Default 65,536 bytes |
| `output` | Result JSON | Default 65,536 bytes |
| `log` | Operational text | Default 65,536 bytes |
| `model` | Trained model archive/binary | 512 MiB |

Default TTL is 86,400 seconds. **Expired means inaccessible through this API, not physically erased.** Public proxies may impose stricter request-size/time limits than the storage code; a 512 MiB local allowance is not a guarantee of a successful public upload.

Error distinctions: `ARTIFACT_EXPIRED`, unavailable object, size/hash mismatch, or too-large upload. The API maps expiry to 410 and other storage read errors to 502. A checksum verifies transfer/storage consistency, not that a provider trained honestly.

## Operational checks

SeaweedFS is bound to `127.0.0.1:8333`; callers should normally use the GreenTokens API rather than direct object credentials. `/health` alone does not test storage. The real pipeline verifier exercises upload/result integrity. Back up the named storage volume and corresponding database metadata coherently. Four-PC relay files are a different storage path; see [experiments](../../experiments/README.md).
