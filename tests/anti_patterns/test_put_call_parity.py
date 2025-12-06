"""
Anti-pattern test: Put-call parity verification.

[T1] Any Black-Scholes implementation MUST satisfy put-call parity.
C - P = S*e^(-qT) - K*e^(-rT)

HALT if parity violated by more than tolerance.

See: CONSTITUTION.md Section 2.1
See: docs/knowledge/domain/option_pricing.md
"""

import pytest
import numpy as np

from annuity_pricing.config.settings import SETTINGS
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
    put_call_parity_check,
)


class TestPutCallParity:
    """Test put-call parity for option pricing."""

    @pytest.mark.anti_pattern
    def test_put_call_parity_atm(self) -> None:
        """
        [T1] Put-call parity must hold for ATM options.

        C - P = S*e^(-qT) - K*e^(-rT)
        """
        S = 100.0
        K = 100.0  # ATM
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        # Expected parity value
        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        # Use actual BS implementation
        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION:\n"
            f"  C - P = {actual_diff:.6f}\n"
            f"  Expected: {expected_diff:.6f}\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}\n"
            f"  Tolerance: {tolerance}\n"
            f"  Check Black-Scholes implementation."
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_itm_call(self) -> None:
        """
        [T1] Put-call parity must hold for ITM calls.
        """
        S = 100.0
        K = 90.0  # ITM call
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (ITM Call):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_otm_call(self) -> None:
        """
        [T1] Put-call parity must hold for OTM calls.
        """
        S = 100.0
        K = 110.0  # OTM call
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (OTM Call):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_short_maturity(self) -> None:
        """
        [T1] Put-call parity must hold for short maturities.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 0.1  # ~5 weeks

        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (Short Maturity):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_long_maturity(self) -> None:
        """
        [T1] Put-call parity must hold for long maturities.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 5.0  # 5 years

        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (Long Maturity):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_high_vol(self) -> None:
        """
        [T1] Put-call parity must hold regardless of volatility.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.50  # High volatility
        T = 1.0

        expected_diff = S * np.exp(-q * T) - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (High Vol):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_zero_dividend(self) -> None:
        """
        [T1] Put-call parity must hold with zero dividends.

        C - P = S - K*e^(-rT)  (when q=0)
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.0  # No dividends
        sigma = 0.20
        T = 1.0

        expected_diff = S - K * np.exp(-r * T)

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        actual_diff = call_price - put_price

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"PUT-CALL PARITY VIOLATION (Zero Dividend):\n"
            f"  Error: {abs(actual_diff - expected_diff):.6f}"
        )

    @pytest.mark.anti_pattern
    def test_put_call_parity_check_function(self) -> None:
        """
        [T1] Test the put_call_parity_check helper function.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)
        put_price = black_scholes_put(S, K, r, q, sigma, T)

        is_valid, error = put_call_parity_check(
            call_price, put_price, S, K, r, q, T
        )

        assert is_valid, f"Put-call parity check failed with error: {error}"

    @pytest.mark.anti_pattern
    def test_put_call_parity_detects_violation(self) -> None:
        """
        [T1] put_call_parity_check should detect violations.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        T = 1.0

        # Intentionally wrong prices that violate parity
        call_price = 15.0
        put_price = 5.0

        is_valid, error = put_call_parity_check(
            call_price, put_price, S, K, r, q, T, tolerance=0.01
        )

        assert not is_valid, "Should detect parity violation"
        assert error > 0.01, f"Error should exceed tolerance: {error}"


class TestParameterizedPutCallParity:
    """Parametrized put-call parity tests across parameter space [Step 7]."""

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize(
        "S,K,r,q,sigma,T",
        [
            # ATM variations
            (100, 100, 0.05, 0.02, 0.20, 1.0),    # Standard ATM
            (100, 100, 0.05, 0.02, 0.40, 1.0),    # High vol ATM
            (100, 100, 0.10, 0.00, 0.20, 1.0),    # High rate, no dividend
            (100, 100, 0.02, 0.05, 0.20, 1.0),    # Dividend > rate
            # ITM variations
            (100, 80, 0.05, 0.02, 0.20, 1.0),     # Deep ITM call
            (100, 90, 0.05, 0.02, 0.30, 0.5),     # ITM call, short term
            # OTM variations
            (100, 110, 0.05, 0.02, 0.20, 1.0),    # OTM call
            (100, 120, 0.03, 0.01, 0.15, 2.0),    # Deep OTM call, long term
            # Extreme parameters
            (50, 50, 0.08, 0.00, 0.50, 0.25),     # High vol, short term
            (200, 180, 0.02, 0.03, 0.25, 3.0),    # Large notional, long term
            (100, 100, 0.01, 0.01, 0.10, 5.0),    # Low rates, very long term
        ],
    )
    def test_put_call_parity_sweep(
        self, S: float, K: float, r: float, q: float, sigma: float, T: float
    ) -> None:
        """
        [T1] Put-call parity: C - P = S*e^(-qT) - K*e^(-rT)

        Tests 11 parameter combinations per audit recommendation.
        """
        call = black_scholes_call(S, K, r, q, sigma, T)
        put = black_scholes_put(S, K, r, q, sigma, T)

        expected = S * np.exp(-q * T) - K * np.exp(-r * T)
        actual = call - put

        tolerance = SETTINGS.option.put_call_parity_tolerance

        assert abs(actual - expected) < tolerance, (
            f"PUT-CALL PARITY VIOLATION:\n"
            f"  Params: S={S}, K={K}, r={r}, q={q}, σ={sigma}, T={T}\n"
            f"  C - P = {actual:.6f}\n"
            f"  Expected = {expected:.6f}\n"
            f"  Error = {abs(actual - expected):.6f}"
        )
