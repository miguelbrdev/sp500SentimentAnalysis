# Implementation plan

## Status and execution boundary

IMP-01 strict input preflight is implemented and its corrected focused suite has 31 passing synthetic tests. Fractional/exponent JSON numbers use exact `Decimal` values for duplicate comparison; values outside the standard library's decimal exponent range fail closed. The remaining units are future work; this plan does not authorize them, dependency installation, paid calls, staging, commits, or pushes. The repository is not yet an end-to-end runnable pipeline, and no original-data run or output is claimed.

The project should remain a small Python CLI. Keep each behavior, its focused synthetic/mocked tests, and its explanatory documentation together as one reviewable work unit. Obtain explicit approval before any commit. Do not split work by file type or treat the plan's order as permission to execute.

The project-local GGA profile is tool-denied and review-only; `.gga` selects it without changing the active OpenCode model/account or global default. A fresh OpenCode process is required to load agent changes. Isolated mock verification demonstrated agent forwarding and strict PASS/FAIL handling, not a live review or approval.

## Work units

| ID | Work and acceptance evidence | Focused synthetic/mocked tests |
| --- | --- | --- |
| IMP-01 | Implemented strict readers and complete preflight for news/CSV, duplicate and ID collision rules, eligible body handling, constituent universe, and first-listed-class mapping. Blocking input issues raise aggregated errors without returning a partial result. Fractional/exponent JSON values remain exact for full-record comparison; future progress/fingerprint serialization is not part of this unit. No model adapter or orchestration is part of this unit; the caller-level no-call gate remains unimplemented. | 31 synthetic tests cover valid inputs; wrong/missing types; duplicate JSON keys/IDs; typed-ID CSV collision; overflow, underflow, finite-rounding collisions and equivalent numeric spellings; identical/conflicting duplicates; extra columns; CSV header/row errors; body omissions and empty headline; ticker normalization; preferred classes; and timezone gaps/folds. |
| IMP-02 | Build one-article prompt and the internal response validator. Use only the confirmed model identifier through an isolated OpenAI adapter. Reject every invalid whole response; allow accepted empty results only under the stated contract. | Separate company labels; incidental neutral; parent/brand mapping; ETF/index benchmark treatment; valid empty/insufficient responses; malformed JSON, refusal/truncation, wrong keys/types, duplicate or noncanonical ticker; article text treated as data. |
| IMP-03 | Add sequential execution, explicit bounded retry/wait policy, private workflow progress, per-attempt ledger, fingerprint compatibility, and replay revalidation. | Mock transport and clock/sleeper; transient/permanent classification; retry and cumulative wait bounds; `Retry-After`; invalid-response regeneration cap; crash/pending/unknown outcome; corrupt/incompatible progress; replay and explicit fresh-workflow boundary. |
| IMP-04 | Implement fixed fractional-day scoring from preflight's New York-aware timestamps, deterministic CSV generation, and output-generation marker. | Fractional days; DST edge cases from IMP-01 timestamps; future date literal weight; neutral-only zero score; mixed signs; no clipping/rounding; exact headers/order; publication failure leaves no claimed current generation. |
| IMP-05 | Wire the proposed CLI and generate the current-run report from current inputs and the complete local attempt ledger. | CLI validation and safe diagnostics; report rebuild on replay; known/unknown attempts; retry and rejected-response usage; cached-input subset; zero denominator; per-article cost and processing/accounting states. |
| IMP-06 | Run the authorized end-to-end pipeline on the supplied inputs, record exact command and outputs, perform output-grounded analysis, and prepare the brief presentation/submission checklist. | No paid test suite. Verify generated headers/counts/score derivation and report cost from the recorded attempt ledger; manual analytical claims cite generated rows and counts. |

Work units are intended to be independently reviewable, not a requirement for six commits. Preserve the user's explicit approval-before-commit rule. A future review can combine adjacent work only if it remains coherent and within the authorized scope.

## Test-first and verification strategy

For each behavior with a meaningful deterministic test, add the smallest failing synthetic/mocked test first, observe RED, implement the behavior, observe GREEN, then exercise negative/alternate paths and refactor while focused tests remain green. No test may require a paid model call or real article text. Add a broader suite only after focused checks and only when authorized.

The focused standard-library test command is:

```text
python -B -m unittest discover -s tests -v
```

This runner has passed 31 IMP-01 tests using synthetic temporary files and an injected timezone seam. It does not test model behavior or prove the production host has New York IANA timezone data. Keep future tests hermetic by mocking paid/model/time/wait boundaries. Record actual command lines, exit status, and diagnostics; never convert a planned check into reported evidence.

## Acceptance traceability

| Requirement area | Planned evidence |
| --- | --- |
| Constituents, parent brands, first-listed class, benchmark funds | IMP-01/02 focused tests and entity output whitelist audit. |
| Company-specific implication and incidental mentions | IMP-02 valid/negative contract cases plus article/company synthetic examples. |
| Production-like input validation | IMP-01 all-input preflight and duplicate/error cases; no model call on invalid inputs. |
| Exact required output schema and score formula | IMP-04 CSV and arithmetic tests, including neutral-only tickers and fractional days. |
| Every model result validated; permitted model only | IMP-02 whole-response validator and adapter configuration review. |
| Bounded calls, token usage, cost per article | IMP-03/05 attempt-ledger, unknown-usage, retry, and cost formula checks. |
| Equivalent-input replay and honest fresh variability | IMP-03 fingerprint/replay tests; document that fresh inference is not guaranteed semantically deterministic. |
| Source-only processing and no hand-edited output | IMP-06 record exact CLI invocation; inspect generated files and input/output path boundaries. |
| Grounded presentation and limitations | IMP-06 cite entity/score counts; disclose coverage, model/replay limits, and actual cost evidence. |

## Authorized model/runtime gate

Before an actual pipeline run, separately obtain explicit paid-call authorization. Do not inspect, probe, or use credentials before that approval. With authorization, verify availability of only OpenAI `gpt-5.6-terra`, the selected SDK/runtime compatibility, and support for each requested parameter. Do not silently substitute a model/provider or assert unsupported seed/temperature settings. Configure SDK retries off so the application's bounded policy is the only retry layer.

Runtime dependencies proposed for evaluation are the OpenAI Python SDK and `tzdata` for portable IANA timezone data where the host lacks it; unit testing uses Python's standard library. Versions and compatibility remain pending authorized verification. No installation has been run.

## Completion and submission evidence

After implementation authorization, run focused tests first and only run broader checks explicitly authorized for the work unit. Then run the actual end-to-end command against the supplied inputs, generating both CSVs and the separate report. Preserve original inputs; never edit output rows manually. Report the actual model, calls, token usage, retry/rejection counts, known and unknown attempts, Batch status, exact cost formula/rates, and cost per eligible accepted article. If any attempt's usage is unknown, state that a complete full-run cost is unavailable.

Use generated `entities.csv` and `scores.csv` to discuss standout companies, why their labels/weighted scores stand out, how concentrated article coverage is, and limits on confidence. Distinguish article frequency from signed weighted score. Scores are not prices, probabilities, or forecasts; a zero can represent only neutral coverage or cancellation. Do not produce analysis claims before output files exist.

The source exercise is sized for 4–6 hours, with submission due October 14, 2026, at 18:00 CET. Submission remains incomplete until the repository link, actual runnable end-to-end command, generated `entities.csv` and `scores.csv`, agent context, and brief presentation are available. The source specification makes Data Quality Report, Prompt Design Iteration, and Cost Optimisation optional challenges; they are not prerequisites for the core plan.
