"""
Base classes for option payoffs.

Provides abstract base for all option payoff calculations.
See: METHODOLOGY.md Section 3
See: docs/knowledge/domain/option_pricing.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import numpy as np


class OptionType(Enum):
    """Option type enumeration."""

    CALL = "call"
    PUT = "put"


class CreditingMethod(Enum):
    """FIA/RILA crediting method enumeration."""

    # FIA methods
    CAP = "cap"  # Point-to-point with cap
    PARTICIPATION = "participation"  # Participation rate
    SPREAD = "spread"  # Spread/margin deduction
    TRIGGER = "trigger"  # Performance triggered

    # RILA methods
    BUFFER = "buffer"  # Buffer absorbs first X% losses
    FLOOR = "floor"  # Floor limits max loss to X%


@dataclass(frozen=True)
class IndexPath:
    """
    Immutable index price path for simulation.

    Attributes
    ----------
    times : np.ndarray
        Time points (years from start)
    values : np.ndarray
        Index values at each time point
    initial_value : float
        Starting index value
    """

    times: tuple[float, ...]
    values: tuple[float, ...]
    initial_value: float

    def __post_init__(self) -> None:
        """Validate path."""
        if len(self.times) != len(self.values):
            raise ValueError(
                f"CRITICAL: times and values must have same length. "
                f"Got times={len(self.times)}, values={len(self.values)}"
            )
        if len(self.times) == 0:
            raise ValueError("CRITICAL: Path cannot be empty")

    @property
    def final_value(self) -> float:
        """Get final index value."""
        return self.values[-1]

    @property
    def total_return(self) -> float:
        """Calculate total return over the path."""
        return (self.final_value - self.initial_value) / self.initial_value

    @property
    def maturity(self) -> float:
        """Get path maturity in years."""
        return self.times[-1]

    @classmethod
    def from_arrays(
        cls,
        times: np.ndarray,
        values: np.ndarray,
        initial_value: float,
    ) -> "IndexPath":
        """Create IndexPath from numpy arrays."""
        return cls(
            times=tuple(float(t) for t in times),
            values=tuple(float(v) for v in values),
            initial_value=initial_value,
        )


@dataclass(frozen=True)
class PayoffResult:
    """
    Immutable payoff calculation result.

    Attributes
    ----------
    credited_return : float
        Return credited to policyholder (decimal)
    index_return : float
        Raw index return (decimal)
    cap_applied : bool
        Whether cap was applied
    floor_applied : bool
        Whether floor was applied
    details : dict
        Additional calculation details
    """

    credited_return: float
    index_return: float
    cap_applied: bool = False
    floor_applied: bool = False
    details: dict | None = None


class BasePayoff(ABC):
    """
    Abstract base class for option payoffs.

    All payoff implementations must:
    1. Implement calculate() method
    2. Return PayoffResult with credited return
    3. Never return credited_return < floor (typically 0 for FIA)

    [T1] FIA payoffs always have 0% floor (principal protection).
    [T1] RILA payoffs can have negative returns up to floor.
    """

    @abstractmethod
    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate payoff for given index return.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal, e.g., 0.10 = 10%)

        Returns
        -------
        PayoffResult
            Credited return and calculation details
        """
        pass

    @abstractmethod
    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """
        Calculate payoff from full index path.

        Used for path-dependent options (e.g., monthly averaging).

        Parameters
        ----------
        path : IndexPath
            Full index price path

        Returns
        -------
        PayoffResult
            Credited return and calculation details
        """
        pass

    def supports_vectorized(self) -> bool:
        """
        Check if this payoff supports vectorized calculation.

        Vectorized calculation provides significant performance benefits
        for Monte Carlo simulation. Path-dependent payoffs (e.g., monthly
        averaging) should override this to return False.

        Returns
        -------
        bool
            True if calculate_vectorized() is available
        """
        return True

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Calculate payoffs for multiple index returns simultaneously.

        Vectorized implementation for Monte Carlo performance.
        Must produce identical results to calling calculate() in a loop.

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns (same shape as input)

        Raises
        ------
        NotImplementedError
            If vectorized calculation not implemented for this payoff
        """
        raise NotImplementedError(
            f"calculate_vectorized() not implemented for {type(self).__name__}. "
            f"Use calculate() in a loop or check supports_vectorized() first."
        )


class VanillaOption:
    """
    Vanilla European option payoff.

    [T1] Call payoff: max(S - K, 0)
    [T1] Put payoff: max(K - S, 0)

    Parameters
    ----------
    strike : float
        Strike price
    option_type : OptionType
        Call or put
    """

    def __init__(self, strike: float, option_type: OptionType):
        if strike <= 0:
            raise ValueError(f"CRITICAL: strike must be > 0, got {strike}")

        self.strike = strike
        self.option_type = option_type

    def payoff(self, spot: float) -> float:
        """
        Calculate option payoff at expiry.

        Parameters
        ----------
        spot : float
            Spot price at expiry

        Returns
        -------
        float
            Option payoff (intrinsic value)
        """
        if spot < 0:
            raise ValueError(f"CRITICAL: spot must be >= 0, got {spot}")

        if self.option_type == OptionType.CALL:
            return max(spot - self.strike, 0.0)
        else:
            return max(self.strike - spot, 0.0)

    def payoff_return(self, spot: float, initial_spot: float) -> float:
        """
        Calculate payoff as return on initial investment.

        Parameters
        ----------
        spot : float
            Spot price at expiry
        initial_spot : float
            Initial spot price

        Returns
        -------
        float
            Payoff as decimal return
        """
        return self.payoff(spot) / initial_spot


def calculate_moneyness(spot: float, strike: float) -> float:
    """
    Calculate option moneyness.

    [T1] Moneyness = S/K

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price

    Returns
    -------
    float
        Moneyness ratio
    """
    if strike <= 0:
        raise ValueError(f"CRITICAL: strike must be > 0, got {strike}")
    return spot / strike


def is_in_the_money(spot: float, strike: float, option_type: OptionType) -> bool:
    """
    Check if option is in the money.

    [T1] Call ITM: S > K
    [T1] Put ITM: S < K

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    option_type : OptionType
        Call or put

    Returns
    -------
    bool
        True if option is ITM
    """
    if option_type == OptionType.CALL:
        return spot > strike
    else:
        return spot < strike
