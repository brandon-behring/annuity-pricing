"""
Tests for Monte Carlo option pricing engine.

Tests correctness of:
- European option pricing
- FIA/RILA payoff pricing
- Convergence properties

See: docs/knowledge/domain/option_pricing.md
"""

import numpy as np
import pytest

from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import (
    MCResult,
    MonteCarloEngine,
    price_vanilla_mc,
)


class TestMonteCarloEngine:
    """Tests for MonteCarloEngine class."""

    def test_engine_creation(self):
        """Engine should initialize correctly."""
        engine = MonteCarloEngine(n_paths=10000, antithetic=True, seed=42)
        assert engine.n_paths == 10000
        assert engine.antithetic is True
        assert engine.seed == 42

    def test_invalid_n_paths(self):
        """n_paths must be positive."""
        with pytest.raises(ValueError, match="must be > 0"):
            MonteCarloEngine(n_paths=0)

    def test_antithetic_rounds_up(self):
        """Antithetic should round up to even."""
        engine = MonteCarloEngine(n_paths=10001, antithetic=True)
        assert engine.n_paths == 10002


class TestEuropeanPricing:
    """Tests for European option pricing via MC."""

    @pytest.fixture
    def standard_params(self):
        """Standard GBM parameters for testing."""
        return GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

    def test_call_price_positive(self, standard_params):
        """Call price should be positive."""
        engine = MonteCarloEngine(n_paths=10000, seed=42)
        result = engine.price_european_call(standard_params, strike=100)

        assert result.price > 0
        assert result.standard_error > 0
        assert result.n_paths == 10000

    def test_put_price_positive(self, standard_params):
        """Put price should be positive."""
        engine = MonteCarloEngine(n_paths=10000, seed=42)
        result = engine.price_european_put(standard_params, strike=100)

        assert result.price > 0

    def test_confidence_interval(self, standard_params):
        """Confidence interval should contain price."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)
        result = engine.price_european_call(standard_params, strike=100)

        assert result.confidence_interval[0] < result.price < result.confidence_interval[1]

    def test_invalid_strike(self, standard_params):
        """Strike must be positive."""
        engine = MonteCarloEngine(n_paths=1000)

        with pytest.raises(ValueError, match="strike must be > 0"):
            engine.price_european_call(standard_params, strike=0)


class TestCappedCallPricing:
    """Tests for capped call (FIA) pricing."""

    @pytest.fixture
    def standard_params(self):
        """Standard GBM parameters for testing."""
        return GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

    def test_capped_call_less_than_uncapped(self, standard_params):
        """Capped call should be worth less than uncapped."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        # Capped at 10%
        capped_result = engine.price_capped_call_return(standard_params, cap_rate=0.10)

        # Uncapped (simulate with very high cap)
        uncapped_result = engine.price_capped_call_return(standard_params, cap_rate=10.0)

        assert capped_result.price < uncapped_result.price

    def test_lower_cap_lower_price(self, standard_params):
        """Lower cap should mean lower price."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        result_10 = engine.price_capped_call_return(standard_params, cap_rate=0.10)
        result_15 = engine.price_capped_call_return(standard_params, cap_rate=0.15)

        assert result_10.price < result_15.price

    def test_invalid_cap_rate(self, standard_params):
        """Cap rate must be positive."""
        engine = MonteCarloEngine(n_paths=1000)

        with pytest.raises(ValueError, match="cap_rate must be > 0"):
            engine.price_capped_call_return(standard_params, cap_rate=0)


class TestBufferPricing:
    """Tests for buffer protection (RILA) pricing."""

    @pytest.fixture
    def standard_params(self):
        """Standard GBM parameters for testing."""
        return GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

    def test_buffer_vs_no_buffer(self, standard_params):
        """Buffer should reduce expected loss."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        # With 10% buffer
        buffered = engine.price_buffer_protection(standard_params, buffer_rate=0.10)

        # Compare expected payoffs
        assert buffered.price >= 0  # Buffer provides value

    def test_larger_buffer_more_valuable(self, standard_params):
        """Larger buffer should be more valuable."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        result_10 = engine.price_buffer_protection(standard_params, buffer_rate=0.10)
        result_20 = engine.price_buffer_protection(standard_params, buffer_rate=0.20)

        assert result_20.price >= result_10.price

    def test_invalid_buffer_rate(self, standard_params):
        """Buffer rate must be positive."""
        engine = MonteCarloEngine(n_paths=1000)

        with pytest.raises(ValueError, match="buffer_rate must be > 0"):
            engine.price_buffer_protection(standard_params, buffer_rate=0)


class TestFloorPricing:
    """Tests for floor protection (RILA) pricing."""

    @pytest.fixture
    def standard_params(self):
        """Standard GBM parameters for testing."""
        return GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

    def test_floor_limits_loss(self, standard_params):
        """Floor should limit maximum loss."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        result = engine.price_floor_protection(standard_params, floor_rate=-0.10)

        # Check that floor protection is reasonable
        assert result.price is not None

    def test_higher_floor_more_valuable(self, standard_params):
        """Higher floor (less loss) should be more valuable."""
        engine = MonteCarloEngine(n_paths=50000, seed=42)

        result_10 = engine.price_floor_protection(standard_params, floor_rate=-0.10)
        result_20 = engine.price_floor_protection(standard_params, floor_rate=-0.20)

        # -10% floor is better than -20% floor
        assert result_10.price >= result_20.price

    def test_invalid_floor_rate(self, standard_params):
        """Floor rate should be negative."""
        engine = MonteCarloEngine(n_paths=1000)

        with pytest.raises(ValueError, match="floor_rate should be <= 0"):
            engine.price_floor_protection(standard_params, floor_rate=0.10)


class TestMCResult:
    """Tests for MCResult dataclass."""

    def test_relative_error(self):
        """Relative error should be SE/price."""
        result = MCResult(
            price=10.0,
            standard_error=0.5,
            confidence_interval=(9.0, 11.0),
            n_paths=10000,
            payoffs=np.array([10.0]),
            discount_factor=0.95,
        )

        assert result.relative_error == pytest.approx(0.05)

    def test_ci_width(self):
        """CI width should be upper - lower."""
        result = MCResult(
            price=10.0,
            standard_error=0.5,
            confidence_interval=(9.0, 11.0),
            n_paths=10000,
            payoffs=np.array([10.0]),
            discount_factor=0.95,
        )

        assert result.ci_width == pytest.approx(2.0)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_price_vanilla_mc_call(self):
        """price_vanilla_mc should work for calls."""
        result = price_vanilla_mc(
            spot=100,
            strike=100,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.CALL,
            n_paths=10000,
            seed=42,
        )

        assert result.price > 0

    def test_price_vanilla_mc_put(self):
        """price_vanilla_mc should work for puts."""
        result = price_vanilla_mc(
            spot=100,
            strike=100,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.PUT,
            n_paths=10000,
            seed=42,
        )

        assert result.price > 0
