codex report — plan re-review (updated plan)
============================================

Scope: second pass on `~/.claude/plans/snazzy-enchanting-whistle.md` after its expansion to “all 62 columns.” Data source: `wink.parquet` stats pulled with `./venv/bin/python`.

Material mismatches / risks
---------------------------
- Completeness vs applicability: Plan lists all columns but still treats several as universally populated. In reality `effectiveannualrate` and `averageannualrate` are only 13,540/1,087,253 rows; `effectiveYield` 142,927; `guaranteeDuration` 198,357 with a -1 outlier; `greatest_date` missing on ~3.5k rows. Notebook should show null %, not just definitions.
- Scaling error: Plan claims `performanceTriggeredRate` “mean ~9%” (even excluding outliers); actual mean is 0.241 (24.1%) with max 999.0 and only 52,901 populated rows. Revisit narrative and outlier handling.
- Applicability tagging: `performanceTriggeredRate` appears in Structured and Indexed rows and even some MYGA/IVA due to data noise (counts: Structured 28,048; Indexed 24,853; RILA 27,202; FIA 20,435). Mark as “Indexed/Structured only; others = noise.”
- Guarantee duration: Values run 1–20 years but also -1; only 198k rows non-null. Need cleaning note and MYGA-only emphasis.
- MGSV interpretation: `mgsvBaseRate` averages 0.874865 (87.5%), suggesting it is the statutory 87.5% factor, not a “base rate” in the usual sense. Clarify that mgsvBaseRate is a percentage of premium, not an interest rate.
- Outlier handling: `capRate` max 9999.99, `performanceTriggeredRate` max 999, `bufferRate` min -0.10. Plan notes outliers but no proposed clipping/winsorization; recommend adding handling guidance.
- Status semantics: `status` distribution is historic/current/nlam/new; plan doesn’t explain filtering to current for analysis. Similarly `mva` has two “None” string values.

Additional enhancements to add
------------------------------
- Null-aware profiling in the notebook with per-column non-null counts and product-group applicability flags.
- Data cleaning steps: coerce “None” strings to null, drop or flag `guaranteeDuration == -1`, decide clipping rules for extreme caps/trigger rates.
- Product applicability matrix: indicate which rate fields are expected per `rateType`/`productGroup`, treating other occurrences as anomalies.
- MGSV section: explicitly note mgsvBaseRate ≈ 87.5% premium factor; mgsvRate/mgsvRateUpperBound are annual rates (0–3.5% and 0–5%).

Key supporting stats (fresh pull)
---------------------------------
- Fixed rate: 171,187 non-null, min 0.0005, max 0.51, mean 0.0295.
- Cap rate: 260,227 non-null, min 0, max 9999.99, mean 0.5501.
- Participation: 454,766 non-null, min 0, max 9.0, mean 1.027.
- Spread: 27,927 non-null, min -0.0725, max 99.0.
- Buffer: 169,056 non-null, min -0.10, max 1.0, mean 0.149.
- Triggered: 52,901 non-null, min 0, max 999, mean 0.241.
- MGSV: baseRate 376,279 non-null (mean 0.8749), rate 376,279 (mean 0.00999), upperBound 360,758 (mean 0.0297).
