"""
Dynamic Lapse Model - Phase 7.

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

See: docs/knowledge/domain/dynamic_lapse.md
See: docs/references/L3/bauer_kling_russ_2008.md (Section 4)
"""

from dataclasses import dataclass
from typing import Callable, Optional
import numpy as np


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
        adjustment_factor = moneyness ** self.assumptions.sensitivity

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
            raise ValueError(
                f"Path lengths must match: gwb={len(gwb_path)}, av={len(av_path)}"
            )

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
