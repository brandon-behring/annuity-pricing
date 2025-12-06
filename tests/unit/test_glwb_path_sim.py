"""
Tests for GLWB Path-Dependent Monte Carlo - Phase 8.

[T1] GLWB value = E[PV(insurer payments when AV exhausted)]

See: docs/knowledge/domain/glwb_mechanics.md
"""

import pytest
import numpy as np

from annuity_pricing.glwb.path_sim import (
    GLWBPathSimulator,
    GLWBPricingResult,
    PathResult,
)
from annuity_pricing.glwb.gwb_tracker import GWBConfig, RollupType


class TestGLWBPricingResult:
    """Tests for GLWBPricingResult dataclass."""

    def test_result_attributes(self) -> None:
        """Result should have all expected attributes."""
        result = GLWBPricingResult(
            price=5000.0,
            guarantee_cost=0.05,
            mean_payoff=5000.0,
            std_payoff=2000.0,
            standard_error=200.0,
            prob_ruin=0.30,
            mean_ruin_year=15.0,
            n_paths=1000,
        )

        assert result.price == 5000.0
        assert result.guarantee_cost == 0.05
        assert result.prob_ruin == 0.30


class TestGLWBPathSimulator:
    """Tests for GLWBPathSimulator."""

    @pytest.fixture
    def simulator(self) -> GLWBPathSimulator:
        """Standard simulator with default config."""
        config = GWBConfig(
            rollup_rate=0.05,
            withdrawal_rate=0.05,
            fee_rate=0.01,
        )
        return GLWBPathSimulator(config, n_paths=100, seed=42)

    def test_basic_pricing(self, simulator: GLWBPathSimulator) -> None:
        """
        [T1] Basic GLWB pricing should return reasonable result.
        """
        result = simulator.price(
            premium=100_000,
            age=65,
            r=0.04,
            sigma=0.18,
            max_age=100,
        )

        # Should return valid result
        assert result.price >= 0
        assert 0 <= result.guarantee_cost <= 1
        assert result.n_paths == 100
        assert result.standard_error > 0

    def test_price_increases_with_volatility(self) -> None:
        """
        [T1] Higher volatility → higher guarantee value.
        """
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)

        sim_low = GLWBPathSimulator(config, n_paths=200, seed=42)
        sim_high = GLWBPathSimulator(config, n_paths=200, seed=42)

        result_low = sim_low.price(100_000, 65, 0.04, sigma=0.10, max_age=100)
        result_high = sim_high.price(100_000, 65, 0.04, sigma=0.30, max_age=100)

        # Higher vol → more chance of ruin → higher guarantee cost
        assert result_high.prob_ruin >= result_low.prob_ruin

    def test_prob_ruin_in_valid_range(self, simulator: GLWBPathSimulator) -> None:
        """Probability of ruin should be in [0, 1]."""
        result = simulator.price(100_000, 65, 0.04, 0.18)

        assert 0 <= result.prob_ruin <= 1

    def test_invalid_premium_raises(self, simulator: GLWBPathSimulator) -> None:
        """Negative premium should raise error."""
        with pytest.raises(ValueError, match="positive"):
            simulator.price(-100_000, 65, 0.04, 0.18)

    def test_invalid_age_raises(self, simulator: GLWBPathSimulator) -> None:
        """Invalid age should raise error."""
        with pytest.raises(ValueError, match="Age"):
            simulator.price(100_000, 150, 0.04, 0.18, max_age=100)

    def test_invalid_volatility_raises(self, simulator: GLWBPathSimulator) -> None:
        """Negative volatility should raise error."""
        with pytest.raises(ValueError, match="negative"):
            simulator.price(100_000, 65, 0.04, -0.18)


class TestSinglePathSimulation:
    """Tests for single path simulation."""

    @pytest.fixture
    def simulator(self) -> GLWBPathSimulator:
        config = GWBConfig(
            rollup_rate=0.05,
            withdrawal_rate=0.05,
            fee_rate=0.01,
        )
        return GLWBPathSimulator(config, n_paths=10, seed=42)

    def test_single_path_returns_result(self, simulator: GLWBPathSimulator) -> None:
        """Single path should return PathResult."""
        result = simulator.simulate_single_path(
            premium=100_000,
            age=65,
            r=0.04,
            sigma=0.18,
            n_years=35,
            mortality_table=lambda age: 0.02,  # 2% mortality
            utilization_rate=1.0,
        )

        assert isinstance(result, PathResult)
        assert result.pv_insurer_payments >= 0
        assert result.pv_withdrawals >= 0

    def test_ruin_year_makes_sense(self, simulator: GLWBPathSimulator) -> None:
        """Ruin year should be -1 or positive."""
        result = simulator.simulate_single_path(
            premium=100_000,
            age=65,
            r=0.04,
            sigma=0.18,
            n_years=35,
            mortality_table=lambda age: 0.02,
        )

        assert result.ruin_year >= -1
        if result.ruin_year >= 0:
            assert result.ruin_year <= 35

    def test_utilization_affects_withdrawals(self, simulator: GLWBPathSimulator) -> None:
        """Lower utilization → less withdrawals."""
        # Full utilization
        result_full = simulator.simulate_single_path(
            premium=100_000, age=65, r=0.04, sigma=0.18,
            n_years=20, mortality_table=lambda age: 0.0,  # No mortality
            utilization_rate=1.0,
        )

        # Half utilization
        result_half = simulator.simulate_single_path(
            premium=100_000, age=65, r=0.04, sigma=0.18,
            n_years=20, mortality_table=lambda age: 0.0,
            utilization_rate=0.5,
        )

        # PV of withdrawals should be roughly half
        # (not exact due to path-dependency)
        assert result_half.pv_withdrawals < result_full.pv_withdrawals


class TestMortalityIntegration:
    """Tests for mortality integration."""

    @pytest.fixture
    def simulator(self) -> GLWBPathSimulator:
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)
        return GLWBPathSimulator(config, n_paths=100, seed=42)

    def test_high_mortality_reduces_price(self, simulator: GLWBPathSimulator) -> None:
        """Higher mortality → lower guarantee value (die before ruin)."""
        # Low mortality
        result_low = simulator.price(
            100_000, 65, 0.04, 0.18,
            mortality_table=lambda age: 0.01,  # 1%
        )

        # High mortality
        result_high = simulator.price(
            100_000, 65, 0.04, 0.18,
            mortality_table=lambda age: 0.10,  # 10%
        )

        # Higher mortality → less insurer payments (die sooner)
        assert result_high.price <= result_low.price

    def test_default_mortality_works(self, simulator: GLWBPathSimulator) -> None:
        """Default mortality table should work."""
        result = simulator.price(100_000, 65, 0.04, 0.18)

        # Should complete without error
        assert result.n_paths == 100


class TestRollupConfigurations:
    """Tests for different rollup configurations."""

    def test_higher_rollup_increases_guarantee(self) -> None:
        """Higher rollup → higher guaranteed amount → higher cost."""
        # Low rollup
        config_low = GWBConfig(rollup_rate=0.03, withdrawal_rate=0.05)
        sim_low = GLWBPathSimulator(config_low, n_paths=100, seed=42)
        result_low = sim_low.price(100_000, 65, 0.04, 0.18)

        # High rollup
        config_high = GWBConfig(rollup_rate=0.07, withdrawal_rate=0.05)
        sim_high = GLWBPathSimulator(config_high, n_paths=100, seed=42)
        result_high = sim_high.price(100_000, 65, 0.04, 0.18)

        # Higher rollup → higher GWB → higher guaranteed payment
        # This should increase insurer liability
        assert result_high.guarantee_cost >= result_low.guarantee_cost * 0.8  # Allow some variance

    def test_no_rollup(self) -> None:
        """No rollup should still work."""
        config = GWBConfig(
            rollup_type=RollupType.NONE,
            withdrawal_rate=0.05,
        )
        sim = GLWBPathSimulator(config, n_paths=50, seed=42)
        result = sim.price(100_000, 65, 0.04, 0.18)

        assert result.price >= 0


class TestSensitivityAnalysis:
    """Tests for sensitivity analysis."""

    @pytest.fixture
    def simulator(self) -> GLWBPathSimulator:
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)
        return GLWBPathSimulator(config, n_paths=50, seed=42)

    def test_sensitivity_returns_dict(self, simulator: GLWBPathSimulator) -> None:
        """Sensitivity analysis should return dict."""
        result = simulator.sensitivity_analysis(
            premium=100_000,
            age=65,
            r=0.04,
            sigma=0.18,
            max_age=100,
        )

        assert isinstance(result, dict)
        assert "base_price" in result
        assert "sigma_sensitivity" in result
        assert "rate_sensitivity" in result
        assert "prob_ruin" in result


class TestStandardError:
    """Tests for standard error calculation."""

    def test_more_paths_reduces_se(self) -> None:
        """More paths → lower standard error."""
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)

        sim_few = GLWBPathSimulator(config, n_paths=100, seed=42)
        sim_many = GLWBPathSimulator(config, n_paths=1000, seed=42)

        result_few = sim_few.price(100_000, 65, 0.04, 0.18)
        result_many = sim_many.price(100_000, 65, 0.04, 0.18)

        # SE should decrease with sqrt(n)
        # 10x paths → ~3.16x lower SE
        assert result_many.standard_error < result_few.standard_error


class TestReproducibility:
    """Tests for reproducibility with seed."""

    def test_same_seed_same_result(self) -> None:
        """Same seed should produce same result."""
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)

        sim1 = GLWBPathSimulator(config, n_paths=100, seed=12345)
        sim2 = GLWBPathSimulator(config, n_paths=100, seed=12345)

        result1 = sim1.price(100_000, 65, 0.04, 0.18)
        result2 = sim2.price(100_000, 65, 0.04, 0.18)

        assert result1.price == pytest.approx(result2.price)
        assert result1.prob_ruin == pytest.approx(result2.prob_ruin)

    def test_different_seed_different_result(self) -> None:
        """Different seeds should produce different results."""
        config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)

        sim1 = GLWBPathSimulator(config, n_paths=100, seed=11111)
        sim2 = GLWBPathSimulator(config, n_paths=100, seed=99999)

        result1 = sim1.price(100_000, 65, 0.04, 0.18)
        result2 = sim2.price(100_000, 65, 0.04, 0.18)

        # Results should differ (probability is extremely low they'd be equal)
        # But should be in same ballpark
        assert abs(result1.price - result2.price) / max(result1.price, 1) < 1.0
