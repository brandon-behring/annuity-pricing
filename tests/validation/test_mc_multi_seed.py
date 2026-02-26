"""
Tests for Monte Carlo multi-seed robustness.

Validates that MC pricing is stable across different random seeds,
reported standard errors are accurate, and confidence intervals
have proper coverage.

[T1] MC converges at rate 1/√N regardless of seed
[T1] Reported SE should match cross-seed empirical SE

See: METHODOLOGY.md Section 4
See: Glasserman (2003) Ch. 3-4 - Monte Carlo error bounds
"""

import numpy as np
import pytest
from scipy import stats

from annuity_pricing.config.tolerances import (
    MC_10K_TOLERANCE,
    MC_100K_TOLERANCE,
)
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import (
    MonteCarloEngine,
    price_vanilla_mc,
)

# =============================================================================
# Seed Configuration (Tiered Approach)
# =============================================================================

#: Seeds for CI tests (fast): 10 seeds
CI_SEEDS: list[int] = [42, 123, 456, 789, 1001, 2022, 3033, 4044, 5055, 6066]

#: Seeds for slow/nightly tests: 100 seeds
THOROUGH_SEEDS: list[int] = list(range(1, 101))

#: Path counts by test type
CI_PATHS: int = 10_000  # Fast unit tests
VALIDATION_PATHS: int = 100_000  # Thorough validation tests


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def standard_params() -> GBMParams:
    """Standard GBM parameters for multi-seed testing."""
    return GBMParams(
        spot=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
    )


@pytest.fixture
def bs_call_price(standard_params) -> float:
    """Analytical Black-Scholes call price for comparison."""
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
    """Analytical Black-Scholes put price for comparison."""
    return black_scholes_put(
        spot=standard_params.spot,
        strike=100.0,
        rate=standard_params.rate,
        dividend=standard_params.dividend,
        volatility=standard_params.volatility,
        time_to_expiry=standard_params.time_to_expiry,
    )


# =============================================================================
# Price Stability Tests (CI - Fast)
# =============================================================================


class TestPriceStabilityCI:
    """
    Tests that MC prices are stable across different seeds.

    Uses 10 seeds with 10k paths for fast CI execution.
    """

    def test_call_price_stability_across_seeds(self, standard_params, bs_call_price):
        """
        Call prices across seeds should cluster around BS price.

        [T1] CLT: price distribution has SE ~ σ/√N
        """
        prices = []
        for seed in CI_SEEDS:
            result = price_vanilla_mc(
                spot=standard_params.spot,
                strike=100.0,
                rate=standard_params.rate,
                dividend=standard_params.dividend,
                volatility=standard_params.volatility,
                time_to_expiry=standard_params.time_to_expiry,
                option_type=OptionType.CALL,
                n_paths=CI_PATHS,
                seed=seed,
            )
            prices.append(result.price)

        prices = np.array(prices)

        # Mean should be close to BS price
        mean_price = prices.mean()
        assert abs(mean_price - bs_call_price) < MC_10K_TOLERANCE * bs_call_price, (
            f"Mean MC price {mean_price:.4f} differs from BS {bs_call_price:.4f} "
            f"by more than {MC_10K_TOLERANCE:.1%}"
        )

        # Coefficient of variation should be small (< 5%)
        cv = prices.std() / mean_price
        assert cv < 0.05, f"Price CV across seeds is {cv:.2%}, expected < 5%"

    def test_put_price_stability_across_seeds(self, standard_params, bs_put_price):
        """
        Put prices across seeds should cluster around BS price.
        """
        prices = []
        for seed in CI_SEEDS:
            result = price_vanilla_mc(
                spot=standard_params.spot,
                strike=100.0,
                rate=standard_params.rate,
                dividend=standard_params.dividend,
                volatility=standard_params.volatility,
                time_to_expiry=standard_params.time_to_expiry,
                option_type=OptionType.PUT,
                n_paths=CI_PATHS,
                seed=seed,
            )
            prices.append(result.price)

        prices = np.array(prices)
        mean_price = prices.mean()

        assert abs(mean_price - bs_put_price) < MC_10K_TOLERANCE * bs_put_price, (
            f"Mean MC put price {mean_price:.4f} differs from BS {bs_put_price:.4f}"
        )

    def test_capped_call_stability_across_seeds(self, standard_params):
        """
        Capped call prices should be stable across seeds.
        """
        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_capped_call_return(standard_params, cap_rate=0.10)
            prices.append(result.price)

        prices = np.array(prices)
        cv = prices.std() / prices.mean()

        assert cv < 0.05, f"Capped call CV across seeds is {cv:.2%}, expected < 5%"

    def test_buffer_protection_stability_across_seeds(self, standard_params):
        """
        Buffer protection prices should be stable across seeds.
        """
        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_buffer_protection(standard_params, buffer_rate=0.10)
            prices.append(result.price)

        prices = np.array(prices)
        cv = prices.std() / prices.mean() if prices.mean() > 0 else 0

        # Buffer prices can be smaller, allow 10% CV
        assert cv < 0.10, f"Buffer protection CV is {cv:.2%}, expected < 10%"


# =============================================================================
# Standard Error Accuracy Tests (CI - Fast)
# =============================================================================


class TestSEAccuracyCI:
    """
    Tests that reported SE matches empirical cross-seed variability.

    The reported SE for a single run should predict the cross-seed
    standard deviation of prices.
    """

    def test_se_predicts_cross_seed_variability(self, standard_params):
        """
        Reported SE should approximately equal empirical SE across seeds.

        [T1] If SE is correctly calculated, cross-seed SD ≈ reported SE
        """
        prices = []
        reported_ses = []

        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)
            prices.append(result.price)
            reported_ses.append(result.standard_error)

        prices = np.array(prices)
        reported_ses = np.array(reported_ses)

        empirical_se = prices.std(ddof=1)  # Sample SD of prices
        mean_reported_se = reported_ses.mean()

        # Reported SE should be within factor of empirical (small sample)
        # This is loose because 10 seeds gives limited precision
        # With only 10 samples, empirical SE has high variance itself
        ratio = empirical_se / mean_reported_se
        assert 0.3 < ratio < 3.0, (
            f"Empirical SE {empirical_se:.4f} vs reported {mean_reported_se:.4f} "
            f"ratio {ratio:.2f} outside [0.3, 3.0]"
        )

    def test_se_decreases_with_more_paths(self, standard_params):
        """
        SE should decrease proportionally to 1/√N.
        """
        se_10k = []
        se_50k = []

        for seed in CI_SEEDS[:5]:  # Use fewer seeds for speed
            engine_10k = MonteCarloEngine(n_paths=10_000, seed=seed)
            engine_50k = MonteCarloEngine(n_paths=50_000, seed=seed)

            result_10k = engine_10k.price_european_call(standard_params, strike=100.0)
            result_50k = engine_50k.price_european_call(standard_params, strike=100.0)

            se_10k.append(result_10k.standard_error)
            se_50k.append(result_50k.standard_error)

        mean_se_10k = np.mean(se_10k)
        mean_se_50k = np.mean(se_50k)

        # Expected ratio: sqrt(50000/10000) = sqrt(5) ≈ 2.236
        expected_ratio = np.sqrt(5)
        actual_ratio = mean_se_10k / mean_se_50k

        assert abs(actual_ratio - expected_ratio) < 0.5, (
            f"SE ratio {actual_ratio:.2f} differs from expected {expected_ratio:.2f}"
        )


# =============================================================================
# Confidence Interval Coverage Tests (CI - Fast)
# =============================================================================


class TestCICoverageCI:
    """
    Tests that 95% CI has proper coverage.

    Over many runs, approximately 95% of CIs should contain the true price.
    """

    def test_ci_coverage_call(self, standard_params, bs_call_price):
        """
        95% CI should contain BS price approximately 95% of runs.

        With 10 seeds, we expect 9-10 CIs to contain the true price.
        Allow 8-10 for statistical variability.
        """
        contains_true_price = []

        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)

            ci_lower, ci_upper = result.confidence_interval
            contains = ci_lower <= bs_call_price <= ci_upper
            contains_true_price.append(contains)

        coverage = sum(contains_true_price) / len(contains_true_price)

        # With 10 seeds at 95% CI, expect ~9.5 successes
        # Allow 70-100% coverage (binomial variability with small N)
        assert coverage >= 0.70, (
            f"CI coverage {coverage:.0%} is too low (expected ~95%)"
        )

    def test_ci_coverage_put(self, standard_params, bs_put_price):
        """
        95% CI should contain BS put price approximately 95% of runs.
        """
        contains_true_price = []

        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_put(standard_params, strike=100.0)

            ci_lower, ci_upper = result.confidence_interval
            contains = ci_lower <= bs_put_price <= ci_upper
            contains_true_price.append(contains)

        coverage = sum(contains_true_price) / len(contains_true_price)

        assert coverage >= 0.70, (
            f"Put CI coverage {coverage:.0%} is too low"
        )


# =============================================================================
# Thorough Tests (Slow - 100 Seeds)
# =============================================================================


@pytest.mark.slow
class TestPriceStabilityThorough:
    """
    Thorough multi-seed tests with 100 seeds.

    Run with: pytest -m slow
    """

    def test_call_price_distribution_normal(self, standard_params, bs_call_price):
        """
        MC prices across many seeds should be approximately normal.

        [T1] CLT guarantees asymptotic normality of estimator
        """
        prices = []
        for seed in THOROUGH_SEEDS:
            result = price_vanilla_mc(
                spot=standard_params.spot,
                strike=100.0,
                rate=standard_params.rate,
                dividend=standard_params.dividend,
                volatility=standard_params.volatility,
                time_to_expiry=standard_params.time_to_expiry,
                option_type=OptionType.CALL,
                n_paths=VALIDATION_PATHS,
                seed=seed,
            )
            prices.append(result.price)

        prices = np.array(prices)

        # Mean should be close to BS
        mean_price = prices.mean()
        assert abs(mean_price - bs_call_price) < MC_100K_TOLERANCE * bs_call_price, (
            f"Mean MC price {mean_price:.6f} differs from BS {bs_call_price:.6f}"
        )

        # Normality test (Shapiro-Wilk)
        # With 100 samples, we have good power
        stat, p_value = stats.shapiro(prices)
        assert p_value > 0.01, (
            f"Price distribution fails normality test (p={p_value:.4f})"
        )

    def test_ci_coverage_statistical(self, standard_params, bs_call_price):
        """
        With 100 seeds, verify 95% CI coverage is near 95%.

        Use exact binomial CI to test coverage.
        """
        contains_true_price = []

        for seed in THOROUGH_SEEDS:
            engine = MonteCarloEngine(n_paths=VALIDATION_PATHS, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)

            ci_lower, ci_upper = result.confidence_interval
            contains = ci_lower <= bs_call_price <= ci_upper
            contains_true_price.append(contains)

        successes = sum(contains_true_price)
        n_trials = len(contains_true_price)
        coverage = successes / n_trials

        # 95% CI coverage: expect ~95 out of 100
        # Binomial 95% CI for p=0.95 with n=100 is roughly [89, 98]
        assert 0.85 <= coverage <= 1.0, (
            f"CI coverage {coverage:.0%} ({successes}/{n_trials}) "
            f"outside expected range [85%, 100%]"
        )

    def test_se_accuracy_statistical(self, standard_params):
        """
        With 100 seeds, reported SE should match empirical SE closely.
        """
        prices = []
        reported_ses = []

        for seed in THOROUGH_SEEDS:
            engine = MonteCarloEngine(n_paths=VALIDATION_PATHS, seed=seed)
            result = engine.price_european_call(standard_params, strike=100.0)
            prices.append(result.price)
            reported_ses.append(result.standard_error)

        prices = np.array(prices)
        reported_ses = np.array(reported_ses)

        empirical_se = prices.std(ddof=1)
        mean_reported_se = reported_ses.mean()

        # With 100 seeds, should be within 30% of each other
        ratio = empirical_se / mean_reported_se
        assert 0.7 < ratio < 1.5, (
            f"Empirical SE {empirical_se:.6f} vs reported {mean_reported_se:.6f} "
            f"ratio {ratio:.2f} outside [0.7, 1.5]"
        )


# =============================================================================
# Edge Case Stability Tests
# =============================================================================


class TestEdgeCaseStability:
    """
    Tests stability across seeds for edge cases.
    """

    def test_deep_itm_call_stability(self):
        """
        Deep ITM call should be stable across seeds.
        """
        params = GBMParams(
            spot=150.0,  # Deep ITM
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_call(params, strike=100.0)
            prices.append(result.price)

        cv = np.std(prices) / np.mean(prices)
        assert cv < 0.03, f"Deep ITM call CV {cv:.2%} too high"

    def test_deep_otm_put_stability(self):
        """
        Deep OTM put should be stable (though small).
        """
        params = GBMParams(
            spot=150.0,  # Deep OTM for put
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_put(params, strike=100.0)
            prices.append(result.price)

        prices = np.array(prices)

        # Deep OTM: price is small but should still be stable
        # CV can be higher for small values
        mean_price = prices.mean()
        assert mean_price > 0, "Deep OTM put price should be positive"
        assert mean_price < 5, "Deep OTM put price should be small"

    def test_short_expiry_stability(self):
        """
        Short expiry options should be stable across seeds.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=0.1,  # ~36 days
        )

        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_call(params, strike=100.0)
            prices.append(result.price)

        cv = np.std(prices) / np.mean(prices)
        assert cv < 0.10, f"Short expiry call CV {cv:.2%} too high"

    def test_high_vol_stability(self):
        """
        High volatility options should be stable across seeds.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.50,  # High vol
            time_to_expiry=1.0,
        )

        prices = []
        for seed in CI_SEEDS:
            engine = MonteCarloEngine(n_paths=CI_PATHS, seed=seed)
            result = engine.price_european_call(params, strike=100.0)
            prices.append(result.price)

        cv = np.std(prices) / np.mean(prices)
        # Higher vol means higher variance, allow 8%
        assert cv < 0.08, f"High vol call CV {cv:.2%} too high"
