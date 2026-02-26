"""
Tests for path consistency between different simulation methods.

Validates that:
- Terminal-only vs full-path give same payoffs for path-independent options
- Monthly averaging is consistent with daily-then-aggregated
- Different step sizes give consistent results

See: METHODOLOGY.md Section 4
See: Glasserman (2003) Ch. 3 - Sample path generation
"""

import numpy as np
import pytest

from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    generate_gbm_paths,
    generate_paths_with_monthly_observations,
    generate_terminal_values,
)
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine

# =============================================================================
# Test Configuration
# =============================================================================

#: Number of paths for consistency tests
N_PATHS: int = 10_000

#: Relative tolerance for payoff consistency
PAYOFF_TOLERANCE: float = 0.05  # 5% relative difference


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def standard_params() -> GBMParams:
    """Standard GBM parameters for consistency testing."""
    return GBMParams(
        spot=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
    )


# =============================================================================
# Terminal vs Full Path Consistency
# =============================================================================


class TestTerminalVsFullPath:
    """
    Tests that terminal-only and full-path give consistent results.

    For path-independent payoffs (European options), terminal-only
    is more efficient but should give the same distribution.
    """

    def test_terminal_values_same_distribution(self, standard_params):
        """
        Terminal values from full path should match terminal-only generation.

        Both methods with same seed should give identical terminal values
        (when same number of paths and antithetic setting).
        """
        # Terminal-only
        terminal_only = generate_terminal_values(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=False,
        )

        # Full path - extract terminal values
        full_path_result = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=252,  # Daily
            seed=42,
            antithetic=False,
        )
        terminal_from_path = full_path_result.terminal_values

        # Both should have same mean (but not identical due to different RNG consumption)
        # Test distribution statistics instead of exact equality
        assert abs(terminal_only.mean() - terminal_from_path.mean()) < 5, (
            f"Means differ: {terminal_only.mean():.4f} vs {terminal_from_path.mean():.4f}"
        )

        assert abs(terminal_only.std() - terminal_from_path.std()) < 3, (
            f"Stds differ: {terminal_only.std():.4f} vs {terminal_from_path.std():.4f}"
        )

    def test_call_payoff_same_distribution(self, standard_params):
        """
        Call payoffs should have same distribution from both methods.
        """
        strike = 100.0

        # Terminal-only payoffs
        terminal_only = generate_terminal_values(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=False,
        )
        payoffs_terminal = np.maximum(terminal_only - strike, 0)

        # Full path payoffs
        full_path = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=252,
            seed=42,
            antithetic=False,
        )
        payoffs_full = np.maximum(full_path.terminal_values - strike, 0)

        # Mean payoffs should be similar
        rel_diff = abs(payoffs_terminal.mean() - payoffs_full.mean()) / (payoffs_terminal.mean() + 1e-10)

        assert rel_diff < PAYOFF_TOLERANCE, (
            f"Call payoff means differ by {rel_diff:.1%}"
        )

    def test_put_payoff_same_distribution(self, standard_params):
        """
        Put payoffs should have same distribution from both methods.
        """
        strike = 100.0

        terminal_only = generate_terminal_values(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=False,
        )
        payoffs_terminal = np.maximum(strike - terminal_only, 0)

        full_path = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=252,
            seed=42,
            antithetic=False,
        )
        payoffs_full = np.maximum(strike - full_path.terminal_values, 0)

        rel_diff = abs(payoffs_terminal.mean() - payoffs_full.mean()) / (payoffs_terminal.mean() + 1e-10)

        assert rel_diff < PAYOFF_TOLERANCE


# =============================================================================
# Monthly Observation Consistency
# =============================================================================


class TestMonthlyObservationConsistency:
    """
    Tests consistency of monthly observation paths.

    For FIA products with monthly averaging, we need to ensure
    monthly observations are consistent.
    """

    def test_monthly_path_shape(self, standard_params):
        """
        Monthly path should have 13 values (initial + 12 months).
        """
        result = generate_paths_with_monthly_observations(
            standard_params,
            n_paths=100,
            seed=42,
            antithetic=False,
        )

        # Should have 13 time points
        assert len(result.times) == 13, f"Expected 13 times, got {len(result.times)}"
        assert result.paths.shape[1] == 13, f"Expected 13 columns, got {result.paths.shape[1]}"

    def test_monthly_times_correct(self, standard_params):
        """
        Monthly observation times should be at month boundaries.
        """
        result = generate_paths_with_monthly_observations(
            standard_params,
            n_paths=100,
            seed=42,
        )

        # Times should be [0, 1/12, 2/12, ..., 12/12]
        expected_times = np.linspace(0, 1.0, 13)

        np.testing.assert_array_almost_equal(result.times, expected_times, decimal=6)

    def test_monthly_initial_value_correct(self, standard_params):
        """
        Monthly path should start at spot price.
        """
        result = generate_paths_with_monthly_observations(
            standard_params,
            n_paths=100,
            seed=42,
        )

        # All paths should start at spot
        np.testing.assert_array_almost_equal(
            result.paths[:, 0],
            np.full(100, standard_params.spot),
            decimal=6,
        )

    def test_monthly_terminal_consistent_with_terminal_only(self, standard_params):
        """
        Terminal values from monthly path should have similar distribution
        to terminal-only generation.
        """
        # Monthly path
        monthly = generate_paths_with_monthly_observations(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=False,
        )
        monthly_terminal = monthly.paths[:, -1]

        # Terminal-only
        terminal_only = generate_terminal_values(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=False,
        )

        # Distributions should be similar
        assert abs(monthly_terminal.mean() - terminal_only.mean()) < 3
        assert abs(monthly_terminal.std() - terminal_only.std()) < 3

    def test_monthly_averaging_calculation(self, standard_params):
        """
        Test that monthly average can be correctly calculated.
        """
        result = generate_paths_with_monthly_observations(
            standard_params,
            n_paths=1000,
            seed=42,
        )

        # Calculate monthly average return for each path
        # Average of monthly prices / initial - 1
        monthly_prices = result.paths[:, 1:]  # Exclude initial
        avg_prices = monthly_prices.mean(axis=1)
        avg_returns = (avg_prices - standard_params.spot) / standard_params.spot

        # Average return should be close to risk-neutral expectation
        # For averaging: E[avg] ≈ E[geometric avg] < E[S(T)]/S(0) - 1
        # So avg_returns.mean() should be somewhat positive but < forward/S - 1
        forward_return = (standard_params.forward - standard_params.spot) / standard_params.spot

        # Average return should be between 0 and forward return (roughly)
        # This is an approximate test
        assert avg_returns.mean() < forward_return * 1.5


# =============================================================================
# Step Size Consistency
# =============================================================================


class TestStepSizeConsistency:
    """
    Tests that different step sizes give consistent terminal values.

    The discretization should not affect terminal distribution significantly.
    """

    def test_different_steps_same_terminal_distribution(self, standard_params):
        """
        Different step sizes should give similar terminal distributions.
        """
        # Daily (252 steps)
        daily = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=252,
            seed=42,
            antithetic=False,
        )

        # Weekly (52 steps)
        weekly = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=52,
            seed=42,
            antithetic=False,
        )

        # Monthly (12 steps)
        monthly = generate_gbm_paths(
            standard_params,
            n_paths=N_PATHS,
            n_steps=12,
            seed=42,
            antithetic=False,
        )

        # All should have similar forward-matching mean
        expected_forward = standard_params.forward

        for name, result in [("daily", daily), ("weekly", weekly), ("monthly", monthly)]:
            mean = result.terminal_values.mean()
            rel_error = abs(mean - expected_forward) / expected_forward

            assert rel_error < 0.05, (
                f"{name} mean {mean:.4f} differs from forward {expected_forward:.4f} "
                f"by {rel_error:.1%}"
            )

    def test_step_size_variance_consistency(self, standard_params):
        """
        Variance should be consistent across step sizes.
        """
        # Different step sizes
        daily = generate_gbm_paths(standard_params, N_PATHS, 252, seed=42, antithetic=False)
        monthly = generate_gbm_paths(standard_params, N_PATHS, 12, seed=42, antithetic=False)

        # Theoretical variance
        T = standard_params.time_to_expiry
        r_q = standard_params.rate - standard_params.dividend
        sigma = standard_params.volatility
        S = standard_params.spot

        expected_var = S**2 * np.exp(2 * r_q * T) * (np.exp(sigma**2 * T) - 1)

        daily_var = daily.terminal_values.var()
        monthly_var = monthly.terminal_values.var()

        # Both should be within 20% of theoretical
        assert abs(daily_var - expected_var) / expected_var < 0.20
        assert abs(monthly_var - expected_var) / expected_var < 0.20


# =============================================================================
# Antithetic Consistency
# =============================================================================


class TestAntitheticConsistency:
    """
    Tests consistency of antithetic variates implementation.
    """

    def test_antithetic_even_paths(self, standard_params):
        """
        Antithetic should require even number of paths (raises for odd).

        Note: MonteCarloEngine rounds up, but generate_terminal_values
        enforces this strictly.
        """
        # Odd input should raise error
        with pytest.raises(ValueError, match="must be even"):
            generate_terminal_values(
                standard_params,
                n_paths=101,
                seed=42,
                antithetic=True,
            )

        # Even input should work
        result = generate_terminal_values(
            standard_params,
            n_paths=100,
            seed=42,
            antithetic=True,
        )
        assert len(result) == 100

    def test_antithetic_pairs_add_to_twice_forward(self, standard_params):
        """
        Antithetic pairs should approximately add to 2 * forward.

        For exact log-normal: S * S_anti = S_0^2 * exp(2*(r-q-σ²/2)*T)
        """
        result = generate_terminal_values(
            standard_params,
            n_paths=1000,  # 500 pairs
            seed=42,
            antithetic=True,
        )

        n_pairs = len(result) // 2
        first_half = result[:n_pairs]
        second_half = result[n_pairs:]

        # Product of pairs
        products = first_half * second_half

        # Expected product: S_0^2 * exp(2*(r-q-σ²/2)*T)
        expected_product = (
            standard_params.spot**2
            * np.exp(2 * standard_params.drift * standard_params.time_to_expiry)
        )

        mean_product = products.mean()

        # Should be close to expected
        rel_error = abs(mean_product - expected_product) / expected_product

        assert rel_error < 0.10, (
            f"Product mean {mean_product:.2f} differs from expected {expected_product:.2f}"
        )

    def test_antithetic_terminal_vs_path_consistent(self, standard_params):
        """
        Antithetic should work consistently for both terminal and path generation.
        """
        # Terminal-only with antithetic
        terminal_anti = generate_terminal_values(
            standard_params,
            n_paths=1000,
            seed=42,
            antithetic=True,
        )

        # Full path with antithetic
        path_anti = generate_gbm_paths(
            standard_params,
            n_paths=1000,
            n_steps=12,
            seed=42,
            antithetic=True,
        )

        # Both should have similar statistics
        assert abs(terminal_anti.mean() - path_anti.terminal_values.mean()) < 5
        assert abs(terminal_anti.std() - path_anti.terminal_values.std()) < 3


# =============================================================================
# MC Engine Path Consistency
# =============================================================================


class TestMCEnginePathConsistency:
    """
    Tests that MonteCarloEngine gives consistent results across methods.
    """

    def test_european_call_same_as_manual(self, standard_params):
        """
        MonteCarloEngine call price should match manual calculation.
        """
        strike = 100.0

        # Via engine
        engine = MonteCarloEngine(n_paths=N_PATHS, antithetic=True, seed=42)
        engine_result = engine.price_european_call(standard_params, strike)

        # Manual calculation
        terminal = generate_terminal_values(
            standard_params,
            n_paths=N_PATHS,
            seed=42,
            antithetic=True,
        )
        payoffs = np.maximum(terminal - strike, 0)
        df = np.exp(-standard_params.rate * standard_params.time_to_expiry)
        manual_price = df * payoffs.mean()

        # Should be identical (same RNG, same calculation)
        assert abs(engine_result.price - manual_price) < 0.01, (
            f"Engine price {engine_result.price:.4f} differs from "
            f"manual {manual_price:.4f}"
        )

    def test_capped_call_consistent(self, standard_params):
        """
        Capped call should be consistent between runs with same seed.
        """
        cap_rate = 0.10

        engine1 = MonteCarloEngine(n_paths=N_PATHS, antithetic=True, seed=42)
        result1 = engine1.price_capped_call_return(standard_params, cap_rate)

        engine2 = MonteCarloEngine(n_paths=N_PATHS, antithetic=True, seed=42)
        result2 = engine2.price_capped_call_return(standard_params, cap_rate)

        # Same seed should give identical result
        assert result1.price == result2.price

    def test_buffer_protection_consistent(self, standard_params):
        """
        Buffer protection should be consistent between runs with same seed.
        """
        buffer_rate = 0.10

        engine1 = MonteCarloEngine(n_paths=N_PATHS, antithetic=True, seed=42)
        result1 = engine1.price_buffer_protection(standard_params, buffer_rate)

        engine2 = MonteCarloEngine(n_paths=N_PATHS, antithetic=True, seed=42)
        result2 = engine2.price_buffer_protection(standard_params, buffer_rate)

        assert result1.price == result2.price


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCaseConsistency:
    """
    Tests consistency for edge case parameters.
    """

    def test_very_short_expiry(self):
        """
        Very short expiry should give consistent results.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=0.01,  # ~3 days
        )

        terminal_only = generate_terminal_values(params, N_PATHS, seed=42, antithetic=False)
        full_path = generate_gbm_paths(params, N_PATHS, 10, seed=42, antithetic=False)

        # Both should be very close to spot (short time)
        assert abs(terminal_only.mean() - params.spot) < 2
        assert abs(full_path.terminal_values.mean() - params.spot) < 2

    def test_high_volatility(self):
        """
        High volatility should give consistent results.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.80,  # Very high
            time_to_expiry=1.0,
        )

        terminal_only = generate_terminal_values(params, N_PATHS, seed=42, antithetic=False)

        # Should still match forward on average
        rel_error = abs(terminal_only.mean() - params.forward) / params.forward

        assert rel_error < 0.10

    def test_zero_vol(self):
        """
        Zero volatility should give deterministic forward.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.0,  # Zero vol
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, 1000, seed=42, antithetic=False)

        # All values should equal forward exactly
        expected_forward = params.forward

        np.testing.assert_array_almost_equal(
            terminal,
            np.full(1000, expected_forward),
            decimal=6,
        )
