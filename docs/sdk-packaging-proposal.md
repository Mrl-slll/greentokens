# SDK packaging — pending dependency approval

The standard-library-only client and CLI work from `sdk/` with PYTHONPATH. Installable packaging is the remaining step, pending the requested approval under AGENTS.md.

| Dependency | License | Release checked | Reason |
| --- | --- | --- | --- |
| setuptools 84.2.1 | MIT | October 2026 | Standard Python build backend; generates the installable package and console command |

Sources: [PyPI release](https://pypi.org/project/setuptools/84.2.1/), [license declaration](https://github.com/pypa/setuptools/blob/main/pyproject.toml).

Proposed `sdk/pyproject.toml` after approval:

```toml
[build-system]
requires = ["setuptools==84.2.1"]
build-backend = "setuptools.build_meta"

[project]
name = "greentokens"
version = "0.1.0"
description = "GreenTokens local developer client"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
greentokens = "greentokens.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["greentokens*"]
```

After approval: add the packaging metadata, install from `./sdk` into a clean virtual environment, verify the CLI from outside the checkout, and update the quickstart to use the installed command. No PyPI publication is authorized or planned in this change.
