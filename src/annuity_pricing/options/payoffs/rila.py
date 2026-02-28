"""
RILA (Registered Index-Linked Annuity) protection payoffs.

Implements payoffs for RILA protection mechanisms:
- Buffer: Absorbs first X% of losses (insurer takes first hit)
- Floor: Limits maximum loss to X% (policyholder never loses more than X%)

See: METHODOLOGY.md Section 3.2
See: docs/knowledge/domain/buffer_floor.md

[T1] Buffer and Floor are fundamentally different protection mechanisms.
[T1] Buffer = long ATM put - short OTM put (put spread)
[T1] Floor = long OTM put at floor strike
"""

import numpy as np

from annuity_pricing.options.payoffs.base import (
    BasePayoff,
    CreditingMethod,
    IndexPath,
    PayoffResult,
)


class BufferPayoff(BasePayoff):
    """
    Buffer protection crediting method.

    [T1] Buffer absorbs the FIRST X% of index losses.
    - Positive returns: Full upside (subject to cap if specified)
    - Negative returns: Insurer absorbs first buffer_rate%, then dollar-for-dollar

    Payoff formula:
    - If index_return >= 0: min(index_return, cap) if cap else index_return
    - If index_return < 0: max(index_return + buffer_rate, floor_rate)

    Parameters
    ----------
    buffer_rate : float
        Buffer percentage (decimal, e.g., 0.10 = 10% buffer)
    cap_rate : float, optional
        Maximum return cap (decimal)
    floor_rate : float, optional
        Absolute minimum return (typically None for buffer products)

    Examples
    --------
    >>> payoff = BufferPayoff(buffer_rate=0.10)  # 10% buffer
    >>> # Index down 8% → 0% credited (buffer absorbs all)
    >>> payoff.calculate(-0.08).credited_return
    0.0
    >>> # Index down 15% → -5% credited (buffer absorbs first 10%)
    >>> payoff.calculate(-0.15).credited_return
    -0.05
    >>> # Index up 12% → 12% credited (full upside)
    >>> payoff.calculate(0.12).credited_return
    0.12

    Notes
    -----
    Buffer products typically have higher caps than FIA products because
    the policyholder bears some downside risk.

    Replication: Buffer ≈ Long ATM put - Short OTM put (put spread)
    """

    def __init__(
        self,
        buffer_rate: float,
        cap_rate: float | None = None,
        floor_rate: float | None = None,
    ):
        if buffer_rate <= 0:
            raise ValueError(f"CRITICAL: buffer_rate must be > 0, got {buffer_rate}")
        if buffer_rate > 1:
            raise ValueError(f"CRITICAL: buffer_rate must be <= 1 (100%), got {buffer_rate}")
        if cap_rate is not None and cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0 if provided, got {cap_rate}")

        self.buffer_rate = buffer_rate
        self.cap_rate = cap_rate
        self.floor_rate = floor_rate  # Absolute floor (rare for buffers)
        self.method = CreditingMethod.BUFFER

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate buffer payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with buffer protection applied
        """
        cap_applied = False
        floor_applied = False
        buffer_applied = False

        if index_return >= 0:
            # Positive return: full upside (subject to cap)
            credited_return = index_return
            if self.cap_rate is not None and credited_return > self.cap_rate:
                credited_return = self.cap_rate
                cap_applied = True
        else:
            # Negative return: buffer absorbs first X%
            # Example: -15% return with 10% buffer → -15% + 10% = -5%
            credited_return = index_return + self.buffer_rate
            buffer_applied = True

            # Can't be better than 0% from buffer alone
            if credited_return > 0:
                credited_return = 0.0

        # Apply absolute floor if specified (rare)
        if self.floor_rate is not None and credited_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "buffer_rate": self.buffer_rate,
                "cap_rate": self.cap_rate,
                "floor_rate": self.floor_rate,
                "buffer_applied": buffer_applied,
                "buffer_benefit": min(self.buffer_rate, -index_return) if index_return < 0 else 0.0,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized buffer payoff calculation.

        [T1] Buffer absorbs first X% of losses.

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        # Start with index returns
        credited = index_returns.copy()

        # For negative returns: add buffer, cap at 0
        negative_mask = index_returns < 0
        credited[negative_mask] = np.minimum(0.0, index_returns[negative_mask] + self.buffer_rate)

        # Apply cap on positive returns
        if self.cap_rate is not None:
            positive_mask = index_returns >= 0
            credited[positive_mask] = np.minimum(credited[positive_mask], self.cap_rate)

        # Apply absolute floor if specified
        if self.floor_rate is not None:
            credited = np.maximum(credited, self.floor_rate)

        return credited


class FloorPayoff(BasePayoff):
    """
    Floor protection crediting method.

    [T1] Floor limits MAXIMUM loss to X%.
    - Positive returns: Full upside (subject to cap if specified)
    - Negative returns: Dollar-for-dollar loss until floor, then protected

    Payoff formula:
    - If index_return >= floor_rate: min(index_return, cap) if cap else index_return
    - If index_return < floor_rate: floor_rate

    Parameters
    ----------
    floor_rate : float
        Maximum loss percentage (decimal, e.g., -0.10 = -10% floor)
        Note: Should be negative for loss protection
    cap_rate : float, optional
        Maximum return cap (decimal)

    Examples
    --------
    >>> payoff = FloorPayoff(floor_rate=-0.10)  # -10% floor
    >>> # Index down 8% → -8% credited (no protection yet)
    >>> payoff.calculate(-0.08).credited_return
    -0.08
    >>> # Index down 15% → -10% credited (floored)
    >>> payoff.calculate(-0.15).credited_return
    -0.10
    >>> # Index up 12% → 12% credited (full upside)
    >>> payoff.calculate(0.12).credited_return
    0.12

    Notes
    -----
    Floor products typically have lower caps than buffer products because
    they provide more tail risk protection.

    Replication: Floor ≈ Long OTM put at (1 + floor_rate) strike
    """

    def __init__(
        self,
        floor_rate: float,
        cap_rate: float | None = None,
    ):
        if floor_rate > 0:
            raise ValueError(
                f"CRITICAL: floor_rate should be <= 0 for loss protection, got {floor_rate}. "
                f"Use negative values (e.g., -0.10 for -10% floor)."
            )
        if floor_rate < -1:
            raise ValueError(f"CRITICAL: floor_rate cannot be < -1 (-100%), got {floor_rate}")
        if cap_rate is not None and cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0 if provided, got {cap_rate}")

        self.floor_rate = floor_rate
        self.cap_rate = cap_rate
        self.method = CreditingMethod.FLOOR

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate floor payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with floor protection applied
        """
        cap_applied = False
        floor_applied = False

        # Apply floor protection
        if index_return < self.floor_rate:
            credited_return = self.floor_rate
            floor_applied = True
        else:
            credited_return = index_return

        # Apply cap if specified
        if self.cap_rate is not None and credited_return > self.cap_rate:
            credited_return = self.cap_rate
            cap_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "floor_rate": self.floor_rate,
                "cap_rate": self.cap_rate,
                "floor_benefit": self.floor_rate - index_return if floor_applied else 0.0,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)

    def calculate_vectorized(self, index_returns: np.ndarray) -> np.ndarray:
        """
        Vectorized floor payoff calculation.

        [T1] Floor limits maximum loss to X%.

        Parameters
        ----------
        index_returns : np.ndarray
            Array of raw index returns (decimal)

        Returns
        -------
        np.ndarray
            Array of credited returns
        """
        # Apply floor protection
        credited = np.maximum(index_returns, self.floor_rate)

        # Apply cap if specified
        if self.cap_rate is not None:
            credited = np.minimum(credited, self.cap_rate)

        return credited


class BufferWithFloorPayoff(BasePayoff):
    """
    Combined buffer and floor protection.

    Some RILA products offer both mechanisms:
    - Buffer absorbs first X% of losses
    - Floor provides backstop at Y%

    Parameters
    ----------
    buffer_rate : float
        Buffer percentage (decimal, e.g., 0.10 = 10% buffer)
    floor_rate : float
        Absolute maximum loss (decimal, e.g., -0.20 = -20% max loss)
    cap_rate : float, optional
        Maximum return cap

    Examples
    --------
    >>> payoff = BufferWithFloorPayoff(buffer_rate=0.10, floor_rate=-0.20)
    >>> # Index down 8% → 0% (buffer absorbs)
    >>> payoff.calculate(-0.08).credited_return
    0.0
    >>> # Index down 25% → -15% → floored to -20%? No: -25% + 10% = -15%
    >>> payoff.calculate(-0.25).credited_return
    -0.15
    >>> # Index down 35% → -25% → but floored to -20%
    >>> payoff.calculate(-0.35).credited_return
    -0.20
    """

    def __init__(
        self,
        buffer_rate: float,
        floor_rate: float,
        cap_rate: float | None = None,
    ):
        if buffer_rate <= 0:
            raise ValueError(f"CRITICAL: buffer_rate must be > 0, got {buffer_rate}")
        if floor_rate > 0:
            raise ValueError(
                f"CRITICAL: floor_rate should be <= 0 for loss protection, got {floor_rate}"
            )
        if cap_rate is not None and cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0 if provided, got {cap_rate}")

        self.buffer_rate = buffer_rate
        self.floor_rate = floor_rate
        self.cap_rate = cap_rate
        self.method = CreditingMethod.BUFFER  # Primary mechanism

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate combined buffer + floor payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with both protections applied
        """
        cap_applied = False
        floor_applied = False
        buffer_applied = False

        if index_return >= 0:
            # Positive return: full upside (subject to cap)
            credited_return = index_return
            if self.cap_rate is not None and credited_return > self.cap_rate:
                credited_return = self.cap_rate
                cap_applied = True
        else:
            # Negative return: apply buffer first
            credited_return = index_return + self.buffer_rate
            buffer_applied = True

            # Can't be better than 0% from buffer alone
            if credited_return > 0:
                credited_return = 0.0

            # Apply floor as backstop
            if credited_return < self.floor_rate:
                credited_return = self.floor_rate
                floor_applied = True

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=floor_applied,
            details={
                "buffer_rate": self.buffer_rate,
                "floor_rate": self.floor_rate,
                "cap_rate": self.cap_rate,
                "buffer_applied": buffer_applied,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)


class StepRateBufferPayoff(BasePayoff):
    """
    Step-rate buffer protection (tiered buffer).

    Some RILAs have tiered buffers:
    - First tier: 100% protection up to X%
    - Second tier: Partial protection from X% to Y%

    Parameters
    ----------
    tier1_buffer : float
        First tier buffer (100% protection, e.g., 0.10 = first 10%)
    tier2_buffer : float
        Second tier buffer (additional protection, e.g., 0.05 = next 5%)
    tier2_protection : float
        Protection rate in tier 2 (e.g., 0.50 = 50% of losses absorbed)
    cap_rate : float, optional
        Maximum return cap

    Examples
    --------
    >>> # 10% full buffer + 50% protection on next 10%
    >>> payoff = StepRateBufferPayoff(
    ...     tier1_buffer=0.10,
    ...     tier2_buffer=0.10,
    ...     tier2_protection=0.50
    ... )
    >>> # Index down 8% → 0% (within tier 1)
    >>> payoff.calculate(-0.08).credited_return
    0.0
    >>> # Index down 15% → tier 1 absorbs 10%, tier 2 absorbs 50% of next 5% = 2.5%
    >>> # Result: -15% + 10% + 2.5% = -2.5%
    >>> payoff.calculate(-0.15).credited_return
    -0.025
    """

    def __init__(
        self,
        tier1_buffer: float,
        tier2_buffer: float,
        tier2_protection: float,
        cap_rate: float | None = None,
    ):
        if tier1_buffer <= 0:
            raise ValueError(f"CRITICAL: tier1_buffer must be > 0, got {tier1_buffer}")
        if tier2_buffer < 0:
            raise ValueError(f"CRITICAL: tier2_buffer must be >= 0, got {tier2_buffer}")
        if not 0 <= tier2_protection <= 1:
            raise ValueError(
                f"CRITICAL: tier2_protection must be in [0, 1], got {tier2_protection}"
            )

        self.tier1_buffer = tier1_buffer
        self.tier2_buffer = tier2_buffer
        self.tier2_protection = tier2_protection
        self.cap_rate = cap_rate
        self.method = CreditingMethod.BUFFER

    def calculate(self, index_return: float) -> PayoffResult:
        """
        Calculate step-rate buffer payoff.

        Parameters
        ----------
        index_return : float
            Raw index return (decimal)

        Returns
        -------
        PayoffResult
            Credited return with tiered buffer applied
        """
        cap_applied = False
        buffer_applied = False

        if index_return >= 0:
            # Positive return: full upside (subject to cap)
            credited_return = index_return
            if self.cap_rate is not None and credited_return > self.cap_rate:
                credited_return = self.cap_rate
                cap_applied = True
        else:
            loss = -index_return  # Convert to positive for easier calculation
            buffer_applied = True

            # Tier 1: 100% protection (absorbs first tier1_buffer% of losses)
            tier1_absorption = min(loss, self.tier1_buffer)

            # Remaining loss after tier 1
            loss_after_tier1 = max(0, loss - self.tier1_buffer)

            # Tier 2: Partial protection (absorbs tier2_protection% of next tier2_buffer%)
            tier2_loss_applicable = min(loss_after_tier1, self.tier2_buffer)
            tier2_absorption = tier2_loss_applicable * self.tier2_protection

            # Beyond tier 2: dollar-for-dollar (no protection)
            beyond_tier2_loss = max(0, loss_after_tier1 - self.tier2_buffer)

            # Total policyholder loss = unprotected portion of tier 2 + beyond tier 2
            policyholder_loss = (
                tier2_loss_applicable * (1 - self.tier2_protection) + beyond_tier2_loss
            )

            credited_return = -policyholder_loss

            # Can't be better than 0%
            if credited_return > 0:
                credited_return = 0.0

        return PayoffResult(
            credited_return=credited_return,
            index_return=index_return,
            cap_applied=cap_applied,
            floor_applied=False,
            details={
                "tier1_buffer": self.tier1_buffer,
                "tier2_buffer": self.tier2_buffer,
                "tier2_protection": self.tier2_protection,
                "cap_rate": self.cap_rate,
                "buffer_applied": buffer_applied,
                "method": self.method.value,
            },
        )

    def calculate_from_path(self, path: IndexPath) -> PayoffResult:
        """Calculate from index path using point-to-point return."""
        return self.calculate(path.total_return)


def create_rila_payoff(
    protection_type: str,
    buffer_rate: float | None = None,
    floor_rate: float | None = None,
    cap_rate: float | None = None,
) -> BasePayoff:
    """
    Factory function to create RILA payoff from parameters.

    Parameters
    ----------
    protection_type : str
        Protection type: 'buffer', 'floor', or 'buffer_floor'
    buffer_rate : float, optional
        Buffer rate (required for 'buffer' and 'buffer_floor')
    floor_rate : float, optional
        Floor rate (required for 'floor' and 'buffer_floor')
    cap_rate : float, optional
        Cap rate

    Returns
    -------
    BasePayoff
        Configured RILA payoff object

    Raises
    ------
    ValueError
        If required parameters missing for protection type
    """
    protection_type = protection_type.lower()

    if protection_type == "buffer":
        if buffer_rate is None:
            raise ValueError("CRITICAL: buffer_rate required for 'buffer' protection")
        return BufferPayoff(buffer_rate=buffer_rate, cap_rate=cap_rate, floor_rate=floor_rate)

    elif protection_type == "floor":
        if floor_rate is None:
            raise ValueError("CRITICAL: floor_rate required for 'floor' protection")
        return FloorPayoff(floor_rate=floor_rate, cap_rate=cap_rate)

    elif protection_type == "buffer_floor":
        if buffer_rate is None:
            raise ValueError("CRITICAL: buffer_rate required for 'buffer_floor' protection")
        if floor_rate is None:
            raise ValueError("CRITICAL: floor_rate required for 'buffer_floor' protection")
        return BufferWithFloorPayoff(
            buffer_rate=buffer_rate, floor_rate=floor_rate, cap_rate=cap_rate
        )

    else:
        raise ValueError(
            f"CRITICAL: Unknown protection type '{protection_type}'. "
            f"Valid types: buffer, floor, buffer_floor"
        )


def compare_buffer_vs_floor(
    buffer_rate: float,
    floor_rate: float,
    index_returns: np.ndarray,
    cap_rate: float | None = None,
) -> dict:
    """
    Compare buffer vs floor protection across a range of index returns.

    Useful for understanding the tradeoffs between protection mechanisms.

    Parameters
    ----------
    buffer_rate : float
        Buffer percentage (e.g., 0.10 for 10%)
    floor_rate : float
        Floor percentage (e.g., -0.10 for -10%)
    index_returns : np.ndarray
        Array of index returns to evaluate
    cap_rate : float, optional
        Cap rate for both products

    Returns
    -------
    dict
        Comparison results with credited returns for each mechanism
    """
    buffer_payoff = BufferPayoff(buffer_rate=buffer_rate, cap_rate=cap_rate)
    floor_payoff = FloorPayoff(floor_rate=floor_rate, cap_rate=cap_rate)

    buffer_credits = np.array([buffer_payoff.calculate(r).credited_return for r in index_returns])
    floor_credits = np.array([floor_payoff.calculate(r).credited_return for r in index_returns])

    return {
        "index_returns": index_returns,
        "buffer_credits": buffer_credits,
        "floor_credits": floor_credits,
        "buffer_better": buffer_credits > floor_credits,
        "floor_better": floor_credits > buffer_credits,
        "same": np.isclose(buffer_credits, floor_credits),
        "buffer_rate": buffer_rate,
        "floor_rate": floor_rate,
        "cap_rate": cap_rate,
    }
