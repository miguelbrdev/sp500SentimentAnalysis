# Architecture

## Outcome and status

This document describes the smallest credible design for a Python CLI that reads `news.json` and `sp500.csv`, classifies eligible company/article pairs, and generates `entities.csv` and `scores.csv`. IMP-01 input preflight is implemented and verified with synthetic standard-library tests; classification, scoring, publication and the full CLI remain future work. No dependency installation, model call or end-to-end run has occurred. The remaining module names and interfaces below are proposals, not runnable commands, and real New York timezone-data availability remains pending.

## Responsibilities

Keep deterministic work in Python and use the model only for contextual entity resolution and company-specific implication labels.

| Part | Responsibility |
| --- | --- |
| CLI and orchestration | Parse paths/options, run complete preflight, coordinate a sequential workflow, and select normal replay or an explicitly fresh classification workflow. |
| Input validation | Parse news and constituents; validate types, dates, duplicate identities, required columns, and canonical tickers before any paid request. |
| Universe and prompt builder | Present the canonical eligible universe and one article's usable text to the model. Article text remains data, not instructions. |
| OpenAI adapter | Make one request at a time to only `gpt-5.6-terra`; record usage and bounded attempt outcomes. |
| Response validator | Validate the entire response against the internal contract and constituent whitelist; reject invalid responses as a whole. |
| Progress/accounting | Reuse compatible accepted classifications, persist attempt state before requests, and calculate cost from per-attempt usage records. |
| Deterministic output | Revalidate replayed classifications, generate exact CSV schemas, aggregate scores, and publish a report tied to the current output generation. |

One small package is sufficient. A possible future layout is `news_sentiment/__main__.py` for CLI/orchestration, with focused modules for input, classification, progress/accounting, and output. Avoid a plugin framework, database, queue, or general-purpose retry subsystem.

## Processing flow

1. Read and fully preflight both inputs. Report detectable blocking errors together where practical; make no model calls if preflight fails.
2. Normalize only what the input contract permits, deduplicate identical records, and retain safe diagnostics. Do not sort constituents before applying the first-listed-class rule.
3. Treat an absent, null, or wrong-type headline/body as a blocking structural error. For a structurally valid article, omit only a present string body that is empty or whitespace-only, even if its headline has text. Process a usable body with an empty headline and issue a warning; do not create neutral rows for omitted articles.
4. For each remaining unique article in stable input order, revalidate any compatible cached response; otherwise persist a pending attempt and make one sequential model request. Do not batch or parallelize calls.
5. Validate each full response. A valid `ok` response may contain zero entities only when no eligible company was identified. A valid `insufficient_information` response is not a neutral result: stop the run rather than filling in missing information.
6. When each article has an accepted classification, calculate exact time-decayed values from the fixed formula, prepare both CSVs, and publish the files with a generation-bound completion marker.
7. Rebuild this invocation's report and cost summary from current inputs and the full local attempt ledger, not from a prior report.

## Classification boundary

The model identifies companies from article context, maps brands or subsidiaries to the available canonical S&P 500 universe, and labels each implication at publication as positive, neutral, or negative. The model can distinguish an affected company from an incidental mention and can give different labels to companies in the same article.

Python owns the allowed ticker set and dual-class selection, input validation, whole-response schema checks, uniqueness, retry limits, accounting, date arithmetic, aggregation, CSV serialization, and output publication. Python can enforce that a ticker is allowed; it cannot prove that the model selected the semantically correct company or sentiment. Do not use an external company dictionary or claim schema validity is semantic proof.

The proposed minimal response has a status (`ok` or `insufficient_information`) and an entities array of `{ticker, label}` objects. Extra/missing keys, wrong types, noncanonical tickers, duplicate tickers, invalid labels, malformed JSON, or refusals are not silently repaired or partially accepted. See [DATA_MODEL.md](DATA_MODEL.md).

## Dates and score calculation

Parse the required local timestamp in `America/New_York`, then compare UTC instants to `2026-09-29 00:00` New York time. Under confirmed user policy, block ambiguous/nonexistent daylight-saving timestamps and accept valid dates after the as-of instant without clamping. For each classified pair calculate fractional elapsed days and apply the literal `0.5 ** (days / 7)` weight. Use labels `+1`, `0`, and `-1`, sum without normalization or clipping, and preserve tickers whose only labels are neutral with score zero. Detect non-finite arithmetic rather than silently substituting a value.

The user confirmed blocking ambiguous/nonexistent local times and literal acceptance of valid post-as-of dates. Computing fractional elapsed days as the difference between UTC instants is a selected technical default, not an explicit source requirement or separate user confirmation. The source fixes the New York timezone and formula but does not prescribe those edge policies. `America/New_York` data availability and portability must be verified in the authorized implementation environment.

## Bounded execution and recovery

- **Confirmed user policy:** Process sequentially, with at most three attempts per article and a shared 60-second cumulative pause budget. Honor a longer server `Retry-After` exactly and stop rather than shortening a required wait. Retry plausible transient network/timeouts, rate limits, and server errors (including overload `503`); stop on auth/configuration/quota/permanent transport errors, refusal, truncation, and unknown failures. Allow at most one contract-invalid regeneration within the shared attempt budget; do not regenerate refusal, truncation, or a valid `insufficient_information` response. Disable SDK-managed retries and preserve counters, pause budget, and not-before restrictions when resuming the same logical workflow.
- **Proposed mechanics:** Define provider-adapter error mappings before generic malformed-response handling. Use a short exponential delay (about 2 seconds, then 4 seconds) with jitter. A 120-second transport timeout is a selected technical default, not a strict wall-clock deadline for a whole attempt. Exact persisted field names and adapter settings are implementation details.

The attempt/wait boundaries above are confirmed user policy, not source-specification mandates; timing and adapter details remain proposed. Keep implementation a small explicit loop rather than an elaborate retry engine.

## Private progress, reproducibility, and publication

**Confirmed user policy:** Keep one private, unversioned JSON progress ledger for one logical workflow, containing accepted classifications and all attempts. It is not a cross-dataset cache; revalidate replay, preserve unknown remote/accounting outcomes, and do not silently make fresh paid calls from corrupt/incompatible progress. Persist a pending attempt before sending a request. If local persistence fails, stop before another request.

**Proposed mechanics:** Define the exact header/fingerprint, classification, and attempt fields. Update the attempt's known outcome/usage and any accepted classification in the same safely replaced snapshot. This does not promise exactly-once billing.

The confirmed fingerprint coverage is the fully validated inputs after only authorized normalization/deduplication, plus the classification model, prompt, response contract, classification rules, and supported parameters. Original file-byte hashes may be recorded for audit only. A presentation-only change or added exact duplicate does not invalidate classifications. Stable serialization and hash encoding are proposed mechanics. Revalidate every cached response and rebuild warnings, counts, score values, and report from the current input. Do not persist article text, raw prompts, raw model responses, credentials, or private source payloads in logs/progress; keep canonical serialization in memory and persist its hash.

If progress is corrupt or incompatible, do not silently begin new paid classifications. An explicit fresh workflow starts a new classification history and does not erase uncertain prior accounting. The new workflow requires the same paid-execution authorization as any model run.

The completion marker and its generation/hash fields are proposed publication mechanics. Prepare both CSVs and write the marker last. A failure before either output replacement leaves the old pair untouched; a failure during the separate replacements may leave an incomplete or mixed generation. The marker detects this state: if it is absent or does not match both files, do not accept or announce the outputs as the current successful generation. No rollback or preservation of the old pair is guaranteed after publication starts. A classification failure produces no new final CSV generation.

Equivalent normalized inputs can replay the same saved classifications and deterministic aggregation. Independent fresh model runs are not guaranteed to return identical semantics. The replay mechanism is not a claim that the specification's broad equivalent-input criterion or an evaluator's exact comparison has been independently proven.

## Usage measurement and cost

**Confirmed user cost policy:** Derive cost from per-attempt usage, including rejected responses and retries; missing usage is unknown, never zero. Cached input is a subset of input and reasoning tokens are a subset of output, so do not double-count either. The denominator is unique eligible articles with an accepted contract response; report `N/A` when it is zero.

**Confirmed report policy:** Record each attempt's input, cached-input, and output usage when supplied; derive totals from attempts, not invocation totals. Report the new invocation, same-workflow history, and all known/unknown attempts. Exact report field names and serialization remain proposed mechanics.

At the confirmed rates, calculate USD as:

```text
((input_tokens - cached_input_tokens) * 2.00
 + cached_input_tokens * 0.20
 + output_tokens * 12.00) / 1,000,000
```

Sum unrounded attempt costs before presentation rounding. Cost per article uses known attempt cost divided by the number of unique eligible articles with an accepted contract response, including accepted empty results and replayed classifications. Exclude exact duplicate records, omitted articles, failures, and `insufficient_information`. If that denominator is zero, report `N/A`. State that contract acceptance does not establish semantic correctness. Do not apply Batch discounts unless Batch was actually used; the proposed workflow does not use Batch.

Keep processing status (`completed`, `completed_with_omissions`, or `failed`) separate from accounting status (`complete_local` or `incomplete`). Valid outputs can coexist with unknown provider cost, but cannot be represented as a complete full-run cost when any attempt usage is unknown.

## Decision status and limits

| Status | Decision or evidence boundary |
| --- | --- |
| Confirmed | Source obligations plus user-confirmed preflight/duplicate/omission rules, New York DST and future-date handling, retry/wait boundaries, private progress/replay policy, and attempt-based costing/denominator. These user policies are not mandates from the source specification. |
| Proposed | Exact response keys, progress/report field layout, canonical serialization/fingerprint encoding, UTC elapsed-duration interpretation, retry delay and timeout settings, and completion-marker publication mechanics. |
| Pending | Authorized model availability and supported request parameters, dependency compatibility, actual full-run usage/cost, generated outputs, and output-grounded analysis. No model or API check has been run. |

Standout-company analysis, coverage concentration, and confidence limits must be computed from generated outputs after an authorized full run. Scores are not prices, probabilities, or predictions. Zero may mean only neutral rows or cancellation of signed contributions. No example result or cost is presented as measured.
