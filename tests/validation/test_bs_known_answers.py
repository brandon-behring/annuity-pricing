"""
Black-Scholes known-answer tests.

[T1] Validates BS implementation against Hull textbook examples.
These are the gold standard - if these fail, the implementation is wrong.

See: Hull, "Options, Futures, and Other Derivatives" (10th ed.)
See: CONSTITUTION.md Section 2.1
"""

import pytest
import numpy as np

from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
    black_scholes_greeks,
)
from annuity_pricing.options.payoffs.base import OptionType


class TestHullTextbookExamples:
    """
    Known-answer tests from Hull's textbook.

    [T1] These examples are academically validated.
    """

    @pytest.mark.validation
    def test_hull_example_15_6(self):
        """
        Hull Example 15.6: European call on non-dividend stock.

        Given:
        - S = 42, K = 40, r = 10%, σ = 20%, T = 0.5 years
        - Expected call price ≈ 4.76

        Reference: Hull (10th ed.) Chapter 15
        """
        S = 42.0
        K = 40.0
        r = 0.10
        q = 0.0  # No dividends
        sigma = 0.20
        T = 0.5

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        # Hull gives approximately 4.76
        assert call_price == pytest.approx(4.76, abs=0.02)

    @pytest.mark.validation
    def test_hull_example_put_price(self):
        """
        Corresponding put price for Example 15.6.

        Using put-call parity: P = C - S + K*e^(-rT)
        P ≈ 4.76 - 42 + 40*e^(-0.10*0.5) ≈ 0.81
        """
        S = 42.0
        K = 40.0
        r = 0.10
        q = 0.0
        sigma = 0.20
        T = 0.5

        put_price = black_scholes_put(S, K, r, q, sigma, T)

        # Expected from put-call parity
        expected_put = 4.76 - S + K * np.exp(-r * T)
        assert put_price == pytest.approx(expected_put, abs=0.03)

    @pytest.mark.validation
    def test_atm_option_approximation(self):
        """
        [T1] ATM approximation: C ≈ 0.4 × S × σ × √T for ATM calls.

        This is a well-known approximation for ATM options.
        """
        S = 100.0
        K = 100.0  # ATM
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        # Approximation: 0.4 × 100 × 0.20 × 1 = 8.0
        # Actual should be close
        assert 7.0 < call_price < 12.0

    @pytest.mark.validation
    def test_deep_itm_call(self):
        """
        [T1] Deep ITM call ≈ S - K*e^(-rT) (intrinsic value).
        """
        S = 150.0
        K = 100.0  # Deep ITM
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        intrinsic = S - K * np.exp(-r * T)

        # Should be close to intrinsic for deep ITM
        assert call_price >= intrinsic  # Must be >= intrinsic
        assert call_price < intrinsic + 5  # Time value diminishes for deep ITM

    @pytest.mark.validation
    def test_deep_otm_call(self):
        """
        [T1] Deep OTM call should be very small.
        """
        S = 100.0
        K = 200.0  # Deep OTM
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        # Should be nearly zero
        assert call_price < 0.01


class TestGreeksKnownValues:
    """Known-answer tests for Greeks."""

    @pytest.mark.validation
    def test_atm_call_delta(self):
        """
        [T1] ATM call delta ≈ 0.5 (slightly higher due to drift).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)

        # ATM call delta should be around 0.5-0.6
        assert 0.5 < result.delta < 0.7

    @pytest.mark.validation
    def test_put_call_delta_relationship(self):
        """
        [T1] Put delta = Call delta - e^(-qT) (for same strike).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)
        put_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.PUT)

        expected_put_delta = call_result.delta - np.exp(-q * T)
        assert put_result.delta == pytest.approx(expected_put_delta, abs=0.001)

    @pytest.mark.validation
    def test_gamma_same_for_put_call(self):
        """
        [T1] Gamma is same for put and call at same strike.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)
        put_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.PUT)

        assert call_result.gamma == pytest.approx(put_result.gamma, abs=0.0001)

    @pytest.mark.validation
    def test_vega_same_for_put_call(self):
        """
        [T1] Vega is same for put and call at same strike.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)
        put_result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.PUT)

        assert call_result.vega == pytest.approx(put_result.vega, abs=0.0001)

    @pytest.mark.validation
    def test_deep_itm_call_delta_near_one(self):
        """
        [T1] Deep ITM call should have delta near 1.
        """
        S = 150.0
        K = 100.0
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)

        assert result.delta > 0.95

    @pytest.mark.validation
    def test_deep_otm_call_delta_near_zero(self):
        """
        [T1] Deep OTM call should have delta near 0.
        """
        S = 100.0
        K = 200.0
        r = 0.05
        q = 0.0
        sigma = 0.20
        T = 1.0

        result = black_scholes_greeks(S, K, r, q, sigma, T, OptionType.CALL)

        assert result.delta < 0.05


class TestBoundaryConditions:
    """Tests for option pricing boundary conditions."""

    @pytest.mark.validation
    def test_call_lower_bound(self):
        """
        [T1] Call >= max(0, S*e^(-qT) - K*e^(-rT)).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        lower_bound = max(0, S * np.exp(-q * T) - K * np.exp(-r * T))

        assert call_price >= lower_bound - 1e-10

    @pytest.mark.validation
    def test_put_lower_bound(self):
        """
        [T1] Put >= max(0, K*e^(-rT) - S*e^(-qT)).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        put_price = black_scholes_put(S, K, r, q, sigma, T)
        lower_bound = max(0, K * np.exp(-r * T) - S * np.exp(-q * T))

        assert put_price >= lower_bound - 1e-10

    @pytest.mark.validation
    def test_call_upper_bound(self):
        """
        [T1] Call <= S*e^(-qT) (can't be worth more than underlying).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        upper_bound = S * np.exp(-q * T)

        assert call_price <= upper_bound + 1e-10

    @pytest.mark.validation
    def test_put_upper_bound(self):
        """
        [T1] Put <= K*e^(-rT) (can't be worth more than strike PV).
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        put_price = black_scholes_put(S, K, r, q, sigma, T)
        upper_bound = K * np.exp(-r * T)

        assert put_price <= upper_bound + 1e-10


class TestVolatilityMonotonicity:
    """Tests for volatility effect on option prices."""

    @pytest.mark.validation
    def test_call_increases_with_vol(self):
        """
        [T1] Call price increases with volatility.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.0
        T = 1.0

        price_low = black_scholes_call(S, K, r, q, 0.10, T)
        price_mid = black_scholes_call(S, K, r, q, 0.20, T)
        price_high = black_scholes_call(S, K, r, q, 0.30, T)

        assert price_low < price_mid < price_high

    @pytest.mark.validation
    def test_put_increases_with_vol(self):
        """
        [T1] Put price increases with volatility.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.0
        T = 1.0

        price_low = black_scholes_put(S, K, r, q, 0.10, T)
        price_mid = black_scholes_put(S, K, r, q, 0.20, T)
        price_high = black_scholes_put(S, K, r, q, 0.30, T)

        assert price_low < price_mid < price_high
