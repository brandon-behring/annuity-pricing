"""
MYGA present value and risk metrics calculations.

Detailed liability valuation for Multi-Year Guaranteed Annuities.
See: METHODOLOGY.md Section 4.1
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CashFlow:
    """Single cash flow."""

    time: float  # Years from now
    amount: float  # Dollar amount


@dataclass(frozen=True)
class MYGAValuation:
    """
    Complete MYGA valuation result.

    Attributes
    ----------
    present_value : float
        PV of all cash flows
    maturity_value : float
        Value at end of guarantee period
    macaulay_duration : float
        Weighted average time to cash flows
    modified_duration : float
        Price sensitivity to rate changes
    convexity : float
        Second-order rate sensitivity
    dollar_duration : float
        DV01 - dollar value of 1bp rate move
    effective_duration : float
        Duration based on actual price changes (for bonds with options)
    """

    present_value: float
    maturity_value: float
    macaulay_duration: float
    modified_duration: float
    convexity: float
    dollar_duration: float
    effective_duration: float | None = None


def calculate_myga_maturity_value(
    principal: float,
    rate: float,
    years: int,
    compounding_frequency: int = 1,
) -> float:
    """
    Calculate MYGA value at maturity.

    Parameters
    ----------
    principal : float
        Initial premium
    rate : float
        Annual interest rate (decimal)
    years : int
        Guarantee duration
    compounding_frequency : int, default 1
        Compounding periods per year (1=annual, 2=semi, 4=quarterly)

    Returns
    -------
    float
        Maturity value

    Examples
    --------
    >>> calculate_myga_maturity_value(100000, 0.045, 5)
    124618.19...
    """
    if principal <= 0:
        raise ValueError(f"CRITICAL: principal must be > 0, got {principal}")
    if rate < 0:
        raise ValueError(f"CRITICAL: rate must be >= 0, got {rate}")
    if years <= 0:
        raise ValueError(f"CRITICAL: years must be > 0, got {years}")

    n = compounding_frequency
    periods = years * n
    periodic_rate = rate / n

    return principal * (1 + periodic_rate) ** periods


def calculate_present_value(
    future_value: float,
    discount_rate: float,
    years: float,
    compounding_frequency: int = 1,
) -> float:
    """
    Calculate present value of future cash flow.

    [T1] PV = FV / (1 + r/n)^(n*t)

    Parameters
    ----------
    future_value : float
        Future value to discount
    discount_rate : float
        Discount rate (decimal)
    years : float
        Time to cash flow
    compounding_frequency : int, default 1
        Compounding periods per year

    Returns
    -------
    float
        Present value
    """
    if future_value < 0:
        raise ValueError(f"CRITICAL: future_value must be >= 0, got {future_value}")

    n = compounding_frequency
    periods = years * n
    periodic_rate = discount_rate / n

    return future_value / (1 + periodic_rate) ** periods


def calculate_macaulay_duration(
    cash_flows: list[CashFlow],
    discount_rate: float,
) -> float:
    """
    Calculate Macaulay duration.

    [T1] D = Σ(t × PV(CF_t)) / Σ(PV(CF_t))

    Parameters
    ----------
    cash_flows : List[CashFlow]
        List of cash flows with time and amount
    discount_rate : float
        Discount rate

    Returns
    -------
    float
        Macaulay duration in years
    """
    if not cash_flows:
        raise ValueError("CRITICAL: cash_flows list is empty")

    weighted_sum = 0.0
    pv_sum = 0.0

    for cf in cash_flows:
        pv = calculate_present_value(cf.amount, discount_rate, cf.time)
        weighted_sum += cf.time * pv
        pv_sum += pv

    if pv_sum == 0:
        raise ValueError("CRITICAL: Total PV is zero, cannot calculate duration")

    return weighted_sum / pv_sum


def calculate_modified_duration(
    macaulay_duration: float,
    discount_rate: float,
    compounding_frequency: int = 1,
) -> float:
    """
    Calculate modified duration.

    [T1] ModD = MacD / (1 + r/n)

    Parameters
    ----------
    macaulay_duration : float
        Macaulay duration
    discount_rate : float
        Discount rate
    compounding_frequency : int, default 1
        Compounding periods per year

    Returns
    -------
    float
        Modified duration
    """
    n = compounding_frequency
    return macaulay_duration / (1 + discount_rate / n)


def calculate_convexity(
    cash_flows: list[CashFlow],
    discount_rate: float,
) -> float:
    """
    Calculate convexity.

    [T1] C = Σ(t × (t+1) × PV(CF_t)) / (PV × (1+r)^2)

    Parameters
    ----------
    cash_flows : List[CashFlow]
        List of cash flows
    discount_rate : float
        Discount rate

    Returns
    -------
    float
        Convexity
    """
    if not cash_flows:
        raise ValueError("CRITICAL: cash_flows list is empty")

    weighted_sum = 0.0
    pv_sum = 0.0

    for cf in cash_flows:
        pv = calculate_present_value(cf.amount, discount_rate, cf.time)
        weighted_sum += cf.time * (cf.time + 1) * pv
        pv_sum += pv

    if pv_sum == 0:
        raise ValueError("CRITICAL: Total PV is zero, cannot calculate convexity")

    return weighted_sum / (pv_sum * (1 + discount_rate) ** 2)


def calculate_dollar_duration(
    present_value: float,
    modified_duration: float,
) -> float:
    """
    Calculate dollar duration (DV01 approximation).

    [T1] DV01 ≈ PV × ModD × 0.0001

    Parameters
    ----------
    present_value : float
        Present value of liability
    modified_duration : float
        Modified duration

    Returns
    -------
    float
        Dollar value of 1bp rate change
    """
    return present_value * modified_duration * 0.0001


def calculate_effective_duration(
    pv_up: float,
    pv_down: float,
    pv_base: float,
    rate_shift: float = 0.01,
) -> float:
    """
    Calculate effective duration from price changes.

    [T1] EffD = (PV_down - PV_up) / (2 × PV_base × Δr)

    Parameters
    ----------
    pv_up : float
        PV when rates shift up
    pv_down : float
        PV when rates shift down
    pv_base : float
        PV at base rates
    rate_shift : float, default 0.01
        Rate shift (1% = 0.01)

    Returns
    -------
    float
        Effective duration
    """
    if pv_base == 0:
        raise ValueError("CRITICAL: pv_base is zero, cannot calculate effective duration")

    return (pv_down - pv_up) / (2 * pv_base * rate_shift)


def value_myga(
    principal: float,
    fixed_rate: float,
    guarantee_duration: int,
    discount_rate: float,
    include_intermediate_flows: bool = False,
) -> MYGAValuation:
    """
    Complete MYGA valuation with all risk metrics.

    Parameters
    ----------
    principal : float
        Initial premium
    fixed_rate : float
        MYGA guaranteed rate (decimal)
    guarantee_duration : int
        Years of guarantee
    discount_rate : float
        Discount rate for PV (decimal)
    include_intermediate_flows : bool, default False
        Whether to include annual interest as separate cash flows
        (default treats as single maturity payment)

    Returns
    -------
    MYGAValuation
        Complete valuation with PV, duration, convexity

    Examples
    --------
    >>> val = value_myga(100000, 0.045, 5, 0.04)
    >>> val.present_value
    102209.97...
    >>> val.macaulay_duration
    5.0
    """
    # Calculate maturity value
    maturity_value = calculate_myga_maturity_value(principal, fixed_rate, guarantee_duration)

    # Build cash flow schedule
    if include_intermediate_flows:
        # Annual interest payments + principal at maturity
        cash_flows = []
        annual_interest = principal * fixed_rate
        for t in range(1, guarantee_duration):
            cash_flows.append(CashFlow(time=float(t), amount=annual_interest))
        # Final payment includes principal + last interest
        cash_flows.append(CashFlow(time=float(guarantee_duration), amount=maturity_value))
    else:
        # Single payment at maturity (typical MYGA structure)
        cash_flows = [CashFlow(time=float(guarantee_duration), amount=maturity_value)]

    # Calculate PV
    present_value = sum(
        calculate_present_value(cf.amount, discount_rate, cf.time)
        for cf in cash_flows
    )

    # Calculate duration and convexity
    macaulay_duration = calculate_macaulay_duration(cash_flows, discount_rate)
    modified_duration = calculate_modified_duration(macaulay_duration, discount_rate)
    convexity = calculate_convexity(cash_flows, discount_rate)
    dollar_duration = calculate_dollar_duration(present_value, modified_duration)

    # Calculate effective duration (shock rates ±1%)
    rate_shift = 0.01
    pv_up = sum(
        calculate_present_value(cf.amount, discount_rate + rate_shift, cf.time)
        for cf in cash_flows
    )
    pv_down = sum(
        calculate_present_value(cf.amount, discount_rate - rate_shift, cf.time)
        for cf in cash_flows
    )
    effective_duration = calculate_effective_duration(pv_up, pv_down, present_value, rate_shift)

    return MYGAValuation(
        present_value=present_value,
        maturity_value=maturity_value,
        macaulay_duration=macaulay_duration,
        modified_duration=modified_duration,
        convexity=convexity,
        dollar_duration=dollar_duration,
        effective_duration=effective_duration,
    )


def sensitivity_analysis(
    principal: float,
    fixed_rate: float,
    guarantee_duration: int,
    base_discount_rate: float,
    rate_shifts: list[float] | None = None,
) -> list[tuple[float, float, float]]:
    """
    Perform sensitivity analysis on discount rate.

    Parameters
    ----------
    principal : float
        Initial premium
    fixed_rate : float
        MYGA rate
    guarantee_duration : int
        Years
    base_discount_rate : float
        Base discount rate
    rate_shifts : List[float], optional
        Rate shifts to analyze. Default: [-1%, -0.5%, 0, +0.5%, +1%]

    Returns
    -------
    List[Tuple[float, float, float]]
        List of (discount_rate, present_value, pct_change)
    """
    if rate_shifts is None:
        rate_shifts = [-0.01, -0.005, 0.0, 0.005, 0.01]

    base_val = value_myga(principal, fixed_rate, guarantee_duration, base_discount_rate)
    base_pv = base_val.present_value

    results = []
    for shift in rate_shifts:
        new_rate = base_discount_rate + shift
        if new_rate <= 0:
            continue  # Skip negative rates

        val = value_myga(principal, fixed_rate, guarantee_duration, new_rate)
        pct_change = (val.present_value - base_pv) / base_pv * 100

        results.append((new_rate, val.present_value, pct_change))

    return results
