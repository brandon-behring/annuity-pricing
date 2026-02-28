"""
Property-based tests for Black-Scholes Greeks.

Uses Hypothesis to verify Greeks mathematical properties hold across
randomly generated inputs.

Properties tested:
1. Delta bounds: call delta ∈ [0, 1], put delta ∈ [-1, 0]
2. Gamma positivity: Γ > 0 for all options
3. Gamma equality: Γ_call = Γ_put at same strike
4. Vega positivity: V > 0 for all options
5. Vega equality: V_call = V_put at same strike
6. Delta-put relationship: Δ_put = Δ_call - e^(-qT)

References:
    [T1] Hull (2021) Ch. 19 - Greeks
    [T1] Black-Scholes Greek derivations

See: docs/knowledge/derivations/bs_greeks.md
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
    GREEKS_NUMERICAL_TOLERANCE,
)
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_greeks,
)

# =============================================================================
# Strategy Definitions
# =============================================================================

spot_strategy = st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
strike_strategy = st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
rate_strategy = st.floats(min_value=-0.05, max_value=0.15, allow_nan=False, allow_infinity=False)
dividend_strategy = st.floats(min_value=0.0, max_value=0.08, allow_nan=False, allow_infinity=False)
vol_strategy = st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False)
time_strategy = st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False)


# =============================================================================
# Delta Properties
# =============================================================================


class TestDeltaBounds:
    """[T1] Delta is bounded: call ∈ [0, 1], put ∈ [-1, 0]."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_delta_bounds(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Call delta in [0, 1]."""
        greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)

        assert greeks.delta >= -ANTI_PATTERN_TOLERANCE, f"Call delta below 0: {greeks.delta}"
        assert greeks.delta <= 1.0 + ANTI_PATTERN_TOLERANCE, f"Call delta above 1: {greeks.delta}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_delta_bounds(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put delta in [-1, 0]."""
        greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        assert greeks.delta >= -1.0 - ANTI_PATTERN_TOLERANCE, f"Put delta below -1: {greeks.delta}"
        assert greeks.delta <= ANTI_PATTERN_TOLERANCE, f"Put delta above 0: {greeks.delta}"


class TestDeltaPutCallRelationship:
    """[T1] Put and call deltas are related: Δ_put = Δ_call - e^(-qT)."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_delta_relationship(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Δ_put = Δ_call - e^(-qT)."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        expected_put_delta = call_greeks.delta - np.exp(-dividend * time)
        actual_put_delta = put_greeks.delta

        assert abs(actual_put_delta - expected_put_delta) < GREEKS_NUMERICAL_TOLERANCE, (
            f"Delta relationship violated: "
            f"Δ_put={actual_put_delta}, expected={expected_put_delta} "
            f"(Δ_call={call_greeks.delta}, e^(-qT)={np.exp(-dividend * time)})"
        )


# =============================================================================
# Gamma Properties
# =============================================================================


class TestGammaProperties:
    """[T1] Gamma is always positive and equal for calls and puts."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_gamma_positive(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Γ > 0 for all options."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        assert call_greeks.gamma > -ANTI_PATTERN_TOLERANCE, (
            f"Call gamma not positive: {call_greeks.gamma}"
        )
        assert put_greeks.gamma > -ANTI_PATTERN_TOLERANCE, (
            f"Put gamma not positive: {put_greeks.gamma}"
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
    def test_gamma_equality(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Γ_call = Γ_put at same strike."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        assert abs(call_greeks.gamma - put_greeks.gamma) < GREEKS_NUMERICAL_TOLERANCE, (
            f"Gamma equality violated: Γ_call={call_greeks.gamma}, Γ_put={put_greeks.gamma}"
        )


# =============================================================================
# Vega Properties
# =============================================================================


class TestVegaProperties:
    """[T1] Vega is always positive and equal for calls and puts."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_vega_positive(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] V > 0 for all options."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        assert call_greeks.vega > -ANTI_PATTERN_TOLERANCE, (
            f"Call vega not positive: {call_greeks.vega}"
        )
        assert put_greeks.vega > -ANTI_PATTERN_TOLERANCE, (
            f"Put vega not positive: {put_greeks.vega}"
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
    def test_vega_equality(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] V_call = V_put at same strike."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)
        put_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        assert abs(call_greeks.vega - put_greeks.vega) < GREEKS_NUMERICAL_TOLERANCE, (
            f"Vega equality violated: V_call={call_greeks.vega}, V_put={put_greeks.vega}"
        )


# =============================================================================
# Rho Properties
# =============================================================================


class TestRhoProperties:
    """[T1] Rho has sign based on option type."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=st.floats(min_value=0.01, max_value=0.15, allow_nan=False, allow_infinity=False),
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_call_rho_positive(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Call rho is positive (call gains from higher rates)."""
        greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)

        # Rho should be positive for calls (higher rate increases call value)
        assert greeks.rho >= -ANTI_PATTERN_TOLERANCE, f"Call rho should be positive: {greeks.rho}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=st.floats(min_value=0.01, max_value=0.15, allow_nan=False, allow_infinity=False),
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_put_rho_negative(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] Put rho is negative (put loses from higher rates)."""
        greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.PUT)

        # Rho should be negative for puts (higher rate decreases put value)
        assert greeks.rho <= ANTI_PATTERN_TOLERANCE, f"Put rho should be negative: {greeks.rho}"


# =============================================================================
# Finite Values Property
# =============================================================================


class TestGreeksFinite:
    """All Greeks are finite for valid inputs."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=200)
    def test_all_greeks_finite(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """All Greeks are finite values."""
        call_greeks = black_scholes_greeks(spot, strike, rate, dividend, vol, time, OptionType.CALL)

        assert np.isfinite(call_greeks.price), f"Price not finite: {call_greeks.price}"
        assert np.isfinite(call_greeks.delta), f"Delta not finite: {call_greeks.delta}"
        assert np.isfinite(call_greeks.gamma), f"Gamma not finite: {call_greeks.gamma}"
        assert np.isfinite(call_greeks.vega), f"Vega not finite: {call_greeks.vega}"
        assert np.isfinite(call_greeks.theta), f"Theta not finite: {call_greeks.theta}"
        assert np.isfinite(call_greeks.rho), f"Rho not finite: {call_greeks.rho}"
