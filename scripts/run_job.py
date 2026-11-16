"""Fixed local Ray Jobs entrypoint; customer input is loaded from MySQL."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.ray_runtime.runner import run


def load_private_env(argv):
    """Optional `--env-file PATH`: settings written by the dispatcher for this one job. Deleted once read."""
    if "--env-file" in argv:
        path = Path(argv[argv.index("--env-file") + 1])
        try:
            os.environ.update(json.loads(path.read_text(encoding="utf-8")))
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    load_private_env(sys.argv)
    sys.exit(run(sys.argv[1]))
