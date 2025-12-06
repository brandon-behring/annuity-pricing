"""
Tests for GWB Tracker - Phase 8.

[T1] GWB is the base for calculating maximum allowed withdrawal.
[T1] GWB grows via rollup until withdrawals begin.
[T1] Ratchet locks in AV gains periodically.

See: docs/knowledge/domain/glwb_mechanics.md
"""

import pytest
import numpy as np

from annuity_pricing.glwb.gwb_tracker import (
    GWBTracker,
    GWBState,
    GWBConfig,
    RollupType,
    StepResult,
)


class TestGWBConfig:
    """Tests for GWBConfig dataclass."""

    def test_default_values(self) -> None:
        """Default config should have reasonable values."""
        config = GWBConfig()

        assert config.rollup_type == RollupType.COMPOUND
        assert config.rollup_rate == 0.05
        assert config.rollup_cap_years == 10
        assert config.ratchet_enabled is True
        assert config.ratchet_frequency == 1
        assert config.withdrawal_rate == 0.05
        assert config.fee_rate == 0.01

    def test_custom_values(self) -> None:
        """Custom config should be accepted."""
        config = GWBConfig(
            rollup_type=RollupType.SIMPLE,
            rollup_rate=0.06,
            rollup_cap_years=15,
            ratchet_enabled=False,
            withdrawal_rate=0.04,
        )

        assert config.rollup_type == RollupType.SIMPLE
        assert config.rollup_rate == 0.06
        assert config.rollup_cap_years == 15
        assert config.ratchet_enabled is False
        assert config.withdrawal_rate == 0.04


class TestGWBTracker:
    """Tests for GWBTracker."""

    @pytest.fixture
    def tracker(self) -> GWBTracker:
        """Standard tracker with default config."""
        config = GWBConfig()
        return GWBTracker(config, initial_premium=100_000)

    def test_initial_state(self, tracker: GWBTracker) -> None:
        """
        [T1] At issue: GWB = AV = premium
        """
        state = tracker.initial_state()

        assert state.gwb == 100_000
        assert state.av == 100_000
        assert state.initial_premium == 100_000
        assert state.rollup_base == 100_000
        assert state.high_water_mark == 100_000
        assert state.years_since_issue == 0.0
        assert state.withdrawal_phase_started is False

    def test_negative_premium_raises(self) -> None:
        """Negative premium should raise error."""
        config = GWBConfig()
        with pytest.raises(ValueError, match="positive"):
            GWBTracker(config, initial_premium=-100_000)

    def test_max_withdrawal_calculation(self, tracker: GWBTracker) -> None:
        """
        [T1] Max Withdrawal = GWB × withdrawal_rate
        """
        state = tracker.initial_state()
        max_wd = tracker.calculate_max_withdrawal(state)

        # $100k × 5% = $5k
        assert max_wd == pytest.approx(5_000)


class TestGWBStep:
    """Tests for GWB stepping."""

    @pytest.fixture
    def tracker(self) -> GWBTracker:
        config = GWBConfig(
            rollup_type=RollupType.COMPOUND,
            rollup_rate=0.05,
            fee_rate=0.01,
        )
        return GWBTracker(config, initial_premium=100_000)

    def test_step_applies_market_return(self, tracker: GWBTracker) -> None:
        """AV should change based on market return."""
        state = tracker.initial_state()

        # 10% positive return
        result = tracker.step(state, av_return=0.10, dt=1.0, withdrawal=0)

        # AV should increase (minus fee)
        assert result.new_state.av > state.av * 1.05  # Some increase after fee

    def test_step_charges_fee(self, tracker: GWBTracker) -> None:
        """Fee should be charged on AV."""
        state = tracker.initial_state()

        result = tracker.step(state, av_return=0.0, dt=1.0, withdrawal=0)

        # Fee = 1% of GWB (default basis)
        expected_fee = 100_000 * 0.01
        assert result.fee_charged == pytest.approx(expected_fee)
        assert result.new_state.av == pytest.approx(100_000 - expected_fee)

    def test_step_applies_rollup_before_withdrawals(self, tracker: GWBTracker) -> None:
        """
        [T1] Rollup applies before withdrawal phase.
        """
        state = tracker.initial_state()

        # No withdrawal
        result = tracker.step(state, av_return=0.0, dt=1.0, withdrawal=0)

        # GWB should grow by rollup (5% compound)
        expected_gwb = 100_000 * 1.05
        assert result.new_state.gwb == pytest.approx(expected_gwb)
        assert result.rollup_applied > 0

    def test_rollup_stops_when_withdrawals_begin(self, tracker: GWBTracker) -> None:
        """
        [T1] Rollup stops when withdrawal phase starts.
        """
        state = tracker.initial_state()

        # Take withdrawal
        result = tracker.step(state, av_return=0.0, dt=1.0, withdrawal=1000)

        # Rollup should NOT apply
        assert result.rollup_applied == 0
        assert result.new_state.withdrawal_phase_started is True

    def test_step_processes_withdrawal(self, tracker: GWBTracker) -> None:
        """Withdrawal should reduce AV."""
        state = tracker.initial_state()

        # Start with some return to have AV
        result1 = tracker.step(state, av_return=0.10, dt=1.0, withdrawal=0)
        state2 = result1.new_state

        # Take withdrawal
        result2 = tracker.step(state2, av_return=0.0, dt=1.0, withdrawal=5000)

        assert result2.withdrawal_taken == pytest.approx(5000)
        assert result2.new_state.av < state2.av

    def test_negative_return_reduces_av(self, tracker: GWBTracker) -> None:
        """Negative return should reduce AV."""
        state = tracker.initial_state()

        result = tracker.step(state, av_return=-0.20, dt=1.0, withdrawal=0)

        # AV = 100k × 0.8 - fee
        assert result.new_state.av < 80_000


class TestGWBRatchet:
    """Tests for ratchet mechanics in GWB."""

    @pytest.fixture
    def tracker_with_ratchet(self) -> GWBTracker:
        config = GWBConfig(
            rollup_type=RollupType.NONE,  # Disable rollup to isolate ratchet
            ratchet_enabled=True,
            ratchet_frequency=1,
            fee_rate=0.0,  # No fees for clarity
        )
        return GWBTracker(config, initial_premium=100_000)

    def test_ratchet_steps_up_on_anniversary(self, tracker_with_ratchet: GWBTracker) -> None:
        """
        [T1] Ratchet locks in AV gains on anniversary.
        """
        state = tracker_with_ratchet.initial_state()

        # Big positive return
        result = tracker_with_ratchet.step(state, av_return=0.20, dt=1.0, withdrawal=0)

        # GWB should step up to AV (which is now ~$120k)
        assert result.ratchet_applied is True
        assert result.new_state.gwb >= 120_000

    def test_no_ratchet_step_down(self, tracker_with_ratchet: GWBTracker) -> None:
        """
        [T1] Ratchet never steps down.
        """
        state = tracker_with_ratchet.initial_state()

        # First: positive return, step up
        result1 = tracker_with_ratchet.step(state, av_return=0.20, dt=1.0, withdrawal=0)
        gwb_after_up = result1.new_state.gwb

        # Second: negative return
        result2 = tracker_with_ratchet.step(result1.new_state, av_return=-0.30, dt=1.0, withdrawal=0)

        # GWB should not decrease
        assert result2.new_state.gwb >= gwb_after_up


class TestRollupCap:
    """Tests for rollup cap."""

    def test_rollup_stops_at_cap(self) -> None:
        """Rollup should stop after cap_years."""
        config = GWBConfig(
            rollup_type=RollupType.COMPOUND,
            rollup_rate=0.05,
            rollup_cap_years=3,
            ratchet_enabled=False,
            fee_rate=0.0,
        )
        tracker = GWBTracker(config, initial_premium=100_000)

        state = tracker.initial_state()

        # Step 5 years, but rollup cap is 3
        for _ in range(5):
            result = tracker.step(state, av_return=0.0, dt=1.0, withdrawal=0)
            state = result.new_state

        # GWB should be 3-year rollup, not 5-year
        expected = 100_000 * (1.05 ** 3)
        assert state.gwb == pytest.approx(expected)


class TestPathSimulation:
    """Tests for path simulation."""

    @pytest.fixture
    def tracker(self) -> GWBTracker:
        config = GWBConfig(
            rollup_type=RollupType.COMPOUND,
            rollup_rate=0.05,
            ratchet_enabled=True,
            fee_rate=0.01,
        )
        return GWBTracker(config, initial_premium=100_000)

    def test_simulate_path_basic(self, tracker: GWBTracker) -> None:
        """Basic path simulation."""
        av_returns = np.array([0.10, 0.05, -0.05, 0.08, 0.03])

        states, results = tracker.simulate_path(av_returns, dt=1.0)

        # Should have n+1 states (initial + after each step)
        assert len(states) == 6
        assert len(results) == 5

    def test_simulate_path_with_withdrawals(self, tracker: GWBTracker) -> None:
        """Path simulation with custom withdrawals."""
        av_returns = np.array([0.10, 0.05, 0.03])
        withdrawals = np.array([0, 5000, 5000])

        states, results = tracker.simulate_path(av_returns, withdrawals, dt=1.0)

        # First step: no withdrawal
        assert results[0].withdrawal_taken == 0

        # Second step: $5k withdrawal
        assert results[1].withdrawal_taken == pytest.approx(5000)

    def test_simulate_path_max_withdrawals(self, tracker: GWBTracker) -> None:
        """Path simulation with max withdrawals (default)."""
        av_returns = np.array([0.10, 0.05, 0.03])

        states, results = tracker.simulate_path(av_returns, withdrawals=None, dt=1.0)

        # Should take max withdrawal each period
        for r in results:
            assert r.withdrawal_taken > 0


class TestGuaranteePayoff:
    """Tests for guarantee payoff calculation."""

    @pytest.fixture
    def tracker(self) -> GWBTracker:
        config = GWBConfig(withdrawal_rate=0.05)
        return GWBTracker(config, initial_premium=100_000)

    def test_payoff_when_av_positive(self, tracker: GWBTracker) -> None:
        """No payoff when AV > 0."""
        state = tracker.initial_state()
        payoff = tracker.calculate_guarantee_payoff(state)

        assert payoff == 0.0

    def test_payoff_when_av_exhausted(self, tracker: GWBTracker) -> None:
        """
        [T1] When AV = 0, insurer pays guaranteed withdrawal.
        """
        # Create exhausted state
        state = GWBState(
            gwb=100_000,
            av=0.0,  # Exhausted
            initial_premium=100_000,
            rollup_base=100_000,
            high_water_mark=100_000,
            years_since_issue=20.0,
            withdrawal_phase_started=True,
        )

        payoff = tracker.calculate_guarantee_payoff(state)

        # Should be max withdrawal = GWB × rate = 100k × 5% = 5k
        assert payoff == pytest.approx(5_000)
