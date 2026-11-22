# Infrastructure: containers and persistent volumes

[System guide](../README.md) · [Operations](../scripts/README.md)

`compose.yaml` is a **Docker Compose deployment definition** for two supporting services. It does not containerize the entire platform: API, dispatcher, Ray and Next.js currently run on the host.

| Service | Image in this checkout | Host listener | Persistent data |
| --- | --- | --- | --- |
| MySQL | `mysql:8.4` | `127.0.0.1:3307` | Named `mysql-data` volume |
| SeaweedFS | `chrislusf/seaweedfs:4.53` | `127.0.0.1:8333` | Named `s3-data` volume |

The Compose project is `greentokens-dev`, with dedicated container names. Loopback publication keeps database/storage off the LAN. Image tags are not immutable image digests; MySQL's tag follows its maintenance line.

## Why containers and volumes

Containers package service dependencies separately from Python/Node tooling. Volumes keep service data after process/container restarts. They are not backups and are not automatically replicated to another computer.

The launcher generates credentials in memory on initial setup, passes them into Compose and recovers them from the dedicated labeled containers later. Therefore invoke [the launcher](../scripts/local_stack.py), rather than expecting a bare `docker compose up` with unset credential variables to succeed. `.env.example` documents variables but is not automatically loaded by the Python launcher.

Do not print `docker inspect` or resolved `docker compose config`: credentials can appear in their output. Container logging is disabled in this definition to avoid bootstrap credential output.

## Lifecycle and gaps

Stop without deleting data:

```powershell
docker stop greentokens-dev-mysql greentokens-dev-storage
```

Do not use volume deletion as routine reset/shutdown. Deleting containers while retaining volumes can also require credential recovery because the launcher reads credentials from container configuration.

There are currently no Compose restart policies or declarative healthchecks. The Python launcher performs database/S3 readiness checks. Docker Desktop normally depends on the desktop user's session for automatic startup, so this is not yet a tested unattended boot deployment. See [availability roadmap](../docs/roadmap.md).

Backups need both database metadata and object data; experiment relay files require separate handling. Recovery must be tested, not inferred from the existence of a volume.
