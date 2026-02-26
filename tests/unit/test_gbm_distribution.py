"""
Tests for GBM path distribution properties.

Validates that simulated paths have correct statistical properties:
- Log-returns are approximately normally distributed
- Consecutive returns are independent (no autocorrelation)
- Terminal values follow log-normal distribution

[T1] GBM SDE: dS = (r - q)S dt + σS dW
[T1] Log-returns: log(S(t+dt)/S(t)) ~ N((r-q-σ²/2)dt, σ²dt)

See: METHODOLOGY.md Section 4
See: Glasserman (2003) Ch. 3 - Generating sample paths
"""

import numpy as np
import pytest
from scipy import stats

from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    PathResult,
    generate_gbm_paths,
    generate_terminal_values,
)

# =============================================================================
# Test Configuration
# =============================================================================

#: Significance level for statistical tests
#: Use 0.01 to reduce false positives in CI
SIGNIFICANCE_LEVEL: float = 0.01

#: Number of paths for distribution tests
DIST_N_PATHS: int = 10_000

#: Number of steps for path tests
DIST_N_STEPS: int = 252  # Daily for 1 year


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def standard_params() -> GBMParams:
    """Standard GBM parameters for distribution testing."""
    return GBMParams(
        spot=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
    )


@pytest.fixture
def paths(standard_params) -> PathResult:
    """Generate paths for testing."""
    return generate_gbm_paths(
        standard_params,
        n_paths=DIST_N_PATHS,
        n_steps=DIST_N_STEPS,
        seed=42,
        antithetic=False,  # Don't use antithetic for distribution tests
    )


# =============================================================================
# Log-Return Normality Tests
# =============================================================================


class TestLogReturnNormality:
    """
    Tests that log-returns are normally distributed.

    [T1] For GBM: log(S(t+dt)/S(t)) ~ N(μdt, σ²dt)
    where μ = r - q - σ²/2
    """

    def test_single_step_log_returns_normal(self, standard_params):
        """
        Single-step log-returns should be approximately normal.

        Test on a sample of paths at a fixed time step.
        """
        # Generate paths
        paths = generate_gbm_paths(
            standard_params,
            n_paths=DIST_N_PATHS,
            n_steps=DIST_N_STEPS,
            seed=42,
            antithetic=False,
        )

        # Extract log-returns at step 100 (arbitrary mid-path)
        step = 100
        log_returns = np.log(paths.paths[:, step + 1] / paths.paths[:, step])

        # Shapiro-Wilk test for normality (on sample due to size limit)
        sample_size = min(5000, len(log_returns))
        sample = np.random.default_rng(42).choice(log_returns, sample_size, replace=False)

        stat, p_value = stats.shapiro(sample)

        assert p_value > SIGNIFICANCE_LEVEL, (
            f"Log-returns fail normality test: Shapiro-Wilk stat={stat:.4f}, "
            f"p-value={p_value:.4f} < {SIGNIFICANCE_LEVEL}"
        )

    def test_aggregate_log_returns_normal(self, standard_params):
        """
        Aggregate log-returns (over full period) should be normal.
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        log_returns = np.log(terminal / standard_params.spot)

        # Shapiro-Wilk test
        sample_size = min(5000, len(log_returns))
        sample = np.random.default_rng(42).choice(log_returns, sample_size, replace=False)

        stat, p_value = stats.shapiro(sample)

        assert p_value > SIGNIFICANCE_LEVEL, (
            f"Aggregate log-returns fail normality: p={p_value:.4f}"
        )

    def test_log_return_mean_matches_theory(self, standard_params):
        """
        Mean of log-returns should match theoretical value.

        [T1] E[log(S(T)/S(0))] = (r - q - σ²/2) * T
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        log_returns = np.log(terminal / standard_params.spot)

        # Theoretical mean
        expected_mean = (
            standard_params.rate
            - standard_params.dividend
            - 0.5 * standard_params.volatility**2
        ) * standard_params.time_to_expiry

        empirical_mean = log_returns.mean()

        # Allow 3 SE tolerance
        se = log_returns.std() / np.sqrt(len(log_returns))
        tolerance = 3 * se

        assert abs(empirical_mean - expected_mean) < tolerance, (
            f"Log-return mean {empirical_mean:.6f} differs from "
            f"theoretical {expected_mean:.6f} by more than 3 SE ({tolerance:.6f})"
        )

    def test_log_return_variance_matches_theory(self, standard_params):
        """
        Variance of log-returns should match theoretical value.

        [T1] Var[log(S(T)/S(0))] = σ² * T
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        log_returns = np.log(terminal / standard_params.spot)

        # Theoretical variance
        expected_var = standard_params.volatility**2 * standard_params.time_to_expiry

        empirical_var = log_returns.var(ddof=1)

        # Chi-squared test for variance
        # Allow 10% relative tolerance for simulation
        relative_error = abs(empirical_var - expected_var) / expected_var

        assert relative_error < 0.10, (
            f"Log-return variance {empirical_var:.6f} differs from "
            f"theoretical {expected_var:.6f} by {relative_error:.1%}"
        )


# =============================================================================
# Return Independence Tests
# =============================================================================


class TestReturnIndependence:
    """
    Tests that consecutive returns are independent.

    [T1] GBM increments are independent: W(t+s) - W(t) independent of W(t)
    """

    def test_lag1_autocorrelation_near_zero(self, paths, standard_params):
        """
        Lag-1 autocorrelation of returns should be near zero.
        """
        # Use a single path's returns (need many steps)
        # Or aggregate across paths at same lag

        # Calculate step-by-step log-returns for each path
        log_returns_all = np.log(paths.paths[:, 1:] / paths.paths[:, :-1])

        # For each path, calculate lag-1 autocorrelation
        # Use mean autocorrelation across paths
        autocorrs = []
        for i in range(min(1000, paths.n_paths)):
            returns = log_returns_all[i, :]
            if len(returns) > 10:
                # Pearson correlation between returns[:-1] and returns[1:]
                corr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
                if not np.isnan(corr):
                    autocorrs.append(corr)

        mean_autocorr = np.mean(autocorrs)

        # Should be near zero (allow ± 0.1 for finite sample)
        assert abs(mean_autocorr) < 0.1, (
            f"Mean lag-1 autocorrelation {mean_autocorr:.4f} is not near zero"
        )

    def test_ljung_box_independence(self, standard_params):
        """
        Ljung-Box test for no autocorrelation up to lag k.
        """
        from scipy.stats import chi2

        # Generate a single long path
        paths = generate_gbm_paths(
            standard_params,
            n_paths=1,
            n_steps=1000,  # Long path
            seed=42,
            antithetic=False,
        )

        log_returns = np.log(paths.paths[0, 1:] / paths.paths[0, :-1])
        n = len(log_returns)

        # Calculate autocorrelations for lags 1-10
        max_lag = 10
        autocorrs = []
        for lag in range(1, max_lag + 1):
            corr = np.corrcoef(log_returns[:-lag], log_returns[lag:])[0, 1]
            autocorrs.append(corr)

        # Ljung-Box statistic
        q_stat = n * (n + 2) * sum(
            (r**2) / (n - k - 1)
            for k, r in enumerate(autocorrs)
        )

        # Compare to chi-squared distribution with max_lag degrees of freedom
        p_value = 1 - chi2.cdf(q_stat, df=max_lag)

        assert p_value > SIGNIFICANCE_LEVEL, (
            f"Ljung-Box test rejects independence: Q={q_stat:.2f}, p={p_value:.4f}"
        )


# =============================================================================
# Terminal Value Distribution Tests
# =============================================================================


class TestTerminalDistribution:
    """
    Tests that terminal values follow log-normal distribution.

    [T1] S(T) ~ LogNormal with parameters:
         μ = log(S) + (r - q - σ²/2)T
         σ = σ√T
    """

    def test_terminal_lognormal_ks(self, standard_params):
        """
        Terminal values should pass KS test for log-normality.
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        # Theoretical log-normal parameters
        mu = np.log(standard_params.spot) + (
            standard_params.rate
            - standard_params.dividend
            - 0.5 * standard_params.volatility**2
        ) * standard_params.time_to_expiry

        sigma = standard_params.volatility * np.sqrt(standard_params.time_to_expiry)

        # KS test against theoretical log-normal
        stat, p_value = stats.kstest(
            terminal,
            'lognorm',
            args=(sigma, 0, np.exp(mu))  # shape, loc, scale for scipy
        )

        assert p_value > SIGNIFICANCE_LEVEL, (
            f"Terminal values fail log-normal KS test: stat={stat:.4f}, p={p_value:.4f}"
        )

    def test_terminal_mean_matches_forward(self, standard_params):
        """
        Mean terminal value should equal forward price.

        [T1] E[S(T)] = S * exp((r-q)*T) = Forward
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        empirical_mean = terminal.mean()
        expected_forward = standard_params.forward

        # Allow 3 SE tolerance
        se = terminal.std() / np.sqrt(len(terminal))
        tolerance = 3 * se

        assert abs(empirical_mean - expected_forward) < tolerance, (
            f"Mean terminal {empirical_mean:.4f} differs from "
            f"forward {expected_forward:.4f} by more than 3 SE"
        )

    def test_terminal_variance_matches_theory(self, standard_params):
        """
        Variance of terminal values should match theoretical.

        [T1] Var[S(T)] = S² * exp(2(r-q)T) * (exp(σ²T) - 1)
        """
        terminal = generate_terminal_values(
            standard_params,
            n_paths=DIST_N_PATHS,
            seed=42,
            antithetic=False,
        )

        empirical_var = terminal.var(ddof=1)

        # Theoretical variance
        T = standard_params.time_to_expiry
        r_q = standard_params.rate - standard_params.dividend
        sigma = standard_params.volatility

        expected_var = (
            standard_params.spot**2
            * np.exp(2 * r_q * T)
            * (np.exp(sigma**2 * T) - 1)
        )

        relative_error = abs(empirical_var - expected_var) / expected_var

        assert relative_error < 0.15, (
            f"Terminal variance {empirical_var:.4f} differs from "
            f"theoretical {expected_var:.4f} by {relative_error:.1%}"
        )


# =============================================================================
# Antithetic Variates Tests
# =============================================================================


class TestAntitheticProperties:
    """
    Tests properties specific to antithetic variates.
    """

    def test_antithetic_pairs_negatively_correlated(self, standard_params):
        """
        Antithetic pairs should be negatively correlated.
        """
        paths = generate_gbm_paths(
            standard_params,
            n_paths=1000,  # 500 pairs
            n_steps=252,
            seed=42,
            antithetic=True,
        )

        # First half and second half are pairs
        n_pairs = paths.n_paths // 2
        first_half = paths.terminal_values[:n_pairs]
        second_half = paths.terminal_values[n_pairs:]

        # Calculate correlation
        corr = np.corrcoef(first_half, second_half)[0, 1]

        # Should be negatively correlated
        assert corr < 0, f"Antithetic pairs should be negatively correlated, got {corr:.4f}"

    def test_antithetic_reduces_variance(self, standard_params):
        """
        Antithetic variates should reduce variance of estimator.
        """
        n_paths = 10_000

        # Without antithetic
        terminal_plain = generate_terminal_values(
            standard_params,
            n_paths=n_paths,
            seed=42,
            antithetic=False,
        )

        # With antithetic
        terminal_anti = generate_terminal_values(
            standard_params,
            n_paths=n_paths,
            seed=42,
            antithetic=True,
        )

        # Variance of mean estimator
        var_plain = terminal_plain.var() / n_paths
        var_anti = terminal_anti.var() / n_paths

        # Antithetic should have lower variance (or at most equal)
        # Allow small tolerance for numerical noise
        assert var_anti <= var_plain * 1.1, (
            f"Antithetic variance {var_anti:.6f} should be <= "
            f"plain variance {var_plain:.6f}"
        )

    def test_antithetic_preserves_mean(self, standard_params):
        """
        Antithetic variates should preserve mean.
        """
        terminal_plain = generate_terminal_values(
            standard_params,
            n_paths=10_000,
            seed=42,
            antithetic=False,
        )

        terminal_anti = generate_terminal_values(
            standard_params,
            n_paths=10_000,
            seed=42,
            antithetic=True,
        )

        # Means should be close
        rel_diff = abs(terminal_plain.mean() - terminal_anti.mean()) / terminal_plain.mean()

        assert rel_diff < 0.05, (
            f"Antithetic mean differs from plain by {rel_diff:.1%}"
        )


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCaseDistributions:
    """
    Tests distributions under edge case parameters.
    """

    def test_high_volatility_distribution(self):
        """
        High volatility paths should still have correct distribution.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.80,  # Very high vol
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=10_000, seed=42)

        # Should still match forward
        empirical_mean = terminal.mean()
        expected_forward = params.forward

        se = terminal.std() / np.sqrt(len(terminal))
        tolerance = 3 * se

        assert abs(empirical_mean - expected_forward) < tolerance, (
            f"High-vol mean {empirical_mean:.2f} differs from forward {expected_forward:.2f}"
        )

    def test_short_expiry_distribution(self):
        """
        Short expiry paths should have correct distribution.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=0.05,  # ~18 days
        )

        terminal = generate_terminal_values(params, n_paths=10_000, seed=42)

        # Log-returns should still be normal
        log_returns = np.log(terminal / params.spot)

        sample = np.random.default_rng(42).choice(log_returns, 5000, replace=False)
        stat, p_value = stats.shapiro(sample)

        assert p_value > SIGNIFICANCE_LEVEL, (
            f"Short expiry log-returns fail normality: p={p_value:.4f}"
        )

    def test_zero_dividend_distribution(self):
        """
        Zero dividend paths should have correct distribution.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.0,  # No dividends
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=10_000, seed=42)

        empirical_mean = terminal.mean()
        expected_forward = params.forward

        se = terminal.std() / np.sqrt(len(terminal))

        assert abs(empirical_mean - expected_forward) < 3 * se
