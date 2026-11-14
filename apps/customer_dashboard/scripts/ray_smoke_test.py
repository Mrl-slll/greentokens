"""Milestone 1: local Ray smoke test (eight deterministic CPU tasks)."""
import os
import socket
import sys

os.environ["RAY_USAGE_STATS_ENABLED"] = "0"
if not os.environ.get("RAY_ADDRESS"):
    os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "0"

import ray

N_TASKS = 8
TIMEOUT_S = 120


@ray.remote(num_cpus=1, num_gpus=0)
def sum_task(n: int) -> dict:
    return {
        "input": n,
        "result": sum(range(n + 1)),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "node_id": ray.get_runtime_context().get_node_id(),
    }


def main() -> int:
    address = os.environ.get("RAY_ADDRESS")
    try:
        if address:
            ray.init(address=address, include_dashboard=False, logging_level="ERROR")
        else:
            ray.init(
                address="local",
                include_dashboard=False,
                logging_level="ERROR",
                num_cpus=min(4, os.cpu_count() or 1),
                num_gpus=0,
                _node_ip_address="127.0.0.1",
            )
        print("Cluster resources:", ray.cluster_resources())
        print("Available resources:", ray.available_resources())

        inputs = [10_000 * (i + 1) for i in range(N_TASKS)]
        refs = [sum_task.remote(n) for n in inputs]  # submit all before collecting
        results = ray.get(refs, timeout=TIMEOUT_S)

        for n, r in zip(inputs, results):
            expected = n * (n + 1) // 2
            if r["input"] != n or r["result"] != expected:
                print(f"FAIL: input {n}: got {r['result']}, expected {expected}")
                return 1
            print(
                f"Task input={n} result={r['result']} "
                f"hostname={r['hostname']} pid={r['pid']} node_id={r['node_id']}"
            )

        hosts = sorted({r["hostname"] for r in results})
        print(f"Successful tasks: {len(results)}/{N_TASKS}")
        print("Hostnames:", hosts)
        print("Distinct worker PIDs:", len({r["pid"] for r in results}))
        print("Distinct node IDs:", len({r["node_id"] for r in results}))
        print("SMOKE TEST PASSED")
        return 0
    except Exception as exc:  # visible failure, nonzero exit
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    finally:
        ray.shutdown()


if __name__ == "__main__":
    sys.exit(main())
