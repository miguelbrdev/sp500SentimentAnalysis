# Data model and contracts

## Status

The two output schemas and fixed score formula are source-specification requirements. Input/duplicate/omission handling, New York DST and future-date handling, the net-direction label interpretation, retry/progress boundaries, and cost denominator below are confirmed user policies, not extra source-specification mandates. Exact response keys, field layouts, canonical serialization, and publication mechanics remain proposed implementation details. No application data has been read and no output has been generated.

## Source files

### `news.json`

The top level is a list of article objects. Each object requires `id`, `date`, `headline`, and `body`; additional keys are allowed and are never passed to the model. The source describes a 100-article fixture, but does not make 100 a validation rule.

| Field | Contract and use |
| --- | --- |
| `id` | Integer or string, but not boolean. Reject empty/whitespace-only or exterior-whitespace strings. Preserve the original string value; serialize integer IDs as decimal text for CSV. Reject collisions after CSV text conversion (for example, integer `1` versus string `"1"`). |
| `date` | Exact string form `YYYY-MM-DDTHH:MM`; no seconds, offset, or exterior whitespace. Validate calendar values and interpret as New York local time. Blocking ambiguous/nonexistent daylight-saving times is confirmed user policy. Computing fractional elapsed days between UTC instants is a proposed technical interpretation. |
| `headline` | Required string; missing, null, or wrong type blocks preflight. A present empty string with a usable body is processed with a warning. |
| `body` | Required string; missing, null, or wrong type blocks preflight. A present empty/whitespace-only string causes omission regardless of headline; report the reason. |

Malformed JSON, duplicate object keys, a non-list top level, a non-object article, missing/wrong-type required fields, or invalid IDs/dates blocks the run before model calls. The present-string empty-body omission and empty-headline warning are confirmed user policy. Process articles in stable source order.

For duplicate IDs, identical complete decoded records (including extra fields) are deduplicated, keeping the first. Any difference in any field blocks the run. Compare values as JSON values, not merely the fields used in the prompt. Duplicate-key JSON objects are blocked because their meaning is ambiguous.

### `sp500.csv`

Require the exact header names `symbol`, `security`, `gics_sector`, `headquarters`, and `date_added`; extra columns are allowed. Repeated headers, malformed CSV, and rows with a field count inconsistent with the header block preflight.

- Trim exterior whitespace from `symbol` only. Reject a ticker that is empty or whitespace-only after trimming. Preserve case; do not otherwise normalize it.
- Require `security` to be a nonempty string after a whitespace check, while preserving its original value. Do not claim that descriptive text has been verified as factually correct.
- Blank auxiliary fields may be warned about. They do not become extra model requirements.
- Identical full rows for a normalized ticker are deduplicated, keeping the first. Conflicting rows for the same normalized ticker block the run, including conflicts in extra columns.
- Preserve source order when applying the first-listed dual-class rule; do not sort the source before resolving it. Use the specified canonical classes `GOOGL`, `FOXA`, `NWSA`, and `BRK.B`.
- The model may map a brand or subsidiary to a parent only within the supplied canonical universe. No external company/brand database is part of the design.

The only market-mention exceptions confirmed by the user are index and ETF products used as benchmarks: do not treat them as constituents or as mentions of their sponsors.

## Eligibility and entity contract

For a structurally valid article, a usable body is eligible even if its headline is empty. Omit only a present string body that is empty or whitespace-only: no entity rows, no score contribution, and no neutral placeholder. Missing/null/wrong-type body or headline is a preflight error, not an omission. Record omission counts and reasons in the run report. Coverage may therefore be partial and must be disclosed.

For every eligible article and identified in-universe company, emit exactly one company-specific label:

| Label | Numeric value | Meaning |
| --- | ---: | --- |
| `positive` | `+1` | Implication for that company's value at publication is positive. |
| `neutral` | `0` | Mention has no implication, including an incidental mention. |
| `negative` | `-1` | Implication for that company's value at publication is negative. |

One article can produce different labels for different companies. Consider the supported net direction of the article's facts and consequences, not a count of positive/negative words or headline priority. Under the confirmed user interpretation, when supported effects have no net direction, use neutral; uncertainty is not a fallback-to-neutral rule. Opposing signals alone do not require cancellation or insufficiency. This net-direction rule is a user-confirmed interpretation, not an explicit source-specification rule. No separate subject/mention output column is added.

## Internal model response (proposed)

Require exactly one JSON object with exactly these keys:

```json
{
  "status": "ok",
  "entities": [
    {"ticker": "<canonical constituent symbol>", "label": "positive|neutral|negative"}
  ]
}
```

The example values are placeholders, not actual article results. `status` is either `ok` or `insufficient_information`. An `ok` response may have an empty array only when the model identified no eligible company. `insufficient_information` is a narrow stop signal for missing information needed to identify or interpret the subject; it is not a response to complexity, mixed signals, missing causal proof, or lack of price magnitude. A self-reported status is not proof.

The validator rejects the entire response for malformed JSON, refusal/truncation, extra or missing keys, incorrect types, an invalid status or label, noncanonical or non-whitelisted symbols, or duplicate tickers. Do not repair values, change case, drop bad rows, or accept a partial array. No eligible article may produce final outputs if it has no accepted contract response; `insufficient_information` stops the run rather than being reconstructed as neutral.

## Required generated CSVs

These are exact schemas with no extra columns. Rows are generated by the pipeline, never hand-edited.

| File | Header | Row rule |
| --- | --- | --- |
| `entities.csv` | `id,ticker,label` | One row per unique `(article, company)` pair. IDs retain their source value as CSV text; tickers are canonical; labels use the three exact lowercase values. |
| `scores.csv` | `ticker,value` | One row for every ticker in `entities.csv`, including neutral-only tickers. Sum all article contributions using the fixed formula. |

Stable input/entity ordering and stable ticker ordering are proposed serialization choices. Do not round intermediate weights or score sums. Serialize final finite numbers consistently without adding a precision rule that changes the calculation.

For each entity, with `days = as_of - article date` in fractional elapsed days and New York `as_of = 2026-09-29 00:00`:

```text
weight = 0.5 ** (days / 7)
score[ticker] = sum(numeric_label * weight)
```

Do not clip, normalize, or round `days`; under confirmed user policy, accept valid future timestamps as written, so their literal formula weight can exceed one, and block ambiguous/nonexistent local timestamps. Computing `days` as the elapsed difference between UTC instants is a proposed technical interpretation, not a separately confirmed policy. Reject/report unsupported non-finite arithmetic rather than silently correcting it. A ticker represented only by neutral rows has a score of zero. A zero total can also reflect cancellation; it is not evidence of no coverage.

## Private progress ledger

The confirmed user policy is one local, unversioned, private ledger for a single logical workflow, separate from result CSVs, with accepted classifications and all attempts. Preserve unknown outcomes, revalidate replay, and do not silently begin fresh paid inference from corrupt/incompatible progress. The precise JSON fields below are proposed mechanics. Do not log or persist article payloads, prompts, raw responses, credentials, or private source text.

| Record area | Minimum contents |
| --- | --- |
| Header | Workflow identity, schema/contract identity, canonical input fingerprint, model/prompt/rules identity, and creation/update metadata. |
| Accepted classifications | Stable article identity and position, validated status/entities, and the request/attempt reference that produced them. |
| Attempts | Stable workflow/article/attempt identity, pending/success/failure/unknown outcome, safe error category, request timing/wait information, and usage counters when known. |

Persist a pending attempt before the request. Afterward, atomically save its known outcome and usage together with any accepted classification. If the response or local write leaves the provider outcome unknown, preserve that uncertainty. Do not promise exactly-once billing. Stop before subsequent calls if progress cannot be safely written.

The confirmed fingerprint coverage is full validated input after only permitted normalization/deduplication, plus classification model, prompt, response contract, rules, and supported parameters. Original input-byte hashes may be audit metadata but do not replace the semantic fingerprint. Ignore presentation-only differences and added exact duplicates after canonicalization. Canonical serialization and hash encoding are proposed mechanics; keep canonical serialization in memory and persist the fingerprint, not its source content. Always revalidate accepted cache entries against the current whitelist and response contract.

Corrupt or incompatible progress never silently triggers new paid inference. An explicit fresh workflow is a new classification history and must not erase accounting uncertainty from the prior workflow. Rebuild all current-input counts, warnings, values, and report fields on each invocation rather than trusting a saved summary.

## Run report and accounting

**Confirmed user cost policy:** Compute cost from all known attempt usage, including retries and rejected responses; missing usage remains unknown. Cached input is part of input, reasoning tokens are part of output, and the per-article denominator is unique eligible articles with an accepted contract response. Exclude duplicates, omissions, failures, and insufficient-information results; use `N/A` for a zero denominator. Keep full cost claims separate from known partial cost.

**Proposed report layout:** Write a separate machine-readable report with processing/accounting states, safe fingerprints, current input/omission/dedup/entity/ticker counts, calls/attempts, known and unknown usage/cost, rates, denominator, per-eligible-article cost, Batch-use disclosure, and safe diagnostic categories. Do not include original article content, raw prompts/responses, credentials, or unsafe exception text. The report field names and state vocabulary are proposed.

Processing state is one of `completed`, `completed_with_omissions`, or `failed`. Accounting is independently `complete_local` or `incomplete`. Valid output files do not imply a complete full-run cost if any attempt usage is unknown.

For every attempt with known nonnegative integer usage (booleans are not integers for this contract), require cached input tokens no greater than input tokens. Cached tokens are a subset of input; reasoning tokens, if reported, are part of output. Compute cost from attempts, including retries and rejected model responses:

```text
known_usd = sum(
  ((input - cached_input) * 2.00
   + cached_input * 0.20
   + output * 12.00) / 1_000_000
)
```

Use decimal/scaled arithmetic or an equivalent no-premature-rounding method; round only for display. Report counts for the new invocation, prior attempts in the same workflow, and all known/unknown attempts. An attempt count is not a billable-generation count. Missing usage remains unknown, not zero.

The per-article denominator is unique eligible articles with an accepted contract result, including accepted empty results and replayed results. Exclude exact duplicates, body-omitted articles, failed classifications, and `insufficient_information`; report `N/A` for a zero denominator. Known partial cost must not be called full-run cost. Use the confirmed standard rates and disclose any actual Batch use; the proposed design does not select Batch.

## Output generation boundary (proposed)

Prepare both complete CSV files before replacing either. A completion marker that binds their generation and hashes, written last, is a proposed way to detect mixed generations; separate file replacements are not jointly atomic. A failure before output replacements leaves the old pair untouched. A failure during replacements may leave an incomplete or mixed generation; if the marker is absent or does not match both files, do not accept or announce the outputs as current/successful. No rollback or preservation of the old pair is guaranteed after publication starts. A failed eligible classification must not produce a new final CSV generation.
