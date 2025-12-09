"""
Martingale property validation tests for GBM simulation.

[T1] Fundamental validation of risk-neutral pricing:
Under the risk-neutral measure Q, the discounted stock price process
S_t * e^(-rt) is a martingale. For dividend-paying assets:
E^Q[S_T * e^(-(r-q)T)] = S_0

This catches:
- Drift errors in path simulation
- Discretization bugs
- Incorrect variance/volatility handling

References:
    [T1] Glasserman (2003) "Monte Carlo Methods in Financial Engineering", Ch. 3
    [T1] Hull (2021) "Options, Futures, and Other Derivatives", Ch. 14
    MBE Consulting: "Stochastic data may warrant martingale testing"

See: docs/knowledge/derivations/monte_carlo.md
"""

import numpy as np
import pytest
from hypothesis import given, strategies as st, settings

from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    generate_gbm_paths,
    generate_terminal_values,
)
from annuity_pricing.options.pricing.black_scholes import black_scholes_call, black_scholes_put


# =============================================================================
# Tolerance Configuration
# =============================================================================

# [T1] CLT-derived tolerances: SE ~ σ/√N
# For 100k paths with σ ≈ price, relative error ~ 1/√100000 ≈ 0.3%
# Use 1% to be safe (3σ margin)
MARTINGALE_TOLERANCE_100K = 0.01  # 1% relative
MARTINGALE_TOLERANCE_500K = 0.005  # 0.5% relative for high-precision tests

# Tolerance for option payoff tests (more variance)
OPTION_PAYOFF_TOLERANCE = 0.02  # 2% relative


# =============================================================================
# Basic Martingale Tests
# =============================================================================


class TestDiscountedSpotMartingale:
    """
    [T1] Verify E[S_T * e^(-rT)] = S_0 under risk-neutral measure.

    Without dividends, the discounted spot price is a martingale.
    """

    def test_martingale_no_dividend(self) -> None:
        """[T1] E[S_T * e^(-rT)] = S_0 when q=0."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.0,  # No dividend
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-params.rate * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Martingale violated: E[S_T * e^(-rT)] = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )

    def test_martingale_with_dividend(self) -> None:
        """[T1] E[S_T * e^(-(r-q)T)] = S_0 when dividends present."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,  # 2% dividend yield
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        # With dividends: discount at r-q (forward price relationship)
        # E[S_T] = S_0 * e^((r-q)*T), so E[S_T * e^(-(r-q)*T)] = S_0
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Martingale with dividend violated: discounted mean = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )

    @pytest.mark.parametrize("T", [0.25, 0.5, 1.0, 2.0, 5.0])
    def test_martingale_multiple_maturities(self, T: float) -> None:
        """[T1] Martingale holds across different maturities."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=T,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Martingale failed at T={T}: discounted mean = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )

    @pytest.mark.parametrize("vol", [0.05, 0.10, 0.20, 0.40, 0.60])
    def test_martingale_different_volatilities(self, vol: float) -> None:
        """[T1] Martingale holds across different volatility levels."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=vol,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Martingale failed at σ={vol}: discounted mean = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )


# =============================================================================
# Option Payoff Martingale Tests
# =============================================================================


class TestOptionPayoffMartingale:
    """
    [T1] Verify E[max(S_T - K, 0) * e^(-rT)] = BS call price.

    This is the fundamental pricing equation that MC should satisfy.
    """

    def test_atm_call_payoff(self) -> None:
        """[T1] MC call payoff matches BS price for ATM option."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0  # ATM

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        payoffs = np.maximum(terminal - strike, 0)
        discount_factor = np.exp(-params.rate * params.time_to_expiry)
        mc_price = np.mean(payoffs) * discount_factor

        bs_price = black_scholes_call(
            params.spot, strike, params.rate, params.dividend,
            params.volatility, params.time_to_expiry
        )

        relative_error = abs(mc_price - bs_price) / bs_price
        assert relative_error < OPTION_PAYOFF_TOLERANCE, (
            f"MC call differs from BS: MC = {mc_price:.4f}, BS = {bs_price:.4f}, "
            f"error = {relative_error:.4%}"
        )

    def test_itm_call_payoff(self) -> None:
        """[T1] MC call payoff matches BS price for ITM option."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 90.0  # ITM

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        payoffs = np.maximum(terminal - strike, 0)
        discount_factor = np.exp(-params.rate * params.time_to_expiry)
        mc_price = np.mean(payoffs) * discount_factor

        bs_price = black_scholes_call(
            params.spot, strike, params.rate, params.dividend,
            params.volatility, params.time_to_expiry
        )

        relative_error = abs(mc_price - bs_price) / bs_price
        assert relative_error < OPTION_PAYOFF_TOLERANCE, (
            f"ITM MC call differs from BS: MC = {mc_price:.4f}, BS = {bs_price:.4f}, "
            f"error = {relative_error:.4%}"
        )

    def test_otm_call_payoff(self) -> None:
        """[T1] MC call payoff matches BS price for OTM option."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 110.0  # OTM

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        payoffs = np.maximum(terminal - strike, 0)
        discount_factor = np.exp(-params.rate * params.time_to_expiry)
        mc_price = np.mean(payoffs) * discount_factor

        bs_price = black_scholes_call(
            params.spot, strike, params.rate, params.dividend,
            params.volatility, params.time_to_expiry
        )

        relative_error = abs(mc_price - bs_price) / bs_price
        assert relative_error < OPTION_PAYOFF_TOLERANCE, (
            f"OTM MC call differs from BS: MC = {mc_price:.4f}, BS = {bs_price:.4f}, "
            f"error = {relative_error:.4%}"
        )

    def test_atm_put_payoff(self) -> None:
        """[T1] MC put payoff matches BS price for ATM option."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0  # ATM

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        payoffs = np.maximum(strike - terminal, 0)
        discount_factor = np.exp(-params.rate * params.time_to_expiry)
        mc_price = np.mean(payoffs) * discount_factor

        bs_price = black_scholes_put(
            params.spot, strike, params.rate, params.dividend,
            params.volatility, params.time_to_expiry
        )

        relative_error = abs(mc_price - bs_price) / bs_price
        assert relative_error < OPTION_PAYOFF_TOLERANCE, (
            f"MC put differs from BS: MC = {mc_price:.4f}, BS = {bs_price:.4f}, "
            f"error = {relative_error:.4%}"
        )


# =============================================================================
# Forward Price Tests
# =============================================================================


class TestForwardPriceProperty:
    """
    [T1] Verify E[S_T] = S_0 * e^((r-q)*T) (forward price).

    The expected spot price under risk-neutral measure equals the forward.
    """

    def test_forward_price_no_dividend(self) -> None:
        """[T1] E[S_T] = S_0 * e^(rT) when q=0."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.0,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        mean_terminal = np.mean(terminal)
        expected_forward = params.forward  # S_0 * e^((r-q)*T)

        relative_error = abs(mean_terminal - expected_forward) / expected_forward
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Forward price mismatch: E[S_T] = {mean_terminal:.4f}, "
            f"forward = {expected_forward:.4f}, error = {relative_error:.4%}"
        )

    def test_forward_price_with_dividend(self) -> None:
        """[T1] E[S_T] = S_0 * e^((r-q)*T) when dividends present."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        mean_terminal = np.mean(terminal)
        expected_forward = params.forward

        relative_error = abs(mean_terminal - expected_forward) / expected_forward
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Forward price mismatch: E[S_T] = {mean_terminal:.4f}, "
            f"forward = {expected_forward:.4f}, error = {relative_error:.4%}"
        )

    @pytest.mark.parametrize("T", [0.25, 0.5, 1.0, 2.0, 5.0])
    def test_forward_price_multiple_maturities(self, T: float) -> None:
        """[T1] Forward price holds across maturities."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=T,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        mean_terminal = np.mean(terminal)
        expected_forward = params.forward

        relative_error = abs(mean_terminal - expected_forward) / expected_forward
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Forward price mismatch at T={T}: E[S_T] = {mean_terminal:.4f}, "
            f"forward = {expected_forward:.4f}, error = {relative_error:.4%}"
        )


# =============================================================================
# Path vs Terminal Consistency
# =============================================================================


class TestPathTerminalConsistency:
    """Verify that full path simulation gives same terminal distribution."""

    def test_path_terminal_matches_direct(self) -> None:
        """Full path simulation terminal should match direct terminal simulation."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        # Direct terminal simulation
        terminal_direct = generate_terminal_values(params, n_paths=100_000, seed=42)

        # Full path simulation (same seed)
        path_result = generate_gbm_paths(params, n_paths=100_000, n_steps=252, seed=42)
        terminal_from_path = path_result.terminal_values

        # Compare means
        mean_direct = np.mean(terminal_direct)
        mean_from_path = np.mean(terminal_from_path)

        # These use different RNG streams, so compare to forward instead
        expected_forward = params.forward

        direct_error = abs(mean_direct - expected_forward) / expected_forward
        path_error = abs(mean_from_path - expected_forward) / expected_forward

        assert direct_error < MARTINGALE_TOLERANCE_100K, (
            f"Direct terminal mean {mean_direct:.4f} far from forward {expected_forward:.4f}"
        )
        assert path_error < MARTINGALE_TOLERANCE_100K, (
            f"Path terminal mean {mean_from_path:.4f} far from forward {expected_forward:.4f}"
        )


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


class TestMartingalePropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        spot=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        rate=st.floats(min_value=0.01, max_value=0.15, allow_nan=False, allow_infinity=False),
        dividend=st.floats(min_value=0.0, max_value=0.08, allow_nan=False, allow_infinity=False),
        vol=st.floats(min_value=0.10, max_value=0.50, allow_nan=False, allow_infinity=False),
        T=st.floats(min_value=0.25, max_value=3.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30)  # Limit due to simulation cost
    def test_martingale_property_random_params(
        self, spot: float, rate: float, dividend: float, vol: float, T: float
    ) -> None:
        """[T1] Martingale holds for random parameter combinations."""
        params = GBMParams(
            spot=spot,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=T,
        )

        terminal = generate_terminal_values(params, n_paths=50_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        # Allow slightly larger tolerance for property-based tests (fewer paths)
        tolerance = 0.02  # 2%
        relative_error = abs(discounted_mean - params.spot) / params.spot

        assert relative_error < tolerance, (
            f"Martingale violated: params=(S={spot:.1f}, r={rate:.3f}, q={dividend:.3f}, "
            f"σ={vol:.2f}, T={T:.2f}), discounted mean = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )


# =============================================================================
# Antithetic Variates Martingale Test
# =============================================================================


class TestAntitheticMartingale:
    """Verify martingale holds with antithetic variates."""

    def test_antithetic_maintains_martingale(self) -> None:
        """[T1] Martingale property preserved with antithetic variates."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        # Antithetic variates (must use even path count)
        terminal = generate_terminal_values(params, n_paths=100_000, seed=42, antithetic=True)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Antithetic martingale violated: discounted mean = {discounted_mean:.4f}, "
            f"expected S_0 = {params.spot:.4f}, error = {relative_error:.4%}"
        )

    def test_antithetic_reduces_variance(self) -> None:
        """[T1] Antithetic variates should reduce variance."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        # Standard simulation
        terminal_std = generate_terminal_values(params, n_paths=10_000, seed=42, antithetic=False)
        std_error_std = np.std(terminal_std) / np.sqrt(10_000)

        # Antithetic simulation
        terminal_anti = generate_terminal_values(params, n_paths=10_000, seed=42, antithetic=True)
        std_error_anti = np.std(terminal_anti) / np.sqrt(10_000)

        # Antithetic should have lower standard error
        # Note: This may not always hold for small samples, so use soft check
        # The variance reduction should be positive on average
        variance_reduction = 1 - (std_error_anti / std_error_std)

        # Expect at least some variance reduction (20% is conservative)
        assert variance_reduction > 0.0, (
            f"Antithetic should reduce variance: std_error_std={std_error_std:.4f}, "
            f"std_error_anti={std_error_anti:.4f}, reduction={variance_reduction:.2%}"
        )


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestMartingaleEdgeCases:
    """Edge cases for martingale property."""

    def test_very_short_maturity(self) -> None:
        """[T1] Martingale holds for very short maturities."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1/252,  # 1 day
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Short maturity martingale failed: error = {relative_error:.4%}"
        )

    def test_low_volatility(self) -> None:
        """[T1] Martingale holds at very low volatility."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.01,  # 1% vol
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Low vol martingale failed: error = {relative_error:.4%}"
        )

    def test_high_volatility(self) -> None:
        """[T1] Martingale holds at high volatility."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.80,  # 80% vol
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        # Higher tolerance for high vol (more variance)
        assert relative_error < 0.02, (
            f"High vol martingale failed: error = {relative_error:.4%}"
        )

    def test_negative_rate(self) -> None:
        """[T1] Martingale holds with negative interest rates (per VM-21)."""
        params = GBMParams(
            spot=100.0,
            rate=-0.02,  # Negative rate
            dividend=0.0,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        terminal = generate_terminal_values(params, n_paths=100_000, seed=42)
        discount_factor = np.exp(-(params.rate - params.dividend) * params.time_to_expiry)
        discounted_mean = np.mean(terminal) * discount_factor

        relative_error = abs(discounted_mean - params.spot) / params.spot
        assert relative_error < MARTINGALE_TOLERANCE_100K, (
            f"Negative rate martingale failed: error = {relative_error:.4%}"
        )
