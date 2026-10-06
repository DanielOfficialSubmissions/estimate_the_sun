# Rules and access audit

Checked 2026-10-06, public official pages in a browser; independent rules reviewer agreed.
Competition: https://www.square1ai.com/competitions/solar-britain
Competition terms: https://www.square1ai.com/competitions/terms (updated 2026-09-21).
Direct web-open and sandbox HTTP initially failed; ordinary browser access succeeded.
Initial browser was signed out. After user sign-in, all three official CSV links became
available without entry. Files downloaded at about 12:50 UTC on 2026-10-06.
No agent registration, acceptance, publication or submission has been performed.

## Entry and scoring

Open from 2026-10-05; closes 2026-11-29 23:59 UTC (2026-11-30 00:59 Europe/Belgrade).
Results scheduled 2026-12-07; seven-day appeal. Last 48 hours: public board quiet period.
Free, solo, one person/account/entry, age 18+, student account and fixed handle.
Autonomous agent authorship is explicitly supported; declare **Autonomous**.
MAE in MW, lower is better. Hidden test split determines metric rank: 70% of final
points; report contributes 30%. No metric points without beating climatology baseline.
Public/private test samples are 30%/70%, assigned by complete days across all seasons.
The site displayed zero entrants and no ranked scores on the check date. This says
nothing about eventual competitiveness or likelihood of winning.
Organizer reference values 700.405 MW (climatology) and 279.183 MW (tree) are PRIVATE
split scores, despite being shown on the public page. Never compare them directly to
our local scores; exact organizer tree implementation is not supplied.

Five scored uploads per UTC day, resets 00:00 UTC (02:00 Belgrade on check date;
01:00 after local DST ends). Up to two final picks; absent selection, best public file.
Rejected format checks do not use a scored upload. Uploads require separate approval.

## Data and software

Use shipped data only. The data-card source licences are not permission to look up
withheld labels. In particular do not open/download the linked PV_Live API spanning
the test period. No target search, hand-labelling, external training data or pretrained
weights. Only deterministic transforms of shipped fields are planned. Do not redistribute
derived dataset files or prediction files. Sharing original solution code/ideas is permitted.
No explicit library whitelist was found. Ordinary local scikit-learn fitting uses no
pretrained data. Exact site coordinates are not provided on the data card, so precise
solar elevation is deferred instead of silently importing geographic resources.

Published schema: id, datetime_utc, installed_capacity_mwp; six weather quantities at
twelve named points; generation_mw only in train. January 2022–June 2025 train;
July 2025–June 2026 test. Counts independently verified from official CSVs: 61,296 and 17,520.
UTC denotes interval START. NASA hourly weather is repeated on both half-hours;
irradiance is hourly Wh/m², target is average generation MW, capacity is MWp.
Do not introduce an erroneous factor of two conversion. Original -999 missing codes
were reportedly blanked; code also handles residual -999 only in weather fields.

Attribution when data are used:
- PV_Live by Sheffield Solar, University of Sheffield — CC BY 4.0.
  https://www.solar.sheffield.ac.uk/pvlive/
- NASA Langley Research Center POWER Project, funded through the NASA Earth Science
  Directorate Applied Science Program. Public Earth science source, as credited by organizer.
These source attributions do not waive the competition redistribution restriction.

## Submission and report

CSV UTF-8, comma separated, <=10 MB, one finite numeric generation_mw per test ID;
17,520 rows. Our stricter validator requires exactly id,generation_mw and test order,
although the site permits reordered columns and ignores extra columns. Site does not
publish a numerical prediction range; nonnegative output is our physical modelling
choice, not a claimed organizer limit. No automatic nameplate upper clipping.

Report: Markdown, 600–1500 words, in the on-page editor. Mandatory headings in order:
1. The problem and who it serves
2. Data and validation
3. Method
4. Error analysis and limitations
5. Reproducibility

Each criterion is graded 0/2/4/6 by three independent judges, using the median.
A public repository/notebook link is required. At least top ten plus random 5% are
audited by regeneration from supplied train.csv; numerical tolerance is not published.
A filed report and beaten baseline are needed for medals/prizes. No grader-directed text.

## Prize, rights and eligibility

Top-three cash awards; amounts scheduled for 2026-11-02 and currently unknown.
Bank/PayPal, AUD or equivalent USD, within 30 days of results after identity verification.
Taxes and transaction charges fall to winner. Country-law/sanction restrictions can
prevent prizes even when participation for record is permitted; no country list provided.
The user's age, citizenship, residence and payment eligibility have NOT been inferred.
Code/report ownership remains with entrant. Entry grants organizer a worldwide,
nonexclusive royalty-free publication licence for entry/report/result and use of
anonymized submissions for grader calibration. Specific competition rules take precedence.
Terms cite NSW, Australia law. These are recorded organizer terms, not legal advice.

## Remaining uncertainty

User eligibility and payment availability; exact coordinates;
pretrained-resource permission; audit tolerance; rank formula edge case for one entrant;
changes after this check. General site Terms of Service/Privacy were not audited here.
Re-check at entry. Only request authorization once local work needing no access is ready.
