# Project documentation

## Objective and rationale

Prepare the required project documentation and implementation plan for the small Python news-to-CSV pipeline. Preserve the authoritative specification and the user-confirmed policies without claiming that proposed code, model settings, tests, or an end-to-end run already exist.

## Authority and authorized scope

- Authority: the privately supplied specification, locally available as `docs/project-spec.md`, plus confirmed project-lead clarifications and user work policies.
- Authorized: `AGENTS.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `IMPLEMENTATION_PLAN.md`, `README.md`, and this planning document.
- Not authorized: application code, dependency installation, original-input or credential inspection, pipeline/model calls, commits, pushes, or remote operations.
- Keep `.atl/`, `.gga`, `.gitignore`, the specification, original inputs and credentials unchanged. Do not copy private input content or the proprietary specification into deliverables.
- Technical artifacts are written in English. Decisions carry confirmed, proposed, or pending status with rationale in the appropriate project document; do not create a separate decision log.

## Work units and route

- [x] **DOC-01 — Write the specification-aligned documentation package.**
  - Route: delegated direct, one bounded writer.
  - Trigger: five non-trivial documentation files and preparation for writing; do not inflate the parent context with source synthesis.
  - Outcome: four required documents and updated root agent context, with coherent contracts, workflow, proposed CLI/dependencies, acceptance checks and honest limitations.
  - Checks: completed structural readback of all five root documents and this task file; manually checked local Markdown links and cross-document contracts after one bounded correction pass for five independent documentation findings. Exact Git command results are recorded below; `git diff --check` covers tracked changes only, so untracked files were reviewed directly.
- [x] **DOC-02 — Verify consistency and provide an honest handoff.**
  - Route: parent structural spot check plus risk-appropriate independent verification; native assessment chooses the applicable review route.
  - Outcome: requirements traceability, policy consistency, no fabricated runnable commands or completed checks, and an explicit next implementation boundary.
  - Checks: independent document verification, bounded corrections and parent Git spot check are complete. The user postponed native review; this is recorded as pending/not approved, not as an approval or receipt.

## Acceptance criteria

- The five required project documents exist and describe a simple Python CLI, not an implemented application or UI.
- Cover constituent/parent/dual-class rules, company-specific labels including incidental mentions, exact CSV schemas, neutral-only tickers, literal fixed time decay and source-only inputs.
- Cover validated whole responses, sequential execution, bounded retries, private progress with separate classifications/attempts, canonical compatibility, current-input report rebuilding and attempt-derived USD costing.
- Retain the requirement for every LLM output to be validated and all tests to use synthetic inputs/mocks rather than paid calls.
- Separate cached-result replay from fresh-inference variability; do not claim universal fresh-run determinism or semantic correctness from schema validation.
- Mark proposed CLI, dependencies, module layout and test runner as not implemented or executed. Keep model availability/parameter support and measured full-run cost pending actual authorized execution.
- Identify required output-grounded analysis, presentation and actual end-to-end command as future deliverables.
- No source, secret, original-data, protected-config or unauthorized-operation changes.

## Test-first applicability

Documentation-only work has no meaningful runnable behavioral RED or configured application test runner. Use structural and technical readback; no RED/GREEN, runtime success, model availability or output correctness may be claimed. Future behavior implementation should use runnable synthetic/mocked test-first checks when applicable.

## Delivery and budget

- Documentation was prepared on `docs/project-documentation`; the user-facing work continues on `feat/preflight-inputs` from branch point `578263d`.
- Delivery strategy: `ask-on-risk`; no PR or chain strategy is selected or authorized.
- Forecast: approximately 450–650 authored changed lines for the coherent documentation package and planning record; advisory, not a cap. Keep formatting and essential content rather than compressing to meet a line count.
- Reviewable commits: `6b67b0a chore: use scoped GGA reviewer`; the companion `feat: add strict input preflight` commit with tests and documentation is pending. The user owns any push.
- Review mode observed: on, decided by global preference. The initial assessment was unassessable without an untracked declaration. A subsequent assessment explicitly selecting the four root documents and this task returned `medium`, six paths and 466 changed lines before this final progress note; its reason was the operational `AGENTS.md` change and its review-due reason was `slice_budget_reached`. Native completion remains blocked, not approved.
- No runtime or delivery receipt is implied by a checklist.

## Verification evidence and progress

- Initial Git observation: clean `main`, sole commit `578263d`.
- Created local branch `docs/project-documentation`; no commit, push or remote operation.
- Parent safety observations: `.codegraph/` and `odd/tasks/` were absent; no index initialized. The parent created the task directory for this authorized planning work.
- Source documents, original data and credentials have not been modified or inspected beyond the authorized specification and agent guidance.
- Engram mirror: the parent owns synchronization and readback of the full task under observation #73, stable topic `odd/project-documentation/tasks`. The initial mirror was read back before delegation; DOC-01 and checking updates are synchronized by the parent, not the writer.
- DOC-01 changed only `AGENTS.md`, the four authorized new root documents, and this task file. Manual readback found the expected links resolving to authorized/existing documents and no cross-document contract conflict.
- One bounded verifier-correction pass clarified confirmed user policies versus proposed mechanics, distinguished malformed/missing headline or body from a present blank-body omission, corrected publication-failure guarantees, rejected empty normalized tickers (and added a focused planned test), and recorded the source duration/deadline. No new policy or runtime work was added.
- Initial command observations: `git diff --check` emitted only the LF-to-CRLF working-copy warning for `AGENTS.md`; `git diff --stat` listed only tracked `AGENTS.md` (35 insertions, 41 deletions) and the same line-ending warning; `git status --short` listed `M AGENTS.md`, the four new root documents as `??`, and the authorized `?? odd/` tree. The newly created root documents and untracked task file are not represented by `git diff --stat` or checked for whitespace by `git diff --check`.
- Correction-pass command observations: `git diff --check; "DIFF_CHECK_EXIT_CODE=$LASTEXITCODE"` returned exit code 0 with no whitespace diagnostics; `git diff --stat; "DIFF_STAT_EXIT_CODE=$LASTEXITCODE"` returned 0 and listed tracked `AGENTS.md` only (39 insertions, 38 deletions); `git status --short; "STATUS_EXIT_CODE=$LASTEXITCODE"` returned 0 with `M AGENTS.md`, four new root documents, and `?? odd/`. Git's LF-to-CRLF warning appeared on the first two commands. Untracked document contents are outside Git diff checks and were read back directly.
- Independent verification read the complete specification, all five documents and confirmed-policy observations. Its targeted readback confirmed the structural, publication, ticker and schedule corrections. The parent completed the same status-label correction in the remaining retry, persistence and report paragraphs without changing operating policy.
- Parent final-source spot check: `git diff --check` returned exit code 0 after those wording refinements; only Git's LF-to-CRLF warning appeared. Git status shows only the authorized root documents and planning tree. No staging or commit occurred.
- Native file selection for the documentation target was resolved, but `review.start` requested a consent-v3 interaction that was not available in that session. The user postponed this native review. No native approval or review-mode change occurred; later code changes form a different candidate.
- At the DOC-01/DOC-02 documentation checkpoint, functional tests/builds/model calls were not run and no pipeline implementation existed; IMP-01 was implemented in the subsequent authorized work unit.
- Full-pipeline implementation, paid execution, dependency installation and remote delivery remain separately authorized phases.

## Next step

Documentation planning and technical verification are complete; native review remains postponed/not approved. The separate GGA-profile commit is recorded above; the feature commit must include the current corrected preflight source and tests, not the old staged snapshot. Leave push/remote delivery to the user. Full application work, dependency installation and paid execution remain separate authorization gates.
