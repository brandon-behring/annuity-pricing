"""
GLWB Withdrawal Utilization Model - Phase 7.

Models policyholder withdrawal behavior for GLWB products.
Tracks actual vs maximum allowed withdrawals.

Theory
------
[T1] Utilization rate = Actual Withdrawal / Maximum Allowed Withdrawal

Empirical patterns (from LIMRA/SOA studies):
- Average utilization: 60-80%
- Higher utilization for older ages
- Lower utilization early in contract

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


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
            raise ValueError(
                f"Path lengths must match: gwb={len(gwb_path)}, ages={len(ages)}"
            )

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
