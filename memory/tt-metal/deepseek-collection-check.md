---
name: deepseek-collection-check
description: How to run the deepseek_v3_d_p pytest collection check against an unbuilt checkout, and why it is slow
metadata:
  type: project
---

The `pytest --collect-only` check on `models/demos/deepseek_v3_d_p/tests/` is the cheapest thing that catches a branch defect static checks miss (a module-level `NameError` collects ZERO tests from a file while `py_compile` and pre-commit both pass). Expected count on the Mistral prefill branch line: **28346** with `--ignore=.../tests/sparse_mla`.

**Running it against an unbuilt checkout** (e.g. `/data/kmabee/tt-metal-3` as of 2026-09-01; it has since been built, see [[shared-tree-multi-session]]): use the built tree's interpreter with PYTHONPATH pointing at the unbuilt one —

```
cd /data/kmabee/tt-metal-3 && TT_METAL_HOME=/data/kmabee/tt-metal PYTHONPATH=/data/kmabee/tt-metal-3 \
  /data/kmabee/tt-metal/python_env/bin/python3 -m pytest models/demos/deepseek_v3_d_p/tests/ \
  --collect-only -q --ignore=models/demos/deepseek_v3_d_p/tests/sparse_mla
```

`ttnn` still resolves to the built tree (`/data/kmabee/tt-metal/ttnn/ttnn/__init__.py`) while `models`/`tests` come from the unbuilt one. That is valid whenever the branch under test changes nothing under `ttnn/` — check that first.

**Three traps:**

- **It opens all 32 chips and costs ~30-60 s of conftest import per invocation.** Never loop it per CI leg — 8 invocations blew a 10-minute cap and produced nothing. Do ONE run over all the files and apply the `-k` expressions offline.
- **`-q` does not print node ids here** (a plugin suppresses it); the capture is the verbose tree instead. Parse `<Module path>` / `<Function name[params]>` lines to rebuild `module::name[params]`, then evaluate `-k` as a boolean over substring tests. The JUnit XML that `--collect-only` writes is empty, so it is no help.
- A stale board fails it with `RuntimeError: Read 0xffffffff over PCIe ID <n>: the board should be reset` — that is hardware, not the branch. `tt-smi -glx_reset` clears it (~1 min, re-inits all 32). Check `/proc/driver/tenstorrent/*/pids` is empty first (see [[device-usage-visibility]]).

Per-leg `-k` selector counts are the other half of the check: they prove the CI legs still select the same tests. See [[mistral4-ci-staging-prereqs]] for the staged `/mnt` paths each leg needs.
