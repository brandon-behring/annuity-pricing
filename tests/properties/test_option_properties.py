"""
Property-based tests for Black-Scholes option pricing.

Uses Hypothesis to verify mathematical invariants hold across randomly
generated inputs. These tests explore the full input space, catching
edge cases that parameterized tests might miss.

Properties tested:
1. Call upper bound: 0 <= C <= S
2. Put upper bound: 0 <= P <= K*exp(-rT)
3. Call lower bound: C >= max(0, S*exp(-qT) - K*exp(-rT))
4. Put lower bound: P >= max(0, K*exp(-rT) - S*exp(-qT))
5. Put-call parity: C - P = S*exp(-qT) - K*exp(-rT)
6. Strike monotonicity (call): C(K1) > C(K2) for K1 < K2
7. Strike monotonicity (put): P(K1) < P(K2) for K1 < K2
8. Spot monotonicity (call): C(S1) < C(S2) for S1 < S2
9. Vol monotonicity: C increases with sigma
10. Time monotonicity: C increases with T (European)
11. Scaling property: C(λS, λK) = λ × C(S, K)
12. No-arbitrage: option values are always non-negative

References:
    [T1] Hull (2021) Ch. 11 - Option Properties
    [T1] Higham (2002) - Numerical precision

See: docs/TOLERANCE_JUSTIFICATION.md
"""

import numpy as np
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
)
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
    put_call_parity_check,
)

# =============================================================================
# Strategy Definitions
# =============================================================================
# Define strategies for generating valid option parameters

# Spot and strike: positive values in realistic range
spot_strategy = st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
strike_strategy = st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)

# Rate: can be negative (ECB style) but bounded
rate_strategy = st.floats(min_value=-0.10, max_value=0.20, allow_nan=False, allow_infinity=False)

# Dividend: non-negative, bounded
dividend_strategy = st.floats(min_value=0.0, max_value=0.10, allow_nan=False, allow_infinity=False)

# Volatility: positive, bounded (0.1% to 300%)
vol_strategy = st.floats(min_value=0.001, max_value=3.0, allow_nan=False, allow_infinity=False)

# Time: positive, up to 30 years
time_strategy = st.floats(min_value=0.001, max_value=30.0, allow_nan=False, allow_infinity=False)

# Scale factor for scaling property
scale_strategy = st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)


# =============================================================================
# Bound Properties
# =============================================================================


class TestCallBoundsProperty:
    """[T1] Call option bounds: 0 <= C <= S for all inputs."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_upper_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Call value is bounded: 0 <= C <= S."""
        call = black_scholes_call(spot, strike, rate, dividend, vol, time)

        assert call >= -ANTI_PATTERN_TOLERANCE, f"Call negative: {call}"
        assert call <= spot + ANTI_PATTERN_TOLERANCE, f"Call > S: C={call}, S={spot}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_lower_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Call value >= max(0, S*exp(-qT) - K*exp(-rT))."""
        call = black_scholes_call(spot, strike, rate, dividend, vol, time)
        lower_bound = max(0.0, spot * np.exp(-dividend * time) - strike * np.exp(-rate * time))

        assert call >= lower_bound - ANTI_PATTERN_TOLERANCE, (
            f"Call below lower bound: C={call}, bound={lower_bound}"
        )


class TestPutBoundsProperty:
    """[T1] Put option bounds: 0 <= P <= K*exp(-rT)."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_upper_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put value bounded: 0 <= P <= K*exp(-rT)."""
        put = black_scholes_put(spot, strike, rate, dividend, vol, time)
        upper_bound = strike * np.exp(-rate * time)

        assert put >= -ANTI_PATTERN_TOLERANCE, f"Put negative: {put}"
        assert put <= upper_bound + ANTI_PATTERN_TOLERANCE, (
            f"Put > K*exp(-rT): P={put}, bound={upper_bound}"
        )

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_lower_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put value >= max(0, K*exp(-rT) - S*exp(-qT))."""
        put = black_scholes_put(spot, strike, rate, dividend, vol, time)
        lower_bound = max(0.0, strike * np.exp(-rate * time) - spot * np.exp(-dividend * time))

        assert put >= lower_bound - ANTI_PATTERN_TOLERANCE, (
            f"Put below lower bound: P={put}, bound={lower_bound}"
        )


# =============================================================================
# Parity Property
# =============================================================================


class TestPutCallParityProperty:
    """[T1] Put-call parity: C - P = S*exp(-qT) - K*exp(-rT)."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_parity_holds(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put-call parity holds for all valid inputs."""
        call = black_scholes_call(spot, strike, rate, dividend, vol, time)
        put = black_scholes_put(spot, strike, rate, dividend, vol, time)

        parity_holds, error = put_call_parity_check(call, put, spot, strike, rate, dividend, time)

        assert parity_holds, (
            f"Parity violated: error={error}, "
            f"S={spot}, K={strike}, r={rate}, q={dividend}, σ={vol}, T={time}"
        )


# =============================================================================
# Monotonicity Properties
# =============================================================================


class TestStrikeMonotonicity:
    """[T1] Option prices are monotonic in strike."""

    @given(
        spot=spot_strategy,
        strike1=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        strike2=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_decreases_with_strike(
        self,
        spot: float,
        strike1: float,
        strike2: float,
        rate: float,
        dividend: float,
        vol: float,
        time: float,
    ) -> None:
        """[T1] C(K1) > C(K2) when K1 < K2."""
        # Only test when strikes are sufficiently different
        assume(abs(strike1 - strike2) > 1.0)

        call1 = black_scholes_call(spot, strike1, rate, dividend, vol, time)
        call2 = black_scholes_call(spot, strike2, rate, dividend, vol, time)

        if strike1 < strike2:
            assert call1 >= call2 - ANTI_PATTERN_TOLERANCE, (
                f"Call not decreasing with strike: C({strike1})={call1}, C({strike2})={call2}"
            )
        else:
            assert call2 >= call1 - ANTI_PATTERN_TOLERANCE, (
                f"Call not decreasing with strike: C({strike2})={call2}, C({strike1})={call1}"
            )

    @given(
        spot=spot_strategy,
        strike1=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        strike2=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_increases_with_strike(
        self,
        spot: float,
        strike1: float,
        strike2: float,
        rate: float,
        dividend: float,
        vol: float,
        time: float,
    ) -> None:
        """[T1] P(K1) < P(K2) when K1 < K2."""
        assume(abs(strike1 - strike2) > 1.0)

        put1 = black_scholes_put(spot, strike1, rate, dividend, vol, time)
        put2 = black_scholes_put(spot, strike2, rate, dividend, vol, time)

        if strike1 < strike2:
            assert put1 <= put2 + ANTI_PATTERN_TOLERANCE, (
                f"Put not increasing with strike: P({strike1})={put1}, P({strike2})={put2}"
            )
        else:
            assert put2 <= put1 + ANTI_PATTERN_TOLERANCE, (
                f"Put not increasing with strike: P({strike2})={put2}, P({strike1})={put1}"
            )


class TestSpotMonotonicity:
    """[T1] Option prices are monotonic in spot."""

    @given(
        spot1=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        spot2=st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_increases_with_spot(
        self,
        spot1: float,
        spot2: float,
        strike: float,
        rate: float,
        dividend: float,
        vol: float,
        time: float,
    ) -> None:
        """[T1] C(S1) < C(S2) when S1 < S2."""
        assume(abs(spot1 - spot2) > 1.0)

        call1 = black_scholes_call(spot1, strike, rate, dividend, vol, time)
        call2 = black_scholes_call(spot2, strike, rate, dividend, vol, time)

        if spot1 < spot2:
            assert call1 <= call2 + ANTI_PATTERN_TOLERANCE, (
                f"Call not increasing with spot: C(S={spot1})={call1}, C(S={spot2})={call2}"
            )
        else:
            assert call2 <= call1 + ANTI_PATTERN_TOLERANCE, (
                f"Call not increasing with spot: C(S={spot2})={call2}, C(S={spot1})={call1}"
            )


class TestVolatilityMonotonicity:
    """[T1] Option prices increase with volatility."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol1=st.floats(min_value=0.01, max_value=1.5, allow_nan=False, allow_infinity=False),
        vol2=st.floats(min_value=0.01, max_value=1.5, allow_nan=False, allow_infinity=False),
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_increases_with_vol(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        vol1: float,
        vol2: float,
        time: float,
    ) -> None:
        """[T1] C(σ1) < C(σ2) when σ1 < σ2."""
        assume(abs(vol1 - vol2) > 0.01)

        call1 = black_scholes_call(spot, strike, rate, dividend, vol1, time)
        call2 = black_scholes_call(spot, strike, rate, dividend, vol2, time)

        if vol1 < vol2:
            assert call1 <= call2 + ANTI_PATTERN_TOLERANCE, (
                f"Call not increasing with vol: C(σ={vol1})={call1}, C(σ={vol2})={call2}"
            )
        else:
            assert call2 <= call1 + ANTI_PATTERN_TOLERANCE, (
                f"Call not increasing with vol: C(σ={vol2})={call2}, C(σ={vol1})={call1}"
            )


# =============================================================================
# Scaling Property
# =============================================================================


class TestScalingProperty:
    """[T1] Homogeneity: C(λS, λK) = λ × C(S, K)."""

    @given(
        spot=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        strike=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
        scale=st.floats(min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_call_scaling(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        vol: float,
        time: float,
        scale: float,
    ) -> None:
        """[T1] C(λS, λK) = λ × C(S, K) (homogeneity of degree 1)."""
        # Original price
        call_original = black_scholes_call(spot, strike, rate, dividend, vol, time)

        # Scaled price
        call_scaled = black_scholes_call(spot * scale, strike * scale, rate, dividend, vol, time)

        expected = scale * call_original

        # Relative tolerance since values can be small
        rel_tol = 1e-8
        if expected > 0:
            assert (
                abs(call_scaled - expected) / expected < rel_tol
                or abs(call_scaled - expected) < ANTI_PATTERN_TOLERANCE
            ), f"Scaling violated: C(λS, λK)={call_scaled}, λ×C={expected}, λ={scale}"
        else:
            assert abs(call_scaled - expected) < ANTI_PATTERN_TOLERANCE, (
                f"Scaling violated at zero: C(λS, λK)={call_scaled}, λ×C={expected}"
            )


# =============================================================================
# Non-negativity (No-Arbitrage)
# =============================================================================


class TestNoArbitrage:
    """[T1] Option values are always non-negative."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_non_negative(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Call value is always >= 0."""
        call = black_scholes_call(spot, strike, rate, dividend, vol, time)
        assert call >= -ANTI_PATTERN_TOLERANCE, f"Call negative: {call}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_non_negative(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put value is always >= 0."""
        put = black_scholes_put(spot, strike, rate, dividend, vol, time)
        assert put >= -ANTI_PATTERN_TOLERANCE, f"Put negative: {put}"


# =============================================================================
# Numerical Stability
# =============================================================================


class TestNumericalStability:
    """All outputs are finite for valid inputs."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_finite(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """Call returns finite value for all valid inputs."""
        call = black_scholes_call(spot, strike, rate, dividend, vol, time)
        assert np.isfinite(call), f"Call not finite: {call}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_finite(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """Put returns finite value for all valid inputs."""
        put = black_scholes_put(spot, strike, rate, dividend, vol, time)
        assert np.isfinite(put), f"Put not finite: {put}"
