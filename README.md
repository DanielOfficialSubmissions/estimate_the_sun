# Estimate the sun — reproducible local solution

**Reproducible competition solution; no competition upload or official ranking.**
Solution owner: **DanielSolaris** (GitHub: **DanielOfficialSubmissions**).
Required competition AI-use declaration: **Autonomous**. This identifies the development
method. Ownership is recorded in OWNERSHIP.md. Rules checked 2026-10-06; see RULES.md.

| Local comparison (MAE, MW) | Development Jul 2023–Jun 2024 | Untouched year Jul 2024–Jun 2025 |
|---|---:|---:|
| Climatology baseline | 494.971 | 606.973 |
| Local tree predicting MW | 193.426 | 283.871 |
| Capacity-factor tree | 146.343 | Not evaluated |
| Selected capacity-factor tree with feature group | **136.342** | **146.456** |

All models in each column share the same evaluation rows. The final choice was fixed
before viewing the untouched-year results. These are local scores, not leaderboard scores.
Organizer references 700.405 and 279.183 are measured on different hidden rows.

## Outputs

- `artifacts/official/submission.csv`: 17,520 rows, exact test ID order; valid and reproducible.
- `reports/TECHNICAL_REPORT.md`: measured English report in the five required sections.
- `EXPERIMENTS.csv`: seven evaluations with parameters, seed, elapsed times and decisions.
- `reports/error_analysis.json`: quarter/month metrics are in model artifacts; this adds
  irradiance/cloud/half-hour segments, error tails and complete-day bootstrap diagnostics.
- `reports/reproduction.json`: fresh training from CSV reproduced identical submission bytes.
- `reports/SUBMISSION_READINESS.md`: status and precise next action; `RULES.md`: requirements and uncertainties.

Final submission SHA-256:
`481488fe2a714a32023de6dd1ae20b4b0d5c3ffa3951a2f451e6d804e91a5aaf`.

Public source: [https://github.com/DanielOfficialSubmissions/estimate_the_sun](https://github.com/DanielOfficialSubmissions/estimate_the_sun).
DanielSolaris has joined the competition. No predictions or report were submitted.

## Reproduce

Obtain train.csv, test.csv and sample_submission.csv from the official signed-in page:
https://www.square1ai.com/competitions/solar-britain . Save them in `data/raw/`.
Do not retrieve withheld targets from PV_Live or any other source.

Fresh machine with uv and CPython 3.13.3 available, from the project directory:

```sh
mkdir -p data/raw
uv --cache-dir .uv-cache venv --python 3.13.3 .venv
uv --cache-dir .uv-cache pip sync --python .venv/bin/python requirements.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python src/solar.py run
```

One-command full pipeline after environment/data preparation:

```sh
.venv/bin/python src/solar.py run
```

It audits files, evaluates fixed development candidates, freezes model selection, evaluates
one untouched year, refits on all training rows, writes predictions, checks a reloaded
model and records hashes. An unchanged rerun resumes cached results without fitting again.
Never delete/alter evidence to use the lockbox for additional tuning.

Independent reconstruction from the already-frozen selection, without loading any model
or redoing development selection/lockbox evaluation:

```sh
.venv/bin/python scripts/reproduce_frozen.py
.venv/bin/python src/solar.py check --submission artifacts/official/submission.csv
.venv/bin/python scripts/analyze_errors.py
```

The first command creates `artifacts/reproduction/submission.csv` and requires exact
byte equality with the original. The original frozen selection/completed metadata must
exist. On a fresh source-only checkout, run the full pipeline first.

## Validation and method

VALIDATION.md was frozen before receiving official data. Development fit ends June 2023;
evaluation is July 2023–June 2024. Untouched-year fit ends June 2024; evaluation is July
2024–June 2025. Selection requires at least 0.5% annual MAE improvement, gains in three
of four quarters and no quarter worsening over 5%. Every accepted candidate actually
improved all four development quarters. No reselection followed the final-year check.

Baseline: mean capacity factor by month/UTC half-hour, scaled by current capacity.
Reference: histogram gradient-boosted tree in MW. Variants: capacity-factor target with
capacity-weighted absolute loss, then cyclic calendar and weather summaries. All use the
same fixed tree parameters. Missing values use native handling; supplied files had none.
No external data, ID features, target lags, guessed coordinates or forced night-zero rule.

This is retrospective estimation with observed weather, not a demonstrated operational
forecast. Larger test capacity, high-output error tails, short development history and
only two annual windows limit extrapolation. Read the measured report before use.

## Environment, verification and source provenance

Python 3.13.3 / macOS x86_64; pinned ten-package requirements.lock. Up to two numerical
threads, seed 20261006, CPU only. Exact cross-platform floating-point equality is not
promised. Dependencies are project-local; no global installations or paid APIs.

`run_provenance.json`, `selection.json`, `lockbox_started.json` and `completed.json` in
artifacts/official bind data/source/model/output versions and the frozen selection.
A saved joblib model is local trusted code; do not load untrusted joblib artifacts.

Eleven invariant tests and full-calendar synthetic software integration passed. Synthetic
fixtures were temporary, used 12 boosting iterations instead of 180, were deleted, and
are excluded from competition results. Real training and fresh-fit verification are
recorded separately. For software integration only: `.venv/bin/python tests/smoke_full.py`.

## Publication and submission

The source-only bundle was approved for publication by the owner. The local submission bundle additionally includes predictions/model metadata
for the user's private use and must not be published or shared as a dataset.

Exclude raw/processed data, fitted models, validation predictions and submission files
from public repositories. `.gitignore` excludes them. The source attributions in RULES.md
must remain. Dependency licences remain upstream; no project licence choice has been
made on the user's behalf. The owner has joined as DanielSolaris and authorized source publication. On-page report
filing, AI declaration, prediction upload and final selection remain pending user actions.
