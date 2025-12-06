"""
Rollup and Ratchet Mechanics - Phase 8.

Implements GWB growth mechanisms:
- Simple rollup: GWB(t) = GWB(0) × (1 + r×t)
- Compound rollup: GWB(t) = GWB(0) × (1 + r)^t
- Ratchet: GWB(t) = max(GWB(t-1), AV(t))

Theory
------
[T1] Simple rollup: Linear growth from base
     GWB(t) = base × (1 + rate × years)

[T1] Compound rollup: Exponential growth from base
     GWB(t) = base × (1 + rate)^years

[T1] Ratchet: Lock in gains, never decrease
     GWB(t) = max(GWB(t-1), AV(t))

See: docs/knowledge/domain/glwb_mechanics.md
"""

from dataclasses import dataclass
from typing import Protocol
import numpy as np


class RollupMechanic(Protocol):
    """Protocol for rollup calculation."""

    def calculate(self, base: float, years: float, rate: float) -> float:
        """
        Calculate rolled-up value.

        Parameters
        ----------
        base : float
            Starting value (initial premium or GWB)
        years : float
            Years since rollup started
        rate : float
            Annual rollup rate (e.g., 0.05 for 5%)

        Returns
        -------
        float
            Rolled-up value
        """
        ...


class SimpleRollup:
    """
    Simple interest rollup.

    [T1] GWB(t) = base × (1 + rate × years)

    Examples
    --------
    >>> rollup = SimpleRollup()
    >>> rollup.calculate(100_000, 5, 0.05)
    125000.0  # $100k + 5 years × 5% = $125k
    """

    def calculate(self, base: float, years: float, rate: float) -> float:
        """
        Calculate simple rollup value.

        [T1] GWB(t) = base × (1 + rate × years)

        Parameters
        ----------
        base : float
            Starting value
        years : float
            Years since rollup started
        rate : float
            Annual rollup rate

        Returns
        -------
        float
            Rolled-up value
        """
        if base < 0:
            raise ValueError(f"Base cannot be negative, got {base}")
        if years < 0:
            raise ValueError(f"Years cannot be negative, got {years}")
        if rate < 0:
            raise ValueError(f"Rate cannot be negative, got {rate}")

        return base * (1 + rate * years)


class CompoundRollup:
    """
    Compound interest rollup.

    [T1] GWB(t) = base × (1 + rate)^years

    Examples
    --------
    >>> rollup = CompoundRollup()
    >>> rollup.calculate(100_000, 5, 0.05)
    127628.16  # $100k × 1.05^5 ≈ $127.6k
    """

    def calculate(self, base: float, years: float, rate: float) -> float:
        """
        Calculate compound rollup value.

        [T1] GWB(t) = base × (1 + rate)^years

        Parameters
        ----------
        base : float
            Starting value
        years : float
            Years since rollup started
        rate : float
            Annual rollup rate

        Returns
        -------
        float
            Rolled-up value
        """
        if base < 0:
            raise ValueError(f"Base cannot be negative, got {base}")
        if years < 0:
            raise ValueError(f"Years cannot be negative, got {years}")
        if rate < -1:
            raise ValueError(f"Rate cannot be less than -100%, got {rate}")

        return base * ((1 + rate) ** years)


class RatchetMechanic:
    """
    Ratchet (step-up) to high water mark.

    [T1] GWB(t) = max(GWB(t-1), AV(t))

    The ratchet locks in market gains by stepping up the GWB
    to the account value when AV exceeds GWB.

    Examples
    --------
    >>> ratchet = RatchetMechanic()
    >>> ratchet.apply_ratchet(100_000, 120_000)  # AV > GWB
    120000.0  # Step up to AV
    >>> ratchet.apply_ratchet(100_000, 80_000)   # AV < GWB
    100000.0  # Keep GWB (no step-down)
    """

    def apply_ratchet(self, gwb: float, av: float) -> float:
        """
        Apply ratchet to GWB.

        [T1] GWB_new = max(GWB, AV)

        Parameters
        ----------
        gwb : float
            Current GWB value
        av : float
            Current account value

        Returns
        -------
        float
            New GWB after ratchet
        """
        if gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb}")
        if av < 0:
            raise ValueError(f"AV cannot be negative, got {av}")

        return max(gwb, av)

    def apply_ratchet_path(
        self,
        gwb_start: float,
        av_path: np.ndarray,
        ratchet_frequency: int = 1,
    ) -> np.ndarray:
        """
        Apply ratchet along an AV path.

        Parameters
        ----------
        gwb_start : float
            Starting GWB value
        av_path : ndarray
            Path of account values
        ratchet_frequency : int
            How often ratchet applies (1 = every period)

        Returns
        -------
        ndarray
            GWB path after ratchets
        """
        if gwb_start < 0:
            raise ValueError(f"GWB cannot be negative, got {gwb_start}")

        n_steps = len(av_path)
        gwb_path = np.zeros(n_steps)
        gwb = gwb_start

        for t in range(n_steps):
            # Apply ratchet on frequency
            if t % ratchet_frequency == 0:
                gwb = self.apply_ratchet(gwb, av_path[t])
            gwb_path[t] = gwb

        return gwb_path


@dataclass(frozen=True)
class RollupResult:
    """
    Result of rollup calculation with breakdown.

    Attributes
    ----------
    rolled_up_value : float
        Final rolled-up value
    base_value : float
        Original base value
    rollup_amount : float
        Amount added by rollup
    years : float
        Years of rollup applied
    effective_rate : float
        Effective annual rate achieved
    """

    rolled_up_value: float
    base_value: float
    rollup_amount: float
    years: float
    effective_rate: float


def calculate_rollup_with_cap(
    base: float,
    years: float,
    rate: float,
    cap_years: int,
    rollup_type: str = "compound",
) -> RollupResult:
    """
    Calculate rollup with year cap.

    Many GLWB products cap rollup at 10 years.

    Parameters
    ----------
    base : float
        Starting value
    years : float
        Years since issue
    rate : float
        Annual rollup rate
    cap_years : int
        Maximum years rollup applies
    rollup_type : str
        "simple" or "compound"

    Returns
    -------
    RollupResult
        Rollup result with breakdown

    Examples
    --------
    >>> result = calculate_rollup_with_cap(100_000, 15, 0.05, 10, "compound")
    >>> result.years
    10.0  # Capped at 10
    >>> result.rolled_up_value  # Same as 10-year rollup
    162889.46
    """
    # Apply cap
    effective_years = min(years, cap_years)

    # Calculate rollup
    if rollup_type == "simple":
        mechanic = SimpleRollup()
    elif rollup_type == "compound":
        mechanic = CompoundRollup()
    else:
        raise ValueError(f"Unknown rollup type: {rollup_type}")

    rolled_up_value = mechanic.calculate(base, effective_years, rate)
    rollup_amount = rolled_up_value - base

    # Calculate effective annual rate
    if effective_years > 0:
        effective_rate = (rolled_up_value / base) ** (1 / effective_years) - 1
    else:
        effective_rate = 0.0

    return RollupResult(
        rolled_up_value=rolled_up_value,
        base_value=base,
        rollup_amount=rollup_amount,
        years=effective_years,
        effective_rate=effective_rate,
    )


def compare_rollup_methods(
    base: float,
    years: float,
    rate: float,
) -> dict:
    """
    Compare simple vs compound rollup.

    Useful for understanding product differences.

    Parameters
    ----------
    base : float
        Starting value
    years : float
        Years of rollup
    rate : float
        Annual rate

    Returns
    -------
    dict
        Comparison of methods

    Examples
    --------
    >>> compare_rollup_methods(100_000, 10, 0.05)
    {'simple': 150000.0, 'compound': 162889.46, 'difference': 12889.46, 'compound_advantage_pct': 8.59}
    """
    simple = SimpleRollup().calculate(base, years, rate)
    compound = CompoundRollup().calculate(base, years, rate)
    difference = compound - simple

    return {
        "simple": simple,
        "compound": compound,
        "difference": difference,
        "compound_advantage_pct": (difference / simple) * 100 if simple > 0 else 0.0,
    }
