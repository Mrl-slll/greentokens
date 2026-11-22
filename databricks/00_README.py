# Databricks notebook source
# MAGIC %md
# MAGIC # GreenTokens on Databricks
# MAGIC Databricks is an **optional customer workspace**. Training runs on GreenTokens computers, not on Databricks compute.
# MAGIC
# MAGIC 1. `01_Submit_Training_Job` submits one job, prints its real `job_id` and **exits** (no waiting).
# MAGIC 2. `02_View_Results` fetches status and metrics later, and writes them to a table so they can show in **Catalog**.
# MAGIC
# MAGIC **Setup:** create a secret scope `greentokens` with keys `url` and `token`. Never paste the token in a notebook.
# MAGIC
# MAGIC **Limits (unverified until tested in your workspace):** Free Edition restricts outbound internet to an unpublished allowlist, so the call to GreenTokens may be blocked. Free Edition is non-commercial and has compute quotas; production Databricks use is not free.
# MAGIC The backend only offers `linear_regression_v1` and `sum_numbers_v1` today. The TrOCR preset is not available yet.
# MAGIC See `databricks/README.md` in the repository for details.
