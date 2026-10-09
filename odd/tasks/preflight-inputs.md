# Input preflight (IMP-01)

## Objective and authorization

Implement the first planned work unit: strict readers, complete input preflight, duplicate/ID rules, article eligibility and a canonical constituent universe. The user authorized this code and local synthetic tests, then requested appropriate commits for recruiter review. The delivery plan is two local commits, without a push: first the scoped GGA reviewer profile, then documentation+IMP-01. No original-input inspection, dependency installation, pipeline-model calls, or remote operations are authorized.

Current correction authorization: fix the confirmed loss of JSON numeric distinctions and use a bounded project reviewer instead of the orchestrator. Local code/configuration changes and synthetic/offline checks are authorized. Do not change credentials, global agent settings, provider, strict mode, timeout, file patterns, dependencies, or submit an additional live review outside the normal commit hook.

Authority: the private local specification, the confirmed policies in the root project documents, and the current explicit IMP-01 authorization. Do not expand into model prompts, classification, retries/progress execution, scoring, CSV publication or the full CLI.

## Allowed edit surfaces

- New `news_sentiment/__init__.py` and `news_sentiment/input.py`.
- New `tests/test_input.py` with synthetic fixtures only.
- Minimal IMP-01 status/authorization/evidence updates in `AGENTS.md`, `README.md` and `IMPLEMENTATION_PLAN.md`, plus the `ARCHITECTURE.md` status sentence to keep the already-authorized documentation accurate.
- This file, `odd/tasks/preflight-inputs.md`.
- Correction-specific surfaces: `news_sentiment/input.py`, `tests/test_input.py`, `.gga` (only the reviewer-agent selector), and new `.opencode/agents/gga-reviewer.md`. Narrow status/evidence updates remain limited to `AGENTS.md`, `README.md`, `IMPLEMENTATION_PLAN.md` and this task.
- All other files stay unchanged, including the supplied inputs, credentials, PDF, private specification, `.atl/`, `.gitignore`, global OpenCode configuration and the prior documentation task. Keep GGA's provider, model selection, `STRICT_MODE=true`, timeout and file patterns unchanged.

## Work units and route

- [x] **INPUT-01 — Implement readers and preflight with test-first evidence.**
  - Route: delegated direct, one bounded writer.
  - Trigger: non-trivial new production/test files and preparation for writing.
  - Outcome: a small standard-library input module, typed results and safe aggregated blocking errors; no model adapter or output generation.
  - Verification: observed meaningful RED, GREEN and focused alternate/negative cases with `python -B -m unittest discover -s tests -v`; structural readback and `git diff --check`.
  - Reopened and corrected: numeric overflow, underflow and finite rounding previously hid conflicts; JSON fractional/exponent values now retain exact `Decimal` values for comparison. This does not add progress serialization.
- [x] **INPUT-02 — Independently verify and hand off the bounded unit.**
  - Route: independent read-only verifier plus a parent command spot check; native assessment determines any additional applicable review.
  - Outcome: independent contract/privacy/scope verification and parent test spot check are recorded below. Native review is separately postponed, not approved; technical verification is not native PASS.
  - Verification: independent verifier reran the focused suite with 31 passing tests and checked the fixed numeric cases. Real-IANA availability and native review approval remain unverified.
- [x] **INPUT-03 — Select a lightweight, tool-free GGA reviewer.**
  - Route: delegated direct with the same bounded writer; agent/configuration preparation is part of the authorized two-fix scope.
  - Outcome: a project-local review-only agent selected by GGA, without changing the normal default agent, model, credentials or strict status checking.
  - Verification: named-agent configuration loads; tools are denied; an isolated mock-provider protocol check demonstrates agent forwarding without contacting the real provider. A mock status is not a real code-review approval.

## Acceptance criteria

- Read each synthetic input snapshot without modifying it; collect detectable news and constituent errors before returning a valid result.
- Enforce strict JSON/list/object/required-field/date-format rules, duplicate keys, typed IDs and CSV-visible collisions; preserve original text, IDs, extra fields and security names.
- Compare complete records without Python's boolean/integer equality conflation. Deduplicate identical records with diagnostics; block conflicting records, including auxiliary-field differences.
- Preserve JSON fractional/exponent numeric distinctions through parsing and comparison; cover overflow, underflow and finite precision loss, plus equivalent numeric spellings. Do not solve only the infinity example or implement future progress serialization here.
- Only normalize exterior ticker whitespace. Require a nonblank normalized ticker and nonblank string security. Allow empty auxiliary cells with warnings and extra columns with full-row comparison.
- Omit only present blank string bodies; missing/null/non-string headline or body blocks. A present blank headline and usable body remains eligible with a warning. Never produce neutral labels or fictitious classifications.
- Preserve the specified preferred classes, never invent an unlisted canonical ticker, and expose an exact permitted/canonical universe for later validation. Do not infer corporate identity by trimming/merging security names.
- Resolve production timestamps using real `America/New_York` IANA data; ambiguous/nonexistent local times block. Missing timezone data fails closed rather than using a fixed-offset or hand-coded production substitute.
- Test timezone logic with explicitly synthetic injected zones while respecting the no-install boundary. Synthetic tests do not prove that real New York data is installed.
- Diagnostics must not include article text, raw input rows, credentials or private source payloads. No network/model client imports or calls are needed.
- Keep the module and future integration interfaces small; the complete CLI, model classification and score calculation remain unimplemented.

## Test policy and environment

- Mode: applicable default ODD test-first, sourced from orchestrator/project instructions and the planned standard-library runner. No external testing framework is required.
- Exact focused runner: `python -B -m unittest discover -s tests -v`.
- Run temporary synthetic fixtures under the pre-approved tool temporary directory by setting only the test process's `TEMP`/`TMP`; do not hard-code a username or absolute machine path in artifacts.
- Known environmental limitation: a previous real `ZoneInfo('America/New_York')` probe failed with missing `tzdata`. No installation is authorized. Test the injectable boundary and failure behavior; leave real-IANA readiness explicitly pending.
- RED — `python -B -m unittest discover -s tests -v`: one meaningful assertion failed (`len(result.articles)` was 0, expected 1); exit 1 before behavior implementation.
- GREEN — `python -B -m unittest discover -s tests -v`: 27 tests passed; exit 0. The suite uses only temporary synthetic files and injected test timezone behavior.
- TRIANGULATE — The same focused suite exercises malformed JSON/CSV, strict fields and IDs, duplicate conflicts, blank-body omission, CSV extras/canonical classes, and synthetic DST gaps/folds; all 27 passed.
- Environment — The production `ZoneInfo("America/New_York")` failure path is tested fail-closed. Synthetic timezone tests do not prove the host's real IANA database is available; readiness remains pending and no install was run.
- Final whitespace check — `git diff --check`: exit 0; Git emitted only its LF-to-CRLF working-copy warning for `AGENTS.md`. This tracked-diff check does not cover untracked files; new files were structurally read back.
- Final status check — `git status --short --branch --untracked-files=all`: exit 0 on `feat/preflight-inputs`; authorized IMP-01 targets are present and pre-existing untracked architecture/data-model/project-documentation files remain unchanged and untracked.
- Independent verification — `gentle-ai-verify`: 27 focused tests passed in 0.058s (exit 0) and nine supplemental checks completed after correcting an initial shell-syntax error; no confirmed code-contract violations were found. This is bounded technical verification, not proof of real-IANA readiness or native review approval.
- Parent spot check — `python -B -m unittest discover -s tests -v`: 27 tests passed in 0.064s (exit 0), after the final authorized `ARCHITECTURE.md` status-sentence and `AGENTS.md` status corrections; no production or test code changed after independent verification.
- Environment/review limits — real `America/New_York` IANA readiness remains unverified because the earlier probe failed for missing `tzdata`; no install or pipeline/model call was made. Native review remains postponed/not approved, and no native assessment or receipt is claimed.

## Correction verification (2026-10-08)

- RED — `python -B -m unittest discover -s tests -v`: 28 tests ran; `test_overflowing_json_numbers_remain_distinct_in_duplicate_records` failed because `InputPreflightError` was not raised for distinct `1e400` and `2e400` values. Exit 1; this was the intended behavior-level failure before the parser change.
- GREEN — `python -B -m unittest discover -s tests -v`: 28 tests passed in 0.062s; exit 0. Fractional/exponent tokens now use `decimal.Decimal`, preserving exact comparison without context normalization or binary-float conversion.
- TRIANGULATE — `python -B -m unittest discover -s tests -v`: 31 tests passed in 0.071s; exit 0. Added underflow (`1e-400`/`2e-400`), adjacent finite values rounded equal by binary float, equivalent spellings (`1.00`/`1.0`, `1e400`/`10e399`), Decimal-valued in-memory retention, out-of-range exponent fail-closed handling, and decimal ID-type rejection. Existing integer, bool/int, nonstandard-constant, privacy, and duplicate cases remain covered.
- OpenCode profile — `opencode debug agent gga-reviewer --pure`: exit 0 without a model request. Resolved name `gga-reviewer`, mode `primary`; configured wildcard deny is effective and all reported tool settings are disabled. No model override is present.
- OpenCode normal loader — `opencode debug agent gga-reviewer`: exit 0; the project agent resolves as `primary` with its final wildcard-deny rule. No model request was made.
- GGA forwarding — GGA v2.10.1 ran in the isolated synthetic Git Bash fixture with fake `opencode`, fake network-check `curl`, and a no-op `rm` shim (preserving test temporaries). The fake received `run --agent gga-reviewer`, discarded the synthetic prompt, and emitted controlled status only: `STATUS: PASSED` returned GGA exit 0; `STATUS: FAILED` returned exit 1. No real provider, account, model request, source article, or review occurred.
- Local reviewer-profile commit — `6b67b0a chore: use scoped GGA reviewer` succeeded with the ordinary hook. Because that commit had no staged Python files, GGA reported `No matching files staged for commit`; no AI review request was made.
- Shell note — an initial WSL Bash probe failed on the installed GGA library's CRLF (`$'\r': command not found`); the final mock used GGA's installed Git Bash path. No vendor source was modified.
- Worktree whitespace check — `git diff --check`: exit 0; only LF-to-CRLF working-copy warnings were emitted for tracked files. This checks working-tree changes, not the staged snapshot or untracked agent file.
- Existing staged snapshot check — `git diff --cached --check`: exit 0 with no output. The original staged snapshot was not modified; the new untracked agent was structurally read back and loaded by the named-agent configuration check.

## Delivery and progress

- Branch: `feat/preflight-inputs`, based on `578263d`. Documentation and IMP-01 are committed as `6b67b0a` and `333a6b0`.
- Strategy: `ask-on-risk`; the initial 500–800 authored-line forecast was advisory, not a cap. The user has asked for two local commits; no push or remote is configured.
- Work-unit commits: `6b67b0a chore: use scoped GGA reviewer`; `333a6b0 feat: add strict input preflight`. The feature commit's normal GGA hook returned `STATUS: PASSED`.
- Native documentation review is postponed, not approved. Its prior consent offer belongs to the old documentation target and must not be reused for changed source. Review mode remains globally on; no preference is changed.
- Engram recovery mirror: `odd/preflight-inputs/tasks`; parent synchronizes and reads back mirror #96 before the task-record closeout commit.

## Evidence and next step

The initial ten-file staged snapshot was cleared before committing to prevent the obsolete numeric implementation from entering history. The scoped GGA profile was committed first; then the corrected documentation, preflight, regression tests and task records were committed together. The feature commit's ordinary hook selected `gga-reviewer` and passed strict status parsing. Real-IANA readiness remains unverified, native review remains postponed/not approved, and no original input, exercise credential or dependency installation was used.

IMP-01 is committed. Future IMP-02 work requires separate authorization. The user handles any push.
