# Databricks notebook source
import sys
import uuid

_here = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().rsplit("/", 1)[0]  # noqa: F821
sys.path.insert(0, "/Workspace" + _here)
from greentokens_client import DatabricksClient  # noqa: E402

dbutils.widgets.dropdown("template", "linear_regression_v1", ["linear_regression_v1", "sum_numbers_v1"])  # noqa: F821
dbutils.widgets.text("request_id", "")  # noqa: F821  (reuse the same value to retry safely)

# COMMAND ----------
client = DatabricksClient(dbutils.secrets.get("greentokens", "url"), dbutils.secrets.get("greentokens", "token"))  # noqa: F821
template = dbutils.widgets.get("template")  # noqa: F821
key = dbutils.widgets.get("request_id") or str(uuid.uuid4())  # noqa: F821
params = {"x": [1, 2, 3, 4, 5], "y": [1, 3, 5, 7, 9]} if template == "linear_regression_v1" else {"values": [1, 2, 3]}
job = client.submit(template, idempotency_key=key, parameters=params)
print("Submitted. job_id =", job["job_id"], "| status =", job["status"], "| request_id =", key)
print("Training runs on GreenTokens computers. Use 02_View_Results later; nothing keeps running here.")
dbutils.notebook.exit(job["job_id"])  # noqa: F821
