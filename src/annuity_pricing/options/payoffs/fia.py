"""
FIA (Fixed Indexed Annuity) crediting payoffs.

Implements payoffs for FIA crediting methods:
- Cap: Point-to-point with maximum return cap
- Participation: Partial participation in index returns
- Spread: Index return minus spread/margin
- Trigger: Performance triggered bonus

See: CONSTITUTION.md Section 3.2
See: docs/knowledge/domain/crediting_methods.md

[T1] All FIA payoffs have 0% floor (principal protection).
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from annuity_pricing.options.payoffs.base import (
    BasePayoff,
    CreditingMethod,
    IndexPath,
    PayoffResult,
)


class CappedCallPayoff(BasePayoff):
    """
    Point-to-point with cap crediting method.

    [T1] Payoff = max(0, min(index_return, cap))

    Parameters
    ----------
    cap_rate : float
        Maximum return cap (decimal, e.g., 0.10 = 10% cap)
    floor_rate : float, default 0.0
        Minimum return floor (typically 0% for principal protection)

    Examples
    --------
    >>> payoff = CappedCallPayoff(cap_rate=0.10)
    >>> result = payoff.calculate(0.15)  # 15% index return
    >>> result.credited_return
    0.10  # Capped at 10%
    """

    def __init__(self, cap_rate: float, floor_rate: float = 0.0):
        if cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0, got {cap_rate}")
        if floor_rate > cap_rate:
            raise ValueError(
                f"CRITICAL: floor_rate ({floor_rate}) cannot exceed cap_rate ({cap_rate})"
            )

        self.cap_rate = cap_rate
        self.floor_rate = floor_rate
        self.method = CreditingMethod.CAP

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate capped call payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with cap/floor applied
        """
        cap_applied = False
        floor_applied = False

        # Apply floor first (principal protection)
        if index_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True
        # Apply cap
        elif index_return > self.cap_rate:
            credited_return = self.cap_rate
            cap_applied = True
        else:
            credited_return = index_return

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "cap_rate": self.cap_rate,
                "floor_rate": self.floor_rate,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized capped call payoff calculation.

        [T1] Payoff = max(floor, min(index_return, cap))

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        # np.clip handles both floor and cap efficiently
        return np.clip(index_returns, self.floor_rate, self.cap_rate)


class ParticipationPayoff(BasePayoff):
    """
    Participation rate crediting method.

    [T1] Payoff = max(floor, participation_rate × max(0, index_return))

    Parameters
    ----------
    participation_rate : float
        Participation rate (decimal, e.g., 0.80 = 80% participation)
    floor_rate : float, default 0.0
        Minimum return floor
    cap_rate : float, optional
        Optional maximum cap

    Examples
    --------
    >>> payoff = ParticipationPayoff(participation_rate=0.80)
    >>> result = payoff.calculate(0.10)  # 10% index return
    >>> result.credited_return
    0.08  # 80% of 10%
    """

    def __init__(
        self,
        participation_rate: float,
        floor_rate: float = 0.0,
        cap_rate: Optional[float] = None,
    ):
        if participation_rate <= 0:
            raise ValueError(
                f"CRITICAL: participation_rate must be > 0, got {participation_rate}"
            )
        if cap_rate is not None and cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0 if provided, got {cap_rate}")

        self.participation_rate = participation_rate
        self.floor_rate = floor_rate
        self.cap_rate = cap_rate
        self.method = CreditingMethod.PARTICIPATION

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate participation payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with participation applied
        """
        cap_applied = False
        floor_applied = False

        # Apply participation to positive returns only
        if index_return > 0:
            credited_return = self.participation_rate * index_return
        else:
            credited_return = 0.0
            floor_applied = True

        # Apply cap if specified
        if self.cap_rate is not None and credited_return > self.cap_rate:
            credited_return = self.cap_rate
            cap_applied = True

        # Apply floor
        if credited_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "participation_rate": self.participation_rate,
                "cap_rate": self.cap_rate,
                "floor_rate": self.floor_rate,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized participation payoff calculation.

        [T1] Payoff = max(floor, min(cap, participation × max(0, return)))

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        # Apply participation to positive returns only
        credited = np.where(
            index_returns > 0,
            self.participation_rate * index_returns,
            0.0
        )

        # Apply cap if specified
        if self.cap_rate is not None:
            credited = np.minimum(credited, self.cap_rate)

        # Apply floor
        credited = np.maximum(credited, self.floor_rate)

        return credited


class SpreadPayoff(BasePayoff):
    """
    Spread/margin crediting method.

    [T1] Payoff = max(floor, index_return - spread)

    Parameters
    ----------
    spread_rate : float
        Spread/margin deducted from return (decimal, e.g., 0.02 = 2% spread)
    floor_rate : float, default 0.0
        Minimum return floor
    cap_rate : float, optional
        Optional maximum cap

    Examples
    --------
    >>> payoff = SpreadPayoff(spread_rate=0.02)
    >>> result = payoff.calculate(0.10)  # 10% index return
    >>> result.credited_return
    0.08  # 10% - 2% spread
    """

    def __init__(
        self,
        spread_rate: float,
        floor_rate: float = 0.0,
        cap_rate: Optional[float] = None,
    ):
        if spread_rate < 0:
            raise ValueError(f"CRITICAL: spread_rate must be >= 0, got {spread_rate}")

        self.spread_rate = spread_rate
        self.floor_rate = floor_rate
        self.cap_rate = cap_rate
        self.method = CreditingMethod.SPREAD

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate spread payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with spread applied
        """
        cap_applied = False
        floor_applied = False

        # Spread only applies to positive returns
        if index_return > 0:
            credited_return = index_return - self.spread_rate
        else:
            credited_return = 0.0

        # Apply cap if specified
        if self.cap_rate is not None and credited_return > self.cap_rate:
            credited_return = self.cap_rate
            cap_applied = True

        # Apply floor
        if credited_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "spread_rate": self.spread_rate,
                "cap_rate": self.cap_rate,
                "floor_rate": self.floor_rate,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized spread payoff calculation.

        [T1] Payoff = max(floor, min(cap, return - spread)) for positive returns

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        # Spread only applies to positive returns
        credited = np.where(
            index_returns > 0,
            index_returns - self.spread_rate,
            0.0
        )

        # Apply cap if specified
        if self.cap_rate is not None:
            credited = np.minimum(credited, self.cap_rate)

        # Apply floor
        credited = np.maximum(credited, self.floor_rate)

        return credited


class TriggerPayoff(BasePayoff):
    """
    Performance triggered crediting method.

    [T1] Payoff = trigger_rate if index_return >= trigger_threshold, else floor

    Parameters
    ----------
    trigger_rate : float
        Fixed return if trigger condition met (decimal)
    trigger_threshold : float, default 0.0
        Minimum return needed to trigger bonus
    floor_rate : float, default 0.0
        Return if trigger not met

    Examples
    --------
    >>> payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0)
    >>> result = payoff.calculate(0.001)  # Small positive return
    >>> result.credited_return
    0.05  # Trigger met, get 5%
    """

    def __init__(
        self,
        trigger_rate: float,
        trigger_threshold: float = 0.0,
        floor_rate: float = 0.0,
    ):
        if trigger_rate < 0:
            raise ValueError(f"CRITICAL: trigger_rate must be >= 0, got {trigger_rate}")

        self.trigger_rate = trigger_rate
        self.trigger_threshold = trigger_threshold
        self.floor_rate = floor_rate
        self.method = CreditingMethod.TRIGGER

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate trigger payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return based on trigger condition
        """
        floor_applied = False
        trigger_met = index_return >= self.trigger_threshold

        if trigger_met:
            credited_return = self.trigger_rate
        else:
            credited_return = self.floor_rate
            floor_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=False,
            floor_applied=floor_applied,
            details={
                "trigger_rate": self.trigger_rate,
                "trigger_threshold": self.trigger_threshold,
                "floor_rate": self.floor_rate,
                "trigger_met": trigger_met,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized trigger payoff calculation.

        [T1] Payoff = trigger_rate if return >= threshold, else floor

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        return np.where(
            index_returns >= self.trigger_threshold,
            self.trigger_rate,
            self.floor_rate
        )


class MonthlyAveragePayoff(BasePayoff):
    """
    Monthly averaging crediting method.

    Uses average of monthly returns instead of point-to-point.
    Reduces volatility but typically has higher cap.

    Note: This payoff is path-dependent and does NOT support vectorized
    calculation. Use calculate_from_path() for accurate monthly averaging.

    Parameters
    ----------
    cap_rate : float
        Maximum return cap
    floor_rate : float, default 0.0
        Minimum return floor
    """

    def __init__(self, cap_rate: float, floor_rate: float = 0.0):
        if cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0, got {cap_rate}")

        self.cap_rate = cap_rate
        self.floor_rate = floor_rate

    def supports_vectorized(self) -> bool:
        """Monthly averaging is path-dependent; vectorized not supported."""
        return False

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate using simple return (for point-to-point fallback).

        For monthly averaging, use calculate_from_path instead.
        """
        cap_applied = False
        floor_applied = False

        if index_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True
        elif index_return > self.cap_rate:
            credited_return = self.cap_rate
            cap_applied = True
        else:
            credited_return = index_return

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={"cap_rate": self.cap_rate, "floor_rate": self.floor_rate},
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """
        Calculate using monthly averaging.

        Parameters
        ----------
        path : IndexPath
            Full index path with monthly observations

        Returns
        -------
        PayoffResult
            Credited return using average
        """
        if len(path.values) < 2:
            return self.calculate(path.total_return)

        # Calculate average of monthly index levels
        avg_value = np.mean(path.values)
        avg_return = (avg_value - path.initial_value) / path.initial_value

        return self.calculate(avg_return)


def create_fia_payoff(
    method: str,
    cap_rate: Optional[float] = None,
    participation_rate: Optional[float] = None,
    spread_rate: Optional[float] = None,
    trigger_rate: Optional[float] = None,
    floor_rate: float = 0.0,
) -> BasePayoff:
    """
    Factory function to create FIA payoff from parameters.

    Parameters
    ----------
    method : str
        Crediting method: 'cap', 'participation', 'spread', 'trigger'
    cap_rate : float, optional
        Cap rate (required for 'cap' method)
    participation_rate : float, optional
        Participation rate (required for 'participation' method)
    spread_rate : float, optional
        Spread rate (required for 'spread' method)
    trigger_rate : float, optional
        Trigger rate (required for 'trigger' method)
    floor_rate : float, default 0.0
        Floor rate

    Returns
    -------
    BasePayoff
        Configured payoff object

    Raises
    ------
    ValueError
        If required parameters missing for method
    """
    method = method.lower()

    if method == "cap":
        if cap_rate is None:
            raise ValueError("CRITICAL: cap_rate required for 'cap' method")
        return CappedCallPayoff(cap_rate=cap_rate, floor_rate=floor_rate)

    elif method == "participation":
        if participation_rate is None:
            raise ValueError("CRITICAL: participation_rate required for 'participation' method")
        return ParticipationPayoff(
            participation_rate=participation_rate,
            floor_rate=floor_rate,
            cap_rate=cap_rate,
        )

    elif method == "spread":
        if spread_rate is None:
            raise ValueError("CRITICAL: spread_rate required for 'spread' method")
        return SpreadPayoff(
            spread_rate=spread_rate,
            floor_rate=floor_rate,
            cap_rate=cap_rate,
        )

    elif method == "trigger":
        if trigger_rate is None:
            raise ValueError("CRITICAL: trigger_rate required for 'trigger' method")
        return TriggerPayoff(
            trigger_rate=trigger_rate,
            floor_rate=floor_rate,
        )

    elif method == "monthly_average":
        # [F.3] Monthly averaging support
        if cap_rate is None:
            raise ValueError("CRITICAL: cap_rate required for 'monthly_average' method")
        return MonthlyAveragePayoff(
            cap_rate=cap_rate,
            floor_rate=floor_rate,
        )

    else:
        raise ValueError(
            f"CRITICAL: Unknown crediting method '{method}'. "
            f"Valid methods: cap, participation, spread, trigger, monthly_average"
        )
