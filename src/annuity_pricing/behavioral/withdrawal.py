"""
GLWB Withdrawal Utilization Model - Phase 7 + Phase H SOA Calibration.

Models policyholder withdrawal behavior for GLWB products.
Tracks actual vs maximum allowed withdrawals.

Theory
------
[T1] Utilization rate = Actual Withdrawal / Maximum Allowed Withdrawal

Empirical patterns (from LIMRA/SOA studies):
- Average utilization: 60-80%
- Higher utilization for older ages
- Lower utilization early in contract

[T2] SOA 2018 calibration adds:
- Duration-based utilization (11% year 1 → 54% year 10)
- Age-based utilization curves
- ITM sensitivity factors (deep ITM → 2.1x utilization)

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md
See: docs/assumptions/BEHAVIOR_CALIBRATION.md (SOA calibration)
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class UtilizationCalibration(Enum):
    """Source of utilization calibration data."""

    HARDCODED = "hardcoded"  # Original fixed parameters
    SOA_2018 = "soa_2018"  # SOA 2018 VA GLB Utilization Study


@dataclass(frozen=True)
class WithdrawalAssumptions:
    """
    Withdrawal behavior assumptions.

    Attributes
    ----------
    base_utilization : float
        Base utilization rate (e.g., 0.70 for 70%)
    age_sensitivity : float
        How much utilization increases with age
    min_utilization : float
        Floor on utilization
    max_utilization : float
        Cap on utilization (should be ≤ 1.0)
    """

    base_utilization: float = 0.70
    age_sensitivity: float = 0.01  # +1% per year over 65
    min_utilization: float = 0.30
    max_utilization: float = 1.00


@dataclass(frozen=True)
class WithdrawalResult:
    """
    Result of withdrawal calculation.

    Attributes
    ----------
    withdrawal_amount : float
        Calculated withdrawal amount
    utilization_rate : float
        Actual / Maximum ratio
    max_allowed : float
        Maximum allowed withdrawal
    """

    withdrawal_amount: float
    utilization_rate: float
    max_allowed: float


class WithdrawalModel:
    """
    GLWB withdrawal utilization model.

    Examples
    --------
    >>> model = WithdrawalModel(WithdrawalAssumptions())
    >>> result = model.calculate_withdrawal(
    ...     gwb=100_000, withdrawal_rate=0.05, age=70
    ... )

    See: docs/knowledge/domain/glwb_mechanics.md
    """

    def __init__(self, assumptions: WithdrawalAssumptions):
        """
        Initialize withdrawal model.

        Parameters
        ----------
        assumptions : WithdrawalAssumptions
            Withdrawal behavior assumptions
        """
        self.assumptions = assumptions

    def calculate_withdrawal(
        self,
        gwb: float,
        withdrawal_rate: float,
        age: int,
        years_since_first_withdrawal: int = 0,
    ) -> WithdrawalResult:
        """
        Calculate expected withdrawal amount.

        [T1] Withdrawal = GWB × withdrawal_rate × utilization_rate

        Parameters
        ----------
        gwb : float
            Guaranteed Withdrawal Benefit value
        withdrawal_rate : float
            Contract withdrawal rate (e.g., 0.05 for 5%)
        age : int
            Current age of annuitant
        years_since_first_withdrawal : int
            Years since first withdrawal (for utilization ramp)

        Returns
        -------
        WithdrawalResult
            Calculated withdrawal with diagnostics
        """
        if gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb}")
        if withdrawal_rate < 0 or withdrawal_rate > 1:
            raise ValueError(f"Withdrawal rate must be in [0, 1], got {withdrawal_rate}")

        # Maximum allowed withdrawal
        max_allowed = gwb * withdrawal_rate

        # Calculate utilization rate
        utilization = self._calculate_utilization(age, years_since_first_withdrawal)

        # Expected withdrawal amount
        withdrawal_amount = max_allowed * utilization

        return WithdrawalResult(
            withdrawal_amount=withdrawal_amount,
            utilization_rate=utilization,
            max_allowed=max_allowed,
        )

    def _calculate_utilization(
        self,
        age: int,
        years_since_first_withdrawal: int,
    ) -> float:
        """
        Calculate utilization rate based on age and experience.

        [T2] Empirical patterns:
        - Base utilization ~70%
        - Higher utilization for older ages
        - Ramp-up in early withdrawal years

        Parameters
        ----------
        age : int
            Current age
        years_since_first_withdrawal : int
            Years since first withdrawal

        Returns
        -------
        float
            Utilization rate in [min_utilization, max_utilization]
        """
        a = self.assumptions

        # Start with base utilization
        utilization = a.base_utilization

        # Age adjustment: higher utilization for older ages
        # Reference age is 65
        age_adjustment = a.age_sensitivity * max(0, age - 65)
        utilization += age_adjustment

        # Early withdrawal ramp-up: lower utilization in first few years
        if years_since_first_withdrawal < 3:
            ramp_factor = 0.7 + 0.1 * years_since_first_withdrawal  # 70%, 80%, 90%
            utilization *= ramp_factor

        # Apply floor and cap
        utilization = np.clip(utilization, a.min_utilization, a.max_utilization)

        return utilization

    def calculate_path_withdrawals(
        self,
        gwb_path: np.ndarray,
        ages: np.ndarray,
        withdrawal_rate: float,
        first_withdrawal_year: int = 0,
    ) -> np.ndarray:
        """
        Calculate withdrawals along a simulation path.

        Parameters
        ----------
        gwb_path : ndarray
            Path of GWB values (shape: [n_steps])
        ages : ndarray
            Ages at each time step (shape: [n_steps])
        withdrawal_rate : float
            Contract withdrawal rate
        first_withdrawal_year : int
            Year when first withdrawal occurs (0 = start)

        Returns
        -------
        ndarray
            Withdrawal amounts at each time step (shape: [n_steps])
        """
        if len(gwb_path) != len(ages):
            raise ValueError(f"Path lengths must match: gwb={len(gwb_path)}, ages={len(ages)}")

        n_steps = len(gwb_path)
        withdrawals = np.zeros(n_steps)

        for t in range(n_steps):
            # Calculate years since first withdrawal
            if t >= first_withdrawal_year:
                years_since = t - first_withdrawal_year
            else:
                # Before first withdrawal - no withdrawal
                withdrawals[t] = 0.0
                continue

            result = self.calculate_withdrawal(
                gwb=gwb_path[t],
                withdrawal_rate=withdrawal_rate,
                age=int(ages[t]),
                years_since_first_withdrawal=years_since,
            )
            withdrawals[t] = result.withdrawal_amount

        return withdrawals

    def get_withdrawal_rate_by_age(self, age: int) -> float:
        """
        Get typical withdrawal rate schedule by age.

        [T2] Based on industry practice:
        - 55-59: 4.0%
        - 60-64: 4.5%
        - 65-69: 5.0%
        - 70-74: 5.5%
        - 75+: 6.0%

        Parameters
        ----------
        age : int
            Age at first withdrawal

        Returns
        -------
        float
            Recommended withdrawal rate
        """
        if age < 55:
            return 0.035  # 3.5% for very early withdrawal
        elif age < 60:
            return 0.040
        elif age < 65:
            return 0.045
        elif age < 70:
            return 0.050
        elif age < 75:
            return 0.055
        else:
            return 0.060


# =============================================================================
# SOA-Calibrated Withdrawal Model (Phase H)
# =============================================================================


@dataclass(frozen=True)
class SOAWithdrawalAssumptions:
    """
    SOA-calibrated withdrawal utilization assumptions.

    [T2] Based on SOA 2018 VA GLB Utilization Study.

    Attributes
    ----------
    use_duration_curve : bool
        Use SOA duration-based utilization curve (default True)
    use_age_curve : bool
        Use SOA age-based utilization curve (default True)
    use_itm_sensitivity : bool
        Apply ITM sensitivity factors (default True)
    use_continuous_itm : bool
        Use continuous (vs discrete) ITM interpolation (default True)
    combination_method : str
        How to combine duration and age effects: 'multiplicative' or 'additive'
    min_utilization : float
        Floor on utilization rate
    max_utilization : float
        Cap on utilization rate (should be ≤ 1.0)
    """

    use_duration_curve: bool = True
    use_age_curve: bool = True
    use_itm_sensitivity: bool = True
    use_continuous_itm: bool = True
    combination_method: str = "multiplicative"
    min_utilization: float = 0.03  # 3% floor (even young ages take some)
    max_utilization: float = 1.00  # 100% cap


@dataclass(frozen=True)
class SOAWithdrawalResult:
    """
    Result of SOA-calibrated withdrawal calculation.

    Attributes
    ----------
    withdrawal_amount : float
        Calculated withdrawal amount
    utilization_rate : float
        Combined utilization rate
    max_allowed : float
        Maximum allowed withdrawal (GWB × rate)
    duration_utilization : float
        Utilization from duration curve
    age_utilization : float
        Utilization from age curve
    itm_factor : float
        ITM sensitivity multiplier applied
    moneyness : float
        GWB/AV ratio (for ITM calculation)
    """

    withdrawal_amount: float
    utilization_rate: float
    max_allowed: float
    duration_utilization: float
    age_utilization: float
    itm_factor: float
    moneyness: float


class SOAWithdrawalModel:
    """
    SOA-calibrated GLWB withdrawal utilization model.

    [T2] Uses SOA 2018 VA GLB Utilization Study data:
    - Duration-based utilization (11% year 1 → 54% year 10)
    - Age-based utilization curves
    - ITM sensitivity factors

    Examples
    --------
    >>> model = SOAWithdrawalModel(SOAWithdrawalAssumptions())
    >>> result = model.calculate_withdrawal(
    ...     gwb=100_000, av=100_000, withdrawal_rate=0.05,
    ...     duration=5, age=70
    ... )
    >>> result.utilization_rate
    ~0.40  # Combined from duration (21.5%) and age (59%)

    >>> result = model.calculate_withdrawal(
    ...     gwb=150_000, av=100_000, withdrawal_rate=0.05,
    ...     duration=5, age=70
    ... )
    >>> result.itm_factor
    2.11  # Deep ITM (GWB/AV = 1.5)

    See Also
    --------
    annuity_pricing.behavioral.calibration : Interpolation functions
    annuity_pricing.behavioral.soa_benchmarks : Source data
    docs/assumptions/BEHAVIOR_CALIBRATION.md : Methodology
    """

    def __init__(self, assumptions: SOAWithdrawalAssumptions):
        """
        Initialize SOA-calibrated withdrawal model.

        Parameters
        ----------
        assumptions : SOAWithdrawalAssumptions
            SOA calibration settings
        """
        self.assumptions = assumptions
        self._calibration_source = UtilizationCalibration.SOA_2018

    def calculate_withdrawal(
        self,
        gwb: float,
        av: float,
        withdrawal_rate: float,
        duration: int,
        age: int,
    ) -> SOAWithdrawalResult:
        """
        Calculate SOA-calibrated withdrawal amount.

        [T2] utilization = f(duration, age, ITM)

        Parameters
        ----------
        gwb : float
            Guaranteed Withdrawal Benefit value
        av : float
            Current account value (for ITM calculation)
        withdrawal_rate : float
            Contract withdrawal rate (e.g., 0.05 for 5%)
        duration : int
            Contract duration in years (1 = first year)
        age : int
            Current age of annuitant

        Returns
        -------
        SOAWithdrawalResult
            Detailed withdrawal calculation results
        """
        from annuity_pricing.behavioral.calibration import (
            combined_utilization,
            get_itm_sensitivity_factor,
            get_itm_sensitivity_factor_continuous,
            interpolate_utilization_by_age,
            interpolate_utilization_by_duration,
        )

        # Validate inputs
        if gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb}")
        if av <= 0:
            raise ValueError(f"Account value must be positive, got {av}")
        if withdrawal_rate < 0 or withdrawal_rate > 1:
            raise ValueError(f"Withdrawal rate must be in [0, 1], got {withdrawal_rate}")
        if duration <= 0:
            raise ValueError(f"Duration must be positive, got {duration}")

        # Maximum allowed withdrawal
        max_allowed = gwb * withdrawal_rate

        # 1. Get duration-based utilization
        if self.assumptions.use_duration_curve:
            duration_util = interpolate_utilization_by_duration(duration)
        else:
            duration_util = 0.50  # Fall back to 50%

        # 2. Get age-based utilization
        if self.assumptions.use_age_curve:
            age_util = interpolate_utilization_by_age(age)
        else:
            age_util = 0.50  # Fall back to 50%

        # 3. Calculate ITM sensitivity factor
        moneyness = gwb / av if av > 0 else 1.0
        if self.assumptions.use_itm_sensitivity:
            if self.assumptions.use_continuous_itm:
                itm_factor = get_itm_sensitivity_factor_continuous(moneyness)
            else:
                itm_factor = get_itm_sensitivity_factor(moneyness)
        else:
            itm_factor = 1.0

        # 4. Combine factors
        if self.assumptions.combination_method == "multiplicative":
            # Use duration as base, adjust by age and ITM
            # Reference: age 67 is "average" mature holder
            base_age_util = (
                interpolate_utilization_by_age(67) if self.assumptions.use_age_curve else 0.32
            )
            age_adjustment = age_util / base_age_util if base_age_util > 0 else 1.0
            utilization = duration_util * age_adjustment * itm_factor

        elif self.assumptions.combination_method == "additive":
            # Simple average of duration and age effects, scaled by ITM
            utilization = ((duration_util + age_util) / 2) * itm_factor

        else:
            # Use the combined_utilization function
            utilization = combined_utilization(
                duration=duration,
                age=age,
                moneyness=moneyness,
                combination_method=self.assumptions.combination_method,
            )

        # 5. Apply floor and cap
        utilization = np.clip(
            utilization,
            self.assumptions.min_utilization,
            self.assumptions.max_utilization,
        )

        # 6. Calculate withdrawal amount
        withdrawal_amount = max_allowed * utilization

        return SOAWithdrawalResult(
            withdrawal_amount=withdrawal_amount,
            utilization_rate=float(utilization),
            max_allowed=max_allowed,
            duration_utilization=duration_util,
            age_utilization=age_util,
            itm_factor=itm_factor,
            moneyness=moneyness,
        )

    def calculate_path_withdrawals(
        self,
        gwb_path: np.ndarray,
        av_path: np.ndarray,
        ages: np.ndarray,
        withdrawal_rate: float,
        start_duration: int = 1,
        first_withdrawal_year: int = 0,
    ) -> np.ndarray:
        """
        Calculate withdrawals along a simulation path.

        Parameters
        ----------
        gwb_path : ndarray
            Path of GWB values (shape: [n_steps])
        av_path : ndarray
            Path of AV values (shape: [n_steps])
        ages : ndarray
            Ages at each time step (shape: [n_steps])
        withdrawal_rate : float
            Contract withdrawal rate
        start_duration : int
            Contract duration at start of path (default 1)
        first_withdrawal_year : int
            Year when first withdrawal occurs (0 = start)

        Returns
        -------
        ndarray
            Withdrawal amounts at each time step (shape: [n_steps])
        """
        if len(gwb_path) != len(av_path):
            raise ValueError(f"Path lengths must match: gwb={len(gwb_path)}, av={len(av_path)}")
        if len(gwb_path) != len(ages):
            raise ValueError(f"Path lengths must match: gwb={len(gwb_path)}, ages={len(ages)}")

        n_steps = len(gwb_path)
        withdrawals = np.zeros(n_steps)

        for t in range(n_steps):
            if t < first_withdrawal_year:
                withdrawals[t] = 0.0
                continue

            duration = start_duration + t

            result = self.calculate_withdrawal(
                gwb=gwb_path[t],
                av=av_path[t],
                withdrawal_rate=withdrawal_rate,
                duration=duration,
                age=int(ages[t]),
            )
            withdrawals[t] = result.withdrawal_amount

        return withdrawals

    def get_utilization_profile(
        self,
        start_age: int,
        start_duration: int = 1,
        years: int = 15,
        moneyness: float = 1.0,
    ) -> dict:
        """
        Generate utilization profile over time.

        Parameters
        ----------
        start_age : int
            Age at start
        start_duration : int
            Duration at start
        years : int
            Number of years to project
        moneyness : float
            Fixed moneyness assumption

        Returns
        -------
        dict
            Mapping of year to utilization rate
        """
        from annuity_pricing.behavioral.calibration import combined_utilization

        profile = {}
        for t in range(years):
            duration = start_duration + t
            age = start_age + t
            util = combined_utilization(
                duration=duration,
                age=age,
                moneyness=moneyness,
                combination_method=self.assumptions.combination_method,
            )
            profile[t] = min(util, self.assumptions.max_utilization)

        return profile

    @property
    def calibration_source(self) -> UtilizationCalibration:
        """Return the calibration data source."""
        return self._calibration_source
