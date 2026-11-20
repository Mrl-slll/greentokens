# Experiments and evidence

[System guide](../README.md) · [Four-PC experiment](four_pc_cpu/README.md)

This directory contains research/validation workflows rather than general customer API features. At the 19 November 2026 audit, the four-PC source and related backend edits were local additions; its `runs/` output directory is ignored by Git. A teammate's clone may not contain either until the source is deliberately published, and ignored model/run outputs need separate delivery.

The current experiment connects four independent HTTPS providers. The operator hosts API/relay/state, while providers compute and remote rank zero averages model changes. This differs from the development Ray group implementation in `core/workloads/ddp.py`.

Treat generated reports as historical evidence, not a claim that those devices are online now. Do not rerun training just to check documentation links. Preserve measured reports and original supplied material; label obsolete design assumptions instead of silently changing historical measurements.
