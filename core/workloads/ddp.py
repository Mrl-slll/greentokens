"""Generic synchronous data-parallel training across computers in a Ray cluster.

One worker per computer (placement group STRICT_SPREAD). Computers exchange results through Ray's own
transfer rather than torch.distributed/Gloo: Gloo advertises addresses a Windows computer and a Mac cannot
use with each other (see memory: two-computer-training-scenarios). Every computer starts from rank 0's exact
weights, trains on its own disjoint slice, and the models are averaged:
  sync_every == 1  -> average gradients every step (standard data parallel)
  sync_every  > 1  -> average the model every N steps and at the last step ("local SGD", far less traffic)
Heavy libraries are imported inside methods; this module is shipped to providers by value.
"""
import json
import time


class TrainingError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


class Reducer:
    """Meeting point: workers hand over a reference to their data; the bytes move computer-to-computer via Ray."""

    def __init__(self, world):
        import asyncio
        self.world, self.data, self.events, self.asyncio = world, {}, {}, asyncio

    async def exchange(self, step, rank, refs):
        slot = self.data.setdefault(step, {})
        event = self.events.setdefault(step, self.asyncio.Event())
        slot[rank] = refs[0]
        if len(slot) == self.world:
            event.set()
        await event.wait()
        result = [slot[r] for r in sorted(slot)]
        for old in [s for s in self.data if s < step - 2]:
            self.data.pop(old, None)
            self.events.pop(old, None)
        return result


class Worker:
    def info(self):
        import platform, socket
        import ray
        return {"host": socket.gethostname(), "os": f"{platform.system()} {platform.machine()}",
                "python": platform.python_version(), "ray": ray.__version__, "ip": ray.util.get_node_ip_address()}

    def train(self, recipe, reducer, rank, world, steps, sync_every, threads):
        import socket
        import numpy as np
        import ray
        import torch
        torch.set_num_threads(threads)
        model = recipe.build()
        params = [p for p in model.parameters() if p.requires_grad]

        def flat(tensors):
            return torch.cat([t.reshape(-1) for t in tensors]).detach().numpy()

        def load_flat(vector, tensors):
            offset = 0
            with torch.no_grad():
                for t in tensors:
                    t.copy_(torch.from_numpy(vector[offset:offset + t.numel()].copy()).view_as(t))
                    offset += t.numel()

        def exchange(key, vector):
            refs = ray.get(reducer.exchange.remote(key, rank, [ray.put(vector)]))
            return [ray.get(r) for r in refs]

        load_flat(exchange(-1, flat(params))[0], params)  # everyone starts from rank 0's weights
        batch = recipe.batches(rank, world)
        before = recipe.evaluate(model) if rank == 0 else None
        opt = torch.optim.AdamW(params, lr=5e-5)
        model.train()
        losses, sync_seconds = [], 0.0
        started = time.perf_counter()
        for step in range(steps):
            loss = recipe.loss(model, batch(step))
            opt.zero_grad()
            loss.backward()
            if sync_every == 1:
                t = time.perf_counter()
                grads = exchange(step, flat([p.grad for p in params]))
                sync_seconds += time.perf_counter() - t
                average, offset = np.mean(grads, axis=0), 0
                for p in params:
                    p.grad.copy_(torch.from_numpy(average[offset:offset + p.numel()].copy()).view_as(p))
                    offset += p.numel()
                opt.step()
            else:
                opt.step()
                if (step + 1) % sync_every == 0 or step == steps - 1:
                    t = time.perf_counter()
                    load_flat(np.mean(exchange(step, flat(params)), axis=0), params)
                    sync_seconds += time.perf_counter() - t
            losses.append(float(loss.item()))
        elapsed = time.perf_counter() - started
        result = {"rank": rank, "host": socket.gethostname(), "steps": steps, "first_loss": round(losses[0], 4),
                  "last_loss": round(sum(losses[-5:]) / len(losses[-5:]), 4), "seconds": round(elapsed, 2),
                  "sync_seconds": round(sync_seconds, 2), "train_seconds": round(elapsed - sync_seconds, 2),
                  "samples_per_second": round(batch.per_worker * world * steps / elapsed, 1),
                  "weights_checksum": round(sum(p.detach().double().sum().item() for p in params), 6)}
        if rank == 0:
            result.update({"eval_before": before, "eval_after": recipe.evaluate(model), "model": recipe.save(model)})
        return result


def run_job(recipe, workers, steps, sync_every, cpus_per_worker, timeout_seconds):
    """Driver side (runs inside the Ray job on the server). Returns (metrics_dict, model_bytes)."""
    import ray
    from ray.util.placement_group import placement_group, remove_placement_group
    from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy
    ray.init(address="auto", logging_level="ERROR")
    nodes = [n for n in ray.nodes() if n["Alive"] and n["Resources"].get("CPU", 0) >= cpus_per_worker]
    if len(nodes) < workers:
        raise TrainingError("NOT_ENOUGH_COMPUTERS", f"{len(nodes)} computers online, {workers} needed")
    pg = placement_group([{"CPU": cpus_per_worker}] * workers, strategy="STRICT_SPREAD")
    try:
        ray.get(pg.ready(), timeout=60)
    except Exception:
        raise TrainingError("NOT_ENOUGH_COMPUTERS", "could not reserve one computer per worker") from None
    deadline = time.monotonic() + timeout_seconds
    try:
        actors = [ray.remote(num_cpus=cpus_per_worker)(Worker).options(
            scheduling_strategy=PlacementGroupSchedulingStrategy(pg, i)).remote() for i in range(workers)]
        infos = ray.get([a.info.remote() for a in actors], timeout=120)
        if len({(i["python"].rsplit(".", 1)[0], i["ray"]) for i in infos}) > 1:
            raise TrainingError("VERSION_MISMATCH", json.dumps(infos))
        reducer = ray.remote(num_cpus=0, max_concurrency=32)(Reducer).remote(workers)
        results = ray.get([a.train.remote(recipe, reducer, r, workers, steps, sync_every, max(1, cpus_per_worker))
                           for r, a in enumerate(actors)], timeout=max(1, deadline - time.monotonic()))
    except TrainingError:
        raise
    except Exception as exc:
        raise TrainingError("PROVIDER_LOST" if "died" in str(exc).lower() or "ActorDied" in type(exc).__name__
                            else "TRAINING_FAILED", f"{type(exc).__name__}: {str(exc)[:200]}") from None
    finally:
        remove_placement_group(pg)
    if len({r["weights_checksum"] for r in results}) != 1:
        raise TrainingError("REPLICAS_DIVERGED")
    lead = results[0]
    model = lead.pop("model")
    computers = []
    for r, info in zip(results, infos):
        computers.append({**{k: info[k] for k in ("host", "os", "python", "ray")},
                          **{k: r[k] for k in ("rank", "train_seconds", "sync_seconds", "seconds", "last_loss")}})
    metrics = {"workers": workers, "steps": steps, "sync_every": sync_every, "first_loss": lead["first_loss"],
               "last_loss": lead["last_loss"], "eval_before": lead["eval_before"], "eval_after": lead["eval_after"],
               "wall_seconds": lead["seconds"], "samples_per_second": lead["samples_per_second"],
               "weights_identical_on_all_computers": True, "computers": computers}
    return metrics, model
