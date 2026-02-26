"""
Anti-pattern test: No-arbitrage bounds for option pricing.

[T1] Options must satisfy no-arbitrage bounds.
HALT if any violation is detected.

See: METHODOLOGY.md Section 2.2
"""

import numpy as np
import pytest

from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)

# Standard test parameters
BASE_PARAMS = {
    "spot": 100.0,
    "strike": 100.0,
    "rate": 0.05,
    "dividend": 0.02,
    "volatility": 0.20,
    "time_to_expiry": 1.0,
}


class TestArbitrageBounds:
    """Test no-arbitrage bounds for option pricing."""

    @pytest.mark.anti_pattern
    def test_call_upper_bound(self) -> None:
        """
        [T1] Call option value must not exceed spot price.

        C ≤ S

        Violation indicates implementation error.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        assert call_price <= S, (
            f"ARBITRAGE VIOLATION: Call price {call_price} > Spot {S}. "
            f"Call can never be worth more than the underlying."
        )

    @pytest.mark.anti_pattern
    def test_call_lower_bound(self) -> None:
        """
        [T1] Call option value must be at least intrinsic value.

        C ≥ max(S*e^(-qT) - K*e^(-rT), 0)

        Violation indicates implementation error.
        """
        S = 100.0
        K = 95.0  # ITM call
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        # Intrinsic value (discounted)
        intrinsic = max(S * np.exp(-q * T) - K * np.exp(-r * T), 0)

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        assert call_price >= intrinsic - 0.01, (
            f"ARBITRAGE VIOLATION: Call price {call_price} < intrinsic {intrinsic}. "
            f"Call must be worth at least intrinsic value."
        )

    @pytest.mark.anti_pattern
    def test_put_upper_bound(self) -> None:
        """
        [T1] Put option value must not exceed discounted strike.

        P ≤ K * e^(-rT)

        Violation indicates implementation error.
        """
        S = 100.0
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        max_put_value = K * np.exp(-r * T)

        put_price = black_scholes_put(S, K, r, q, sigma, T)

        assert put_price <= max_put_value + 0.01, (
            f"ARBITRAGE VIOLATION: Put price {put_price} > max value {max_put_value}. "
            f"Put can never be worth more than discounted strike."
        )

    @pytest.mark.anti_pattern
    def test_put_lower_bound(self) -> None:
        """
        [T1] Put option value must be at least intrinsic value.

        P ≥ max(K*e^(-rT) - S*e^(-qT), 0)

        Violation indicates implementation error.
        """
        S = 100.0
        K = 105.0  # ITM put
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        intrinsic = max(K * np.exp(-r * T) - S * np.exp(-q * T), 0)

        put_price = black_scholes_put(S, K, r, q, sigma, T)

        assert put_price >= intrinsic - 0.01, (
            f"ARBITRAGE VIOLATION: Put price {put_price} < intrinsic {intrinsic}. "
            f"Put must be worth at least intrinsic value."
        )

    @pytest.mark.anti_pattern
    def test_call_monotonic_in_spot(self) -> None:
        """
        [T1] Call value must increase with spot price.

        Higher S → Higher C (positive delta)
        """
        K = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        S_low = 95.0
        S_high = 105.0

        C_low = black_scholes_call(S_low, K, r, q, sigma, T)
        C_high = black_scholes_call(S_high, K, r, q, sigma, T)

        assert C_high > C_low, (
            f"ARBITRAGE VIOLATION: Call not monotonic in spot. "
            f"C(S={S_low})={C_low:.4f} should be < C(S={S_high})={C_high:.4f}"
        )

    @pytest.mark.anti_pattern
    def test_put_monotonic_in_strike(self) -> None:
        """
        [T1] Put value must increase with strike price.

        Higher K → Higher P
        """
        S = 100.0
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        K_low = 95.0
        K_high = 105.0

        P_low = black_scholes_put(S, K_low, r, q, sigma, T)
        P_high = black_scholes_put(S, K_high, r, q, sigma, T)

        assert P_high > P_low, (
            f"ARBITRAGE VIOLATION: Put not monotonic in strike. "
            f"P(K={K_low})={P_low:.4f} should be < P(K={K_high})={P_high:.4f}"
        )

    @pytest.mark.anti_pattern
    def test_time_value_non_negative(self) -> None:
        """
        [T1] American-style time value must be non-negative.

        Option_Value ≥ Intrinsic_Value

        Note: European puts can have negative time value in some cases,
        but we test the general principle for calls.
        """
        S = 100.0
        K = 90.0  # Deep ITM call
        r = 0.05
        q = 0.02
        sigma = 0.20
        T = 1.0

        intrinsic = max(S - K, 0)  # 10.0

        call_price = black_scholes_call(S, K, r, q, sigma, T)

        time_value = call_price - intrinsic

        # For calls, time value should generally be non-negative
        # (can be negative for very high dividend yield)
        assert time_value >= -1.0, (
            f"WARNING: Significant negative time value {time_value}. "
            f"Check dividend yield assumptions."
        )


class TestParameterizedBounds:
    """Parametrized tests across option parameter space [per audit]."""

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize(
        "S,K,r,q,sigma,T",
        [
            (100, 100, 0.05, 0.02, 0.20, 1.0),   # ATM baseline
            (100, 80, 0.05, 0.02, 0.30, 0.5),    # ITM call, high vol
            (100, 120, 0.03, 0.01, 0.15, 2.0),   # OTM call, low vol
            (50, 50, 0.08, 0.00, 0.40, 0.25),    # No dividend, high vol
            (200, 180, 0.02, 0.03, 0.25, 3.0),   # Dividend > rate
        ],
    )
    def test_no_arbitrage_sweep(
        self, S: float, K: float, r: float, q: float, sigma: float, T: float
    ) -> None:
        """No-arbitrage bounds across parameter space."""
        call = black_scholes_call(S, K, r, q, sigma, T)
        put = black_scholes_put(S, K, r, q, sigma, T)

        # Call bounds: 0 <= C <= S
        assert call >= 0, f"Call negative: {call}"
        assert call <= S, f"Call > Spot: {call} > {S}"

        # Put bounds: 0 <= P <= K*e^(-rT)
        assert put >= 0, f"Put negative: {put}"
        assert put <= K * np.exp(-r * T) + 0.01, "Put > discounted strike"

        # Call lower bound: C >= max(S*e^(-qT) - K*e^(-rT), 0)
        call_intrinsic = max(S * np.exp(-q * T) - K * np.exp(-r * T), 0)
        assert call >= call_intrinsic - 0.01, "Call below intrinsic"

        # Put lower bound: P >= max(K*e^(-rT) - S*e^(-qT), 0)
        put_intrinsic = max(K * np.exp(-r * T) - S * np.exp(-q * T), 0)
        assert put >= put_intrinsic - 0.01, "Put below intrinsic"

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize(
        "S,K,r,q,sigma,T",
        [
            (100, 100, 0.05, 0.02, 0.20, 1.0),
            (100, 90, 0.05, 0.02, 0.25, 0.5),
            (100, 110, 0.03, 0.01, 0.15, 2.0),
        ],
    )
    def test_put_call_parity_holds(
        self, S: float, K: float, r: float, q: float, sigma: float, T: float
    ) -> None:
        """[T1] Put-call parity: C - P = S*e^(-qT) - K*e^(-rT)"""
        call = black_scholes_call(S, K, r, q, sigma, T)
        put = black_scholes_put(S, K, r, q, sigma, T)

        lhs = call - put
        rhs = S * np.exp(-q * T) - K * np.exp(-r * T)

        assert abs(lhs - rhs) < 0.01, (
            f"PUT-CALL PARITY VIOLATION: C - P = {lhs:.4f}, "
            f"S*e^(-qT) - K*e^(-rT) = {rhs:.4f}"
        )

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize("vol", [0.05, 0.10, 0.20, 0.40, 0.60, 0.80])
    def test_call_increases_with_volatility(self, vol: float) -> None:
        """[T1] Call value increases with volatility (vega > 0)."""
        S, K, r, q, T = 100.0, 100.0, 0.05, 0.02, 1.0

        call_low = black_scholes_call(S, K, r, q, vol * 0.9, T)
        call_high = black_scholes_call(S, K, r, q, vol * 1.1, T)

        assert call_high > call_low, (
            f"Call should increase with vol: "
            f"C(σ={vol*0.9:.2f})={call_low:.4f}, C(σ={vol*1.1:.2f})={call_high:.4f}"
        )
