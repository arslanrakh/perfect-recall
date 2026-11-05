# PerfectRecall

**Jev-powered memory for AI agents.** Try it on Hermes. Replace Mnemosyne while keeping your existing SQLite database, memory banks, and tool calls.

An independent 120-question LongMemEval-S experiment reduced final-answer errors from **62 to 17 (72.6%)**, using the same GPT-5.6 Luna caller with high reasoning effort. Accuracy rose from **48.3% to 85.8%**. These are results for a frozen predecessor of this release, not a fresh validation of the renamed package or an official leaderboard score. [Methods, results, regressions, and reproduction](benchmarks/README.md).

PerfectRecall asks Jev to evaluate every eligible memory against short criteria supplied by the calling agent. It returns the original evidence for that agent to reason over. There is no embedding model, vector index, or hidden query-writing model in the production package.

Jev is a remote decision model. It answers typed questions, for example whether one memory matches one criterion, and does not generate text. The default model is `typesafe/jev-1.13` on OpenRouter: you need an OpenRouter API key, and recall costs money.

## Install in Hermes

Hermes versions with Git plugin installation can install the repository as a directory plugin. Then run the native memory setup:

```sh
hermes plugins install https://github.com/arslanrakh/perfect-recall
hermes memory setup perfectrecall
```

This installs the repository's code and declared Python dependencies without a separate PerfectRecall pip installation. The setup command backs up configuration, selects PerfectRecall, and disables legacy source plugins while keeping their files. Set `OPENROUTER_API_KEY` in the Hermes environment and restart.

PerfectRecall is not in the Hermes plugin catalog, so `hermes plugins install perfectrecall` by bare name does not work. Recent Hermes versions scan plugins installed from a Git URL. For this repository the scan returns a "caution" verdict, mostly for benchmark scripts, documentation and the inherited database repair tool, and Hermes refuses the install. Read the findings; if you accept them, run the install again with `--force`. [Installation and rollback](docs/INSTALLATION.md).

### Install as a Python package

Python 3.10 or newer is required. Install into **the same Python environment that runs Hermes**. On a standard Hermes installation:

```sh
~/.hermes/hermes-agent/venv/bin/python -m pip install 'git+https://github.com/arslanrakh/perfect-recall.git'
~/.hermes/hermes-agent/venv/bin/python -m perfectrecall.install
```

For another Hermes location, use its Python executable. This repository is the installation source; PerfectRecall is not published on PyPI. Hermes discovers the installed package by its `hermes_agent.memory_providers` entry point.

Set `OPENROUTER_API_KEY` in the environment used to start Hermes, or in your existing Hermes secret configuration. Restart Hermes. The installer selects `memory.provider: perfectrecall`, backs up an existing configuration, and disables legacy source plugins by moving them intact outside the plugin discovery directory. It also works with an empty Hermes profile and no previous memory provider. Hermes itself must already be installed.

```sh
python -m perfectrecall.install --hermes-home /path/to/profile
python -m perfectrecall jev-status
```

`jev-status` reports configuration and key presence; it does not print the key or make an API call. [Installation, migration, and rollback](docs/INSTALLATION.md).

## Configuration

PerfectRecall reads these environment variables. Each `PERFECTRECALL_*` variable overrides the legacy `MNEMOSYNE_*` variable of the same suffix, so existing Mnemosyne settings keep working.

| Variable | Default | Effect |
|---|---|---|
| `OPENROUTER_API_KEY` | none | Key for the default Jev provider. Recall fails without it. |
| `PERFECTRECALL_JEV_PROVIDER` | `openrouter` | `openrouter` or `typesafe`. `typesafe` reads `TYPESAFE_API_KEY` instead. |
| `PERFECTRECALL_JEV_MODEL` | `typesafe/jev-1.13` | Jev model name; with `typesafe`, the default is `jev-1.13.0`. |
| `PERFECTRECALL_JEV_TIMEOUT` | `30` | Seconds per Jev request. |
| `PERFECTRECALL_JEV_WORKERS` | `128` | Concurrent Jev requests, 1 to 256. |
| `PERFECTRECALL_PREFETCH_MODE` | `economy` | `economy` or `strict`; see below. |
| `PERFECTRECALL_DATA_DIR` | `$HERMES_HOME/mnemosyne/data` | Where the SQLite databases live; `~/.hermes/mnemosyne/data` without `HERMES_HOME`. |

`python -m perfectrecall jev-status` prints the resolved provider, model, worker count, data directory, and whether the key is set.

## Automatic memory

Hermes calls the provider before and after turns. Prefetch injects relevant memory into context without an explicit search call. Post-turn synchronization saves useful user messages automatically. Assistant messages are excluded by default; `sync_roles` makes that choice configurable. Normal scope, profile isolation, write-approval, and self-echo protections remain in place.

```yaml
memory:
  provider: perfectrecall
  perfectrecall:
    sync_roles: [user]
    default_scope: global
```

`global` deliberately shares these memories across sessions within the same bank. Omit it to preserve the inherited session scope. Existing `memory.mnemosyne` settings are still honored; `memory.perfectrecall` takes precedence.

## Spend less on conversation follow-ups

Economy prefetch is enabled by default in Hermes from 0.1.0a4. Jev checks whether a message can reuse the previous search question. Every turn still reads the eligible corpus; exact cached decisions avoid paying to evaluate unchanged memories again. New records are evaluated, and expired or inaccessible records are excluded.

Explicit recall always searches the supplied question. Set `memory.perfectrecall.prefetch_mode: strict` or `PERFECTRECALL_PREFETCH_MODE=strict` to search each new message. Economy uses a heuristic gate and can miss a need for additional evidence; its tests and limits are described in [conversation cost measurements](docs/CONVERSATION_COST.md).

## Use from Python or MCP

```python
from perfectrecall import PerfectRecall

memory = PerfectRecall(session_id="project-cedar")
memory.remember("Project Cedar uses PostgreSQL.")
hits = memory.recall(
    "Which database does Cedar use?",
    evidence_questions=["Does this memory name Project Cedar's database?"],
)
```

The `mnemosyne` Python namespace and `mnemosyne_*` tool names remain as compatibility interfaces. To run the inherited MCP tool surface, install the `mcp` extra and start the server (stdio by default; `--transport` selects SSE or HTTP):

```sh
python -m pip install 'perfect-recall[mcp] @ git+https://github.com/arslanrakh/perfect-recall.git'
perfectrecall mcp
```

Optional encrypted synchronization uses the `sync` extra in the same way.

The tool description teaches the calling agent to ask up to three short, concrete yes/no questions. It should retrieve partial facts, follow links through subsequent searches, and perform comparisons itself. [Tool guidance](docs/TOOLS.md).

## Data handling and limits

SQLite remains local. **Eligible memory text and queries are sent to the configured Jev API** for decisions. Optional Hermes-assisted consolidation can also use the host's language model. This is not an offline or zero-cloud memory system. Keep credentials outside the repository. [Privacy and security](SECURITY.md).

Recall scans the full eligible corpus using native Jev question batches, pooled HTTPS connections, and parallel duplicate checks. A live check of the 0.1.0a2 wheel with **10,000 mixed-length records** completed automatic retrieval after reopening in **4.19 seconds**. An explicit search with three criteria took **9.57 seconds cold / 0.73 seconds warm**. These are single synthetic observations, not a latency guarantee. [Measurements and reproduction](docs/PERFORMANCE.md).

The default remains 128 concurrent requests, configurable with `PERFECTRECALL_JEV_WORKERS` from 1 to 256. Batching reduces network round trips; raising thread count alone did not solve the original problem. Prefetch has a 6.5-second cooperative decision budget to leave cleanup time before Hermes' eight-second window. Required decision failures are reported as failures, never as a successful partial scan. Cost and latency still grow with text volume.

PerfectRecall is an alpha release. The name describes the goal; it is not a guarantee of perfect memory. Model availability, routing, prices, and results can change.

## Development

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check
python scripts/audit_release.py
python -m build
```

The test suite needs no API key. Live checks in `scripts/` run only with `--live` and cost money. [CONTRIBUTING.md](CONTRIBUTING.md) has the rules for changes; [AGENTS.md](AGENTS.md) describes the layout for coding agents and people alike.

## Credits and license

PerfectRecall is an independent fork of [Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne), originally by Abdias J. The inherited storage, memory lifecycle, integrations, and much of the tool surface are upstream work. No affiliation or endorsement is implied.

MIT. See [LICENSE](LICENSE), [NOTICE](NOTICE), and [third-party notices](THIRD_PARTY_NOTICES.md).
