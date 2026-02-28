"""
Dynamic Lapse Model - Phase 7 + Phase H SOA Calibration.

Implements moneyness-based lapse rates for GLWB/GMWB products.
Higher ITM guarantees → lower lapse rates (rational behavior).

Theory
------
[T1] Base lapse rate adjusted by moneyness factor:
    lapse_rate(t) = base_lapse * f(moneyness)

where moneyness = GWB / AV (guarantee value / account value)
- moneyness < 1: OTM guarantee → higher lapse (rational)
- moneyness > 1: ITM guarantee → lower lapse (rational)
- moneyness = 1: ATM → base lapse

[T2] SOA 2006 calibration adds:
- Duration-based surrender curves (1.4% year 1 → 11.2% year 8)
- Surrender charge cliff effect (2.48x at SC expiration)
- Age-based adjustment factors

See: docs/knowledge/domain/dynamic_lapse.md
See: docs/references/L3/bauer_kling_russ_2008.md (Section 4)
See: docs/assumptions/BEHAVIOR_CALIBRATION.md (SOA calibration)
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class CalibrationSource(Enum):
    """Source of calibration data for lapse model."""

    HARDCODED = "hardcoded"  # Original fixed parameters
    SOA_2006 = "soa_2006"  # SOA 2006 Deferred Annuity Persistency Study


@dataclass(frozen=True)
class LapseAssumptions:
    """
    Lapse rate assumptions.

    Attributes
    ----------
    base_annual_lapse : float
        Base annual lapse rate (e.g., 0.05 for 5%)
    min_lapse : float
        Floor on dynamic lapse rate
    max_lapse : float
        Cap on dynamic lapse rate
    sensitivity : float
        Sensitivity of lapse to moneyness (higher = more responsive)
    """

    base_annual_lapse: float = 0.05
    min_lapse: float = 0.01
    max_lapse: float = 0.25
    sensitivity: float = 1.0


@dataclass(frozen=True)
class LapseResult:
    """
    Result of lapse calculation.

    Attributes
    ----------
    lapse_rate : float
        Calculated lapse rate
    moneyness : float
        GWB/AV ratio used
    adjustment_factor : float
        Multiplier applied to base lapse
    """

    lapse_rate: float
    moneyness: float
    adjustment_factor: float


class DynamicLapseModel:
    """
    Dynamic lapse model with moneyness adjustment.

    Examples
    --------
    >>> model = DynamicLapseModel(LapseAssumptions())
    >>> result = model.calculate_lapse(gwb=110_000, av=100_000)  # ITM
    >>> result.lapse_rate < 0.05  # Lower than base
    True

    See: docs/knowledge/domain/dynamic_lapse.md
    """

    def __init__(self, assumptions: LapseAssumptions):
        """
        Initialize dynamic lapse model.

        Parameters
        ----------
        assumptions : LapseAssumptions
            Lapse rate assumptions
        """
        self.assumptions = assumptions

    def calculate_lapse(
        self,
        gwb: float,
        av: float,
        surrender_period_complete: bool = False,
    ) -> LapseResult:
        """
        Calculate dynamic lapse rate.

        [T1] lapse_rate = base_lapse × f(moneyness)

        Parameters
        ----------
        gwb : float
            Guaranteed Withdrawal Benefit value
        av : float
            Current account value
        surrender_period_complete : bool
            Whether surrender period has ended

        Returns
        -------
        LapseResult
            Calculated lapse rate with diagnostics
        """
        # Validate inputs
        if av <= 0:
            raise ValueError(f"Account value must be positive, got {av}")
        if gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb}")

        # Calculate moneyness = AV / GWB
        # Moneyness > 1: AV exceeds guarantee (OTM guarantee) → higher lapse
        # Moneyness < 1: AV below guarantee (ITM guarantee) → lower lapse
        if gwb > 0:
            moneyness = av / gwb
        else:
            moneyness = 1.0  # No guarantee, use base rate

        # Dynamic adjustment factor
        # Apply sensitivity: factor = moneyness^sensitivity
        adjustment_factor = moneyness**self.assumptions.sensitivity

        # Calculate adjusted lapse rate
        base_rate = self.assumptions.base_annual_lapse

        # If still in surrender period, reduce lapse significantly
        if not surrender_period_complete:
            base_rate = base_rate * 0.2  # 80% reduction during surrender period

        # Apply dynamic adjustment
        lapse_rate = base_rate * adjustment_factor

        # Apply floor and cap
        lapse_rate = np.clip(
            lapse_rate,
            self.assumptions.min_lapse,
            self.assumptions.max_lapse,
        )

        return LapseResult(
            lapse_rate=lapse_rate,
            moneyness=moneyness,
            adjustment_factor=adjustment_factor,
        )

    def calculate_path_lapses(
        self,
        gwb_path: np.ndarray,
        av_path: np.ndarray,
        surrender_period_ends: int = 0,
    ) -> np.ndarray:
        """
        Calculate lapse rates along a simulation path.

        Parameters
        ----------
        gwb_path : ndarray
            Path of GWB values (shape: [n_steps])
        av_path : ndarray
            Path of AV values (shape: [n_steps])
        surrender_period_ends : int
            Time step when surrender period ends (0 = already complete)

        Returns
        -------
        ndarray
            Lapse rates at each time step (shape: [n_steps])
        """
        if len(gwb_path) != len(av_path):
            raise ValueError(f"Path lengths must match: gwb={len(gwb_path)}, av={len(av_path)}")

        n_steps = len(gwb_path)
        lapse_rates = np.zeros(n_steps)

        for t in range(n_steps):
            surrender_complete = t >= surrender_period_ends
            result = self.calculate_lapse(
                gwb=gwb_path[t],
                av=av_path[t],
                surrender_period_complete=surrender_complete,
            )
            lapse_rates[t] = result.lapse_rate

        return lapse_rates

    def calculate_survival_probability(
        self,
        lapse_rates: np.ndarray,
        dt: float = 1.0,
    ) -> np.ndarray:
        """
        Calculate cumulative survival probability from lapse rates.

        [T1] survival_t = prod(1 - lapse_s * dt) for s in [0, t)

        Parameters
        ----------
        lapse_rates : ndarray
            Annual lapse rates at each time step
        dt : float
            Time step size in years (default 1.0)

        Returns
        -------
        ndarray
            Cumulative survival probabilities (shape: [n_steps + 1])
            First element is 1.0 (survival at t=0)
        """
        n_steps = len(lapse_rates)
        survival = np.ones(n_steps + 1)

        for t in range(n_steps):
            # Probability of not lapsing in period t
            prob_stay = 1.0 - lapse_rates[t] * dt
            survival[t + 1] = survival[t] * max(prob_stay, 0.0)

        return survival


# =============================================================================
# SOA-Calibrated Lapse Model (Phase H)
# =============================================================================


@dataclass(frozen=True)
class SOALapseAssumptions:
    """
    SOA-calibrated lapse rate assumptions.

    [T2] Based on SOA 2006 Deferred Annuity Persistency Study.

    Attributes
    ----------
    surrender_charge_length : int
        Length of surrender charge period in years (default 7)
    use_duration_curve : bool
        Use SOA duration-based surrender curve (default True)
    use_sc_cliff_effect : bool
        Apply surrender charge cliff multiplier (default True)
    use_age_adjustment : bool
        Apply age-based surrender rate adjustment (default False)
    moneyness_sensitivity : float
        Sensitivity of lapse to moneyness (for GLWB products)
    min_lapse : float
        Floor on lapse rate
    max_lapse : float
        Cap on lapse rate
    """

    surrender_charge_length: int = 7
    use_duration_curve: bool = True
    use_sc_cliff_effect: bool = True
    use_age_adjustment: bool = False
    moneyness_sensitivity: float = 1.0
    min_lapse: float = 0.005  # 0.5% floor
    max_lapse: float = 0.25  # 25% cap


@dataclass(frozen=True)
class SOALapseResult:
    """
    Result of SOA-calibrated lapse calculation.

    Attributes
    ----------
    lapse_rate : float
        Final calculated lapse rate
    base_rate : float
        Base surrender rate from SOA duration curve
    sc_cliff_factor : float
        Surrender charge cliff multiplier applied
    moneyness : float
        GWB/AV ratio (for GLWB)
    moneyness_factor : float
        Multiplier from moneyness adjustment
    age_factor : float
        Multiplier from age adjustment (if enabled)
    """

    lapse_rate: float
    base_rate: float
    sc_cliff_factor: float
    moneyness: float
    moneyness_factor: float
    age_factor: float


class SOADynamicLapseModel:
    """
    SOA-calibrated dynamic lapse model.

    [T2] Uses SOA 2006 Deferred Annuity Persistency Study data:
    - Duration-based surrender curves
    - Surrender charge cliff effect (2.48x at expiration)
    - Optional age adjustment

    Examples
    --------
    >>> model = SOADynamicLapseModel(SOALapseAssumptions())
    >>> result = model.calculate_lapse(
    ...     gwb=110_000, av=100_000, duration=1, years_to_sc_end=6
    ... )
    >>> result.base_rate
    0.014  # 1.4% from SOA year 1

    >>> result = model.calculate_lapse(
    ...     gwb=100_000, av=100_000, duration=8, years_to_sc_end=-1
    ... )
    >>> result.base_rate
    0.112  # 11.2% post-SC cliff

    See Also
    --------
    annuity_pricing.behavioral.calibration : Interpolation functions
    annuity_pricing.behavioral.soa_benchmarks : Source data
    docs/assumptions/BEHAVIOR_CALIBRATION.md : Methodology
    """

    def __init__(self, assumptions: SOALapseAssumptions):
        """
        Initialize SOA-calibrated lapse model.

        Parameters
        ----------
        assumptions : SOALapseAssumptions
            SOA calibration settings
        """
        self.assumptions = assumptions
        self._calibration_source = CalibrationSource.SOA_2006

    def calculate_lapse(
        self,
        gwb: float,
        av: float,
        duration: int,
        years_to_sc_end: int = 0,
        age: int | None = None,
    ) -> SOALapseResult:
        """
        Calculate SOA-calibrated lapse rate.

        [T2] lapse_rate = base_rate × sc_cliff × moneyness_factor × age_factor

        Parameters
        ----------
        gwb : float
            Guaranteed Withdrawal Benefit value
        av : float
            Current account value
        duration : int
            Contract duration in years (1 = first year)
        years_to_sc_end : int
            Years until SC expires (0 = just expired, negative = post-SC)
        age : int, optional
            Policyholder age (for age adjustment)

        Returns
        -------
        SOALapseResult
            Detailed lapse calculation results
        """
        from annuity_pricing.behavioral.calibration import (
            get_sc_cliff_multiplier,
            interpolate_surrender_by_age,
            interpolate_surrender_by_duration,
        )

        # Validate inputs
        if av <= 0:
            raise ValueError(f"Account value must be positive, got {av}")
        if gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb}")
        if duration <= 0:
            raise ValueError(f"Duration must be positive, got {duration}")

        # 1. Get base rate from SOA duration curve
        if self.assumptions.use_duration_curve:
            base_rate = interpolate_surrender_by_duration(
                duration=duration,
                sc_length=self.assumptions.surrender_charge_length,
            )
        else:
            # Fall back to flat 5% if disabled
            base_rate = 0.05

        # 2. Apply SC cliff effect if applicable
        if self.assumptions.use_sc_cliff_effect:
            sc_cliff_factor = get_sc_cliff_multiplier(years_to_sc_end)
            # Only apply cliff if we're near the cliff period
            # The duration curve already captures some of this
            if abs(years_to_sc_end) <= 2:
                # Blend between duration curve and cliff effect
                # Duration curve baseline is for 7-year SC
                base_cliff_rate = 0.058  # Year 7 rate before cliff
                if base_rate > base_cliff_rate:
                    # Already past cliff in duration curve, reduce cliff factor
                    sc_cliff_factor = max(1.0, sc_cliff_factor * 0.5)
        else:
            sc_cliff_factor = 1.0

        # 3. Calculate moneyness adjustment (for GLWB products)
        if gwb > 0:
            moneyness = gwb / av  # GWB/AV (>1 = ITM guarantee)
            # ITM guarantee → lower lapse (inverse of OTM behavior)
            # Use inverse: when GWB > AV (ITM), factor < 1
            moneyness_factor = (av / gwb) ** self.assumptions.moneyness_sensitivity
        else:
            moneyness = 1.0
            moneyness_factor = 1.0

        # 4. Age adjustment (optional)
        if self.assumptions.use_age_adjustment and age is not None:
            # Get age-based rate and compare to overall average
            age_rate = interpolate_surrender_by_age(age, surrender_type="full")
            avg_rate = 0.052  # SOA average full surrender rate
            age_factor = age_rate / avg_rate
        else:
            age_factor = 1.0

        # 5. Combine factors
        lapse_rate = base_rate * sc_cliff_factor * moneyness_factor * age_factor

        # 6. Apply floor and cap
        lapse_rate = np.clip(
            lapse_rate,
            self.assumptions.min_lapse,
            self.assumptions.max_lapse,
        )

        return SOALapseResult(
            lapse_rate=float(lapse_rate),
            base_rate=base_rate,
            sc_cliff_factor=sc_cliff_factor,
            moneyness=moneyness,
            moneyness_factor=moneyness_factor,
            age_factor=age_factor,
        )

    def calculate_path_lapses(
        self,
        gwb_path: np.ndarray,
        av_path: np.ndarray,
        start_duration: int = 1,
        surrender_charge_length: int | None = None,
        ages: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Calculate lapse rates along a simulation path.

        Parameters
        ----------
        gwb_path : ndarray
            Path of GWB values (shape: [n_steps])
        av_path : ndarray
            Path of AV values (shape: [n_steps])
        start_duration : int
            Contract duration at start of path (default 1)
        surrender_charge_length : int, optional
            Override SC length (default: use assumptions)
        ages : ndarray, optional
            Ages at each time step (for age adjustment)

        Returns
        -------
        ndarray
            Lapse rates at each time step (shape: [n_steps])
        """
        if len(gwb_path) != len(av_path):
            raise ValueError(f"Path lengths must match: gwb={len(gwb_path)}, av={len(av_path)}")

        sc_length = surrender_charge_length or self.assumptions.surrender_charge_length
        n_steps = len(gwb_path)
        lapse_rates = np.zeros(n_steps)

        for t in range(n_steps):
            duration = start_duration + t
            years_to_sc_end = sc_length - duration

            age = int(ages[t]) if ages is not None else None

            result = self.calculate_lapse(
                gwb=gwb_path[t],
                av=av_path[t],
                duration=duration,
                years_to_sc_end=years_to_sc_end,
                age=age,
            )
            lapse_rates[t] = result.lapse_rate

        return lapse_rates

    def calculate_survival_probability(
        self,
        lapse_rates: np.ndarray,
        dt: float = 1.0,
    ) -> np.ndarray:
        """
        Calculate cumulative survival probability from lapse rates.

        [T1] survival_t = prod(1 - lapse_s * dt) for s in [0, t)

        Parameters
        ----------
        lapse_rates : ndarray
            Annual lapse rates at each time step
        dt : float
            Time step size in years (default 1.0)

        Returns
        -------
        ndarray
            Cumulative survival probabilities (shape: [n_steps + 1])
        """
        n_steps = len(lapse_rates)
        survival = np.ones(n_steps + 1)

        for t in range(n_steps):
            prob_stay = 1.0 - lapse_rates[t] * dt
            survival[t + 1] = survival[t] * max(prob_stay, 0.0)

        return survival

    @property
    def calibration_source(self) -> CalibrationSource:
        """Return the calibration data source."""
        return self._calibration_source
