"""
GWB (Guaranteed Withdrawal Base) Tracker - Phase 8.

Tracks the Guaranteed Withdrawal Base through:
- Rollup (simple or compound)
- Ratchet (step-up to AV high water mark)
- Reset (periodic comparison)

Theory
------
[T1] GWB is the base for calculating maximum allowed withdrawal:
    Max Withdrawal = GWB × Withdrawal Rate

The GWB evolves via:
- Rollup: GWB(t+1) = GWB(t) × (1 + rollup_rate)
- Ratchet: GWB(t) = max(GWB(t), AV(t)) on anniversary
- Reset: Periodic reset to max(GWB, AV) with restrictions

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md (Section 3)
"""

from dataclasses import dataclass, replace
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .rollup import SimpleRollup, CompoundRollup, RatchetMechanic


class RollupType(Enum):
    """Type of rollup applied to GWB."""
    SIMPLE = "simple"
    COMPOUND = "compound"
    NONE = "none"


@dataclass(frozen=True)
class GWBState:
    """
    Current state of the Guaranteed Withdrawal Base.

    Attributes
    ----------
    gwb : float
        Current GWB value
    av : float
        Current account value
    initial_premium : float
        Original premium (may be needed for some contracts)
    rollup_base : float
        Base for rollup calculation
    high_water_mark : float
        Highest AV achieved (for ratchet)
    years_since_issue : float
        Time since contract issue
    withdrawal_phase_started : bool
        Whether withdrawals have begun
    total_withdrawals : float
        Cumulative withdrawals taken
    """

    gwb: float
    av: float
    initial_premium: float
    rollup_base: float
    high_water_mark: float
    years_since_issue: float
    withdrawal_phase_started: bool
    total_withdrawals: float = 0.0


@dataclass(frozen=True)
class GWBConfig:
    """
    Configuration for GWB mechanics.

    Attributes
    ----------
    rollup_type : RollupType
        Simple, compound, or none
    rollup_rate : float
        Annual rollup rate (e.g., 0.05 for 5%)
    rollup_cap_years : int
        Maximum years rollup applies (e.g., 10)
    ratchet_enabled : bool
        Whether ratchet/step-up applies
    ratchet_frequency : int
        Years between ratchet opportunities
    withdrawal_rate : float
        Guaranteed withdrawal rate (e.g., 0.05 for 5%)
    fee_rate : float
        Annual fee as % of GWB or AV (e.g., 0.01 for 1%)
    fee_basis : str
        "gwb" or "av" - what fees are charged against
    """

    rollup_type: RollupType = RollupType.COMPOUND
    rollup_rate: float = 0.05
    rollup_cap_years: int = 10
    ratchet_enabled: bool = True
    ratchet_frequency: int = 1
    withdrawal_rate: float = 0.05
    fee_rate: float = 0.01
    fee_basis: str = "gwb"


@dataclass(frozen=True)
class StepResult:
    """
    Result of stepping GWB forward.

    Attributes
    ----------
    new_state : GWBState
        Updated state after step
    rollup_applied : float
        Amount of rollup added
    ratchet_applied : bool
        Whether ratchet triggered
    fee_charged : float
        Fee amount charged
    withdrawal_taken : float
        Actual withdrawal taken
    excess_withdrawal : float
        Amount over max allowed (reduces GWB)
    """

    new_state: GWBState
    rollup_applied: float
    ratchet_applied: bool
    fee_charged: float
    withdrawal_taken: float
    excess_withdrawal: float


class GWBTracker:
    """
    Tracks GWB through time with rollup and ratchet.

    [T1] GWB determines guaranteed withdrawal amount.
    [T1] GWB grows via rollup until withdrawals begin.
    [T1] Ratchet locks in AV gains periodically.

    Examples
    --------
    >>> config = GWBConfig(rollup_rate=0.05)
    >>> tracker = GWBTracker(config, initial_premium=100_000)
    >>> state = tracker.initial_state()
    >>> new_state = tracker.step(state, av_return=-0.10, dt=1.0)

    See: docs/knowledge/domain/glwb_mechanics.md
    """

    def __init__(self, config: GWBConfig, initial_premium: float):
        """
        Initialize GWB tracker.

        Parameters
        ----------
        config : GWBConfig
            GWB mechanics configuration
        initial_premium : float
            Initial premium amount
        """
        if initial_premium <= 0:
            raise ValueError(f"Initial premium must be positive, got {initial_premium}")

        self.config = config
        self.initial_premium = initial_premium

        # Initialize rollup mechanics
        if config.rollup_type == RollupType.SIMPLE:
            self._rollup = SimpleRollup()
        elif config.rollup_type == RollupType.COMPOUND:
            self._rollup = CompoundRollup()
        else:
            self._rollup = None

        self._ratchet = RatchetMechanic() if config.ratchet_enabled else None

    def initial_state(self) -> GWBState:
        """
        Create initial GWB state at contract issue.

        [T1] At issue: GWB = AV = premium

        Returns
        -------
        GWBState
            Initial state with GWB = AV = premium
        """
        return GWBState(
            gwb=self.initial_premium,
            av=self.initial_premium,
            initial_premium=self.initial_premium,
            rollup_base=self.initial_premium,
            high_water_mark=self.initial_premium,
            years_since_issue=0.0,
            withdrawal_phase_started=False,
            total_withdrawals=0.0,
        )

    def step(
        self,
        state: GWBState,
        av_return: float,
        dt: float = 1.0,
        withdrawal: float = 0.0,
    ) -> StepResult:
        """
        Step GWB state forward in time.

        [T1] Sequence of operations:
        1. Apply market return to AV
        2. Charge fees
        3. Apply rollup to GWB (if not in withdrawal phase)
        4. Apply ratchet (on anniversary if enabled)
        5. Process withdrawal

        Parameters
        ----------
        state : GWBState
            Current state
        av_return : float
            Account value return (decimal, e.g., -0.10 for -10%)
        dt : float
            Time step in years
        withdrawal : float
            Requested withdrawal amount this period

        Returns
        -------
        StepResult
            Updated state with step diagnostics
        """
        gwb = state.gwb
        av = state.av
        years = state.years_since_issue + dt
        rollup_applied = 0.0
        ratchet_applied = False
        excess_withdrawal = 0.0

        # 1. Apply market return to AV
        av = av * (1 + av_return)
        av = max(0.0, av)  # AV cannot go negative

        # 2. Charge fees
        fee = self._calculate_fee(gwb, av, dt)
        av = max(0.0, av - fee)

        # 3. Apply rollup (only before withdrawal phase starts)
        withdrawal_phase = state.withdrawal_phase_started or withdrawal > 0
        if not withdrawal_phase and self._rollup is not None:
            # Rollup applies to base, capped at rollup_cap_years
            if years <= self.config.rollup_cap_years:
                new_gwb = self._rollup.calculate(
                    state.rollup_base,
                    years,
                    self.config.rollup_rate,
                )
                rollup_applied = new_gwb - gwb
                gwb = new_gwb

        # 4. Apply ratchet (on anniversary if enabled)
        if self._ratchet is not None:
            # Check if we're on a ratchet anniversary
            is_anniversary = (
                int(years) > int(state.years_since_issue) and
                int(years) % self.config.ratchet_frequency == 0
            )
            if is_anniversary:
                new_gwb = self._ratchet.apply_ratchet(gwb, av)
                if new_gwb > gwb:
                    ratchet_applied = True
                    gwb = new_gwb

        # 5. Update high water mark
        high_water_mark = max(state.high_water_mark, av)

        # 6. Process withdrawal
        max_withdrawal = self.calculate_max_withdrawal_from_values(gwb)
        actual_withdrawal = min(withdrawal, max(av, 0))  # Can't withdraw more than AV

        if withdrawal > max_withdrawal:
            # Excess withdrawal reduces GWB proportionally
            excess_withdrawal = withdrawal - max_withdrawal
            if gwb > 0:
                reduction_ratio = excess_withdrawal / gwb
                gwb = gwb * (1 - reduction_ratio)

        av = max(0.0, av - actual_withdrawal)
        total_withdrawals = state.total_withdrawals + actual_withdrawal

        # Create new state
        new_state = GWBState(
            gwb=gwb,
            av=av,
            initial_premium=state.initial_premium,
            rollup_base=state.rollup_base,
            high_water_mark=high_water_mark,
            years_since_issue=years,
            withdrawal_phase_started=withdrawal_phase,
            total_withdrawals=total_withdrawals,
        )

        return StepResult(
            new_state=new_state,
            rollup_applied=rollup_applied,
            ratchet_applied=ratchet_applied,
            fee_charged=fee,
            withdrawal_taken=actual_withdrawal,
            excess_withdrawal=excess_withdrawal,
        )

    def calculate_max_withdrawal(self, state: GWBState) -> float:
        """
        Calculate maximum allowed withdrawal.

        [T1] Max Withdrawal = GWB × withdrawal_rate

        Parameters
        ----------
        state : GWBState
            Current state

        Returns
        -------
        float
            Maximum allowed withdrawal
        """
        return self.calculate_max_withdrawal_from_values(state.gwb)

    def calculate_max_withdrawal_from_values(self, gwb: float) -> float:
        """
        Calculate maximum allowed withdrawal from GWB value.

        Parameters
        ----------
        gwb : float
            Current GWB value

        Returns
        -------
        float
            Maximum allowed withdrawal
        """
        return gwb * self.config.withdrawal_rate

    def _calculate_fee(self, gwb: float, av: float, dt: float) -> float:
        """Calculate fee for the period."""
        if self.config.fee_basis == "gwb":
            base = gwb
        else:
            base = av

        return base * self.config.fee_rate * dt

    def simulate_path(
        self,
        av_returns: np.ndarray,
        withdrawals: Optional[np.ndarray] = None,
        dt: float = 1.0,
    ) -> tuple[list[GWBState], list[StepResult]]:
        """
        Simulate GWB evolution along a path of returns.

        Parameters
        ----------
        av_returns : ndarray
            Array of AV returns for each period
        withdrawals : ndarray, optional
            Array of withdrawal amounts (default: max allowed each period)
        dt : float
            Time step in years

        Returns
        -------
        tuple[list[GWBState], list[StepResult]]
            States and step results at each time
        """
        n_steps = len(av_returns)

        if withdrawals is None:
            # Default: take max withdrawal each period
            withdrawals = np.full(n_steps, np.nan)  # Will calculate dynamically

        states = [self.initial_state()]
        results = []

        for t in range(n_steps):
            state = states[-1]

            # Calculate withdrawal (max if nan)
            if np.isnan(withdrawals[t]):
                withdrawal = self.calculate_max_withdrawal(state)
            else:
                withdrawal = withdrawals[t]

            result = self.step(state, av_returns[t], dt, withdrawal)
            states.append(result.new_state)
            results.append(result)

        return states, results

    def calculate_guarantee_payoff(self, state: GWBState) -> float:
        """
        Calculate guarantee payoff when AV is exhausted.

        [T1] When AV = 0, insurer pays guaranteed withdrawal
        until policyholder death.

        Parameters
        ----------
        state : GWBState
            Current state

        Returns
        -------
        float
            Guaranteed annual payment (if AV exhausted)
        """
        if state.av <= 0:
            return self.calculate_max_withdrawal(state)
        return 0.0
