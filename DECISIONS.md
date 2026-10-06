# Decisions

2026-10-06:
- Use shipped CSVs only; never query the linked PV_Live target API, even though the public data card links it.
- No ID or row-order features. Parse and sort UTC timestamps for fitting; preserve original test order on output.
- Target is retrospective generation estimation using observed weather, not a day-ahead forecast. State this deployment limitation.
- Keep synthetic software tests separate from actual competition experiments and scores.
- Train centrally with at most two CPU threads. No paid services; unknown prize size limits scope to cheap models.
- Freeze validation before receiving target values: development year July 2023–June 2024 after training through June 2023; lockbox July 2024–June 2025 after training through June 2024. Assess four seasonal quarters on development year, select once, evaluate lockbox once. Lockbox training may include development year after selection; no lockbox labels may select or tune a model.
- Development uses a shorter training history than final competition fit; this limits performance extrapolation. No random row split and no future training rows in validation.
- Do not claim to reproduce the organizer's tree baseline exactly: its implementation/parameters are not supplied on the page. Implement an explicitly named local reference.
- Solar elevation requires coordinates absent from the published column list. Defer precise solar geometry until permitted coordinates are supplied or clarified; calendar harmonics require only supplied timestamps.

Review and stop decisions:
- Fixed crash recovery: cached metrics/predictions repair the experiment journal idempotently,
  with atomic replacement and no refit. Cache checks compare rows, predictions hash and MAE.
- Check frozen-selection integrity before modifying logs; verify completed provenance.
- Tests now prove that resume cannot call fit, and tampered selection cannot modify the journal.
- Full synthetic smoke uses 12 iterations solely to verify flow cheaply. It is not a model
  experiment, cannot establish improvement, and its temporary predictions are deleted.
- Stop after all useful access-independent preparation because official downloads require
  a signed-in account. Do not spend six hours manufacturing substitute data or tuning toys.
- Technical report remains explicitly incomplete; no invented feature importance, failures,
  ranking, MAE or financial impact. User action needed: obtain the three official CSVs.

Official-data continuation, 2026-10-06:
- User sign-in unlocked official CSV downloads without joining/accepting rules. Downloaded
  only the three shipped files via visible links. Data availability blocker resolved.
- Official count/schema/calendar/ID and weather-pair checks passed; missing-weather counts
  were all zero. Test installed capacity exceeds the training range.
- Executed exactly the four predeclared development candidates and three final-year checks.
  All three successive improvements passed every quarter; selected hgb_features before lockbox.
- Development: baseline 494.9712, MW tree 193.4261, normalized 146.3426, engineered 136.3425 MW.
  Lockbox: baseline 606.9734, MW tree 283.8709, frozen engineered 146.4556 MW.
- The unnormalized tree was not selected; it had pronounced lockbox underprediction
  (bias -212.6224 MW) and Q2 MAE 550.0507 MW. Treat scale extrapolation as a hypothesis,
  not a demonstrated sole cause. No post-lockbox corrective tuning performed.
- Final model fitted on all 61,296 official training rows; all 17,520 test predictions
  validated. Independent fresh fit from the same frozen source reproduced exact CSV bytes.
- Error diagnostics show persistent bright-condition and tail errors; do not infer
  operational forecasts, guaranteed savings, official score, ranking or winning chances.
- Stop after a working locally improved prototype and cheap predefined ablations because
  prize amounts are unknown and the package is ready. Public code publication and all
  participation/report/upload actions require user's separate authorization.
