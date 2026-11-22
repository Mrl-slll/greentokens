import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ray_smoke_test.py"


class RaySmokeTest(unittest.TestCase):
    def test_script_runs_and_validates_eight_tasks(self):
        env = {k: v for k, v in os.environ.items() if k != "RAY_ADDRESS"}
        env["RAY_USAGE_STATS_ENABLED"] = "0"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, timeout=240, env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Successful tasks: 8/8", proc.stdout)
        self.assertIn("SMOKE TEST PASSED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
