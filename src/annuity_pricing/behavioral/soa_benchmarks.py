"""
SOA Benchmark Data for Policyholder Behavior Calibration.

[T2] Empirical data extracted from free SOA research studies.
These tables are used to calibrate lapse and withdrawal models.

Data Sources
------------
1. SOA 2006 Deferred Annuity Persistency Study (78 pages)
   - Tables 5-8: Surrender rates by duration, age, cost structure
   - Source: https://www.soa.org (free PDF)

2. SOA 2018 VA GLB Utilization Study (338 pages)
   - Tables 1-17, 1-18, 1-21: GLWB utilization by duration, age, ITM
   - Source: https://www.soa.org/limra (free PDF)

Notes
-----
- SOA 2019-2021 VA Behavior Study exists but detailed data requires
  paid access to Experience Studies Pro. Using 2006/2018 data as primary.
- All rates are expressed as decimals (e.g., 0.05 = 5%)

See Also
--------
docs/assumptions/BEHAVIOR_CALIBRATION.md : Full methodology documentation
"""

from typing import Final

# =============================================================================
# SOA 2006 Deferred Annuity Persistency Study
# =============================================================================

# Table 6: Surrender Rates by Contract Year (7-Year Surrender Charge Schedule)
# Key insight: Surrender rate spikes at year 8 (post-SC) then declines
SOA_2006_SURRENDER_BY_DURATION_7YR_SC: Final[dict[int, float]] = {
    1: 0.014,  # 1.4% - Year 1 (6 years SC remaining)
    2: 0.023,  # 2.3% - Year 2 (5 years SC remaining)
    3: 0.028,  # 2.8% - Year 3 (4 years SC remaining)
    4: 0.032,  # 3.2% - Year 4 (3 years SC remaining)
    5: 0.037,  # 3.7% - Year 5 (2 years SC remaining)
    6: 0.043,  # 4.3% - Year 6 (1 year SC remaining)
    7: 0.053,  # 5.3% - Year 7 (SC expires end of year)
    8: 0.112,  # 11.2% - Year 8 (first post-SC year) **CLIFF**
    9: 0.082,  # 8.2% - Year 9 (second post-SC year)
    10: 0.077,  # 7.7% - Year 10
    11: 0.067,  # 6.7% - Year 11+ (steady state)
}

# Table 5: Surrender Rates by Position in Surrender Charge Period
# Used to calculate SC cliff multiplier for different SC lengths
SOA_2006_SC_CLIFF_EFFECT: Final[dict[str, float]] = {
    "years_remaining_3plus": 0.026,  # 2.6% - 3+ years remaining
    "years_remaining_2": 0.049,  # 4.9% - 2 years remaining
    "years_remaining_1": 0.058,  # 5.8% - 1 year remaining
    "at_expiration": 0.144,  # 14.4% - SC just expired **CLIFF**
    "post_sc_year_1": 0.111,  # 11.1% - 1 year after SC
    "post_sc_year_2": 0.098,  # 9.8% - 2 years after SC
    "post_sc_year_3plus": 0.086,  # 8.6% - 3+ years after SC
}

# Calculated: SC cliff multiplier = 14.4% / 5.8% = 2.48x
SOA_2006_SC_CLIFF_MULTIPLIER: Final[float] = 0.144 / 0.058  # ~2.48

# Table 8: Full Surrender Rates by Owner Age
# Key insight: Full surrender is relatively flat by age (~5%)
SOA_2006_FULL_SURRENDER_BY_AGE: Final[dict[int, float]] = {
    35: 0.053,  # Under 40
    45: 0.052,  # 40-49
    52: 0.052,  # 50-54
    57: 0.052,  # 55-59
    62: 0.060,  # 60-64
    67: 0.058,  # 65-69
    72: 0.054,  # 70-74
    80: 0.049,  # 75-84
    87: 0.052,  # 85+
}

# Table 8: Partial Withdrawal Rates by Owner Age
# Key insight: Partial withdrawals increase dramatically with age (RMDs)
SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE: Final[dict[int, float]] = {
    35: 0.037,  # 3.7% - Under 40
    45: 0.039,  # 3.9% - 40-49
    52: 0.053,  # 5.3% - 50-54
    57: 0.072,  # 7.2% - 55-59
    62: 0.130,  # 13.0% - 60-64 (early retirement)
    67: 0.173,  # 17.3% - 65-69
    72: 0.315,  # 31.5% - 70-74 (RMD age) **PEAK**
    80: 0.285,  # 28.5% - 75-84
    87: 0.202,  # 20.2% - 85+ (declining due to mortality)
}


# =============================================================================
# SOA 2018 VA GLB Utilization Study
# =============================================================================

# Table 1-17: GLWB Utilization by Duration (years since issue)
# Key insight: Utilization ramps from 11% (year 1) to 54% (year 10)
SOA_2018_GLWB_UTILIZATION_BY_DURATION: Final[dict[int, float]] = {
    1: 0.111,  # 11.1% - First year
    2: 0.177,  # 17.7%
    3: 0.199,  # 19.9%
    4: 0.205,  # 20.5%
    5: 0.215,  # 21.5%
    6: 0.233,  # 23.3%
    7: 0.256,  # 25.6%
    8: 0.365,  # 36.5% - Spike (reaching typical retirement age)
    9: 0.459,  # 45.9%
    10: 0.518,  # 51.8%
    11: 0.536,  # 53.6% - Steady state
}

# Table 1-18: GLWB Utilization by Age (2008 cohort data)
# Uses 2008 cohort as most mature data point
SOA_2018_GLWB_UTILIZATION_BY_AGE: Final[dict[int, float]] = {
    55: 0.05,  # 5% - Under 60
    62: 0.16,  # 16% - 60-64
    67: 0.32,  # 32% - 65-69
    72: 0.59,  # 59% - 70-74 (RMD age)
    77: 0.65,  # 65% - 75-79 (near peak)
    82: 0.63,  # 63% - 80+ (slight decline)
}

# Figure 1-44: ITM Sensitivity Factors by Degree of Moneyness
# Multipliers relative to not-ITM baseline (age 70-74 reference)
# BB/CV > 100% means benefit base exceeds contract value (ITM guarantee)
SOA_2018_ITM_SENSITIVITY: Final[dict[str, float]] = {
    "not_itm": 1.00,  # Baseline: BB/CV <= 100%
    "itm_100_125": 1.39,  # 100-125% ITM: 53% / 38%
    "itm_125_150": 1.79,  # 125-150% ITM: 68% / 38%
    "itm_150_plus": 2.11,  # >150% ITM: 80% / 38% (deep ITM)
}

# Figure 1-43: ITM vs Not-ITM Withdrawal Rates by Age
# Shows that age explains most of the ITM effect
SOA_2018_ITM_VS_NOT_ITM_BY_AGE: Final[dict[int, dict[str, float]]] = {
    52: {"itm": 0.04, "not_itm": 0.03},  # Under 55
    57: {"itm": 0.03, "not_itm": 0.05},  # 55-59 (anomaly: ITM < not-ITM)
    62: {"itm": 0.12, "not_itm": 0.09},  # 60-64
    67: {"itm": 0.29, "not_itm": 0.18},  # 65-69
    72: {"itm": 0.56, "not_itm": 0.38},  # 70-74
    77: {"itm": 0.61, "not_itm": 0.44},  # 75-79
    82: {"itm": 0.62, "not_itm": 0.45},  # 80+
}


# =============================================================================
# Derived Constants and Multipliers
# =============================================================================

# Post-SC decay factors (relative to cliff year)
# Year 0 (cliff) = 100%, Year 1 = 77%, Year 2 = 68%, Year 3+ = 60%
SOA_2006_POST_SC_DECAY: Final[dict[int, float]] = {
    0: 1.00,  # At SC expiration: 14.4%
    1: 0.77,  # Year 1 after: 11.1% / 14.4% = 0.77
    2: 0.68,  # Year 2 after: 9.8% / 14.4% = 0.68
    3: 0.60,  # Year 3+ after: 8.6% / 14.4% = 0.60
}

# Key insights documented for reference
SOA_KEY_INSIGHTS: Final[dict[str, str]] = {
    "sc_cliff": "Surrender rate jumps 2.5x at SC expiration (5.8% -> 14.4%)",
    "age_paradox": "Full surrender flat by age (~5%), partial withdrawal increases 3.7% -> 31.5%",
    "duration_effect": "GLWB utilization ramps from 11% (year 1) to 54% (year 10)",
    "itm_weak": "Overall ITM effect is +11pp (30% vs 19%), but age explains most variance",
    "deep_itm": "Deep ITM (>150%) shows meaningful sensitivity increase (2.11x)",
}


# =============================================================================
# Data Quality Notes
# =============================================================================

DATA_QUALITY_NOTES: Final[dict[str, str]] = {
    "soa_2006": "Deferred annuity data, may differ from VA behavior",
    "soa_2018": "VA GLWB data, most relevant for GLWB products",
    "age_midpoints": "Age keys represent midpoints of age bands",
    "interpolation": "Linear interpolation recommended for intermediate values",
    "calibration_date": "Data extracted 2025-12-08 from free SOA PDFs",
}
