# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · View results
# MAGIC Paste the **job id** from notebook 01 into the box at the top, then **Run all**.
# MAGIC You will see: the job's status, accuracy before and after training, **one row per computer that took part**,
# MAGIC and the trained model's size and checksum. The results are also saved as tables in **Catalog**
# MAGIC (`workspace > default > greentokens_training_jobs` and `greentokens_training_computers`) if your workspace allows it.

# COMMAND ----------
import hashlib
import sys

_here = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().rsplit("/", 1)[0]  # noqa: F821
sys.path.insert(0, "/Workspace" + _here)
from greentokens_client import DatabricksClient, model_artifact_id, summarize  # noqa: E402

dbutils.widgets.text("job_id", "", "Job id")  # noqa: F821
dbutils.widgets.text("scope", "greentokens", "Secret scope")  # noqa: F821
dbutils.widgets.text("table_prefix", "workspace.default.greentokens", "Catalog table prefix")  # noqa: F821
dbutils.widgets.dropdown("download_model", "no", ["no", "yes"], "Download the trained model file")  # noqa: F821

# COMMAND ----------
get = dbutils.widgets.get  # noqa: F821
client = DatabricksClient(dbutils.secrets.get(get("scope"), "url"), dbutils.secrets.get(get("scope"), "token"))  # noqa: F821
job = client.status(get("job_id").strip())
result = client.result(job["job_id"]) if job["status"] == "SUCCEEDED" else None
summary, rows = summarize(job, result)
print(f"Job {job['job_id']}: {job['status']}" + (f" ({job['error_code']})" if job.get("error_code") else ""))
if job["status"] not in ("SUCCEEDED",):
    print("Not finished successfully yet. Run this notebook again in a minute." if job["status"] in ("QUEUED", "DISPATCHING", "RUNNING")
          else "The job did not succeed; the error code above says why.")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Summary

# COMMAND ----------
display(spark.createDataFrame([(k, "" if v is None else str(v)) for k, v in summary.items() if k != "result_json"],  # noqa: F821
                              ["field", "value"]))

# COMMAND ----------
# MAGIC %md
# MAGIC ### Computers that trained (one row each)

# COMMAND ----------
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType  # noqa: E402

num = lambda v: None if v is None else float(v)  # noqa: E731
computer_schema = StructType([StructField(n, t, True) for n, t in [
    ("job_id", StringType()), ("rank", IntegerType()), ("computer", StringType()), ("os", StringType()),
    ("python", StringType()), ("ray", StringType()), ("gpu", StringType()), ("device", StringType()),
    ("train_seconds", DoubleType()), ("sync_seconds", DoubleType()),
    ("total_seconds", DoubleType()), ("last_loss", DoubleType())]])
computers = spark.createDataFrame([(r["job_id"], r["rank"], r["computer"], r["os"], r["python"], r["ray"], r["gpu"], r["device"],  # noqa: F821
                                    num(r["train_seconds"]), num(r["sync_seconds"]), num(r["total_seconds"]), num(r["last_loss"]))
                                   for r in rows], computer_schema)
display(computers)  # noqa: F821
if rows:
    slow = max(rows, key=lambda r: r["train_seconds"] or 0)
    print(f"{len(rows)} computers trained together. The slowest was {slow['computer']} "
          f"({slow['train_seconds']} s training); the others waited for it at the sharing points.")

# COMMAND ----------
summary_schema = StructType([StructField(n, t, True) for n, t in [
    ("job_id", StringType()), ("status", StringType()), ("template_id", StringType()), ("created_at", StringType()),
    ("updated_at", StringType()), ("error_code", StringType()), ("computers", IntegerType()), ("computer_names", StringType()),
    ("accuracy_before", DoubleType()), ("accuracy_after", DoubleType()), ("first_loss", DoubleType()), ("last_loss", DoubleType()),
    ("wall_seconds", DoubleType()), ("model_name", StringType()), ("device", StringType()), ("gpu", StringType()),
    ("model_mb", DoubleType()), ("model_sha256", StringType()), ("result_json", StringType())]])
doubles = {"accuracy_before", "accuracy_after", "first_loss", "last_loss", "wall_seconds", "model_mb"}
summary_df = spark.createDataFrame([tuple(num(summary[f.name]) if f.name in doubles else summary[f.name]  # noqa: F821
                                          for f in summary_schema.fields)], summary_schema)

# Save to Catalog. Only this job's own rows; rerunning replaces them instead of duplicating.
prefix = get("table_prefix")
try:
    for table, frame in ((f"{prefix}_training_jobs", summary_df), (f"{prefix}_training_computers", computers)):
        if spark.catalog.tableExists(table):  # noqa: F821
            spark.sql(f"DELETE FROM {table} WHERE job_id = '{job['job_id']}'")  # noqa: F821
        frame.write.mode("append").option("mergeSchema", "true").saveAsTable(table)
    print(f"Saved to Catalog: {prefix}_training_jobs and {prefix}_training_computers")
except Exception as exc:
    print("LIMITATION: could not save to Catalog, so nothing appears there. The tables above still show the results.",
          type(exc).__name__)

# COMMAND ----------
# MAGIC %md
# MAGIC ### Download the trained model (optional)
# MAGIC Set the widget **Download the trained model file** to `yes` and run this cell. The file is checked against its checksum.

# COMMAND ----------
model_id = model_artifact_id(job)
if get("download_model") == "yes":
    if not model_id:
        print("This job has no model file.")
    else:
        data = client.artifact(model_id)
        ok = hashlib.sha256(data).hexdigest() == summary["model_sha256"]
        path = f"/tmp/{job['job_id']}.safetensors"
        with open(path, "wb") as f:
            f.write(data)
        print(f"Downloaded {len(data) / 1e6:.1f} MB to {path}. Checksum matches: {ok}")
else:
    print("Model file:", f"{summary['model_mb']} MB, sha256 {summary['model_sha256'][:12]}..." if model_id else "none for this job")
