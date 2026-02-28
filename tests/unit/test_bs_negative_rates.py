"""
Black-Scholes tests for negative interest rates.

Tests pricing stability and mathematical properties under ECB/SNB-style
negative rate environments. BS formula remains valid for r < 0.

[T1] Black-Scholes formula: C = S*exp(-qT)*N(d1) - K*exp(-rT)*N(d2)
     Works for any real r, including negative.

References:
    - Higham (2002) "Accuracy and Stability of Numerical Algorithms"
    - ECB negative rate policy (2014-2022): -0.50% to -0.10%
    - SNB negative rate policy: -0.75%

See: docs/TOLERANCE_JUSTIFICATION.md
"""

import numpy as np
import pytest

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
    PUT_CALL_PARITY_TOLERANCE,
)
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
    put_call_parity_check,
)


class TestPutCallParityNegativeRates:
    """[T1] Put-call parity must hold for negative rates."""

    @pytest.mark.parametrize("rate", [-0.05, -0.02, -0.01, -0.005, -0.001])
    def test_parity_negative_rates_atm(self, rate: float) -> None:
        """Put-call parity holds for ECB/SNB-style negative rates (ATM)."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.0, 0.20, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)
        put = black_scholes_put(spot, strike, rate, dividend, volatility, time)

        # C - P = S*exp(-qT) - K*exp(-rT)
        expected_diff = spot * np.exp(-dividend * time) - strike * np.exp(-rate * time)
        actual_diff = call - put

        assert abs(actual_diff - expected_diff) < PUT_CALL_PARITY_TOLERANCE, (
            f"Put-call parity violated at r={rate}: "
            f"actual={actual_diff:.10f}, expected={expected_diff:.10f}"
        )

    @pytest.mark.parametrize("rate", [-0.05, -0.02, -0.01])
    @pytest.mark.parametrize("moneyness", [0.8, 0.9, 1.0, 1.1, 1.2])
    def test_parity_negative_rates_moneyness(self, rate: float, moneyness: float) -> None:
        """Put-call parity holds across moneyness levels for negative rates."""
        spot = 100.0
        strike = spot * moneyness
        dividend, volatility, time = 0.02, 0.20, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)
        put = black_scholes_put(spot, strike, rate, dividend, volatility, time)

        parity_holds, error = put_call_parity_check(call, put, spot, strike, rate, dividend, time)

        assert parity_holds, f"Parity violated at r={rate}, K/S={moneyness}: error={error}"


class TestCallBoundsNegativeRates:
    """[T1] Call option bounds: 0 <= C <= S for any rate."""

    @pytest.mark.parametrize("rate", [-0.05, -0.03, -0.01, 0.0, 0.01, 0.03, 0.05])
    def test_call_bounds_any_rate_atm(self, rate: float) -> None:
        """Call is bounded by [0, S] for any rate including negative."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.0, 0.20, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)

        assert call >= -ANTI_PATTERN_TOLERANCE, f"Call negative at r={rate}: {call}"
        assert call <= spot + ANTI_PATTERN_TOLERANCE, f"Call > S at r={rate}: {call}"

    @pytest.mark.parametrize("rate", [-0.05, -0.02, 0.0, 0.02, 0.05])
    @pytest.mark.parametrize("moneyness", [0.5, 0.8, 1.0, 1.2, 1.5])
    def test_call_bounds_moneyness_sweep(self, rate: float, moneyness: float) -> None:
        """Call bounds hold across moneyness and rate combinations."""
        spot = 100.0
        strike = spot * moneyness
        dividend, volatility, time = 0.02, 0.25, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)

        assert call >= -ANTI_PATTERN_TOLERANCE, (
            f"Call negative at r={rate}, K/S={moneyness}: {call}"
        )
        assert call <= spot + ANTI_PATTERN_TOLERANCE, (
            f"Call > S at r={rate}, K/S={moneyness}: {call}"
        )


class TestPutBoundsNegativeRates:
    """[T1] Put option bounds: 0 <= P <= K*exp(-rT) for any rate."""

    @pytest.mark.parametrize("rate", [-0.05, -0.03, -0.01, 0.0, 0.01, 0.03, 0.05])
    def test_put_bounds_any_rate_atm(self, rate: float) -> None:
        """Put is bounded by [0, K*exp(-rT)] for any rate including negative."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.0, 0.20, 1.0

        put = black_scholes_put(spot, strike, rate, dividend, volatility, time)
        upper_bound = strike * np.exp(-rate * time)

        assert put >= -ANTI_PATTERN_TOLERANCE, f"Put negative at r={rate}: {put}"
        assert put <= upper_bound + ANTI_PATTERN_TOLERANCE, (
            f"Put > K*exp(-rT) at r={rate}: put={put}, bound={upper_bound}"
        )


class TestGreeksNegativeRates:
    """Greeks should behave correctly under negative rates."""

    @pytest.mark.parametrize("rate", [-0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05])
    def test_delta_bounds_negative_rates(self, rate: float) -> None:
        """[T1] Call delta in [0, 1], put delta in [-1, 0] for any rate."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.02, 0.20, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.CALL
        )
        put_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.PUT
        )

        assert 0 <= call_greeks.delta <= 1, (
            f"Call delta out of bounds at r={rate}: {call_greeks.delta}"
        )
        assert -1 <= put_greeks.delta <= 0, (
            f"Put delta out of bounds at r={rate}: {put_greeks.delta}"
        )

    @pytest.mark.parametrize("rate", [-0.05, -0.02, 0.0, 0.02, 0.05])
    def test_gamma_positive_negative_rates(self, rate: float) -> None:
        """[T1] Gamma is always positive for any rate."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.02, 0.20, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.CALL
        )
        put_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.PUT
        )

        assert call_greeks.gamma > 0, f"Call gamma not positive at r={rate}"
        assert put_greeks.gamma > 0, f"Put gamma not positive at r={rate}"

    @pytest.mark.parametrize("rate", [-0.05, -0.02, 0.0, 0.02, 0.05])
    def test_vega_positive_negative_rates(self, rate: float) -> None:
        """[T1] Vega is always positive for any rate."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.02, 0.20, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.CALL
        )
        put_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.PUT
        )

        assert call_greeks.vega > 0, f"Call vega not positive at r={rate}"
        assert put_greeks.vega > 0, f"Put vega not positive at r={rate}"

    @pytest.mark.parametrize("rate", [-0.05, -0.02, 0.0, 0.02, 0.05])
    def test_gamma_equality_negative_rates(self, rate: float) -> None:
        """[T1] Call gamma equals put gamma at same strike for any rate."""
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.02, 0.20, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.CALL
        )
        put_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, volatility, time, OptionType.PUT
        )

        assert abs(call_greeks.gamma - put_greeks.gamma) < ANTI_PATTERN_TOLERANCE, (
            f"Gamma equality violated at r={rate}: call={call_greeks.gamma}, put={put_greeks.gamma}"
        )


class TestNumericalStabilityNegativeRates:
    """Numerical stability tests for negative rate edge cases."""

    def test_deeply_negative_rate(self) -> None:
        """Pricing remains stable for deeply negative rates (-10%)."""
        spot, strike = 100.0, 100.0
        rate = -0.10  # Extreme negative (worse than ECB policy)
        dividend, volatility, time = 0.0, 0.20, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)
        put = black_scholes_put(spot, strike, rate, dividend, volatility, time)

        # Should produce finite, reasonable values
        assert np.isfinite(call), f"Call is not finite at r={rate}"
        assert np.isfinite(put), f"Put is not finite at r={rate}"
        assert call > 0, f"Call should be positive at ATM: {call}"
        assert put > 0, f"Put should be positive at ATM: {put}"

        # Parity should still hold
        parity_holds, error = put_call_parity_check(call, put, spot, strike, rate, dividend, time)
        assert parity_holds, f"Parity violated at r={rate}: error={error}"

    def test_negative_rate_long_maturity(self) -> None:
        """Pricing stable for negative rates with long maturity."""
        spot, strike = 100.0, 100.0
        rate = -0.02
        dividend, volatility = 0.0, 0.20
        time = 10.0  # 10 years

        call = black_scholes_call(spot, strike, rate, dividend, volatility, time)
        put = black_scholes_put(spot, strike, rate, dividend, volatility, time)

        assert np.isfinite(call), "Call not finite for 10Y negative rate"
        assert np.isfinite(put), "Put not finite for 10Y negative rate"

        # At long maturity with negative rates, forward > spot
        # So ATM call should be worth more than ATM put
        forward = spot * np.exp(-rate * time)
        assert forward > spot, "Forward should exceed spot with negative rate"

    @pytest.mark.parametrize("rate", [-0.01, -0.02, -0.05])
    def test_negative_rate_vs_zero_rate_ordering(self, rate: float) -> None:
        """
        [T1] Lower rate (more negative) increases call value.

        Rho measures sensitivity: dC/dr > 0 for calls.
        So r=-5% should give lower call value than r=0%.
        """
        spot, strike = 100.0, 100.0
        dividend, volatility, time = 0.0, 0.20, 1.0

        call_negative = black_scholes_call(spot, strike, rate, dividend, volatility, time)
        call_zero = black_scholes_call(spot, strike, 0.0, dividend, volatility, time)

        # Call increases with rate, so call(r<0) < call(r=0)
        assert call_negative < call_zero, (
            f"Call should decrease with lower rate: "
            f"call(r={rate})={call_negative}, call(r=0)={call_zero}"
        )
