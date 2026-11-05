# perfectrecall

Instructions for coding agents working in this repository. `CLAUDE.md` imports this file, so
Claude Code, Codex and other tools read the same text. `README.md` is for people who install
and use the package.

## What this is

PerfectRecall is memory for AI agents, written in Python (3.10 or newer, MIT). It stores memories
in local SQLite and recalls them by asking Jev, a remote decision model, whether each eligible
memory matches one to three short yes/no criteria supplied by the calling agent. The matching
original records go back to the agent. There are no embeddings, no vector index and no
query-writing language model in the production package.

It is a hard fork of [Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne) at commit
`199d4bc6662bd51c18275331ddeb51ac07387acf` (`NOTICE`). Storage, banks, scopes, the Hermes
provider lifecycle and the `mnemosyne_*` tools come from upstream and stay compatible: an existing
Mnemosyne database, configuration and tool call work unchanged.

Three ways to use it: a Hermes memory provider (a Git directory plugin, or an installed package
found by entry point), an MCP server (`perfectrecall mcp`), and a Python library
(`from perfectrecall import PerfectRecall`). It is not in the Hermes plugin catalog. Releases are
alphas (`perfectrecall.__version__`); from 0.1.0a6 they are on PyPI as `perfect-recall` (the import
name stays `perfectrecall`), and GitHub pre-releases carry the same wheel and sdist.

Jev is called through OpenRouter's Decisions API by default (`typesafe/jev-1.13`,
`OPENROUTER_API_KEY`), or TypeSafe directly (`PERFECTRECALL_JEV_PROVIDER=typesafe`,
`TYPESAFE_API_KEY`). Every live call costs money.

## Layout

```
perfectrecall/              own: public package, CLI, Hermes installer
  __init__.py               __version__; configure() maps PERFECTRECALL_* onto MNEMOSYNE_*, forces Jev
  cli.py                    `perfectrecall` / `mnemosyne` commands: --version, jev-status, then the inherited CLI
  install.py                `python -m perfectrecall.install`: back up config.yaml, select the provider, park legacy plugins
  hermes/                   Hermes provider and plugin entry point; post_setup() serves `hermes memory setup`
mnemosyne/                  inherited implementation namespace (storage, CLI, MCP server, tool schemas)
  core/jev*.py              own: Jev client, evidence batching, recall, tournaments
hermes_memory_provider/     inherited Hermes provider; _conversation_prefetch.py (economy mode) is own
__init__.py, plugin.yaml    directory-plugin entry point that Hermes loads from a Git checkout
tests/                      pytest suite; no network, no API key
scripts/                    own: release audit, verification against real Hermes, latency and cost measurements
benchmarks/                 own: frozen historical evaluation code, patches, result views (README.md explains)
docs/                       ARCHITECTURE, INSTALLATION, TOOLS, PERFORMANCE, CONVERSATION_COST, VERIFICATION
```

Of the inherited modules under `mnemosyne/` and `hermes_memory_provider/`, about half are
unchanged from the baseline commit and half are modified. The largest changes are in
`core/beam.py`, `core/memory.py`, `cli.py`, `install.py`, `core/sync.py` and `core/shmr.py`. To see
what changed in a file, diff it against upstream at the baseline commit. Upstream's benchmarks,
deployment files and most of its tests were not carried over: five files in `tests/` come from
upstream (`conftest.py`, the scope, export and forget tests), the rest are own.

## Develop

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
HERMES_HOME="$(mktemp -d)" TZ=UTC .venv/bin/python -m pytest -q
.venv/bin/ruff check
.venv/bin/python scripts/audit_release.py
.venv/bin/python -m build
```

This is what CI runs (`.github/workflows/ci.yml`, Python 3.10, 3.11 and 3.13). Set `HERMES_HOME`
to a scratch directory so no test reads a real Hermes profile. The suite needs no API key and
replaces Jev with test doubles.

`scripts/audit_release.py` fails on private files (`.db`, `.env`, keys), credentials, absolute
home-directory paths, Cyrillic text, removed vector modules and their imports. Write example
paths as `/path/to/...`.

`python -m perfectrecall jev-status` prints the resolved provider, model, worker count, data
directory and whether the key is set, without a network call.

## Check against real Hermes

These need a Hermes checkout and Hermes' own Python environment with `PyYAML` and `httpx`.
Without `--live`, Jev answers are scripted and nothing is billed.

```sh
python scripts/verify_hermes.py --hermes-root /path/to/hermes-agent --plugin-dir . --output /tmp/hermes-dir.json
python scripts/verify_hermes.py --hermes-root /path/to/hermes-agent --wheel dist/perfect_recall-<version>-py3-none-any.whl --output /tmp/hermes-wheel.json
```

The first copies this checkout into a temporary profile as a directory plugin and runs native
setup, discovery, automatic capture and prefetch after reopening; the second does the same for a
built wheel. `verify_install.py`, `verify_mcp.py`, `verify_drop_in.py` and
`verify_timeout_recovery.py` check a clean install, the MCP stdio server, an upstream database
opened in place, and recovery after a prefetch deadline. With `--live`, the `measure_*` and
`evaluate_*` scripts and `verify_conversation_gate.py` make paid calls; use it only when asked.

## Benchmarks

`python benchmarks/summarize_results.py` recomputes the published quality numbers from
`benchmarks/results/` offline: 120 LongMemEval-S cases, 62 to 17 errors, 48.3% to 85.8%
accuracy. `benchmarks/README.md` describes how to reproduce them. That needs a separate
environment (`benchmarks/work/`), the LongMemEval and PersonaMem downloads in
`benchmarks/downloads/`, and an OpenRouter key file outside the repository; the runs are paid.
Those directories and `benchmarks/runs/` are ignored by git.

When describing results, keep the qualifiers the docs already carry: the independent run used a
frozen predecessor runtime, not the current release; the 90.8% figure is development work on the
same cases; PersonaMem-v2 was a tie; none of it is an official leaderboard score.

## Release

The owner releases. An agent prepares, verifies and stops.

1. Set the version in `perfectrecall/__init__.py`, `mnemosyne/__init__.py`, the three identical
   `plugin.yaml` files (root, `perfectrecall/hermes/`, `hermes_memory_provider/`) and
   `CITATION.cff`. `pyproject.toml` reads it from `perfectrecall.__version__`.
2. Add a `CHANGELOG.md` entry that says what changed and whether any new measurement backs it.
   Record checks in `docs/VERIFICATION.md` when they were run.
3. Run the Develop commands, both `verify_hermes.py` modes, and
   `python scripts/audit_release.py --artifact dist/<wheel> --artifact dist/<sdist>`.
4. The owner tags `vX.Y.Z...`, pushes, creates the GitHub pre-release with the wheel and sdist, and
   uploads both to PyPI (`uv publish dist/*`).

The sdist follows `MANIFEST.in` (an explicit list). `AGENTS.md` and `CLAUDE.md` are not in it and
not in the wheel; keep it that way.

## Conventions

- English for code, comments and docs. Keep the existing plain, qualified tone in claims.
- Keep compatibility surfaces: the `mnemosyne` import namespace, `mnemosyne_*` tool names, the
  `MNEMOSYNE_*` variables, `memory.mnemosyne` configuration, and the default data directory
  `$HERMES_HOME/mnemosyne/data`. Do not rename them as cleanup.
- New settings read `MNEMOSYNE_*` in code; users set `PERFECTRECALL_*`, which `configure()` copies
  over at import. Call `configure()` before importing `mnemosyne` in any new entry point.
- Retrieval scans all eligible evidence. A failed Jev decision raises (`JevError`); it never
  counts as "irrelevant", and a partial scan never reports success.
- Changes to filtering or scope test what is disclosed to Jev, not only what is returned.
- Hermes and MCP share one recall tool description (`mnemosyne/tool_schemas.py`,
  `hermes_memory_provider`); a test checks they match.
- Files under `benchmarks/historical/` keep their exact bytes (`.gitattributes`), including the
  old name Jevosyne, because hashes and case selections depend on them. Do not edit result JSON
  under `benchmarks/results/` by hand.

## Do not

- Add embeddings, a vector engine or a query-writing language model to the production package.
- Commit API keys, `.env` files, live databases, profile backups or conversation exports.
- Run `--live` scripts or the historical benchmark unless the owner asks: they bill the owner's
  account.
- Present a development result as an independent confirmation, or describe the benchmark as an
  official LongMemEval score.
- Claim Hermes catalog availability. Installation is by Git URL, and Hermes (checked 2026-11-04)
  refuses it after its security scan unless the user passes `--force`.
- Push, tag, publish to PyPI, or change GitHub settings unless the owner asks.
