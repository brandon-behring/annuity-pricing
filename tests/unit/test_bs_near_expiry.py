"""
Black-Scholes tests for near-expiry behavior.

Tests pricing stability and convergence to intrinsic value as T → 0.
Near-expiry options present numerical challenges due to:
- Division by √T in d1/d2 calculations
- Rapid gamma increase (gamma blowup)
- Delta approaching step function

[T1] At T = 0: C = max(S - K, 0), P = max(K - S, 0)
[T1] As T → 0: options converge to intrinsic value

References:
    - Higham (2002) Ch. 1 - Condition numbers and numerical stability
    - Hull (2021) Ch. 19 - Greeks at expiry

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


class TestExpiryLimitCall:
    """[T1] Call converges to intrinsic value as T → 0."""

    def test_atm_call_to_zero_at_expiry(self) -> None:
        """ATM call → 0 as T → 0."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.1, 0.01, 0.001, 0.0001, 0.0]
        calls = [black_scholes_call(spot, strike, rate, dividend, sigma, t) for t in times]

        # Should be monotonically decreasing toward 0
        for i in range(len(calls) - 1):
            assert calls[i] >= calls[i + 1] - ANTI_PATTERN_TOLERANCE, (
                f"ATM call not decreasing: C(T={times[i]})={calls[i]}, "
                f"C(T={times[i + 1]})={calls[i + 1]}"
            )

        # At T=0, should be exactly 0 (ATM intrinsic)
        assert abs(calls[-1]) < ANTI_PATTERN_TOLERANCE, (
            f"ATM call at expiry should be 0: {calls[-1]}"
        )

    def test_itm_call_to_intrinsic_at_expiry(self) -> None:
        """ITM call → intrinsic value as T → 0."""
        spot, strike = 110.0, 100.0  # ITM
        rate, dividend, sigma = 0.05, 0.0, 0.20
        intrinsic = spot - strike  # 10

        times = [1.0, 0.1, 0.01, 0.001, 0.0001, 0.0]
        calls = [black_scholes_call(spot, strike, rate, dividend, sigma, t) for t in times]

        # Should converge to intrinsic
        assert abs(calls[-1] - intrinsic) < ANTI_PATTERN_TOLERANCE, (
            f"ITM call at expiry should be {intrinsic}: got {calls[-1]}"
        )

        # Time value should decrease
        for i in range(len(calls) - 1):
            time_value_i = calls[i] - intrinsic
            time_value_next = calls[i + 1] - intrinsic
            # Time value decreases (approximately, allowing small tolerance)
            assert time_value_next <= time_value_i + 0.01, (
                f"Time value not decreasing properly: "
                f"TV(T={times[i]})={time_value_i}, TV(T={times[i + 1]})={time_value_next}"
            )

    def test_otm_call_to_zero_at_expiry(self) -> None:
        """OTM call → 0 as T → 0."""
        spot, strike = 90.0, 100.0  # OTM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.1, 0.01, 0.001, 0.0001, 0.0]
        calls = [black_scholes_call(spot, strike, rate, dividend, sigma, t) for t in times]

        # Should converge to 0
        assert abs(calls[-1]) < ANTI_PATTERN_TOLERANCE, (
            f"OTM call at expiry should be 0: {calls[-1]}"
        )


class TestExpiryLimitPut:
    """[T1] Put converges to intrinsic value as T → 0."""

    def test_atm_put_to_zero_at_expiry(self) -> None:
        """ATM put → 0 as T → 0."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.1, 0.01, 0.001, 0.0]
        puts = [black_scholes_put(spot, strike, rate, dividend, sigma, t) for t in times]

        # At T=0, should be exactly 0
        assert abs(puts[-1]) < ANTI_PATTERN_TOLERANCE, f"ATM put at expiry should be 0: {puts[-1]}"

    def test_itm_put_to_intrinsic_at_expiry(self) -> None:
        """ITM put → intrinsic value as T → 0."""
        spot, strike = 90.0, 100.0  # ITM put
        rate, dividend, sigma = 0.05, 0.0, 0.20
        intrinsic = strike - spot  # 10

        puts = [
            black_scholes_put(spot, strike, rate, dividend, sigma, t)
            for t in [1.0, 0.1, 0.01, 0.001, 0.0]
        ]

        assert abs(puts[-1] - intrinsic) < ANTI_PATTERN_TOLERANCE, (
            f"ITM put at expiry should be {intrinsic}: got {puts[-1]}"
        )


class TestNearExpiryStability:
    """Numerical stability for very small T."""

    @pytest.mark.parametrize(
        "time_to_expiry",
        [1e-4, 1e-5, 1e-6, 1e-7, 1e-8],
    )
    def test_no_nan_near_expiry(self, time_to_expiry: float) -> None:
        """No NaN/Inf for microseconds to expiry."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time_to_expiry)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time_to_expiry)

        assert np.isfinite(call), f"Call is NaN/Inf at T={time_to_expiry}"
        assert np.isfinite(put), f"Put is NaN/Inf at T={time_to_expiry}"

    @pytest.mark.parametrize("time_to_expiry", [1e-4, 1e-6, 1e-8])
    @pytest.mark.parametrize("moneyness", [0.9, 1.0, 1.1])
    def test_no_nan_moneyness_grid(self, time_to_expiry: float, moneyness: float) -> None:
        """No NaN/Inf across moneyness at near-expiry."""
        spot = 100.0
        strike = spot * moneyness
        rate, dividend, sigma = 0.05, 0.02, 0.20

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time_to_expiry)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time_to_expiry)

        assert np.isfinite(call), f"Call is NaN/Inf at T={time_to_expiry}, K/S={moneyness}"
        assert np.isfinite(put), f"Put is NaN/Inf at T={time_to_expiry}, K/S={moneyness}"

    def test_bounds_hold_near_expiry(self) -> None:
        """Option bounds hold even at very small T."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20

        for time in [1e-4, 1e-6, 1e-8]:
            call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
            put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

            assert call >= -ANTI_PATTERN_TOLERANCE, f"Call negative at T={time}"
            assert call <= spot + ANTI_PATTERN_TOLERANCE, f"Call > S at T={time}"
            assert put >= -ANTI_PATTERN_TOLERANCE, f"Put negative at T={time}"
            assert put <= strike + ANTI_PATTERN_TOLERANCE, f"Put > K at T={time}"


class TestPutCallParityNearExpiry:
    """[T1] Put-call parity must hold at near-expiry."""

    @pytest.mark.parametrize(
        "time_to_expiry",
        [0.001, 0.0001, 1e-5, 1e-6],
    )
    def test_parity_near_expiry_atm(self, time_to_expiry: float) -> None:
        """Put-call parity holds at near-expiry (ATM)."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time_to_expiry)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time_to_expiry)

        # Use slightly looser tolerance near expiry due to numerical issues
        # But still much tighter than old 0.01 tolerance
        parity_tolerance = max(PUT_CALL_PARITY_TOLERANCE, 1e-6)
        parity_holds, error = put_call_parity_check(
            call,
            put,
            spot,
            strike,
            rate,
            dividend,
            time_to_expiry,
            tolerance=parity_tolerance,
        )

        assert parity_holds, f"Parity violated at T={time_to_expiry}: error={error}"

    @pytest.mark.parametrize("time_to_expiry", [0.001, 1e-5])
    @pytest.mark.parametrize("moneyness", [0.9, 1.0, 1.1])
    def test_parity_near_expiry_moneyness(self, time_to_expiry: float, moneyness: float) -> None:
        """Parity holds across moneyness at near-expiry."""
        spot = 100.0
        strike = spot * moneyness
        rate, dividend, sigma = 0.05, 0.02, 0.20

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time_to_expiry)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time_to_expiry)

        parity_tolerance = max(PUT_CALL_PARITY_TOLERANCE, 1e-6)
        parity_holds, error = put_call_parity_check(
            call,
            put,
            spot,
            strike,
            rate,
            dividend,
            time_to_expiry,
            tolerance=parity_tolerance,
        )

        assert parity_holds, (
            f"Parity violated at T={time_to_expiry}, K/S={moneyness}: error={error}"
        )


class TestGreeksNearExpiry:
    """Greeks behavior at near-expiry."""

    def test_delta_approaches_step_function_itm_call(self) -> None:
        """[T1] ITM call delta → 1 as T → 0."""
        spot, strike = 110.0, 100.0  # ITM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.1, 0.01, 0.001]
        deltas = []
        for t in times:
            greeks = black_scholes_greeks(spot, strike, rate, dividend, sigma, t, OptionType.CALL)
            deltas.append(greeks.delta)

        # Delta should increase toward 1 for ITM
        for i in range(len(deltas) - 1):
            assert deltas[i] <= deltas[i + 1] + 0.01, (
                f"ITM delta not increasing: Δ(T={times[i]})={deltas[i]}"
            )

        # At very short T, delta should be close to 1
        assert deltas[-1] > 0.99, f"ITM delta should approach 1: {deltas[-1]}"

    def test_delta_approaches_step_function_otm_call(self) -> None:
        """[T1] OTM call delta → 0 as T → 0."""
        spot, strike = 90.0, 100.0  # OTM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.1, 0.01, 0.001]
        deltas = []
        for t in times:
            greeks = black_scholes_greeks(spot, strike, rate, dividend, sigma, t, OptionType.CALL)
            deltas.append(greeks.delta)

        # Delta should decrease toward 0 for OTM
        for i in range(len(deltas) - 1):
            assert deltas[i] >= deltas[i + 1] - 0.01, (
                f"OTM delta not decreasing: Δ(T={times[i]})={deltas[i]}"
            )

        # At very short T, delta should be close to 0
        assert deltas[-1] < 0.01, f"OTM delta should approach 0: {deltas[-1]}"

    def test_gamma_increases_near_expiry_atm(self) -> None:
        """[T1] ATM gamma increases as T → 0 (gamma blowup)."""
        spot, strike = 100.0, 100.0  # ATM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [1.0, 0.5, 0.1, 0.05, 0.01]
        gammas = []
        for t in times:
            greeks = black_scholes_greeks(spot, strike, rate, dividend, sigma, t, OptionType.CALL)
            gammas.append(greeks.gamma)

        # Gamma should increase for ATM as T decreases
        for i in range(len(gammas) - 1):
            assert gammas[i] < gammas[i + 1], (
                f"ATM gamma not increasing: Γ(T={times[i]})={gammas[i]}, "
                f"Γ(T={times[i + 1]})={gammas[i + 1]}"
            )

    def test_greeks_finite_near_expiry(self) -> None:
        """All Greeks remain finite (no blowup to Inf) at small but non-zero T."""
        spot, strike = 100.0, 100.0
        rate, dividend, sigma = 0.05, 0.0, 0.20
        time = 0.001  # 1 day

        greeks = black_scholes_greeks(spot, strike, rate, dividend, sigma, time, OptionType.CALL)

        assert np.isfinite(greeks.delta), "Delta not finite near expiry"
        assert np.isfinite(greeks.gamma), "Gamma not finite near expiry"
        assert np.isfinite(greeks.vega), "Vega not finite near expiry"
        assert np.isfinite(greeks.theta), "Theta not finite near expiry"
        assert np.isfinite(greeks.rho), "Rho not finite near expiry"


class TestTimeMonotonicity:
    """[T1] Option time value decreases as T → 0 (theta always negative for long)."""

    def test_call_time_value_decreases(self) -> None:
        """Call time value (extrinsic) decreases with T for ATM."""
        spot, strike = 100.0, 100.0  # ATM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [2.0, 1.0, 0.5, 0.25, 0.1, 0.01]
        calls = [black_scholes_call(spot, strike, rate, dividend, sigma, t) for t in times]

        # ATM call value decreases with time (all time value)
        for i in range(len(calls) - 1):
            assert calls[i] > calls[i + 1], (
                f"ATM call not decreasing: C(T={times[i]})={calls[i]}, "
                f"C(T={times[i + 1]})={calls[i + 1]}"
            )

    def test_put_time_value_decreases(self) -> None:
        """Put time value (extrinsic) decreases with T for ATM."""
        spot, strike = 100.0, 100.0  # ATM
        rate, dividend, sigma = 0.05, 0.0, 0.20

        times = [2.0, 1.0, 0.5, 0.25, 0.1, 0.01]
        puts = [black_scholes_put(spot, strike, rate, dividend, sigma, t) for t in times]

        # ATM put value decreases with time
        for i in range(len(puts) - 1):
            assert puts[i] > puts[i + 1], (
                f"ATM put not decreasing: P(T={times[i]})={puts[i]}, "
                f"P(T={times[i + 1]})={puts[i + 1]}"
            )
