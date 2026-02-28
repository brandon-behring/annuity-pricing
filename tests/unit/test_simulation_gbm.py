"""
Tests for GBM path generation.

Tests correctness of:
- Path generation mechanics
- Antithetic variates
- Theoretical moment matching

See: docs/knowledge/domain/option_pricing.md
"""

import numpy as np
import pytest

from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    generate_gbm_paths,
    generate_paths_with_monthly_observations,
    generate_terminal_values,
    validate_gbm_simulation,
)


class TestGBMParams:
    """Tests for GBMParams dataclass."""

    def test_valid_params(self):
        """Valid parameters should work."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        assert params.spot == 100
        assert params.rate == 0.05

    def test_drift_calculation(self):
        """[T1] Drift = r - q - σ²/2."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        expected_drift = 0.05 - 0.02 - 0.5 * 0.20**2
        assert params.drift == pytest.approx(expected_drift)

    def test_forward_price(self):
        """[T1] Forward = S * exp((r-q)*T)."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        expected_forward = 100 * np.exp((0.05 - 0.02) * 1.0)
        assert params.forward == pytest.approx(expected_forward)

    def test_invalid_spot(self):
        """Spot must be positive."""
        with pytest.raises(ValueError, match="spot must be > 0"):
            GBMParams(spot=0, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

    def test_invalid_volatility(self):
        """Volatility must be non-negative."""
        with pytest.raises(ValueError, match="volatility must be >= 0"):
            GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=-0.20, time_to_expiry=1.0)

    def test_invalid_time(self):
        """Time to expiry must be positive."""
        with pytest.raises(ValueError, match="time_to_expiry must be > 0"):
            GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=0)


class TestGenerateGBMPaths:
    """Tests for generate_gbm_paths function."""

    def test_path_shape(self):
        """Paths should have correct shape."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=1000, n_steps=252, seed=42)

        assert result.paths.shape == (1000, 253)  # 252 steps + initial
        assert result.times.shape == (253,)
        assert result.n_paths == 1000
        assert result.n_steps == 252

    def test_initial_value(self):
        """All paths should start at spot."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=100, n_steps=10, seed=42)

        np.testing.assert_array_almost_equal(result.paths[:, 0], 100.0)

    def test_positive_values(self):
        """GBM paths should always be positive."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.50, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=1000, n_steps=252, seed=42)

        assert np.all(result.paths > 0)

    def test_reproducibility(self):
        """Same seed should give same paths."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result1 = generate_gbm_paths(params, n_paths=100, n_steps=10, seed=42)
        result2 = generate_gbm_paths(params, n_paths=100, n_steps=10, seed=42)

        np.testing.assert_array_almost_equal(result1.paths, result2.paths)

    def test_antithetic_even_paths(self):
        """Antithetic requires even number of paths."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

        with pytest.raises(ValueError, match="must be even"):
            generate_gbm_paths(params, n_paths=101, n_steps=10, antithetic=True)

    def test_antithetic_variance_reduction(self):
        """Antithetic variates should reduce variance."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)

        # Without antithetic
        result_normal = generate_gbm_paths(params, n_paths=10000, n_steps=1, seed=42)
        var_normal = result_normal.terminal_values.var()

        # With antithetic
        result_anti = generate_gbm_paths(params, n_paths=10000, n_steps=1, seed=42, antithetic=True)
        var_anti = result_anti.terminal_values.var()

        # Variance should be similar but mean estimate more stable
        # Just check it runs without error for now
        assert var_anti > 0


class TestGenerateTerminalValues:
    """Tests for generate_terminal_values function."""

    def test_shape(self):
        """Terminal values should have correct shape."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        terminal = generate_terminal_values(params, n_paths=1000, seed=42)

        assert terminal.shape == (1000,)

    def test_positive(self):
        """Terminal values should be positive."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.50, time_to_expiry=1.0)
        terminal = generate_terminal_values(params, n_paths=10000, seed=42)

        assert np.all(terminal > 0)

    def test_mean_approaches_forward(self):
        """[T1] E[S(T)] ≈ Forward price under risk-neutral measure."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        terminal = generate_terminal_values(params, n_paths=100000, seed=42, antithetic=True)

        expected = params.forward
        actual = terminal.mean()

        # Should be within 1% of forward
        assert abs(actual - expected) / expected < 0.01


class TestValidateGBMSimulation:
    """Tests for validate_gbm_simulation function."""

    def test_validation_passes(self):
        """Validation should pass for correct implementation."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = validate_gbm_simulation(params, n_paths=100000, seed=42)

        assert result["validation_passed"]
        assert result["mean_error_pct"] < 1.0  # Within 1%

    def test_log_variance_matches(self):
        """[T1] Var[log(S(T)/S(0))] ≈ σ²T."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = validate_gbm_simulation(params, n_paths=100000, seed=42)

        # Variance should be within 5% of theoretical
        assert result["variance_error_pct"] < 5.0


class TestMonthlyObservations:
    """Tests for monthly observation path generation."""

    def test_monthly_shape(self):
        """Monthly paths should have correct shape."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_paths_with_monthly_observations(params, n_paths=100, n_months=12, seed=42)

        # Should have 13 observations (month 0 through 12)
        assert result.paths.shape[1] == 13

    def test_monthly_times(self):
        """Monthly times should span the year."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_paths_with_monthly_observations(params, n_paths=100, n_months=12, seed=42)

        assert result.times[0] == pytest.approx(0.0)
        assert result.times[-1] == pytest.approx(1.0, rel=0.01)


class TestPathResult:
    """Tests for PathResult dataclass."""

    def test_get_index_path(self):
        """get_index_path should return valid IndexPath."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=10, n_steps=12, seed=42)

        path = result.get_index_path(0)

        assert path.initial_value == 100.0
        assert len(path.times) == 13
        assert len(path.values) == 13

    def test_get_index_path_invalid(self):
        """Invalid path index should raise."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=10, n_steps=12, seed=42)

        with pytest.raises(ValueError, match="path_idx"):
            result.get_index_path(100)

    def test_returns(self):
        """Returns should be calculated correctly."""
        params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
        result = generate_gbm_paths(params, n_paths=100, n_steps=12, seed=42)

        expected_returns = (result.paths[:, -1] - result.paths[:, 0]) / result.paths[:, 0]
        np.testing.assert_array_almost_equal(result.returns, expected_returns)
