"""
Calibration Functions for SOA-Based Behavioral Models.

[T2] Interpolation and lookup functions using SOA benchmark data.

This module provides functions to:
1. Interpolate surrender rates by contract duration
2. Calculate surrender charge cliff effects
3. Interpolate GLWB utilization by duration and age
4. Calculate ITM sensitivity factors

See Also
--------
annuity_pricing.behavioral.soa_benchmarks : Source data tables
docs/assumptions/BEHAVIOR_CALIBRATION.md : Full methodology documentation
"""


from annuity_pricing.behavioral.soa_benchmarks import (
    SOA_2006_FULL_SURRENDER_BY_AGE,
    SOA_2006_POST_SC_DECAY,
    SOA_2006_SC_CLIFF_EFFECT,
    SOA_2006_SC_CLIFF_MULTIPLIER,
    SOA_2006_SURRENDER_BY_DURATION_7YR_SC,
    SOA_2018_GLWB_UTILIZATION_BY_AGE,
    SOA_2018_GLWB_UTILIZATION_BY_DURATION,
    SOA_2018_ITM_SENSITIVITY,
)

# =============================================================================
# Generic Interpolation Utilities
# =============================================================================


def _linear_interpolate(
    x: float,
    x_points: dict[int, float] | dict[float, float],  # type: ignore[type-arg]
    extrapolate: bool = True,
) -> float:
    """
    Linear interpolation/extrapolation from a dict of {x: y} points.

    Parameters
    ----------
    x : float
        The x value to interpolate at
    x_points : dict
        Dictionary mapping x values to y values (must be sorted by x)
    extrapolate : bool
        If True, extrapolate beyond data range using nearest values

    Returns
    -------
    float
        Interpolated y value
    """
    # Sort keys for proper interpolation
    keys = sorted(x_points.keys())
    values = [x_points[k] for k in keys]  # type: ignore[index]

    # Handle boundary cases
    if x <= keys[0]:
        return values[0] if extrapolate else values[0]
    if x >= keys[-1]:
        return values[-1] if extrapolate else values[-1]

    # Find bracketing points
    for i in range(len(keys) - 1):
        if keys[i] <= x <= keys[i + 1]:
            x0, x1 = keys[i], keys[i + 1]
            y0, y1 = values[i], values[i + 1]
            # Linear interpolation
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)

    # Fallback (should not reach)
    return values[-1]


# =============================================================================
# Surrender Rate Functions (SOA 2006)
# =============================================================================


def interpolate_surrender_by_duration(
    duration: int,
    sc_length: int = 7,
) -> float:
    """
    Interpolate surrender rate from SOA 2006 Table 6.

    [T2] Based on 7-year surrender charge schedule data.

    Parameters
    ----------
    duration : int
        Contract duration in years (1-indexed: year 1 = first year)
    sc_length : int
        Surrender charge period length (default 7 years)

    Returns
    -------
    float
        Annual surrender rate (decimal, e.g., 0.05 = 5%)

    Examples
    --------
    >>> interpolate_surrender_by_duration(1)  # Year 1
    0.014
    >>> interpolate_surrender_by_duration(8)  # Post-SC cliff
    0.112

    Notes
    -----
    For SC lengths other than 7, the function scales the duration
    to match the 7-year pattern and applies the cliff effect at
    the appropriate year.
    """
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")

    # Handle SC length scaling
    if sc_length == 7:
        # Direct lookup from SOA data
        if duration in SOA_2006_SURRENDER_BY_DURATION_7YR_SC:
            return SOA_2006_SURRENDER_BY_DURATION_7YR_SC[duration]
        # Extrapolate for durations > 11
        if duration > 11:
            return SOA_2006_SURRENDER_BY_DURATION_7YR_SC[11]
        # Interpolate
        return _linear_interpolate(duration, SOA_2006_SURRENDER_BY_DURATION_7YR_SC)

    # Scale for different SC lengths
    # Normalize duration to SC period position
    if duration <= sc_length:
        # During SC period: scale to 7-year equivalent
        scaled_duration = (duration / sc_length) * 7
        return _linear_interpolate(scaled_duration, SOA_2006_SURRENDER_BY_DURATION_7YR_SC)
    else:
        # Post-SC: years after SC expiration
        years_post_sc = duration - sc_length
        # Map to year 8+ in 7-year data
        equivalent_duration = 7 + years_post_sc
        return _linear_interpolate(
            min(equivalent_duration, 11),
            SOA_2006_SURRENDER_BY_DURATION_7YR_SC
        )


def get_sc_cliff_multiplier(
    years_to_sc_end: int,
) -> float:
    """
    Get surrender charge cliff multiplier from SOA 2006 Table 5.

    [T2] The cliff effect is the spike in surrenders when SC expires.

    Parameters
    ----------
    years_to_sc_end : int
        Years until surrender charge expires
        - Positive: years remaining in SC period
        - Zero: SC just expired (cliff year)
        - Negative: years after SC expired

    Returns
    -------
    float
        Multiplier relative to normal in-SC surrender rate

    Examples
    --------
    >>> get_sc_cliff_multiplier(3)   # 3+ years remaining
    1.0
    >>> get_sc_cliff_multiplier(0)   # SC just expired
    2.48...  # The cliff!
    >>> get_sc_cliff_multiplier(-1)  # 1 year after SC
    1.91...

    Notes
    -----
    Multipliers are calculated relative to the 3+ years remaining
    base rate (2.6%).
    """
    base_rate = SOA_2006_SC_CLIFF_EFFECT['years_remaining_3plus']

    if years_to_sc_end >= 3:
        return 1.0  # Base rate
    elif years_to_sc_end == 2:
        return SOA_2006_SC_CLIFF_EFFECT['years_remaining_2'] / base_rate
    elif years_to_sc_end == 1:
        return SOA_2006_SC_CLIFF_EFFECT['years_remaining_1'] / base_rate
    elif years_to_sc_end == 0:
        return SOA_2006_SC_CLIFF_MULTIPLIER  # 2.48x
    elif years_to_sc_end == -1:
        return SOA_2006_SC_CLIFF_EFFECT['post_sc_year_1'] / base_rate
    elif years_to_sc_end == -2:
        return SOA_2006_SC_CLIFF_EFFECT['post_sc_year_2'] / base_rate
    else:  # years_to_sc_end <= -3
        return SOA_2006_SC_CLIFF_EFFECT['post_sc_year_3plus'] / base_rate


def get_post_sc_decay_factor(
    years_after_sc: int,
) -> float:
    """
    Get post-SC decay factor relative to cliff year.

    [T2] After the SC cliff, surrender rates decay over 3 years.

    Parameters
    ----------
    years_after_sc : int
        Years after SC expiration (0 = cliff year)

    Returns
    -------
    float
        Decay factor relative to cliff year (1.0 at cliff)

    Examples
    --------
    >>> get_post_sc_decay_factor(0)  # Cliff year
    1.0
    >>> get_post_sc_decay_factor(1)  # Year after
    0.77
    >>> get_post_sc_decay_factor(5)  # 5 years after
    0.60
    """
    if years_after_sc <= 0:
        return SOA_2006_POST_SC_DECAY[0]
    elif years_after_sc == 1:
        return SOA_2006_POST_SC_DECAY[1]
    elif years_after_sc == 2:
        return SOA_2006_POST_SC_DECAY[2]
    else:
        return SOA_2006_POST_SC_DECAY[3]


def interpolate_surrender_by_age(
    age: int,
    surrender_type: str = 'full',
) -> float:
    """
    Interpolate surrender rate by owner age from SOA 2006 Table 8.

    [T2] Full surrender is flat by age; partial withdrawal increases.

    Parameters
    ----------
    age : int
        Owner age
    surrender_type : str
        Either 'full' or 'partial'

    Returns
    -------
    float
        Annual surrender/withdrawal rate (decimal)

    Examples
    --------
    >>> interpolate_surrender_by_age(65, 'full')
    0.058
    >>> interpolate_surrender_by_age(72, 'partial')
    0.315  # Peak at RMD age
    """
    from annuity_pricing.behavioral.soa_benchmarks import (
        SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE,
    )

    if surrender_type == 'full':
        return _linear_interpolate(age, SOA_2006_FULL_SURRENDER_BY_AGE)
    elif surrender_type == 'partial':
        return _linear_interpolate(age, SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE)
    else:
        raise ValueError(f"surrender_type must be 'full' or 'partial', got {surrender_type}")


# =============================================================================
# GLWB Utilization Functions (SOA 2018)
# =============================================================================


def interpolate_utilization_by_duration(
    duration: int,
) -> float:
    """
    Interpolate GLWB utilization from SOA 2018 Table 1-17.

    [T2] Utilization ramps from 11% (year 1) to 54% (year 10+).

    Parameters
    ----------
    duration : int
        Contract duration in years (1-indexed)

    Returns
    -------
    float
        Utilization rate (decimal, e.g., 0.50 = 50%)

    Examples
    --------
    >>> interpolate_utilization_by_duration(1)
    0.111
    >>> interpolate_utilization_by_duration(10)
    0.518
    """
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")

    if duration in SOA_2018_GLWB_UTILIZATION_BY_DURATION:
        return SOA_2018_GLWB_UTILIZATION_BY_DURATION[duration]

    # Extrapolate for durations > 11
    if duration > 11:
        return SOA_2018_GLWB_UTILIZATION_BY_DURATION[11]

    return _linear_interpolate(duration, SOA_2018_GLWB_UTILIZATION_BY_DURATION)


def interpolate_utilization_by_age(
    age: int,
) -> float:
    """
    Interpolate GLWB utilization from SOA 2018 Table 1-18.

    [T2] Utilization increases with age: 5% at 55 to 65% at 77.

    Parameters
    ----------
    age : int
        Current age of annuitant

    Returns
    -------
    float
        Utilization rate (decimal)

    Examples
    --------
    >>> interpolate_utilization_by_age(55)
    0.05
    >>> interpolate_utilization_by_age(72)
    0.59
    """
    return _linear_interpolate(age, SOA_2018_GLWB_UTILIZATION_BY_AGE)


def get_itm_sensitivity_factor(
    moneyness: float,
) -> float:
    """
    Get ITM sensitivity multiplier from SOA 2018 Figure 1-44.

    [T2] Withdrawal rates increase when guarantee is in-the-money.

    Parameters
    ----------
    moneyness : float
        GWB / AV ratio (>1 means ITM guarantee)
        - <= 1.0: Not ITM (baseline)
        - 1.0-1.25: Shallow ITM
        - 1.25-1.50: Moderate ITM
        - > 1.50: Deep ITM

    Returns
    -------
    float
        Multiplier to apply to base utilization rate

    Examples
    --------
    >>> get_itm_sensitivity_factor(0.9)   # OTM
    1.0
    >>> get_itm_sensitivity_factor(1.1)   # Shallow ITM
    1.39
    >>> get_itm_sensitivity_factor(1.6)   # Deep ITM
    2.11
    """
    if moneyness <= 1.0:
        return SOA_2018_ITM_SENSITIVITY['not_itm']
    elif moneyness <= 1.25:
        return SOA_2018_ITM_SENSITIVITY['itm_100_125']
    elif moneyness <= 1.50:
        return SOA_2018_ITM_SENSITIVITY['itm_125_150']
    else:
        return SOA_2018_ITM_SENSITIVITY['itm_150_plus']


def get_itm_sensitivity_factor_continuous(
    moneyness: float,
) -> float:
    """
    Get ITM sensitivity with continuous interpolation between buckets.

    [T2] Smoother version of discrete bucket ITM sensitivity.

    Parameters
    ----------
    moneyness : float
        GWB / AV ratio

    Returns
    -------
    float
        Smoothly interpolated ITM multiplier

    Notes
    -----
    Uses linear interpolation between bucket boundaries for
    smoother behavior in MC simulations.
    """
    if moneyness <= 1.0:
        return 1.0

    # Create interpolation points
    x_points = {
        1.00: SOA_2018_ITM_SENSITIVITY['not_itm'],
        1.125: SOA_2018_ITM_SENSITIVITY['itm_100_125'],  # Midpoint of 1.0-1.25
        1.375: SOA_2018_ITM_SENSITIVITY['itm_125_150'],  # Midpoint of 1.25-1.50
        1.75: SOA_2018_ITM_SENSITIVITY['itm_150_plus'],  # Representative of >1.50
    }

    return _linear_interpolate(moneyness, x_points)


# =============================================================================
# Combined Utilization Calculation
# =============================================================================


def combined_utilization(
    duration: int,
    age: int,
    moneyness: float = 1.0,
    combination_method: str = 'multiplicative',
) -> float:
    """
    Combine duration, age, and ITM effects for total utilization.

    [T2] Combines SOA 2018 data for comprehensive utilization estimate.

    Parameters
    ----------
    duration : int
        Contract duration in years
    age : int
        Current age of annuitant
    moneyness : float
        GWB / AV ratio (for ITM sensitivity)
    combination_method : str
        How to combine factors: 'multiplicative' or 'additive'

    Returns
    -------
    float
        Combined utilization rate (capped at 1.0)

    Examples
    --------
    >>> combined_utilization(duration=5, age=70, moneyness=1.0)
    ~0.40  # Duration=21.5%, Age=59%, combined

    Notes
    -----
    The multiplicative method assumes factors are independent:
        util = base_duration × (age_factor / base_age) × itm_factor

    This prevents double-counting the base utilization effect.
    """
    # Get base components
    util_duration = interpolate_utilization_by_duration(duration)
    util_age = interpolate_utilization_by_age(age)
    itm_factor = get_itm_sensitivity_factor(moneyness)

    if combination_method == 'multiplicative':
        # Use duration as base, adjust for age deviation from 67
        # Reference age is 67 (SOA midpoint for mature utilization)
        base_age_util = interpolate_utilization_by_age(67)

        # Scale duration by relative age effect
        age_adjustment = util_age / base_age_util if base_age_util > 0 else 1.0

        # Apply factors
        combined = util_duration * age_adjustment * itm_factor

    elif combination_method == 'additive':
        # Simple average of duration and age effects, scaled by ITM
        combined = ((util_duration + util_age) / 2) * itm_factor

    else:
        raise ValueError("combination_method must be 'multiplicative' or 'additive'")

    # Cap at 100%
    return min(combined, 1.0)


# =============================================================================
# Diagnostic Functions
# =============================================================================


def get_surrender_curve(
    sc_length: int = 7,
    max_duration: int = 15,
) -> dict[int, float]:
    """
    Generate full surrender rate curve for given SC length.

    Parameters
    ----------
    sc_length : int
        Surrender charge period length
    max_duration : int
        Maximum duration to calculate

    Returns
    -------
    dict
        Mapping of duration to surrender rate
    """
    return {
        d: interpolate_surrender_by_duration(d, sc_length)
        for d in range(1, max_duration + 1)
    }


def get_utilization_curve(
    age: int = 70,
    max_duration: int = 15,
) -> dict[int, float]:
    """
    Generate GLWB utilization curve by duration for fixed age.

    Parameters
    ----------
    age : int
        Annuitant age (for age adjustment)
    max_duration : int
        Maximum duration to calculate

    Returns
    -------
    dict
        Mapping of duration to utilization rate
    """
    return {
        d: combined_utilization(d, age, moneyness=1.0)
        for d in range(1, max_duration + 1)
    }
