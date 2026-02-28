"""
Tests for Dynamic Lapse Model - Phase 7.

[T1] Dynamic lapse rates adjust based on guarantee moneyness.

See: docs/knowledge/domain/dynamic_lapse.md
"""

import numpy as np
import pytest

from annuity_pricing.behavioral.dynamic_lapse import (
    DynamicLapseModel,
    LapseAssumptions,
)


class TestLapseAssumptions:
    """Tests for LapseAssumptions dataclass."""

    def test_default_values(self) -> None:
        """Default assumptions should be reasonable."""
        assumptions = LapseAssumptions()

        assert assumptions.base_annual_lapse == 0.05  # 5%
        assert assumptions.min_lapse == 0.01  # 1% floor
        assert assumptions.max_lapse == 0.25  # 25% cap
        assert assumptions.sensitivity == 1.0  # Linear sensitivity

    def test_custom_values(self) -> None:
        """Custom assumptions should be accepted."""
        assumptions = LapseAssumptions(
            base_annual_lapse=0.08,
            min_lapse=0.02,
            max_lapse=0.30,
            sensitivity=1.5,
        )

        assert assumptions.base_annual_lapse == 0.08
        assert assumptions.min_lapse == 0.02
        assert assumptions.max_lapse == 0.30
        assert assumptions.sensitivity == 1.5


class TestDynamicLapseModel:
    """Tests for DynamicLapseModel."""

    @pytest.fixture
    def model(self) -> DynamicLapseModel:
        """Standard model with default assumptions."""
        return DynamicLapseModel(LapseAssumptions())

    def test_atm_guarantee_base_lapse(self, model: DynamicLapseModel) -> None:
        """
        [T1] When AV = GWB (moneyness=1), lapse = base rate.
        """
        result = model.calculate_lapse(
            gwb=100_000,
            av=100_000,
            surrender_period_complete=True,
        )

        assert result.moneyness == 1.0
        assert result.adjustment_factor == 1.0
        assert result.lapse_rate == 0.05  # Base rate

    def test_itm_guarantee_lower_lapse(self, model: DynamicLapseModel) -> None:
        """
        [T1] When AV < GWB (ITM guarantee), lapse < base rate.

        Rational: policyholders keep valuable guarantees.
        """
        result = model.calculate_lapse(
            gwb=120_000,  # GWB > AV
            av=100_000,
            surrender_period_complete=True,
        )

        assert result.moneyness < 1.0  # 100k/120k = 0.833
        assert result.adjustment_factor < 1.0
        assert result.lapse_rate < 0.05  # Below base

    def test_otm_guarantee_higher_lapse(self, model: DynamicLapseModel) -> None:
        """
        [T1] When AV > GWB (OTM guarantee), lapse > base rate.

        Rational: policyholders may surrender if guarantee has little value.
        """
        result = model.calculate_lapse(
            gwb=80_000,  # GWB < AV
            av=100_000,
            surrender_period_complete=True,
        )

        assert result.moneyness > 1.0  # 100k/80k = 1.25
        assert result.adjustment_factor > 1.0
        assert result.lapse_rate > 0.05  # Above base

    def test_surrender_period_reduces_lapse(self, model: DynamicLapseModel) -> None:
        """
        [T1] Lapse is significantly lower during surrender period.
        """
        # During surrender period
        result_in_surrender = model.calculate_lapse(
            gwb=100_000,
            av=100_000,
            surrender_period_complete=False,
        )

        # After surrender period
        result_post_surrender = model.calculate_lapse(
            gwb=100_000,
            av=100_000,
            surrender_period_complete=True,
        )

        # Should be much lower during surrender period
        assert result_in_surrender.lapse_rate < result_post_surrender.lapse_rate
        # Expect ~80% reduction (0.05 * 0.2 = 0.01)
        assert result_in_surrender.lapse_rate == pytest.approx(0.01, abs=0.001)

    def test_lapse_floor_enforced(self) -> None:
        """
        [T1] Lapse rate cannot go below minimum.
        """
        # Very ITM guarantee (low moneyness)
        model = DynamicLapseModel(LapseAssumptions(min_lapse=0.02))

        result = model.calculate_lapse(
            gwb=200_000,  # Very high guarantee
            av=100_000,
            surrender_period_complete=True,
        )

        # Should be floored at min_lapse
        assert result.lapse_rate >= 0.02

    def test_lapse_cap_enforced(self) -> None:
        """
        [T1] Lapse rate cannot exceed maximum.
        """
        # Very OTM guarantee (high moneyness)
        model = DynamicLapseModel(LapseAssumptions(max_lapse=0.20))

        result = model.calculate_lapse(
            gwb=50_000,  # Very low guarantee
            av=100_000,
            surrender_period_complete=True,
        )

        # Should be capped at max_lapse
        assert result.lapse_rate <= 0.20

    def test_sensitivity_amplifies_adjustment(self) -> None:
        """
        [T1] Higher sensitivity = more responsive to moneyness.
        """
        # Low sensitivity
        model_low = DynamicLapseModel(LapseAssumptions(sensitivity=0.5))
        result_low = model_low.calculate_lapse(
            gwb=80_000, av=100_000, surrender_period_complete=True
        )

        # High sensitivity
        model_high = DynamicLapseModel(LapseAssumptions(sensitivity=2.0))
        result_high = model_high.calculate_lapse(
            gwb=80_000, av=100_000, surrender_period_complete=True
        )

        # High sensitivity should have larger adjustment
        assert result_high.adjustment_factor > result_low.adjustment_factor

    def test_zero_gwb_uses_base_rate(self, model: DynamicLapseModel) -> None:
        """
        [T1] With no guarantee (GWB=0), use base rate.
        """
        result = model.calculate_lapse(
            gwb=0,  # No guarantee
            av=100_000,
            surrender_period_complete=True,
        )

        assert result.moneyness == 1.0
        assert result.lapse_rate == 0.05

    def test_invalid_av_raises(self, model: DynamicLapseModel) -> None:
        """Negative AV should raise error."""
        with pytest.raises(ValueError, match="positive"):
            model.calculate_lapse(gwb=100_000, av=-10_000, surrender_period_complete=True)

    def test_invalid_gwb_raises(self, model: DynamicLapseModel) -> None:
        """Negative GWB should raise error."""
        with pytest.raises(ValueError, match="negative"):
            model.calculate_lapse(gwb=-100_000, av=100_000, surrender_period_complete=True)


class TestPathLapses:
    """Tests for path-based lapse calculations."""

    @pytest.fixture
    def model(self) -> DynamicLapseModel:
        return DynamicLapseModel(LapseAssumptions())

    def test_path_lapses_basic(self, model: DynamicLapseModel) -> None:
        """Calculate lapse rates along a path."""
        # Simple path: AV constant, GWB constant
        gwb_path = np.array([100_000, 100_000, 100_000])
        av_path = np.array([100_000, 100_000, 100_000])

        lapse_rates = model.calculate_path_lapses(gwb_path, av_path)

        assert len(lapse_rates) == 3
        assert all(r == 0.05 for r in lapse_rates)  # All at base rate

    def test_path_lapses_varying_moneyness(self, model: DynamicLapseModel) -> None:
        """Lapse rates should vary with moneyness along path."""
        # GWB fixed, AV increases (guarantee becomes OTM)
        gwb_path = np.array([100_000, 100_000, 100_000])
        av_path = np.array([100_000, 110_000, 120_000])

        lapse_rates = model.calculate_path_lapses(gwb_path, av_path)

        # Lapse should increase as AV exceeds GWB
        assert lapse_rates[0] < lapse_rates[1] < lapse_rates[2]

    def test_path_lapses_surrender_period(self, model: DynamicLapseModel) -> None:
        """Surrender period should affect lapse rates."""
        gwb_path = np.array([100_000, 100_000, 100_000, 100_000, 100_000])
        av_path = np.array([100_000, 100_000, 100_000, 100_000, 100_000])

        # Surrender period ends at step 3
        lapse_rates = model.calculate_path_lapses(gwb_path, av_path, surrender_period_ends=3)

        # First 3 periods: lower lapse (in surrender)
        assert lapse_rates[0] < 0.05
        assert lapse_rates[1] < 0.05
        assert lapse_rates[2] < 0.05

        # After surrender period: base rate
        assert lapse_rates[3] == 0.05
        assert lapse_rates[4] == 0.05

    def test_path_length_mismatch_raises(self, model: DynamicLapseModel) -> None:
        """Mismatched path lengths should raise error."""
        gwb_path = np.array([100_000, 100_000, 100_000])
        av_path = np.array([100_000, 100_000])  # Different length

        with pytest.raises(ValueError, match="lengths must match"):
            model.calculate_path_lapses(gwb_path, av_path)


class TestSurvivalProbability:
    """Tests for survival probability calculation."""

    @pytest.fixture
    def model(self) -> DynamicLapseModel:
        return DynamicLapseModel(LapseAssumptions())

    def test_survival_starts_at_one(self, model: DynamicLapseModel) -> None:
        """Survival probability at t=0 should be 1.0."""
        lapse_rates = np.array([0.05, 0.05, 0.05])
        survival = model.calculate_survival_probability(lapse_rates)

        assert survival[0] == 1.0

    def test_survival_decreases(self, model: DynamicLapseModel) -> None:
        """Survival probability should decrease over time."""
        lapse_rates = np.array([0.05, 0.05, 0.05, 0.05, 0.05])
        survival = model.calculate_survival_probability(lapse_rates)

        # Should be monotonically decreasing
        for i in range(len(survival) - 1):
            assert survival[i] > survival[i + 1]

    def test_survival_calculation(self, model: DynamicLapseModel) -> None:
        """Verify survival probability formula."""
        lapse_rates = np.array([0.10, 0.10])  # 10% each year
        survival = model.calculate_survival_probability(lapse_rates)

        # Expected: 1.0, 0.90, 0.81
        assert survival[0] == pytest.approx(1.0)
        assert survival[1] == pytest.approx(0.90)
        assert survival[2] == pytest.approx(0.81)

    def test_survival_with_varying_rates(self, model: DynamicLapseModel) -> None:
        """Survival with different lapse rates each period."""
        lapse_rates = np.array([0.05, 0.10, 0.15])
        survival = model.calculate_survival_probability(lapse_rates)

        # Manual calculation
        expected = [1.0, 0.95, 0.95 * 0.90, 0.95 * 0.90 * 0.85]
        for i, exp in enumerate(expected):
            assert survival[i] == pytest.approx(exp, rel=1e-6)
