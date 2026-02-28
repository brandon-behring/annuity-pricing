"""
Black-Scholes tests for extreme volatility levels.

Tests pricing stability and mathematical properties under extreme volatility:
- Near-zero volatility (σ = 0.1%): deterministic limit
- High volatility (σ = 100%+): crisis conditions
- VIX historical extremes: ~12% (calm) to ~80% (2008 crisis)

[T1] BS formula remains valid for any σ > 0, though numerical precision degrades
     at extremes.

References:
    - Glasserman (2003) Ch. 3 - MC variance at extreme σ
    - VIX historical data: March 2020 spike to 82.69

See: docs/TOLERANCE_JUSTIFICATION.md
"""

import numpy as np
import pytest

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
)
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
    put_call_parity_check,
)


class TestCallBoundsExtremeVol:
    """[T1] Call option bounds: 0 <= C <= S for any volatility."""

    @pytest.mark.parametrize(
        "sigma",
        [0.001, 0.01, 0.05, 0.10, 0.20, 0.50, 1.0, 1.5, 2.0, 3.0],
    )
    def test_call_bounds_extreme_vol(self, sigma: float) -> None:
        """Call is bounded by [0, S] from σ=0.1% to σ=300%."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)

        assert call >= -ANTI_PATTERN_TOLERANCE, f"Call negative at σ={sigma}: {call}"
        assert call <= spot + ANTI_PATTERN_TOLERANCE, f"Call > S at σ={sigma}: {call}"

    @pytest.mark.parametrize("sigma", [0.001, 0.50, 1.5, 2.5])
    @pytest.mark.parametrize("moneyness", [0.7, 0.9, 1.0, 1.1, 1.3])
    def test_call_bounds_vol_moneyness_grid(self, sigma: float, moneyness: float) -> None:
        """Call bounds hold across volatility and moneyness combinations."""
        spot = 100.0
        strike = spot * moneyness
        rate, dividend, time = 0.05, 0.02, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)

        assert call >= -ANTI_PATTERN_TOLERANCE, (
            f"Call negative at σ={sigma}, K/S={moneyness}: {call}"
        )
        assert call <= spot + ANTI_PATTERN_TOLERANCE, (
            f"Call > S at σ={sigma}, K/S={moneyness}: {call}"
        )


class TestPutCallParityExtremeVol:
    """[T1] Put-call parity must hold at extreme volatilities."""

    @pytest.mark.parametrize(
        "sigma",
        [0.001, 0.01, 0.10, 0.50, 1.0, 1.5, 2.0],
    )
    def test_parity_extreme_vol_atm(self, sigma: float) -> None:
        """Put-call parity holds at extreme volatilities (ATM)."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

        parity_holds, error = put_call_parity_check(call, put, spot, strike, rate, dividend, time)

        assert parity_holds, f"Parity violated at σ={sigma}: error={error}"

    @pytest.mark.parametrize("sigma", [0.01, 0.50, 1.5])
    @pytest.mark.parametrize("moneyness", [0.8, 1.0, 1.2])
    def test_parity_vol_moneyness_grid(self, sigma: float, moneyness: float) -> None:
        """Parity holds across volatility/moneyness grid."""
        spot = 100.0
        strike = spot * moneyness
        rate, dividend, time = 0.05, 0.02, 1.0

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

        parity_holds, error = put_call_parity_check(call, put, spot, strike, rate, dividend, time)

        assert parity_holds, f"Parity violated at σ={sigma}, K/S={moneyness}: error={error}"


class TestNearZeroVolatility:
    """Tests for near-zero volatility (deterministic limit)."""

    def test_near_zero_vol_call_itm(self) -> None:
        """
        [T1] At σ → 0, ITM call → max(0, S*exp(-qT) - K*exp(-rT)).

        For deep ITM with negligible vol, call approaches forward intrinsic.
        """
        spot, strike = 100.0, 80.0  # ITM
        rate, dividend, time = 0.05, 0.02, 1.0
        sigma = 0.001  # Near-zero

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)

        # Expected: intrinsic value discounted
        forward_intrinsic = max(
            0.0,
            spot * np.exp(-dividend * time) - strike * np.exp(-rate * time),
        )

        # At near-zero vol, should be close to forward intrinsic
        assert abs(call - forward_intrinsic) < 0.1, (
            f"Near-zero vol ITM call not near intrinsic: call={call}, expected≈{forward_intrinsic}"
        )

    def test_near_zero_vol_call_otm(self) -> None:
        """[T1] At σ → 0, OTM call → 0."""
        spot, strike = 100.0, 120.0  # OTM
        rate, dividend, time = 0.05, 0.0, 1.0
        sigma = 0.001

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)

        # OTM call at near-zero vol should be nearly worthless
        assert call < 0.01, f"Near-zero vol OTM call should be ~0: {call}"

    def test_near_zero_vol_finite(self) -> None:
        """No NaN/Inf for very small volatility."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0
        sigma = 0.0001  # Very small

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

        assert np.isfinite(call), f"Call is not finite at σ={sigma}"
        assert np.isfinite(put), f"Put is not finite at σ={sigma}"


class TestVeryHighVolatility:
    """Tests for very high volatility (crisis conditions)."""

    def test_high_vol_call_approaches_spot(self) -> None:
        """
        [T1] At σ → ∞, call → S*exp(-qT).

        As volatility increases, call approaches spot (discounted by dividend).
        """
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        calls = []
        sigmas = [0.5, 1.0, 2.0, 3.0, 5.0]
        for sigma in sigmas:
            call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
            calls.append(call)

        # Should be monotonically increasing toward limit
        for i in range(len(calls) - 1):
            assert calls[i] < calls[i + 1], (
                f"Call not increasing with vol: "
                f"C(σ={sigmas[i]})={calls[i]}, C(σ={sigmas[i + 1]})={calls[i + 1]}"
            )

        # At very high vol, call should be close to S*exp(-qT)
        limit = spot * np.exp(-dividend * time)
        assert calls[-1] > 0.9 * limit, (
            f"High vol call not approaching limit: call={calls[-1]}, limit={limit}"
        )

    def test_high_vol_put_approaches_strike(self) -> None:
        """
        [T1] At σ → ∞, put → K*exp(-rT).

        As volatility increases, put approaches strike PV.
        """
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0

        puts = []
        sigmas = [0.5, 1.0, 2.0, 3.0, 5.0]
        for sigma in sigmas:
            put = black_scholes_put(spot, strike, rate, dividend, sigma, time)
            puts.append(put)

        # Should be monotonically increasing toward limit
        for i in range(len(puts) - 1):
            assert puts[i] < puts[i + 1], (
                f"Put not increasing with vol: "
                f"P(σ={sigmas[i]})={puts[i]}, P(σ={sigmas[i + 1]})={puts[i + 1]}"
            )

    def test_crisis_vol_levels_stable(self) -> None:
        """Pricing stable at 2008/2020 crisis volatility levels."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.02, 0.0, 1.0

        # VIX spike levels
        crisis_vols = [0.65, 0.75, 0.85]  # 65-85% annualized

        for sigma in crisis_vols:
            call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
            put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

            assert np.isfinite(call), f"Call not finite at crisis σ={sigma}"
            assert np.isfinite(put), f"Put not finite at crisis σ={sigma}"
            assert call > 0, f"Call should be positive at σ={sigma}: {call}"
            assert put > 0, f"Put should be positive at σ={sigma}: {put}"


class TestGreeksExtremeVol:
    """Greeks behavior at extreme volatility levels."""

    @pytest.mark.parametrize("sigma", [0.01, 0.20, 1.0, 2.0])
    def test_delta_bounds_extreme_vol(self, sigma: float) -> None:
        """[T1] Delta bounded in [0,1] for calls, [-1,0] for puts."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, sigma, time, OptionType.CALL
        )
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, sigma, time, OptionType.PUT)

        assert 0 <= call_greeks.delta <= 1, (
            f"Call delta out of bounds at σ={sigma}: {call_greeks.delta}"
        )
        assert -1 <= put_greeks.delta <= 0, (
            f"Put delta out of bounds at σ={sigma}: {put_greeks.delta}"
        )

    @pytest.mark.parametrize("sigma", [0.01, 0.20, 1.0, 2.0])
    def test_gamma_positive_extreme_vol(self, sigma: float) -> None:
        """[T1] Gamma is always positive."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, sigma, time, OptionType.CALL
        )

        assert call_greeks.gamma > 0, f"Gamma not positive at σ={sigma}: {call_greeks.gamma}"

    @pytest.mark.parametrize("sigma", [0.01, 0.20, 1.0, 2.0])
    def test_vega_positive_extreme_vol(self, sigma: float) -> None:
        """[T1] Vega is always positive."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        call_greeks = black_scholes_greeks(
            spot, strike, rate, dividend, sigma, time, OptionType.CALL
        )

        assert call_greeks.vega > 0, f"Vega not positive at σ={sigma}: {call_greeks.vega}"

    def test_vega_peaks_at_forward(self) -> None:
        """
        [T1] Vega is highest at the forward strike F = S·e^((r-q)T).

        Vega peaks at the forward price, not at the spot price ("ATM").
        For r=5%, q=2%, T=1: F = 100·e^(0.03) ≈ 103.05
        """
        spot = 100.0
        rate, dividend, sigma, time = 0.05, 0.02, 0.20, 1.0

        # Forward strike
        forward = spot * np.exp((rate - dividend) * time)

        # Sample strikes around and including the forward
        strikes = [90.0, 95.0, 100.0, forward, 105.0, 110.0, 115.0]
        vegas = []
        for strike in strikes:
            greeks = black_scholes_greeks(
                spot, strike, rate, dividend, sigma, time, OptionType.CALL
            )
            vegas.append((strike, greeks.vega))

        # Vega at forward should be the maximum
        vega_at_forward = next(v for k, v in vegas if abs(k - forward) < 0.01)
        max_vega = max(v for _, v in vegas)

        assert abs(vega_at_forward - max_vega) < 0.01, (
            f"Vega should peak at forward F={forward:.2f}: "
            f"vega(F)={vega_at_forward:.4f}, max_vega={max_vega:.4f}"
        )

    def test_vega_symmetric_around_forward(self) -> None:
        """
        [T1] Vega is approximately symmetric around the forward strike.

        Options equidistant from the forward should have similar vegas.
        """
        spot = 100.0
        rate, dividend, sigma, time = 0.05, 0.02, 0.20, 1.0

        forward = spot * np.exp((rate - dividend) * time)

        # Test strikes symmetric around forward
        offset = 10.0
        greeks_below = black_scholes_greeks(
            spot, forward - offset, rate, dividend, sigma, time, OptionType.CALL
        )
        greeks_above = black_scholes_greeks(
            spot, forward + offset, rate, dividend, sigma, time, OptionType.CALL
        )

        # Vegas should be approximately equal
        assert abs(greeks_below.vega - greeks_above.vega) < 0.05, (
            f"Vega asymmetric around forward: "
            f"vega({forward - offset:.0f})={greeks_below.vega:.4f}, "
            f"vega({forward + offset:.0f})={greeks_above.vega:.4f}"
        )


class TestVolatilityMonotonicity:
    """[T1] Option prices increase monotonically with volatility."""

    def test_call_increases_with_vol(self) -> None:
        """Call price strictly increases with volatility."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        sigmas = [0.05, 0.10, 0.20, 0.40, 0.80]
        calls = [black_scholes_call(spot, strike, rate, dividend, sigma, time) for sigma in sigmas]

        for i in range(len(calls) - 1):
            assert calls[i] < calls[i + 1], (
                f"Call not monotonic in vol: "
                f"C(σ={sigmas[i]})={calls[i]} >= C(σ={sigmas[i + 1]})={calls[i + 1]}"
            )

    def test_put_increases_with_vol(self) -> None:
        """Put price strictly increases with volatility."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        sigmas = [0.05, 0.10, 0.20, 0.40, 0.80]
        puts = [black_scholes_put(spot, strike, rate, dividend, sigma, time) for sigma in sigmas]

        for i in range(len(puts) - 1):
            assert puts[i] < puts[i + 1], (
                f"Put not monotonic in vol: "
                f"P(σ={sigmas[i]})={puts[i]} >= P(σ={sigmas[i + 1]})={puts[i + 1]}"
            )


class TestNumericalStabilityExtremeVol:
    """Numerical stability at volatility extremes."""

    def test_no_overflow_very_high_vol(self) -> None:
        """No overflow at very high volatility (σ = 500%)."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0
        sigma = 5.0  # 500%

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

        assert np.isfinite(call), f"Call overflowed at σ={sigma}"
        assert np.isfinite(put), f"Put overflowed at σ={sigma}"

    def test_no_underflow_very_low_vol(self) -> None:
        """No underflow at very low volatility (σ = 0.01%)."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.0, 1.0
        sigma = 0.0001  # 0.01%

        call = black_scholes_call(spot, strike, rate, dividend, sigma, time)
        put = black_scholes_put(spot, strike, rate, dividend, sigma, time)

        assert np.isfinite(call), f"Call underflowed at σ={sigma}"
        assert np.isfinite(put), f"Put underflowed at σ={sigma}"
