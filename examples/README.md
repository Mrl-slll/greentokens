# Examples and local model demonstrations

[System guide](../README.md) · [Workloads](../core/workloads/README.md)

Examples are small, inspectable entry points for learning or measurement. They are not all registered backend templates.

| Directory | What it does | Services needed |
| --- | --- | --- |
| `training/` | JSON/TOML inputs for the SDK's linear regression example | Backend/Ray/storage for submission |
| `bert_tiny_cpu/` | Standalone BERT-tiny sentiment baseline and generated checkpoints | Its own ML environment and initial model/data downloads; not the job API |

The standalone BERT script predates some platform training features. Its dependency/runtime instructions are scoped to that experiment. The main platform now also has Ray and provider training templates; do not infer backend capabilities from historical baseline wording.

The root web inference demo discovers verified `bert-tiny-run-*` checkpoints and calls `scripts/predict_cpu.py`. This performs local prediction with a saved model, not a distributed training submission. A clean clone without generated model files will not have the same demo assets. See [baseline instructions](bert_tiny_cpu/README.md).

When adding examples, state whether execution is standalone, Ray-backed or provider-backed; whether it downloads models/data; and whether outputs are generated/ignored. Keep model metrics tied to the exact dataset and run rather than presenting them as platform guarantees.
