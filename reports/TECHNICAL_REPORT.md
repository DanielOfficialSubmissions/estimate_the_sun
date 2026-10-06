## The problem and who it serves

Great Britain's grid operator needs a national estimate of solar generation to inform
balancing decisions. This solution estimates average generation in MW for each half-hour
from the competition's observed weather and installed PV capacity. Better estimates can
inform reserve planning, but this retrospective exercise does not demonstrate operational
forecast accuracy: the supplied weather describes what already happened.

On a held-out July 2024–June 2025 year, mean absolute error fell from 606.973 MW for
capacity-scaled climatology to 146.456 MW, a reduction of 460.518 MW or 75.87%. Multiplying
by the half-hour duration gives a reduction of 230.259 MWh in mean absolute interval-energy
error. This is an error-equivalent quantity, not a measured reduction in reserve purchases,
costs, emissions, or curtailment. No official submission or ranking has been obtained.

## Data and validation

The downloaded organizer files contain 61,296 training half-hours from January 2022
through June 2025, and 17,520 test half-hours from July 2025 through June 2026. Both
have complete, unique UTC half-hour grids and unique IDs; their ID sets are disjoint.
All 72 weather fields are present without missing values. The two half-hours in each
hour share identical weather, as documented. Irradiance is hourly Wh/m², capacity is MWp,
and the target is generation MW; no factor-of-two irradiance conversion was applied.

Installed capacity spans 14,067.77–20,790.60 MWp in training and 20,795.10–23,803.42 MWp
in test. This observed extrapolation risk supported testing the preplanned capacity-factor
variant. Before the lockbox boundary, 20,913 of 43,776 labels were zero. Dataset summaries
of later targets were suppressed until selection was frozen.

The validation protocol was recorded before obtaining official data. Development training
ends June 2023; evaluation covers July 2023–June 2024, including leap day, with 17,568
rows. Selection uses overall MW MAE with four-quarter safeguards: at least 0.5% improvement,
improvement in at least three quarters, and no quarter more than 5% worse. The selected
configuration was saved before evaluation on an untouched July 2024–June 2025 lockbox,
using training through June 2024. All compared models use identical rows within each split.

This mirrors the competition's following-year distribution shift; entire UTC days and
repeated-weather hours stay on one side of a boundary. Four quarters are correlated
seasonal diagnostics, not independent validation folds. No random row split, automatic
random early stopping, target lags, ID features, external labels, or learned preprocessing
from validation/test was used. Histogram binning is fitted on training data. No withheld
target source was consulted. Public/private test assignment was not exploited.

## Method

The baseline uses mean training capacity factor for each month and UTC half-hour, multiplied
by the row's installed capacity. This reproduces the stated climatology recipe locally;
it is not an assertion that means are optimal under absolute loss.

All tree candidates use scikit-learn HistGradientBoostingRegressor with absolute-error
loss, 180 iterations, learning rate 0.07, 31 leaves, minimum leaf size 30, L2 regularization
1.0, seed 20261006, and early stopping disabled. The local reference uses shipped weather,
capacity, month, half-hour and day of year to predict MW. The normalized variant predicts
generation divided by capacity, with sample weights proportional to capacity. Its weighted
absolute objective corresponds to MW absolute error after restoring capacity.

The final variant adds daily/yearly sine and cosine features, mean/standard deviation/minimum/
maximum and missing counts for each weather quantity across twelve points, and a protected
mean all-sky/clear-sky irradiance ratio. These are deterministic row-local calculations.
No precise solar coordinates or external geography were imported. Predictions are clipped
only below zero; no forced night-zero rule or nameplate upper cap was selected.

| Model | Development MAE, MW | Lockbox MAE, MW |
|---|---:|---:|
| Capacity-scaled climatology | 494.971 | 606.973 |
| Local tree predicting MW | 193.426 | 283.871 |
| Capacity-factor tree | 146.343 | Not evaluated |
| Capacity-factor tree plus feature group | 136.342 | 146.456 |

Each successive development candidate improved all four quarters. Normalization reduced
development MAE by 24.34%; adding the feature group reduced it a further 6.83%. This is
a group ablation, not evidence about individual feature importance. The selected model
improved every lockbox quarter relative to both baselines, reducing local tree error by
48.41%. The raw-MW approach failed to match the normalized solution: lockbox bias was
−212.622 MW and April–June MAE 550.051 MW, versus 199.417 MW for the winner. Capacity
extrapolation is a plausible contributor, not a proven causal explanation.

Organizer references 700.405 MW and 279.183 MW are on hidden competition rows. They
cannot be compared directly with these local scores; the exact organizer tree implementation
was unavailable. There is no evidence that local ranking tracks the public leaderboard.
No further model selection occurred after opening the lockbox.

## Error analysis and limitations

Selected-model lockbox quarterly MAE was 153.805, 103.171, 129.640 and 199.417 MW, from
July–September 2024 through April–June 2025. Error is larger in the brighter quarter.
For rows with cross-point mean irradiance above 400 Wh/m², MAE was 393.183 MW across
2,084 rows, versus 0.324 MW across 8,172 zero-mean-irradiance rows. The latter is an
observed weather segment, not an astronomical night definition. Overall MAE therefore
conceals substantial errors at higher output.

Mean prediction bias was +25.976 MW. The 99th percentile absolute error was 1,074.456 MW
and the maximum 3,933.206 MW. Hour-start MAE was 149.473 MW versus 143.439 MW at
half-past. Hourly weather cannot resolve all half-hour fluctuations; this is a plausible
resolution limitation, not an attribution established by these comparisons.

A paired bootstrap of 2,000 complete-day resamples placed the climatology-baseline improvement
between 423.684 and 499.842 MW at its empirical 95% interval. It ignores cross-day
correlation and is only a sensitivity diagnostic, not a guarantee for the test year.
The evaluation contains only two annual windows and shorter development history than
the final fit. Future capacity composition, weather coverage and PV_Live estimation may
change. National targets cannot establish regional fairness or site-level accuracy.
Operators over-trusting these predictions could procure inappropriate reserves; deployment
requires error-tail and bias monitoring, capacity/weather drift checks and operational
fallbacks, plus weather inputs actually available at the decision time.

## Reproducibility

Solution owner: **DanielSolaris** (GitHub: **DanielOfficialSubmissions**). Required AI-use declaration:
**Autonomous**. The source package includes src/solar.py, VALIDATION.md, pinned
requirements.lock, tests, experiment journal and diagnostic scripts. Python 3.13.3,
scikit-learn 1.6.1, pandas 2.2.3 and NumPy 2.2.6 were used on macOS x86_64, with at
most two numerical threads and no paid computing services. From a prepared environment,
`.venv/bin/python src/solar.py run` audits the official files in data/raw, evaluates the
fixed candidates, freezes selection, evaluates the lockbox, refits on all training data
and writes artifacts/official/submission.csv.

Eleven invariant tests and a separate synthetic software integration passed. A fresh fit
from the official training CSV, without loading the saved model or reselecting candidates,
reproduced the final 17,520-row CSV byte for byte. Its SHA-256 begins 481488fe2a714a32;
the full hash and input/source hashes are recorded in completed.json and reproduction.json.
No NaN, infinity, negative prediction, duplicate/missing ID or order mismatch remains.
Cross-platform bitwise identity is not promised. Public source repository: [https://github.com/DanielOfficialSubmissions/estimate_the_sun](https://github.com/DanielOfficialSubmissions/estimate_the_sun). Source credit: PV_Live, Sheffield Solar, University of Sheffield,
CC BY 4.0; NASA Langley Research Center POWER Project. Competition data and prediction
files must not be included in a public code repository.
