# S&P 500 company news sentiment

## Current status

IMP-01 provides strict input preflight in `news_sentiment/input.py`, with 31 passing standard-library tests using synthetic files. Fractional/exponent JSON numbers are parsed as `Decimal` and compared exactly in full-record duplicate checks, so overflow, underflow, and binary-float rounding cannot conceal conflicting extras. A number outside the standard library's decimal exponent range fails closed as invalid JSON; integer tokens and typed ID rules are unchanged. Decimal-valued extras remain in memory only, so any future progress/fingerprint serialization must encode them losslessly.

The current project work is available at [miguelbrdev/sp500SentimentAnalysis](https://github.com/miguelbrdev/sp500SentimentAnalysis), branch `feat/preflight-inputs`.

The repository is not a runnable end-to-end pipeline: classification, progress/replay, scoring, CSV publication, and the CLI remain unimplemented. Original inputs were not inspected or run; no model call, paid API use, dependency installation, generated output, or real-data validation is claimed. Production readiness for the real New York IANA timezone data remains pending.

Project GGA selects the tool-denied, review-only `.opencode/agents/gga-reviewer.md` profile through `.gga`. It uses the active OpenCode model/account without changing the global default or credentials; GGA's provider, strict mode, and timeout remain `opencode`, `true`, and `300`. Restart OpenCode to load agent-file changes in an existing session. Offline mock tests verified `--agent gga-reviewer` forwarding and strict status handling only; no real AI review or approval is claimed.

## Reading path

1. [Agent instructions](AGENTS.md) summarize authority, confirmed rules, and safety boundaries.
2. [Architecture](ARCHITECTURE.md) explains the proposed code/model split and workflow.
3. [Data model](DATA_MODEL.md) defines input, internal, output, progress, and accounting contracts.
4. [Implementation plan](IMPLEMENTATION_PLAN.md) defines future test-first work and acceptance evidence.

The private source specification remains the authority. These documents summarize requirements without reproducing the source document or any private input.

## Intended pipeline

The planned Python CLI reads only `news.json` and `sp500.csv`, identifies eligible S&P 500 companies, produces one company-specific label per article/company pair, and aggregates the fixed time-decayed score. It does not fetch news or prices, add a UI, or hand-edit outputs. Required outputs are exactly `entities.csv` (`id,ticker,label`) and `scores.csv` (`ticker,value`).

The pipeline model, if separately authorized, is only OpenAI `gpt-5.6-terra`; agentic coding tools are a separate use. Code validates all model output and performs input checks, date arithmetic, scoring, costing, and CSV generation. See [the proposed contracts](DATA_MODEL.md).

## Proposed CLI and dependencies — not runnable yet

A possible package entry point and option set is:

```text
python -m news_sentiment --news <news.json> --constituents <sp500.csv> --entities-out <entities.csv> --scores-out <scores.csv> --progress <private-progress.json> --report <run-report.json> [--fresh]
```

All paths and options above are a proposed interface, not an actual end-to-end command. `--fresh` would start a new classification workflow and must not erase the previous workflow's uncertain attempt accounting. Keep progress outside version-controlled source files. A credential may be provisioned/used only after explicit paid-execution authorization; this repository must not reveal its value.

Proposed runtime dependencies are the OpenAI Python SDK for the permitted model and `tzdata` where an IANA timezone database is not available from the host. IMP-01 uses the standard library only; its timezone tests inject synthetic zones and do not prove real New York timezone data is installed. A prior production-zone probe failed because timezone data was unavailable. Exact versions and compatibility remain pending authorized verification; no dependency was installed.

## Planned checks and submission status

The focused command `python -B -m unittest discover -s tests -v` has passed all 31 IMP-01 tests. They use temporary synthetic inputs and injected timezone behavior, never original articles or paid calls. This result covers input preflight only, not any future model, scoring, CLI, or end-to-end behavior. See the [plan](IMPLEMENTATION_PLAN.md) for unit boundaries and acceptance evidence.

Not yet delivered: actual end-to-end command, generated `entities.csv` and `scores.csv`, measured call/token/cost report, output-grounded company and coverage analysis, and brief presentation. Once generated, analysis must distinguish article frequency from weighted score and state coverage, replay/model, and cost limitations. No results are fabricated in this README.
