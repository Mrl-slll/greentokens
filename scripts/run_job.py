"""Fixed local Ray Jobs entrypoint; customer input is loaded from MySQL."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.ray_runtime.runner import run

if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
