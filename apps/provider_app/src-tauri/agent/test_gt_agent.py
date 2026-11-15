"""Unit tests for gt_agent (standard library only; no Ray process is started)."""
import unittest

import gt_agent as g

TOKEN = "0123456789abcdef0123456789abcdef"

STATUS = """======== Autoscaler status: 2026-11-15 10:00:00 ========
Node status
---------------------------------------------------------------
Active:
 1 node_3f2a9c0d1e
Idle:
 1 node_77b1aa20ff
Pending:
 (no pending nodes)
Recent failures:
 (no failures)

Resources
---------------------------------------------------------------
Usage:
 0.0/6.0 CPU
"""


class CodeTests(unittest.TestCase):
    def test_valid_code(self):
        self.assertEqual(g.parse_code(f"GT1-192.168.1.20-{TOKEN}"), ("192.168.1.20", TOKEN))
        self.assertEqual(g.parse_code(f"  GT1-10.0.0.5-{TOKEN}\n"), ("10.0.0.5", TOKEN))

    def test_rejects_bad_codes(self):
        for bad in ["", "hello", f"GT1-8.8.8.8-{TOKEN}", f"GT1-127.0.0.1-{TOKEN}", f"GT1-999.1.1.1-{TOKEN}",
                    f"GT1-192.168.1.20-{TOKEN.upper()}", f"GT1-192.168.1.20-{TOKEN}; calc", "GT1-192.168.1.20-abc"]:
            with self.subTest(bad=bad), self.assertRaises(g.Friendly):
                g.parse_code(bad)


class StatusTests(unittest.TestCase):
    def test_counts_active_and_idle_nodes(self):
        self.assertEqual(g.parse_active_nodes(STATUS), 2)

    def test_no_nodes(self):
        self.assertEqual(g.parse_active_nodes("Active:\n (no active nodes)\nPending:\n (no pending nodes)\n"), 0)


class ArgsTests(unittest.TestCase):
    def test_node_args_use_fixed_ports_covered_by_firewall(self):
        args = g.node_args(3, "192.168.1.20")
        self.assertIn("--num-cpus", args)
        self.assertEqual(args[args.index("--num-cpus") + 1], "3")
        self.assertEqual(args[args.index("--num-gpus") + 1], "0")
        ports = [int(args[args.index(flag) + 1]) for flag in g.FIXED_PORTS]
        ports += [g.GCS_PORT, g.CLIENT_SERVER_PORT]
        self.assertTrue(all(6379 <= p <= 6386 for p in ports))
        self.assertEqual(g.WORKER_PORTS, (10002, 10101))
        self.assertEqual(g.FIREWALL_PORTS, ["6379-6386", "10002-10101"])

    def test_env_enables_token_auth_and_windows_cluster(self):
        env = g.ray_env(TOKEN)
        self.assertEqual(env["RAY_AUTH_MODE"], "token")
        self.assertEqual(env["RAY_AUTH_TOKEN"], TOKEN)
        self.assertEqual(env["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"], "1")

    def test_cpu_limit_validated(self):
        with self.assertRaises(g.Friendly):
            g.main(["stop", "--cpus", "0"])


if __name__ == "__main__":
    unittest.main()
