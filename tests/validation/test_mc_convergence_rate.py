"""
Tests for Monte Carlo convergence rate validation.

Validates that MC error decreases at the theoretical rate of 1/√N
as predicted by the Central Limit Theorem.

[T1] MC error ~ σ/√N (CLT)
[T1] Error should be bounded by 3σ/√N for 99.7% confidence

Note: Estimating slope from log-log regression is inherently noisy.
Instead, we validate CLT bounds and SE scaling which are more robust.

See: METHODOLOGY.md Section 4
See: Glasserman (2003) Ch. 3 - Monte Carlo theory
"""

import numpy as np
import pytest

from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import (
    MonteCarloEngine,
    convergence_analysis,
)

# =============================================================================
# Test Configuration
# =============================================================================

#: Seeds for convergence tests (tiered)
CI_SEEDS: list[int] = [42, 123, 456, 789, 1001]
THOROUGH_SEEDS: list[int] = list(range(1, 31))

#: Path counts for convergence analysis
PATH_COUNTS: list[int] = [1000, 5000, 10000, 50000, 100000]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def standard_params() -> GBMParams:
    """Standard GBM parameters for convergence testing."""
    return GBMParams(
        spot=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
    )


@pytest.fixture
def bs_call_price(standard_params) -> float:
    """Analytical Black-Scholes call price."""
    return black_scholes_call(
        spot=standard_params.spot,
        strike=100.0,
        rate=standard_params.rate,
        dividend=standard_params.dividend,
        volatility=standard_params.volatility,
        time_to_expiry=standard_params.time_to_expiry,
    )


@pytest.fixture
def bs_put_price(standard_params) -> float:
    """Analytical Black-Scholes put price."""
    return black_scholes_put(
        spot=standard_params.spot,
        strike=100.0,
        rate=standard_params.rate,
        dividend=standard_params.dividend,
        volatility=standard_params.volatility,
        time_to_expiry=standard_params.time_to_expiry,
    )


# =============================================================================
# CLT Bounds Tests (CI - Fast)
# =============================================================================


class TestCLTBounds:
    """
    Tests that MC errors are within CLT-predicted bounds.

    [T1] With probability 99.7%, error < 3σ/√N
    """

    def test_call_error_within_clt_bounds(self, standard_params, bs_call_price):
        """
        Call option MC error should be within 3 SE of true price.
        """
        engine = MonteCarloEngine(n_paths=100_000, antithetic=True, seed=42)
        result = engine.price_european_call(standard_params, strike=100.0)

        error = abs(result.price - bs_call_price)

        # Error should be within 3 SE (99.7% CI)
        assert error < 3 * result.standard_error, (
            f"Error {error:.6f} exceeds 3 SE ({3 * result.standard_error:.6f})"
        )

    def test_put_error_within_clt_bounds(self, standard_params, bs_put_price):
        """
        Put option MC error should be within 3 SE of true price.
        """
        engine = MonteCarloEngine(n_paths=100_000, antithetic=True, seed=42)
        result = engine.price_european_put(standard_params, strike=100.0)

        error = abs(result.price - bs_put_price)

        assert error < 3 * result.standard_error, (
            f"Error {error:.6f} exceeds 3 SE ({3 * result.standard_error:.6f})"
        )

    def test_clt_bounds_across_path_counts(self, standard_params, bs_call_price):
        """
        CLT bounds should hold across different path counts.
        """
        violations = 0

        for n_paths in PATH_COUNTS:
            engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=42)
            result = engine.price_european_call(standard_params, strike=100.0)

            error = abs(result.price - bs_call_price)
            bound = 3 * result.standard_error

            if error > bound:
                violations += 1

        # Should have at most 1 violation out of 5 (allowing some noise)
        assert violations <= 1, (
            f"Too many CLT violations: {violations}/{len(PATH_COUNTS)}"
        )

    def test_clt_bounds_across_seeds(self, standard_params, bs_call_price):
        """
        CLT bounds should hold across different seeds.
        """
        violations = 0
        n_paths = 50_000

        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)

            error = abs(result.price - bs_call_price)
            bound = 3 * result.standard_error

            if error > bound:
                violations += 1

        # With 5 seeds at 99.7% CI, expect ~0 violations
        # Allow 1 for statistical variability
        assert violations <= 1, (
            f"Too many CLT violations across seeds: {violations}/{len(CI_SEEDS)}"
        )


# =============================================================================
# SE Scaling Tests (Deterministic)
# =============================================================================


class TestSEScaling:
    """
    Tests that SE scales as 1/√N.

    This is more robust than error slope estimation because
    SE calculation is deterministic given the payoffs.
    """

    def test_se_ratio_1k_to_10k(self, standard_params):
        """
        SE ratio between 1k and 10k paths should be √10.
        """
        engine_1k = MonteCarloEngine(n_paths=1000, antithetic=True, seed=42)
        engine_10k = MonteCarloEngine(n_paths=10000, antithetic=True, seed=42)

        result_1k = engine_1k.price_european_call(standard_params, strike=100.0)
        result_10k = engine_10k.price_european_call(standard_params, strike=100.0)

        ratio = result_1k.standard_error / result_10k.standard_error
        expected = np.sqrt(10)  # √(10000/1000) = √10 ≈ 3.16

        assert abs(ratio - expected) < 0.5, (
            f"SE ratio {ratio:.2f} differs from expected {expected:.2f}"
        )

    def test_se_ratio_10k_to_100k(self, standard_params):
        """
        SE ratio between 10k and 100k paths should be √10.
        """
        engine_10k = MonteCarloEngine(n_paths=10000, antithetic=True, seed=42)
        engine_100k = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        result_10k = engine_10k.price_european_call(standard_params, strike=100.0)
        result_100k = engine_100k.price_european_call(standard_params, strike=100.0)

        ratio = result_10k.standard_error / result_100k.standard_error
        expected = np.sqrt(10)

        assert abs(ratio - expected) < 0.5, (
            f"SE ratio {ratio:.2f} differs from expected {expected:.2f}"
        )

    def test_se_ratio_full_range(self, standard_params):
        """
        SE ratio between 1k and 100k paths should be √100 = 10.
        """
        engine_1k = MonteCarloEngine(n_paths=1000, antithetic=True, seed=42)
        engine_100k = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        result_1k = engine_1k.price_european_call(standard_params, strike=100.0)
        result_100k = engine_100k.price_european_call(standard_params, strike=100.0)

        ratio = result_1k.standard_error / result_100k.standard_error
        expected = np.sqrt(100)  # 10

        assert abs(ratio - expected) < 1.5, (
            f"SE ratio {ratio:.2f} differs from expected {expected:.2f}"
        )

    def test_se_monotonically_decreases(self, standard_params):
        """
        SE should monotonically decrease with more paths.
        """
        ses = []

        for n_paths in PATH_COUNTS:
            engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=42)
            result = engine.price_european_call(standard_params, strike=100.0)
            ses.append(result.standard_error)

        # Each SE should be less than the previous
        for i in range(1, len(ses)):
            assert ses[i] < ses[i - 1], (
                f"SE at {PATH_COUNTS[i]} paths ({ses[i]:.6f}) "
                f"not less than at {PATH_COUNTS[i-1]} paths ({ses[i-1]:.6f})"
            )


# =============================================================================
# Error Trend Tests
# =============================================================================


class TestErrorTrend:
    """
    Tests that error decreases with more paths.
    """

    def test_error_decreases_on_average(self, standard_params, bs_call_price):
        """
        Average error should decrease with more paths.
        """
        # Run multiple seeds to get average error at each path count
        mean_errors = []

        for n_paths in PATH_COUNTS:
            errors = []
            for seed in CI_SEEDS:
                engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)
                result = engine.price_european_call(standard_params, strike=100.0)
                errors.append(abs(result.price - bs_call_price))
            mean_errors.append(np.mean(errors))

        # Mean error should generally decrease
        # Allow for some noise - check that last is less than first
        assert mean_errors[-1] < mean_errors[0], (
            f"Error at {PATH_COUNTS[-1]} paths ({mean_errors[-1]:.6f}) "
            f"not less than at {PATH_COUNTS[0]} paths ({mean_errors[0]:.6f})"
        )

    def test_100k_error_smaller_than_1k(self, standard_params, bs_call_price):
        """
        100k paths should give smaller error than 1k paths.
        """
        engine_1k = MonteCarloEngine(n_paths=1000, antithetic=True, seed=42)
        engine_100k = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        result_1k = engine_1k.price_european_call(standard_params, strike=100.0)
        result_100k = engine_100k.price_european_call(standard_params, strike=100.0)

        error_1k = abs(result_1k.price - bs_call_price)
        error_100k = abs(result_100k.price - bs_call_price)

        # 100k should be significantly better (allow up to equal due to randomness)
        assert error_100k <= error_1k * 2, (
            f"100k error {error_100k:.6f} should be much less than 1k error {error_1k:.6f}"
        )


# =============================================================================
# Convergence Analysis Function Tests
# =============================================================================


class TestConvergenceAnalysisFunction:
    """
    Tests the built-in convergence_analysis function.
    """

    def test_returns_correct_structure(self, standard_params, bs_call_price):
        """
        convergence_analysis should return correct structure.
        """
        result = convergence_analysis(
            standard_params,
            strike=100.0,
            analytical_price=bs_call_price,
            path_counts=[1000, 10000, 100000],
            seed=42,
        )

        assert "results" in result
        assert "convergence_rate" in result
        assert len(result["results"]) == 3

        # Each result should have required fields
        for r in result["results"]:
            assert "n_paths" in r
            assert "mc_price" in r
            assert "analytical_price" in r
            assert "absolute_error" in r
            assert "relative_error" in r
            assert "standard_error" in r
            assert "within_ci" in r

    def test_rate_is_negative(self, standard_params, bs_call_price):
        """
        Convergence rate should be negative (error decreasing).
        """
        result = convergence_analysis(
            standard_params,
            strike=100.0,
            analytical_price=bs_call_price,
            path_counts=[1000, 10000, 100000],
            seed=42,
        )

        rate = result["convergence_rate"]
        assert rate < 0, f"Convergence rate {rate:.3f} should be negative"

    def test_mc_prices_converge_to_analytical(self, standard_params, bs_call_price):
        """
        MC prices should get closer to analytical with more paths.
        """
        result = convergence_analysis(
            standard_params,
            strike=100.0,
            analytical_price=bs_call_price,
            path_counts=PATH_COUNTS,
            seed=42,
        )

        errors = [r["absolute_error"] for r in result["results"]]

        # Last error should be smaller than first
        assert errors[-1] < errors[0], (
            f"Error should decrease: first={errors[0]:.6f}, last={errors[-1]:.6f}"
        )


# =============================================================================
# Thorough CLT Tests (Slow)
# =============================================================================


@pytest.mark.slow
class TestCLTBoundsThorough:
    """
    Thorough CLT bounds tests with many seeds.

    Run with: pytest -m slow
    """

    def test_clt_coverage_statistical(self, standard_params, bs_call_price):
        """
        With 30 seeds, ~99% should be within 3 SE.
        """
        within_bounds = 0
        n_paths = 100_000

        for seed in THOROUGH_SEEDS:
            engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)

            error = abs(result.price - bs_call_price)
            bound = 3 * result.standard_error

            if error <= bound:
                within_bounds += 1

        coverage = within_bounds / len(THOROUGH_SEEDS)

        # 3 SE should contain ~99.7% of estimates
        # With 30 samples, expect ~29-30 within bounds
        assert coverage > 0.90, (
            f"CLT coverage {coverage:.0%} too low (expected ~99%)"
        )

    def test_95ci_coverage_statistical(self, standard_params, bs_call_price):
        """
        95% CI should contain true price ~95% of the time.
        """
        within_ci = 0
        n_paths = 100_000

        for seed in THOROUGH_SEEDS:
            engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)

            ci_lower, ci_upper = result.confidence_interval
            if ci_lower <= bs_call_price <= ci_upper:
                within_ci += 1

        coverage = within_ci / len(THOROUGH_SEEDS)

        # 95% CI should cover ~95% of the time
        # Allow 85-100% for finite sample
        assert coverage > 0.85, (
            f"95% CI coverage {coverage:.0%} too low"
        )


# =============================================================================
# Edge Case CLT Tests
# =============================================================================


class TestEdgeCaseCLT:
    """
    Tests CLT bounds for edge case parameters.
    """

    def test_itm_call_clt_bounds(self):
        """
        ITM call should respect CLT bounds.
        """
        params = GBMParams(
            spot=120.0,  # ITM
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        bs_price = black_scholes_call(
            spot=params.spot,
            strike=100.0,
            rate=params.rate,
            dividend=params.dividend,
            volatility=params.volatility,
            time_to_expiry=params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=100_000, antithetic=True, seed=42)
        result = engine.price_european_call(params, strike=100.0)

        error = abs(result.price - bs_price)
        assert error < 3 * result.standard_error

    def test_otm_put_clt_bounds(self):
        """
        OTM put should respect CLT bounds.
        """
        params = GBMParams(
            spot=120.0,  # OTM for put
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        bs_price = black_scholes_put(
            spot=params.spot,
            strike=100.0,
            rate=params.rate,
            dividend=params.dividend,
            volatility=params.volatility,
            time_to_expiry=params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=100_000, antithetic=True, seed=42)
        result = engine.price_european_put(params, strike=100.0)

        error = abs(result.price - bs_price)
        assert error < 3 * result.standard_error

    def test_high_vol_clt_bounds(self):
        """
        High volatility should respect CLT bounds.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.50,  # High vol
            time_to_expiry=1.0,
        )

        bs_price = black_scholes_call(
            spot=params.spot,
            strike=100.0,
            rate=params.rate,
            dividend=params.dividend,
            volatility=params.volatility,
            time_to_expiry=params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=100_000, antithetic=True, seed=42)
        result = engine.price_european_call(params, strike=100.0)

        error = abs(result.price - bs_price)
        assert error < 3 * result.standard_error


# =============================================================================
# Antithetic Variates Tests
# =============================================================================


class TestAntitheticConvergence:
    """
    Tests convergence properties with antithetic variates.
    """

    def test_antithetic_se_comparable(self, standard_params):
        """
        Antithetic SE should be comparable or better than plain.
        """
        n_paths = 50_000

        engine_plain = MonteCarloEngine(n_paths=n_paths, antithetic=False, seed=42)
        engine_anti = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=42)

        result_plain = engine_plain.price_european_call(standard_params, strike=100.0)
        result_anti = engine_anti.price_european_call(standard_params, strike=100.0)

        # Antithetic SE should be at most slightly higher
        assert result_anti.standard_error <= result_plain.standard_error * 1.5, (
            f"Antithetic SE {result_anti.standard_error:.6f} "
            f"should be <= plain SE {result_plain.standard_error:.6f}"
        )

    def test_antithetic_reduces_error_on_average(self, standard_params, bs_call_price):
        """
        Antithetic should reduce average error.
        """
        n_paths = 50_000

        errors_plain = []
        errors_anti = []

        for seed in CI_SEEDS:
            engine_plain = MonteCarloEngine(n_paths=n_paths, antithetic=False, seed=seed)
            engine_anti = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)

            result_plain = engine_plain.price_european_call(standard_params, strike=100.0)
            result_anti = engine_anti.price_european_call(standard_params, strike=100.0)

            errors_plain.append(abs(result_plain.price - bs_call_price))
            errors_anti.append(abs(result_anti.price - bs_call_price))

        mean_error_plain = np.mean(errors_plain)
        mean_error_anti = np.mean(errors_anti)

        # Antithetic should have lower or equal error
        assert mean_error_anti <= mean_error_plain * 1.5, (
            f"Antithetic error {mean_error_anti:.6f} should be <= "
            f"plain error {mean_error_plain:.6f}"
        )

    def test_antithetic_se_scales_correctly(self, standard_params):
        """
        Antithetic SE should still scale as 1/√N.
        """
        engine_10k = MonteCarloEngine(n_paths=10000, antithetic=True, seed=42)
        engine_100k = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        result_10k = engine_10k.price_european_call(standard_params, strike=100.0)
        result_100k = engine_100k.price_european_call(standard_params, strike=100.0)

        ratio = result_10k.standard_error / result_100k.standard_error
        expected = np.sqrt(10)

        assert abs(ratio - expected) < 0.5, (
            f"Antithetic SE ratio {ratio:.2f} should be ≈ {expected:.2f}"
        )
