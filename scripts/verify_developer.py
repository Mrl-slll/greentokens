"""Exercise the source SDK and real CPU training via the running local stack."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from greentokens import Client, GreenTokensError
from greentokens.cli import main, load_pipeline


def verify():
    client = Client()
    assert client.check()["status"] == "ok"
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "training"
        assert main(["init", str(project)]) == 0
        pipeline = str(project / "training.toml")
        assert main(["explain", pipeline]) == 0
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert main(["submit", pipeline]) == 0
        submitted, _ = json.JSONDecoder().raw_decode(output.getvalue())
        job_id = submitted["job_id"]
        config, data = load_pipeline(pipeline)
        replay = client.submit(config["template_id"], parameters=data,
                               idempotency_key=config["idempotency_key"], requirements=config["requirements"])
        assert replay["job_id"] == job_id
        job = client.wait(job_id)
        assert job["status"] == "SUCCEEDED", job["error_code"]
        model = client.result(job_id)["result"]
        assert model["slope"] == 2 and model["intercept"] == 1 and model["training_mse"] == 0
        path = Path(tmp) / "model.json"
        assert main(["result", job_id, "--output", str(path)]) == 0
        assert json.loads(path.read_text())["result"] == model
        assert main(["logs", job_id]) == 0
        try:
            Client(user="bob").result(job_id)
        except GreenTokensError:
            pass
        else:
            raise AssertionError("Foreign identity read training output")
        print(f"PASS CLI training, retry, downloaded model, logs, isolation; job={job_id}", flush=True)
        upload = client.upload(data)
        second = client.submit("linear_regression_v1", input_artifact_id=upload["artifact_id"], idempotency_key=str(uuid4()))
        assert client.wait(second["job_id"])["status"] == "SUCCEEDED"
        assert client.result(second["job_id"])["result"] == model
        print("PASS SDK training from uploaded S3 dataset", flush=True)


if __name__ == "__main__":
    verify()
