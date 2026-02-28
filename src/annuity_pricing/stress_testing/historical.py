"""
Historical Crisis Definitions for Stress Testing - Phase I.

[T2] Contains calibrated data for 7 major market crises (2000-2022).
All parameters sourced from FRED (DGS10), Yahoo Finance (S&P500), CBOE (VIX).

Each crisis includes:
- Summary statistics (peak-to-trough equity, VIX peak, rate change)
- Monthly profiles for path-dependent simulation
- Recovery type classification (V, U, L-shaped)

Data Sources:
- Equity: S&P 500 total return (Yahoo Finance ^GSPC)
- Rates: 10-Year Treasury (FRED DGS10)
- VIX: CBOE Volatility Index (Yahoo Finance ^VIX)

See: docs/stress_testing/HISTORICAL_SCENARIOS.md
"""

from dataclasses import dataclass
from enum import Enum


class RecoveryType(Enum):
    """Recovery shape classification."""

    V_SHAPED = "v"  # Quick bounce-back (< 6 months)
    U_SHAPED = "u"  # Extended bottom (6-18 months)
    L_SHAPED = "l"  # Prolonged depression (> 18 months)


@dataclass(frozen=True)
class CrisisProfile:
    """
    Monthly evolution during a crisis.

    Represents market state at a specific month offset from crisis start.

    Attributes
    ----------
    month : float
        Month offset from crisis start (0 = start, negative = pre-crisis).
        Fractional months allowed for intra-month events (e.g., 0.5 = mid-month).
    equity_cumulative : float
        Cumulative equity return from start (decimal, e.g., -0.30 = -30%)
    rate_level : float
        10-Year Treasury rate at this point (decimal, e.g., 0.035 = 3.5%)
    vix_level : float
        VIX index level at this point
    """

    month: float
    equity_cumulative: float
    rate_level: float
    vix_level: float


@dataclass(frozen=True)
class HistoricalCrisis:
    """
    Complete historical crisis definition.

    [T2] All parameters empirically calibrated from market data.

    Attributes
    ----------
    name : str
        Crisis identifier (e.g., "2008_gfc")
    display_name : str
        Human-readable name (e.g., "2008 Global Financial Crisis")
    start_date : str
        Crisis start date (YYYY-MM format)
    end_date : str
        Crisis trough date (YYYY-MM format)
    equity_shock : float
        Peak-to-trough equity decline (decimal, negative)
    rate_shock : float
        Change in 10Y rate (decimal, e.g., -0.0254 = -254 bps)
    vix_peak : float
        Maximum VIX level during crisis
    duration_months : int
        Months from start to trough
    recovery_months : int
        Months from trough to pre-crisis level recovery
    recovery_type : RecoveryType
        V, U, or L-shaped recovery pattern
    profile : Tuple[CrisisProfile, ...]
        Monthly evolution data (immutable tuple)
    notes : str
        Additional context about the crisis
    """

    name: str
    display_name: str
    start_date: str
    end_date: str
    equity_shock: float
    rate_shock: float
    vix_peak: float
    duration_months: int
    recovery_months: int
    recovery_type: RecoveryType
    profile: tuple[CrisisProfile, ...]
    notes: str


# =============================================================================
# 2008 Global Financial Crisis
# =============================================================================
# Peak: Oct 2007, Trough: Mar 2009
# S&P 500: 1565 -> 677 (-56.8%)
# 10Y: 4.68% -> 2.14% (-254 bps)
# VIX Peak: 80.9 (Nov 2008)

_PROFILE_2008_GFC = (
    # Pre-crisis baseline
    CrisisProfile(month=-3, equity_cumulative=0.05, rate_level=0.0468, vix_level=16.0),
    CrisisProfile(month=-2, equity_cumulative=0.03, rate_level=0.0455, vix_level=17.5),
    CrisisProfile(month=-1, equity_cumulative=0.01, rate_level=0.0445, vix_level=19.0),
    # Crisis onset (Oct 2007)
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0468, vix_level=18.5),
    # 2007 Q4 - Bear Stearns hedge funds fail
    CrisisProfile(month=1, equity_cumulative=-0.04, rate_level=0.0440, vix_level=22.0),
    CrisisProfile(month=2, equity_cumulative=-0.06, rate_level=0.0410, vix_level=24.0),
    CrisisProfile(month=3, equity_cumulative=-0.10, rate_level=0.0390, vix_level=25.0),
    # 2008 Q1 - Bear Stearns collapse
    CrisisProfile(month=4, equity_cumulative=-0.12, rate_level=0.0365, vix_level=28.0),
    CrisisProfile(month=5, equity_cumulative=-0.14, rate_level=0.0350, vix_level=26.0),
    CrisisProfile(month=6, equity_cumulative=-0.13, rate_level=0.0380, vix_level=23.0),
    # 2008 Q2 - Relative calm
    CrisisProfile(month=7, equity_cumulative=-0.14, rate_level=0.0395, vix_level=22.5),
    CrisisProfile(month=8, equity_cumulative=-0.18, rate_level=0.0410, vix_level=23.5),
    CrisisProfile(month=9, equity_cumulative=-0.22, rate_level=0.0390, vix_level=25.0),
    # 2008 Q3 - Lehman collapse (Sep 15)
    CrisisProfile(month=10, equity_cumulative=-0.25, rate_level=0.0370, vix_level=32.0),
    CrisisProfile(month=11, equity_cumulative=-0.30, rate_level=0.0340, vix_level=46.0),
    CrisisProfile(month=12, equity_cumulative=-0.40, rate_level=0.0280, vix_level=80.9),  # VIX peak
    # 2008 Q4 - TARP, Fed intervention
    CrisisProfile(month=13, equity_cumulative=-0.45, rate_level=0.0250, vix_level=56.0),
    CrisisProfile(month=14, equity_cumulative=-0.42, rate_level=0.0220, vix_level=45.0),
    CrisisProfile(month=15, equity_cumulative=-0.38, rate_level=0.0210, vix_level=40.0),
    # 2009 Q1 - Final capitulation
    CrisisProfile(month=16, equity_cumulative=-0.50, rate_level=0.0275, vix_level=48.0),
    CrisisProfile(month=17, equity_cumulative=-0.568, rate_level=0.0214, vix_level=52.0),  # Trough
    # Recovery begins (Mar 2009)
    CrisisProfile(month=18, equity_cumulative=-0.50, rate_level=0.0260, vix_level=42.0),
    CrisisProfile(month=19, equity_cumulative=-0.42, rate_level=0.0310, vix_level=35.0),
    CrisisProfile(month=20, equity_cumulative=-0.35, rate_level=0.0340, vix_level=30.0),
    CrisisProfile(month=21, equity_cumulative=-0.30, rate_level=0.0360, vix_level=27.0),
    # Recovery continues through 2009
    CrisisProfile(month=24, equity_cumulative=-0.20, rate_level=0.0380, vix_level=24.0),
    CrisisProfile(month=30, equity_cumulative=-0.10, rate_level=0.0370, vix_level=22.0),
    CrisisProfile(month=36, equity_cumulative=0.00, rate_level=0.0350, vix_level=20.0),
    # Full recovery (Oct 2011 to surpass Oct 2007)
    CrisisProfile(month=48, equity_cumulative=0.10, rate_level=0.0200, vix_level=18.0),
    CrisisProfile(month=54, equity_cumulative=0.20, rate_level=0.0180, vix_level=16.0),
)

CRISIS_2008_GFC = HistoricalCrisis(
    name="2008_gfc",
    display_name="2008 Global Financial Crisis",
    start_date="2007-10",
    end_date="2009-03",
    equity_shock=-0.568,
    rate_shock=-0.0254,  # 4.68% -> 2.14%
    vix_peak=80.9,
    duration_months=17,
    recovery_months=54,
    recovery_type=RecoveryType.U_SHAPED,
    profile=_PROFILE_2008_GFC,
    notes="Lehman collapse, credit freeze. Fed cut rates to zero. TARP $700B.",
)


# =============================================================================
# 2020 COVID-19 Crash
# =============================================================================
# Peak: Feb 19, 2020, Trough: Mar 23, 2020
# S&P 500: 3386 -> 2237 (-31.3%)
# 10Y: 1.59% -> 0.21% (-138 bps, all-time low)
# VIX Peak: 82.69 (Mar 16, 2020)

_PROFILE_2020_COVID = (
    # Pre-crisis (Jan-Feb 2020)
    CrisisProfile(month=-2, equity_cumulative=0.03, rate_level=0.0175, vix_level=13.0),
    CrisisProfile(month=-1, equity_cumulative=0.04, rate_level=0.0159, vix_level=14.0),
    # Feb 2020 - Peak reached Feb 19
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0159, vix_level=15.0),
    # Mar 2020 - Fastest 30% drop in history
    CrisisProfile(month=0.5, equity_cumulative=-0.15, rate_level=0.0100, vix_level=55.0),
    CrisisProfile(
        month=1, equity_cumulative=-0.313, rate_level=0.0021, vix_level=82.69
    ),  # VIX peak
    CrisisProfile(month=1.2, equity_cumulative=-0.25, rate_level=0.0060, vix_level=65.0),
    # Apr 2020 - Stimulus response, rapid recovery
    CrisisProfile(month=2, equity_cumulative=-0.15, rate_level=0.0065, vix_level=40.0),
    CrisisProfile(month=3, equity_cumulative=-0.08, rate_level=0.0068, vix_level=30.0),
    CrisisProfile(month=4, equity_cumulative=-0.05, rate_level=0.0072, vix_level=27.0),
    # Recovery (V-shaped)
    CrisisProfile(month=5, equity_cumulative=0.00, rate_level=0.0090, vix_level=25.0),
    CrisisProfile(month=6, equity_cumulative=0.05, rate_level=0.0095, vix_level=24.0),
    CrisisProfile(month=7, equity_cumulative=0.10, rate_level=0.0110, vix_level=22.0),
    CrisisProfile(month=8, equity_cumulative=0.15, rate_level=0.0120, vix_level=20.0),
    # New highs (Aug 2020)
    CrisisProfile(month=9, equity_cumulative=0.20, rate_level=0.0130, vix_level=19.0),
)

CRISIS_2020_COVID = HistoricalCrisis(
    name="2020_covid",
    display_name="2020 COVID-19 Crash",
    start_date="2020-02",
    end_date="2020-03",
    equity_shock=-0.313,
    rate_shock=-0.0138,  # 1.59% -> 0.21%
    vix_peak=82.69,
    duration_months=1,  # Fastest bear market in history
    recovery_months=5,
    recovery_type=RecoveryType.V_SHAPED,
    profile=_PROFILE_2020_COVID,
    notes="Fastest bear market entry. Fed unlimited QE, $2.2T CARES Act. V-shaped recovery.",
)


# =============================================================================
# 2000 Dot-Com Crash
# =============================================================================
# Peak: Mar 2000, Trough: Oct 2002
# S&P 500: 1527 -> 777 (-49.2%)
# 10Y: 6.44% -> 4.23% (-221 bps)
# VIX Peak: ~45 (Aug 2002)

_PROFILE_2000_DOTCOM = (
    # Pre-crash euphoria (late 1999)
    CrisisProfile(month=-3, equity_cumulative=0.15, rate_level=0.0620, vix_level=22.0),
    CrisisProfile(month=-2, equity_cumulative=0.12, rate_level=0.0640, vix_level=21.0),
    CrisisProfile(month=-1, equity_cumulative=0.08, rate_level=0.0650, vix_level=23.0),
    # Mar 2000 - NASDAQ peak
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0644, vix_level=24.0),
    # 2000 - Tech bubble deflating
    CrisisProfile(month=3, equity_cumulative=-0.05, rate_level=0.0620, vix_level=25.0),
    CrisisProfile(month=6, equity_cumulative=-0.10, rate_level=0.0600, vix_level=26.0),
    CrisisProfile(month=9, equity_cumulative=-0.15, rate_level=0.0560, vix_level=28.0),
    CrisisProfile(month=12, equity_cumulative=-0.20, rate_level=0.0520, vix_level=30.0),
    # 2001 - Recession, 9/11
    CrisisProfile(month=15, equity_cumulative=-0.25, rate_level=0.0490, vix_level=32.0),
    CrisisProfile(month=18, equity_cumulative=-0.30, rate_level=0.0450, vix_level=35.0),  # 9/11
    CrisisProfile(month=21, equity_cumulative=-0.28, rate_level=0.0500, vix_level=28.0),
    CrisisProfile(month=24, equity_cumulative=-0.32, rate_level=0.0510, vix_level=26.0),
    # 2002 - Corporate scandals (Enron, WorldCom)
    CrisisProfile(month=27, equity_cumulative=-0.38, rate_level=0.0480, vix_level=35.0),
    CrisisProfile(month=30, equity_cumulative=-0.45, rate_level=0.0440, vix_level=45.0),  # VIX peak
    CrisisProfile(month=31, equity_cumulative=-0.492, rate_level=0.0423, vix_level=42.0),  # Trough
    # Slow recovery begins
    CrisisProfile(month=36, equity_cumulative=-0.40, rate_level=0.0400, vix_level=30.0),
    CrisisProfile(month=42, equity_cumulative=-0.30, rate_level=0.0420, vix_level=25.0),
    CrisisProfile(month=48, equity_cumulative=-0.20, rate_level=0.0440, vix_level=20.0),
    CrisisProfile(month=60, equity_cumulative=-0.10, rate_level=0.0460, vix_level=18.0),
    CrisisProfile(month=72, equity_cumulative=0.00, rate_level=0.0480, vix_level=15.0),
    CrisisProfile(month=84, equity_cumulative=0.10, rate_level=0.0500, vix_level=14.0),
    CrisisProfile(month=90, equity_cumulative=0.15, rate_level=0.0480, vix_level=13.0),
)

CRISIS_2000_DOTCOM = HistoricalCrisis(
    name="2000_dotcom",
    display_name="2000 Dot-Com Crash",
    start_date="2000-03",
    end_date="2002-10",
    equity_shock=-0.492,
    rate_shock=-0.0221,  # 6.44% -> 4.23%
    vix_peak=45.0,
    duration_months=31,
    recovery_months=90,  # Didn't surpass 2000 peak until Oct 2007
    recovery_type=RecoveryType.L_SHAPED,
    profile=_PROFILE_2000_DOTCOM,
    notes="Tech bubble collapse. Enron/WorldCom scandals. 9/11 shock. Fed cut to 1%.",
)


# =============================================================================
# 2011 European Debt Crisis
# =============================================================================
# Local peak: May 2011, Trough: Oct 2011
# S&P 500: 1363 -> 1166 (-14.5%)
# 10Y: 3.31% -> 1.56% (-175 bps)
# VIX Peak: 48 (Aug 2011)

_PROFILE_2011_EURO_DEBT = (
    # Pre-crisis (Q1 2011)
    CrisisProfile(month=-2, equity_cumulative=0.03, rate_level=0.0350, vix_level=17.0),
    CrisisProfile(month=-1, equity_cumulative=0.02, rate_level=0.0340, vix_level=18.0),
    # May 2011 - Peak
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0331, vix_level=17.5),
    # Jun-Jul 2011 - Greece concerns
    CrisisProfile(month=1, equity_cumulative=-0.02, rate_level=0.0300, vix_level=20.0),
    CrisisProfile(month=2, equity_cumulative=-0.05, rate_level=0.0280, vix_level=23.0),
    # Aug 2011 - US debt downgrade, EU contagion
    CrisisProfile(month=3, equity_cumulative=-0.12, rate_level=0.0220, vix_level=48.0),  # VIX peak
    # Sep-Oct 2011 - Trough
    CrisisProfile(month=4, equity_cumulative=-0.10, rate_level=0.0180, vix_level=38.0),
    CrisisProfile(month=5, equity_cumulative=-0.145, rate_level=0.0156, vix_level=35.0),  # Trough
    # Recovery (V-shaped)
    CrisisProfile(month=6, equity_cumulative=-0.08, rate_level=0.0200, vix_level=28.0),
    CrisisProfile(month=7, equity_cumulative=-0.02, rate_level=0.0210, vix_level=24.0),
    CrisisProfile(month=8, equity_cumulative=0.02, rate_level=0.0190, vix_level=22.0),
    CrisisProfile(month=9, equity_cumulative=0.05, rate_level=0.0200, vix_level=20.0),
    CrisisProfile(month=10, equity_cumulative=0.08, rate_level=0.0210, vix_level=18.0),
)

CRISIS_2011_EURO_DEBT = HistoricalCrisis(
    name="2011_euro_debt",
    display_name="2011 European Debt Crisis",
    start_date="2011-05",
    end_date="2011-10",
    equity_shock=-0.145,
    rate_shock=-0.0175,  # 3.31% -> 1.56%
    vix_peak=48.0,
    duration_months=5,
    recovery_months=6,
    recovery_type=RecoveryType.V_SHAPED,
    profile=_PROFILE_2011_EURO_DEBT,
    notes="Greek default fears, US debt downgrade by S&P. ECB intervention.",
)


# =============================================================================
# 2015 China/Oil Crisis
# =============================================================================
# Peak: Jun 2015, Trough: Feb 2016
# S&P 500: 2130 -> 1868 (-12.3%)
# 10Y: 2.43% -> 1.81% (-62 bps)
# VIX Peak: 28 (Aug 2015)

_PROFILE_2015_CHINA = (
    # Pre-crisis
    CrisisProfile(month=-2, equity_cumulative=0.02, rate_level=0.0250, vix_level=13.0),
    CrisisProfile(month=-1, equity_cumulative=0.01, rate_level=0.0245, vix_level=14.0),
    # Jun 2015 - Peak
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0243, vix_level=14.0),
    # Jul-Aug 2015 - China devaluation
    CrisisProfile(month=1, equity_cumulative=-0.02, rate_level=0.0235, vix_level=15.0),
    CrisisProfile(month=2, equity_cumulative=-0.08, rate_level=0.0210, vix_level=28.0),  # VIX peak
    # Sep-Nov 2015 - Stabilization
    CrisisProfile(month=3, equity_cumulative=-0.06, rate_level=0.0220, vix_level=22.0),
    CrisisProfile(month=4, equity_cumulative=-0.03, rate_level=0.0230, vix_level=18.0),
    CrisisProfile(month=5, equity_cumulative=-0.01, rate_level=0.0225, vix_level=16.0),
    # Dec 2015 - Jan 2016 - Oil crash
    CrisisProfile(month=6, equity_cumulative=-0.05, rate_level=0.0230, vix_level=20.0),
    CrisisProfile(month=7, equity_cumulative=-0.10, rate_level=0.0200, vix_level=25.0),
    CrisisProfile(month=8, equity_cumulative=-0.123, rate_level=0.0181, vix_level=26.0),  # Trough
    # Recovery (U-shaped)
    CrisisProfile(month=9, equity_cumulative=-0.08, rate_level=0.0190, vix_level=22.0),
    CrisisProfile(month=10, equity_cumulative=-0.05, rate_level=0.0180, vix_level=18.0),
    CrisisProfile(month=11, equity_cumulative=-0.02, rate_level=0.0175, vix_level=16.0),
    CrisisProfile(month=12, equity_cumulative=0.00, rate_level=0.0180, vix_level=15.0),
)

CRISIS_2015_CHINA = HistoricalCrisis(
    name="2015_china",
    display_name="2015-16 China/Oil Crisis",
    start_date="2015-06",
    end_date="2016-02",
    equity_shock=-0.123,
    rate_shock=-0.0062,  # 2.43% -> 1.81%
    vix_peak=28.0,
    duration_months=8,
    recovery_months=12,
    recovery_type=RecoveryType.U_SHAPED,
    profile=_PROFILE_2015_CHINA,
    notes="China yuan devaluation, oil crash to $26/bbl. First Fed hike in 9 years.",
)


# =============================================================================
# 2018 Q4 Correction
# =============================================================================
# Peak: Sep 2018, Trough: Dec 2018
# S&P 500: 2930 -> 2366 (-19.3%)
# 10Y: 3.23% -> 2.86% (-37 bps)
# VIX Peak: 36 (Dec 2018)

_PROFILE_2018_Q4 = (
    # Pre-crisis
    CrisisProfile(month=-2, equity_cumulative=0.03, rate_level=0.0290, vix_level=12.0),
    CrisisProfile(month=-1, equity_cumulative=0.02, rate_level=0.0310, vix_level=13.0),
    # Sep 2018 - Peak
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0323, vix_level=12.5),
    # Oct 2018 - Trade war escalation
    CrisisProfile(month=1, equity_cumulative=-0.07, rate_level=0.0315, vix_level=25.0),
    # Nov 2018 - Continued decline
    CrisisProfile(month=2, equity_cumulative=-0.08, rate_level=0.0305, vix_level=22.0),
    # Dec 2018 - Fed hike, capitulation
    CrisisProfile(month=3, equity_cumulative=-0.15, rate_level=0.0290, vix_level=30.0),
    CrisisProfile(
        month=3.5, equity_cumulative=-0.193, rate_level=0.0286, vix_level=36.0
    ),  # Trough, VIX peak
    # Recovery (V-shaped)
    CrisisProfile(month=4, equity_cumulative=-0.10, rate_level=0.0270, vix_level=20.0),
    CrisisProfile(month=5, equity_cumulative=-0.05, rate_level=0.0265, vix_level=17.0),
    CrisisProfile(month=6, equity_cumulative=-0.02, rate_level=0.0260, vix_level=15.0),
    CrisisProfile(month=7, equity_cumulative=0.00, rate_level=0.0250, vix_level=14.0),
    CrisisProfile(month=8, equity_cumulative=0.05, rate_level=0.0245, vix_level=13.0),
)

CRISIS_2018_Q4 = HistoricalCrisis(
    name="2018_q4",
    display_name="2018 Q4 Correction",
    start_date="2018-09",
    end_date="2018-12",
    equity_shock=-0.193,
    rate_shock=-0.0037,  # 3.23% -> 2.86%
    vix_peak=36.0,
    duration_months=3,
    recovery_months=4,
    recovery_type=RecoveryType.V_SHAPED,
    profile=_PROFILE_2018_Q4,
    notes="Trade war fears, Fed tightening. Powell 'pivot' in Jan 2019.",
)


# =============================================================================
# 2022 Rate Shock
# =============================================================================
# Peak: Dec 2021, Trough: Oct 2022
# S&P 500: 4766 -> 3578 (-24.9%)
# 10Y: 1.51% -> 4.33% (+282 bps - RISING rates)
# VIX Peak: 36.5 (Mar 2022)

_PROFILE_2022_RATES = (
    # Pre-crisis
    CrisisProfile(month=-2, equity_cumulative=0.03, rate_level=0.0160, vix_level=17.0),
    CrisisProfile(month=-1, equity_cumulative=0.02, rate_level=0.0150, vix_level=18.0),
    # Dec 2021 - Peak
    CrisisProfile(month=0, equity_cumulative=0.00, rate_level=0.0151, vix_level=18.0),
    # Jan-Feb 2022 - Inflation fears
    CrisisProfile(month=1, equity_cumulative=-0.05, rate_level=0.0180, vix_level=22.0),
    CrisisProfile(month=2, equity_cumulative=-0.08, rate_level=0.0195, vix_level=28.0),
    # Mar 2022 - Ukraine invasion, Fed starts hiking
    CrisisProfile(month=3, equity_cumulative=-0.10, rate_level=0.0230, vix_level=36.5),  # VIX peak
    CrisisProfile(month=4, equity_cumulative=-0.12, rate_level=0.0280, vix_level=30.0),
    # Q2 2022 - Aggressive rate hikes
    CrisisProfile(month=5, equity_cumulative=-0.15, rate_level=0.0300, vix_level=28.0),
    CrisisProfile(month=6, equity_cumulative=-0.20, rate_level=0.0325, vix_level=32.0),
    CrisisProfile(month=7, equity_cumulative=-0.18, rate_level=0.0290, vix_level=25.0),
    # Q3 2022 - Bear market rally, then continuation
    CrisisProfile(month=8, equity_cumulative=-0.14, rate_level=0.0305, vix_level=23.0),
    CrisisProfile(month=9, equity_cumulative=-0.20, rate_level=0.0380, vix_level=30.0),
    CrisisProfile(month=10, equity_cumulative=-0.249, rate_level=0.0433, vix_level=32.0),  # Trough
    # Recovery (U-shaped)
    CrisisProfile(month=11, equity_cumulative=-0.20, rate_level=0.0420, vix_level=26.0),
    CrisisProfile(month=12, equity_cumulative=-0.15, rate_level=0.0390, vix_level=22.0),
    CrisisProfile(month=13, equity_cumulative=-0.12, rate_level=0.0380, vix_level=20.0),
    CrisisProfile(month=14, equity_cumulative=-0.08, rate_level=0.0400, vix_level=18.0),
)

CRISIS_2022_RATES = HistoricalCrisis(
    name="2022_rates",
    display_name="2022 Rate Shock",
    start_date="2021-12",
    end_date="2022-10",
    equity_shock=-0.249,
    rate_shock=0.0282,  # +282 bps (RISING rates, unique crisis)
    vix_peak=36.5,
    duration_months=10,
    recovery_months=14,
    recovery_type=RecoveryType.U_SHAPED,
    profile=_PROFILE_2022_RATES,
    notes="Inflation surge, Fed fastest hikes since 1980s. Bond rout. Unique: rising rates.",
)


# =============================================================================
# Collection and Utilities
# =============================================================================

ALL_HISTORICAL_CRISES: tuple[HistoricalCrisis, ...] = (
    CRISIS_2008_GFC,
    CRISIS_2020_COVID,
    CRISIS_2000_DOTCOM,
    CRISIS_2011_EURO_DEBT,
    CRISIS_2015_CHINA,
    CRISIS_2018_Q4,
    CRISIS_2022_RATES,
)

_CRISIS_BY_NAME: dict[str, HistoricalCrisis] = {c.name: c for c in ALL_HISTORICAL_CRISES}


def get_crisis_by_name(name: str) -> HistoricalCrisis:
    """
    Retrieve a crisis definition by name.

    Parameters
    ----------
    name : str
        Crisis identifier (e.g., "2008_gfc", "2020_covid")

    Returns
    -------
    HistoricalCrisis
        The crisis definition

    Raises
    ------
    ValueError
        If crisis name not found
    """
    if name not in _CRISIS_BY_NAME:
        valid_names = ", ".join(sorted(_CRISIS_BY_NAME.keys()))
        raise ValueError(f"Unknown crisis name: '{name}'. Valid names: {valid_names}")
    return _CRISIS_BY_NAME[name]


def get_crisis_summary() -> dict[str, dict[str, float]]:
    """
    Get summary statistics for all historical crises.

    Returns
    -------
    Dict[str, Dict[str, float]]
        Nested dict: crisis_name -> {equity_shock, rate_shock, vix_peak, duration_months}

    Examples
    --------
    >>> summary = get_crisis_summary()
    >>> summary["2008_gfc"]["equity_shock"]
    -0.568
    """
    return {
        c.name: {
            "equity_shock": c.equity_shock,
            "rate_shock": c.rate_shock,
            "vix_peak": c.vix_peak,
            "duration_months": c.duration_months,
            "recovery_months": c.recovery_months,
        }
        for c in ALL_HISTORICAL_CRISES
    }


def get_profile_at_month(crisis: HistoricalCrisis, month: float) -> CrisisProfile | None:
    """
    Get crisis profile at a specific month (exact match).

    Parameters
    ----------
    crisis : HistoricalCrisis
        The crisis to query
    month : float
        Month offset from crisis start

    Returns
    -------
    Optional[CrisisProfile]
        The profile if exact match found, None otherwise
    """
    for profile in crisis.profile:
        if profile.month == month:
            return profile
    return None


def interpolate_profile(crisis: HistoricalCrisis, month: float) -> CrisisProfile:
    """
    Interpolate crisis profile at any month.

    Uses linear interpolation between known data points.

    Parameters
    ----------
    crisis : HistoricalCrisis
        The crisis to query
    month : float
        Month offset from crisis start

    Returns
    -------
    CrisisProfile
        Interpolated profile

    Raises
    ------
    ValueError
        If month is outside profile range
    """
    profiles = sorted(crisis.profile, key=lambda p: p.month)

    if month < profiles[0].month:
        raise ValueError(f"Month {month} before earliest profile ({profiles[0].month})")
    if month > profiles[-1].month:
        raise ValueError(f"Month {month} after latest profile ({profiles[-1].month})")

    # Find bracketing profiles
    for i in range(len(profiles) - 1):
        if profiles[i].month <= month <= profiles[i + 1].month:
            p1, p2 = profiles[i], profiles[i + 1]
            # Linear interpolation weight
            if p2.month == p1.month:
                t = 0.0
            else:
                t = (month - p1.month) / (p2.month - p1.month)

            return CrisisProfile(
                month=month,
                equity_cumulative=p1.equity_cumulative
                + t * (p2.equity_cumulative - p1.equity_cumulative),
                rate_level=p1.rate_level + t * (p2.rate_level - p1.rate_level),
                vix_level=p1.vix_level + t * (p2.vix_level - p1.vix_level),
            )

    # Should never reach here if input is valid
    raise ValueError(f"Could not interpolate month {month}")
