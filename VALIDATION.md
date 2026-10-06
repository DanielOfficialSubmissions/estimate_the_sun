# Frozen validation protocol — 2026-10-06, before data access

This is retrospective estimation with supplied observed weather, not an operational forecast.

1. Development fit: 2022-01-01 00:00 UTC through 2023-06-30 23:30 UTC.
2. Development evaluation: 2023-07-01 through 2024-06-30, scored as a full year and four quarters.
3. Freeze model choice/configuration using development only.
4. Lockbox fit: 2022-01-01 through 2024-06-30.
5. Lockbox evaluation ONCE: 2024-07-01 through 2025-06-30. Compare climatology,
   local HGB MW reference and the frozen candidate on identical rows; do not select again.
6. Final fit on all shipped training rows; output original test ID order.

Train/validation boundaries are UTC midnight, so repeated hourly weather and half-hours
from the same day never straddle the boundary. No lags, future targets, external labels,
ID encodings, target-based imputers, or random validation/early stopping. Tree histogram
binning is fitted on training only; NaNs are handled natively. Features are row-local.

Fixed candidate order: climatology, HGB MW, HGB capacity factor, HGB capacity factor
with calendar harmonics and weather summaries. Parameters: src/solar.py, seed 20261006.
Capacity-factor loss uses sample weights proportional to capacity so the objective is
MAE in MW. It may still perform worse: normalization is a hypothesis, not a fact.
No forced night zeroing: hourly irradiance zero alone is insufficient evidence about
half-hour generation at twilight. No hard upper cap at nameplate capacity.

Replace the current candidate only if full-year MAE is strictly at least 0.5% lower,
at least three of four quarters improve, and no quarter worsens by over 5%.
Four quarters from one fixed-origin year are correlated diagnostics, not four independent
folds. The subsequent untouched year tests generalization; a failure there is reported,
not used for further tuning. The shorter development training history is a limitation.

selection.json is written before lockbox evaluation; its hash is locked in
lockbox_started.json. Input, source, dependency and protocol hashes support resuming
without repeating completed evaluations. If the process dies mid-fit, only that unfinished
fit may repeat. Keep the original artifacts; never erase them to reopen the lockbox.
Any follow-up research after viewing lockbox results needs a newly stated validation
limitation, not a claim that the same year remains untouched.

Synthetic fixtures validate software only. Their metrics must never appear as
competition evidence or in the root EXPERIMENTS.csv.
