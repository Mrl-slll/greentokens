# SST-2 local data directory

Run `../../download_assets.py` using your Python environment, or follow the parent
example README. The downloader creates these files here:

- `train-00000-of-00001.parquet`: 67,349 labeled training examples.
- `validation-00000-of-00001.parquet`: 872 labeled validation examples.
- `test-00000-of-00001.parquet`: 1,821 examples with hidden labels; not used for training/evaluation here.

Source: <https://huggingface.co/datasets/stanfordnlp/sst2>

Revision: `8d51e7e4887a4caaa95b3fbebbf53c0490b58bbb`.
Upstream license metadata: `unknown`. Original Parquet data is not committed to
this public repository; its hashes and download URLs are in `../manifest.json`.
