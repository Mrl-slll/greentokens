# Databricks notebook source
import json
import sys

_here = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().rsplit("/", 1)[0]  # noqa: F821
sys.path.insert(0, "/Workspace" + _here)
from greentokens_client import DatabricksClient  # noqa: E402

dbutils.widgets.text("job_id", "")  # noqa: F821
dbutils.widgets.text("table", "workspace.default.greentokens_job_metrics")  # noqa: F821  (catalog.schema.table)

# COMMAND ----------
client = DatabricksClient(dbutils.secrets.get("greentokens", "url"), dbutils.secrets.get("greentokens", "token"))  # noqa: F821
job = client.status(dbutils.widgets.get("job_id"))  # noqa: F821
row = {"job_id": job["job_id"], "status": job["status"], "template_id": job["template_id"],
       "created_at": str(job["created_at"]), "updated_at": str(job["updated_at"]),
       "worker_hostname": job["attempts"][-1]["worker_hostname"] if job["attempts"] else None,
       "result_json": json.dumps(client.result(job["job_id"])) if job["status"] == "SUCCEEDED" else None}
df = spark.createDataFrame([row])  # noqa: F821
display(df)  # noqa: F821

# COMMAND ----------
# Only this job's own row (the API is organization-scoped) is written. If table creation is not allowed,
# the DataFrame above is all you get, and nothing appears in Catalog.
try:
    df.write.mode("append").saveAsTable(dbutils.widgets.get("table"))  # noqa: F821
    print("Saved to", dbutils.widgets.get("table"), "- check Catalog. (Unverified on Free Edition until you see it there.)")
except Exception as exc:
    print("LIMITATION: could not create the table, so nothing appears in Catalog. DataFrame only.", type(exc).__name__)
