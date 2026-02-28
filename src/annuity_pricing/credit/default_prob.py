"""
AM Best rating to probability of default mapping.

[T2] Based on AM Best Impairment Rate and Rating Transition Study (1977-2023).
Impairment rates are used as proxy for default probability.

Key findings from AM Best study:
- Higher ratings have lower impairment rates
- Impairment rates increase with rating observation period
- Average time to impairment: 17 years for A++/A+, 11.4 years for B/B-

References
----------
[T2] AM Best. "Best's Impairment Rate and Rating Transition Study – 1977 to 2023."
     https://web.ambest.com/
[T2] NAIC. "Not All Insurer Financial Strength Ratings Are Created Equal."
     https://content.naic.org/
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class AMBestRating(Enum):
    """
    AM Best Financial Strength Ratings (FSR).

    [T1] Secure ratings: A++, A+, A, A-, B++, B+
    [T1] Vulnerable ratings: B, B-, C++, C+, C, C-, D, E, F, S
    """

    # Secure ratings
    A_PLUS_PLUS = "A++"  # Superior
    A_PLUS = "A+"  # Superior
    A = "A"  # Excellent
    A_MINUS = "A-"  # Excellent
    B_PLUS_PLUS = "B++"  # Very Good
    B_PLUS = "B+"  # Very Good

    # Vulnerable ratings
    B = "B"  # Adequate
    B_MINUS = "B-"  # Adequate
    C_PLUS_PLUS = "C++"  # Marginal
    C_PLUS = "C+"  # Marginal
    C = "C"  # Weak
    C_MINUS = "C-"  # Weak
    D = "D"  # Poor
    E = "E"  # Under Regulatory Supervision
    F = "F"  # In Liquidation
    S = "S"  # Rating Suspended


@dataclass(frozen=True)
class RatingPD:
    """
    Probability of default data for an AM Best rating.

    Attributes
    ----------
    rating : AMBestRating
        The AM Best rating
    annual_pd : float
        1-year probability of default/impairment (decimal)
    pd_5yr : float
        5-year cumulative PD (decimal)
    pd_10yr : float
        10-year cumulative PD (decimal)
    pd_15yr : float
        15-year cumulative PD (decimal)
    """

    rating: AMBestRating
    annual_pd: float
    pd_5yr: float
    pd_10yr: float
    pd_15yr: float


# AM Best Impairment Rates by Rating (1977-2023 study)
# [T2] Values extracted from AM Best published data
# Note: These are impairment rates, which include regulatory intervention,
# not just missed payments (higher than pure default rates)
AM_BEST_IMPAIRMENT_RATES: dict[AMBestRating, RatingPD] = {
    # Superior (A++, A+): Very low impairment rates
    # [T2] 10-year cumulative ~2% for combined A++/A+
    AMBestRating.A_PLUS_PLUS: RatingPD(
        rating=AMBestRating.A_PLUS_PLUS,
        annual_pd=0.0001,  # 0.01%
        pd_5yr=0.005,  # 0.5%
        pd_10yr=0.015,  # 1.5%
        pd_15yr=0.025,  # 2.5%
    ),
    AMBestRating.A_PLUS: RatingPD(
        rating=AMBestRating.A_PLUS,
        annual_pd=0.0002,  # 0.02%
        pd_5yr=0.008,  # 0.8%
        pd_10yr=0.020,  # 2.0%
        pd_15yr=0.035,  # 3.5%
    ),
    # Excellent (A, A-): Low impairment rates
    # [T2] "a" rating: 0.02% 1-year, 0.22% 10-year
    # [T2] "A-" rating: 0.11% 1-year, 3.10% 15-year
    AMBestRating.A: RatingPD(
        rating=AMBestRating.A,
        annual_pd=0.0002,  # 0.02%
        pd_5yr=0.008,  # 0.8%
        pd_10yr=0.022,  # 2.2%
        pd_15yr=0.040,  # 4.0%
    ),
    AMBestRating.A_MINUS: RatingPD(
        rating=AMBestRating.A_MINUS,
        annual_pd=0.0011,  # 0.11%
        pd_5yr=0.015,  # 1.5%
        pd_10yr=0.050,  # 5.0% (NAIC/Fitch: 5-6% for A/A-)
        pd_15yr=0.031,  # 3.1%
    ),
    # Very Good (B++, B+): Moderate impairment rates
    AMBestRating.B_PLUS_PLUS: RatingPD(
        rating=AMBestRating.B_PLUS_PLUS,
        annual_pd=0.0020,  # 0.20%
        pd_5yr=0.025,  # 2.5%
        pd_10yr=0.070,  # 7.0%
        pd_15yr=0.100,  # 10.0%
    ),
    AMBestRating.B_PLUS: RatingPD(
        rating=AMBestRating.B_PLUS,
        annual_pd=0.0035,  # 0.35%
        pd_5yr=0.040,  # 4.0%
        pd_10yr=0.100,  # 10.0%
        pd_15yr=0.150,  # 15.0%
    ),
    # Adequate (B, B-): Higher impairment rates
    # [T2] B/B-: 1.35% 1-year
    AMBestRating.B: RatingPD(
        rating=AMBestRating.B,
        annual_pd=0.0100,  # 1.0%
        pd_5yr=0.080,  # 8.0%
        pd_10yr=0.180,  # 18.0%
        pd_15yr=0.280,  # 28.0%
    ),
    AMBestRating.B_MINUS: RatingPD(
        rating=AMBestRating.B_MINUS,
        annual_pd=0.0135,  # 1.35%
        pd_5yr=0.100,  # 10.0%
        pd_10yr=0.220,  # 22.0%
        pd_15yr=0.350,  # 35.0%
    ),
    # Marginal (C++, C+): High impairment rates
    AMBestRating.C_PLUS_PLUS: RatingPD(
        rating=AMBestRating.C_PLUS_PLUS,
        annual_pd=0.0200,  # 2.0%
        pd_5yr=0.150,  # 15.0%
        pd_10yr=0.300,  # 30.0%
        pd_15yr=0.450,  # 45.0%
    ),
    AMBestRating.C_PLUS: RatingPD(
        rating=AMBestRating.C_PLUS,
        annual_pd=0.0250,  # 2.5%
        pd_5yr=0.180,  # 18.0%
        pd_10yr=0.350,  # 35.0%
        pd_15yr=0.500,  # 50.0%
    ),
    # Weak (C, C-): Very high impairment rates
    # [T2] "b" rating (comparable to C): 3.29% 1-year
    AMBestRating.C: RatingPD(
        rating=AMBestRating.C,
        annual_pd=0.0329,  # 3.29%
        pd_5yr=0.220,  # 22.0%
        pd_10yr=0.400,  # 40.0%
        pd_15yr=0.550,  # 55.0%
    ),
    AMBestRating.C_MINUS: RatingPD(
        rating=AMBestRating.C_MINUS,
        annual_pd=0.0400,  # 4.0%
        pd_5yr=0.280,  # 28.0%
        pd_10yr=0.480,  # 48.0%
        pd_15yr=0.620,  # 62.0%
    ),
    # Poor and worse: Near-certain impairment
    AMBestRating.D: RatingPD(
        rating=AMBestRating.D,
        annual_pd=0.0800,  # 8.0%
        pd_5yr=0.400,  # 40.0%
        pd_10yr=0.650,  # 65.0%
        pd_15yr=0.800,  # 80.0%
    ),
    AMBestRating.E: RatingPD(
        rating=AMBestRating.E,
        annual_pd=0.2000,  # 20.0% (under regulatory supervision)
        pd_5yr=0.700,  # 70.0%
        pd_10yr=0.900,  # 90.0%
        pd_15yr=0.950,  # 95.0%
    ),
    AMBestRating.F: RatingPD(
        rating=AMBestRating.F,
        annual_pd=1.0000,  # 100% (already in liquidation)
        pd_5yr=1.000,
        pd_10yr=1.000,
        pd_15yr=1.000,
    ),
    AMBestRating.S: RatingPD(
        rating=AMBestRating.S,
        annual_pd=0.1000,  # 10% (suspended, high uncertainty)
        pd_5yr=0.500,
        pd_10yr=0.750,
        pd_15yr=0.850,
    ),
}


def rating_from_string(rating_str: str) -> AMBestRating:
    """
    Parse AM Best rating string to enum.

    Parameters
    ----------
    rating_str : str
        Rating string (e.g., "A++", "A+", "A", "A-", "B++", etc.)

    Returns
    -------
    AMBestRating
        Parsed rating enum

    Raises
    ------
    ValueError
        If rating string not recognized

    Examples
    --------
    >>> rating_from_string("A++")
    <AMBestRating.A_PLUS_PLUS: 'A++'>
    >>> rating_from_string("A-")
    <AMBestRating.A_MINUS: 'A-'>
    """
    rating_str = rating_str.strip().upper()

    # Handle variations
    rating_map = {
        "A++": AMBestRating.A_PLUS_PLUS,
        "A+": AMBestRating.A_PLUS,
        "A": AMBestRating.A,
        "A-": AMBestRating.A_MINUS,
        "B++": AMBestRating.B_PLUS_PLUS,
        "B+": AMBestRating.B_PLUS,
        "B": AMBestRating.B,
        "B-": AMBestRating.B_MINUS,
        "C++": AMBestRating.C_PLUS_PLUS,
        "C+": AMBestRating.C_PLUS,
        "C": AMBestRating.C,
        "C-": AMBestRating.C_MINUS,
        "D": AMBestRating.D,
        "E": AMBestRating.E,
        "F": AMBestRating.F,
        "S": AMBestRating.S,
    }

    if rating_str not in rating_map:
        raise ValueError(
            f"CRITICAL: Unknown AM Best rating '{rating_str}'. "
            f"Valid ratings: {list(rating_map.keys())}"
        )

    return rating_map[rating_str]


def get_annual_pd(rating: AMBestRating) -> float:
    """
    Get 1-year probability of default for AM Best rating.

    [T2] Based on AM Best impairment rate study (1977-2023).

    Parameters
    ----------
    rating : AMBestRating
        AM Best rating

    Returns
    -------
    float
        Annual PD (decimal, e.g., 0.001 = 0.1%)

    Examples
    --------
    >>> get_annual_pd(AMBestRating.A)
    0.0002
    >>> get_annual_pd(AMBestRating.B_MINUS)
    0.0135
    """
    return AM_BEST_IMPAIRMENT_RATES[rating].annual_pd


def get_cumulative_pd(
    rating: AMBestRating,
    years: int,
) -> float:
    """
    Get cumulative probability of default over given period.

    [T2] Interpolates between 1, 5, 10, 15-year values.
    For years > 15, uses simple extrapolation.

    Parameters
    ----------
    rating : AMBestRating
        AM Best rating
    years : int
        Number of years (1-30)

    Returns
    -------
    float
        Cumulative PD (decimal)

    Examples
    --------
    >>> get_cumulative_pd(AMBestRating.A, 10)
    0.022
    >>> get_cumulative_pd(AMBestRating.B_MINUS, 5)
    0.10
    """
    if years < 1:
        raise ValueError(f"CRITICAL: years must be >= 1. Got: {years}")

    pd_data = AM_BEST_IMPAIRMENT_RATES[rating]

    if years == 1:
        return pd_data.annual_pd
    elif years <= 5:
        # Interpolate between 1-year and 5-year
        t = (years - 1) / 4
        return pd_data.annual_pd + t * (pd_data.pd_5yr - pd_data.annual_pd)
    elif years <= 10:
        # Interpolate between 5-year and 10-year
        t = (years - 5) / 5
        return pd_data.pd_5yr + t * (pd_data.pd_10yr - pd_data.pd_5yr)
    elif years <= 15:
        # Interpolate between 10-year and 15-year
        t = (years - 10) / 5
        return pd_data.pd_10yr + t * (pd_data.pd_15yr - pd_data.pd_10yr)
    else:
        # Extrapolate beyond 15 years (cap at 100%)
        # Use decaying growth rate
        base_rate = pd_data.pd_15yr
        annual_increment = (pd_data.pd_15yr - pd_data.pd_10yr) / 5
        extra_years = years - 15
        extrapolated = base_rate + annual_increment * extra_years * 0.5
        return min(extrapolated, 1.0)


def get_pd_term_structure(
    rating: AMBestRating,
    max_years: int = 30,
) -> np.ndarray:
    """
    Get PD term structure for given rating.

    Parameters
    ----------
    rating : AMBestRating
        AM Best rating
    max_years : int
        Maximum years for term structure

    Returns
    -------
    np.ndarray
        Array of cumulative PDs from year 1 to max_years
    """
    return np.array([get_cumulative_pd(rating, year) for year in range(1, max_years + 1)])


def get_hazard_rate(rating: AMBestRating) -> float:
    """
    Get instantaneous hazard rate for rating.

    [T1] h = -ln(1 - PD_annual) ≈ PD_annual for small PD

    Parameters
    ----------
    rating : AMBestRating
        AM Best rating

    Returns
    -------
    float
        Hazard rate (continuous, per year)
    """
    annual_pd = get_annual_pd(rating)
    if annual_pd >= 1.0:
        return float("inf")
    return -np.log(1 - annual_pd)
