codex report — WINK plan gap analysis
=====================================

Context: review of `~/.claude/plans/snazzy-enchanting-whistle.md` against the actual `wink.parquet` schema (62 cols) and product mix (FIA, RILA, MYGA, IVA, FA).

Plan coverage gaps (27 columns currently undocumented)
------------------------------------------------------
- averageannualrate
- bonusRate1, bonusRate1Footnote, bonusRate2, bonusRate2Footnote, bonusRate3, bonusRate4, bonusRate5
- bufferModifier
- defaultActuarialView
- effectiveYield
- fundGroup, fundManager
- greatest_date
- mgsvBaseRate, mgsvRate, mgsvRateUpperBound
- othercreditingstrategyinformation
- performanceTriggeredRate
- productNameSuffix, productTypeID
- rateType, ratesBand
- rowNumber
- shareClass
- subaccountUsed
- surrChargeDuration

Product mix reminders (counts)
------------------------------
- IVA 460,264; FIA 334,074; RILA 160,294; MYGA 122,513; FA 10,106; None 2 (rows: 1,087,253).
- RateType distribution: Variable 442,144; Indexed 304,662; Fixed 171,187; Structured 169,258; None 2.

Why the gaps matter
-------------------
- FIA fields: capRate, participationRate, spreadRate, indexingMethod, indexCreditingFrequency, indexUsed, bonusRate*, premiumBand, ratesBand, surrChargeDuration, mva.
- RILA fields: bufferRate, bufferModifier, performanceTriggeredRate, capRate, indexUsed/method, surrChargeDuration; long disclosures live in othercreditingstrategyinformation; rateType == “Structured”.
- MYGA/FA fields: fixedRate, guaranteeDuration, mgsv* (nonforfeiture), mva, surrChargeDuration, premiumBand; bonusRate* footnotes show banded promos.
- IVA fields: fundGroup, fundManager, subaccountUsed, shareClass; fee touchpoints via netExpenseRatio, annualFeeForIndexingMethod.
- Cross-cutting: productTypeID/rateType map product group semantics; productNameSuffix carries channel/state variants; defaultActuarialView/indexingMethod supply calc logic; greatest_date/rowVersion/rowNumber support audit and dedup.

Data and typing considerations
------------------------------
- Percent fields stored as decimals (e.g., bonusRate1 up to 0.50). Document scale.
- Timestamps are int64 nanos; also string “None” present in some text columns—coerce to nulls.
- surrChargeDuration holds numeric years as strings; premiumBand/ratesBand capture tiering that affects rates/bonuses.
- Footnote columns contain long free-text product disclosures; summarize and trim for the data dictionary.

Notebook/doc updates to add
---------------------------
- Include the 27 missing columns in the schema table with applicability flags (FIA/RILA/MYGA/IVA/FA) and unit/scale notes.
- Normalize types: convert timestamp ints to datetimes; convert “None” strings to nulls; clarify percent scales.
- Add categorical dictionaries: rateType, productTypeID, indexingMethod, defaultActuarialView, bufferModifier, premiumBand, ratesBand, shareClass, surrChargeDuration buckets.
- Build product-group dashboards (counts, rate ranges, surrender durations, bonus prevalence) to keep the data dictionary actionable for forecasting.

External references to anchor definitions
-----------------------------------------
- FINRA Regulatory Notice 22-08 (complex products, includes RILA sales obligations): https://www.finra.org/rules-guidance/notices/22-08
- SEC Investor Bulletin on Registered Index-Linked Annuities: https://www.sec.gov/oiea/investor-alerts-and-bulletins/ib_rilas
- NAIC consumer resources (surrender, MVA, nonforfeiture context): https://content.naic.org/consumer-resources
- Wink AnnuitySpecs product glossary for field labels/index methods: https://www.winkintel.com/analysis-tools/annuityspecs/
- LIMRA quarterly U.S. annuity sales releases (market sizing by FIA/RILA/MYGA): https://www.limra.com/en/newsroom/news-releases/
