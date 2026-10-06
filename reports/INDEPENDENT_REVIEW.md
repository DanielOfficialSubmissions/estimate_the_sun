# Independent checks — 2026-10-06

Two auxiliary agents were used as requested. No auxiliary model-training process was run.

## Rules reviewer

Read official competition and terms pages in a normal public browser. Confirmed open
status, Autonomous option, solo entry, 18+/student-account conditions, shipped-data-only
restriction, submission limits, report rubric, audit and payment/IP terms. Detailed record:
RULES.md. Did not register, accept terms, retrieve any labels or modify external state.

## Validation/code reviewer

Read-only review of src/solar.py, protocol, tests and documentation. Checked chronology,
row-local features, absence of ID/target features, MW MAE and capacity weights, disabled
random early stopping, pre-lockbox selection, output ID alignment and artifact integrity.
No direct leakage or remaining blocking scaffold defect found. This is not evidence of
competition predictive performance or a guarantee that unseen data meet the schema.

Found and fixed:
1. A crash after saving metrics but before journal append could omit an experiment.
   Cached results now reconstruct journal entries atomically and idempotently.
2. An altered selection could modify journal entries before the lockbox hash check.
   Integrity checks now precede those writes; completed provenance is also checked.
3. A resume test comparing only prediction hashes could miss deterministic retraining.
   The test now replaces fit with a function that raises on any attempted fit.
4. Added a fully missing weather column alongside the already-tested missing row.

After review changes, all 11 unit/invariant tests and the complete synthetic integration
passed. The integration verifies selection tampering is rejected without journal changes.

Residual limitations: actual official CSVs and quality untested; development quarters
are correlated, not independent folds; short training history limits extrapolation;
lockbox discipline also requires not deleting outputs or using a new directory to retune.

## Official data and measured result review

After user sign-in, the reviewer checked official schema/audit and independently
recomputed MAE for all seven saved prediction tables. All matched. Selection guards
chose hgb_features, all four quarters improved, and the final CSV had exact test IDs,
finite nonnegative numbers and matching hashes. Source/input/model/selection/provenance
were consistent. Fresh-fit reproduction passed. The 1,176-word report and README were
checked against measured values; suggested wording/stale-status corrections were applied.

Final assessment: local package ready; no remaining blocking local defect. Public code
URL, entry and uploads remain user-controlled. No official-score/competitiveness claim.
