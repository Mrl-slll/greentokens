# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Submit a training job
# MAGIC Sends **one** job to GreenTokens, prints its **job id**, and finishes. Nothing keeps running here.
# MAGIC The training itself runs on GreenTokens computers (not on Databricks).
# MAGIC
# MAGIC * `bert_tiny_ddp_v1`: fine-tune a small BERT model (movie-review sentiment) across **N computers at once**.
# MAGIC * `linear_regression_v1`, `sum_numbers_v1`: tiny sample jobs that run on one computer.
# MAGIC
# MAGIC Next: copy the job id, open **02_View_Results**, paste it, and run.

# COMMAND ----------
import sys
import uuid

_here = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().rsplit("/", 1)[0]  # noqa: F821
sys.path.insert(0, "/Workspace" + _here)
from greentokens_client import DatabricksClient  # noqa: E402

dbutils.widgets.dropdown("template", "bert_tiny_ddp_v1", ["bert_tiny_ddp_v1", "linear_regression_v1", "sum_numbers_v1"])  # noqa: F821
dbutils.widgets.text("workers", "2", "Computers (bert only)")  # noqa: F821
dbutils.widgets.text("steps", "100", "Training steps (bert only)")  # noqa: F821
dbutils.widgets.text("examples", "480", "Training examples (bert only)")  # noqa: F821
dbutils.widgets.text("sync_every", "50", "Share results every N steps (bert only)")  # noqa: F821
dbutils.widgets.text("scope", "greentokens", "Secret scope")  # noqa: F821
dbutils.widgets.text("request_id", "", "Request id (leave empty for a new job)")  # noqa: F821

# COMMAND ----------
get = dbutils.widgets.get  # noqa: F821
client = DatabricksClient(dbutils.secrets.get(get("scope"), "url"), dbutils.secrets.get(get("scope"), "token"))  # noqa: F821
template = get("template")
key = get("request_id") or str(uuid.uuid4())

if template == "bert_tiny_ddp_v1":
    params = {"workers": int(get("workers")), "steps": int(get("steps")), "examples": int(get("examples")),
              "sync_every": int(get("sync_every")), "global_batch": 96, "max_length": 128, "eval_examples": 200}
    requirements = {"max_runtime_seconds": 1800}
elif template == "linear_regression_v1":
    params, requirements = {"x": [1, 2, 3, 4, 5], "y": [1, 3, 5, 7, 9]}, None
else:
    params, requirements = {"values": [1, 2, 3]}, None

job = client.submit(template, idempotency_key=key, parameters=params, requirements=requirements)
print("Submitted.")
print("  job_id     =", job["job_id"])
print("  status     =", job["status"])
print("  request_id =", key, "(re-running with this same value will NOT start a second job)")
if template == "bert_tiny_ddp_v1":
    print(f"Training on {params['workers']} computer(s). Usually 1-3 minutes. Run 02_View_Results with the job id.")
dbutils.notebook.exit(job["job_id"])  # noqa: F821
