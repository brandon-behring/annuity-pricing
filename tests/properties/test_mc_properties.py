"""
Property-based tests for Monte Carlo simulation.

Uses Hypothesis to verify Monte Carlo properties:
1. MC call price bounded by BS bounds
2. MC convergence to BS (statistical test)
3. MC put-call parity (approximate)
4. Variance reduction effectiveness

References:
    [T1] Glasserman (2003) Ch. 3-4 - Monte Carlo Methods
    [T1] CLT for MC convergence

See: docs/TOLERANCE_JUSTIFICATION.md for CLT-derived tolerances
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from annuity_pricing.config.tolerances import (
    MC_10K_TOLERANCE,
    MC_100K_TOLERANCE,
)
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)
from annuity_pricing.options.simulation.monte_carlo import monte_carlo_price

# =============================================================================
# Strategy Definitions
# =============================================================================

# More constrained strategies for MC (expensive to run)
spot_strategy = st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False)
strike_strategy = st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False)
rate_strategy = st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False)
dividend_strategy = st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False)
vol_strategy = st.floats(min_value=0.10, max_value=0.50, allow_nan=False, allow_infinity=False)
time_strategy = st.floats(min_value=0.25, max_value=2.0, allow_nan=False, allow_infinity=False)


# =============================================================================
# MC Bound Properties
# =============================================================================


class TestMCBoundsProperty:
    """[T1] MC prices should satisfy no-arbitrage bounds."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=50)  # Fewer examples due to MC cost
    def test_mc_call_upper_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] MC call bounded: 0 <= C <= S."""
        mc_price = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=10_000,
            option_type="call",
            seed=42,
        )

        assert mc_price >= -MC_10K_TOLERANCE, f"MC call negative: {mc_price}"
        assert mc_price <= spot + MC_10K_TOLERANCE, f"MC call > S: {mc_price} > {spot}"

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=50)
    def test_mc_put_upper_bound(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] MC put bounded: 0 <= P <= K*exp(-rT)."""
        mc_price = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=10_000,
            option_type="put",
            seed=42,
        )

        upper_bound = strike * np.exp(-rate * time)

        assert mc_price >= -MC_10K_TOLERANCE, f"MC put negative: {mc_price}"
        assert mc_price <= upper_bound + MC_10K_TOLERANCE, (
            f"MC put > K*exp(-rT): {mc_price} > {upper_bound}"
        )


# =============================================================================
# MC Convergence Property
# =============================================================================


class TestMCConvergenceProperty:
    """[T1] MC converges to BS for vanilla options."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=30)  # Expensive tests
    def test_mc_converges_to_bs_call(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] MC call converges to BS call within CLT bounds."""
        bs_price = black_scholes_call(spot, strike, rate, dividend, vol, time)
        mc_price = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=100_000,
            option_type="call",
            seed=42,
        )

        # Use CLT-derived tolerance: 3σ/√N
        # For typical option prices, σ ≈ price, so tolerance scales with price
        tolerance = max(MC_100K_TOLERANCE * spot, 0.10)  # At least 0.10 absolute

        assert abs(mc_price - bs_price) < tolerance, (
            f"MC not converging to BS: MC={mc_price}, BS={bs_price}, "
            f"diff={abs(mc_price - bs_price)}, tol={tolerance}"
        )

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=30)
    def test_mc_converges_to_bs_put(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] MC put converges to BS put within CLT bounds."""
        bs_price = black_scholes_put(spot, strike, rate, dividend, vol, time)
        mc_price = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=100_000,
            option_type="put",
            seed=42,
        )

        tolerance = max(MC_100K_TOLERANCE * spot, 0.10)

        assert abs(mc_price - bs_price) < tolerance, (
            f"MC not converging to BS: MC={mc_price}, BS={bs_price}, "
            f"diff={abs(mc_price - bs_price)}, tol={tolerance}"
        )


# =============================================================================
# MC Parity Property
# =============================================================================


class TestMCParityProperty:
    """[T1] MC prices approximately satisfy put-call parity."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=30)
    def test_mc_parity_approximate(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """[T1] MC C - P ≈ S*exp(-qT) - K*exp(-rT) within MC tolerance."""
        # Use same seed for both to reduce variance in comparison
        mc_call = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=50_000,
            option_type="call",
            seed=42,
        )
        mc_put = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=50_000,
            option_type="put",
            seed=42,
        )

        actual_diff = mc_call - mc_put
        expected_diff = spot * np.exp(-dividend * time) - strike * np.exp(-rate * time)

        # MC parity tolerance is looser due to independent simulations
        tolerance = max(MC_10K_TOLERANCE * spot * 2, 0.50)

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"MC parity violated: actual_diff={actual_diff}, "
            f"expected_diff={expected_diff}, error={abs(actual_diff - expected_diff)}"
        )


# =============================================================================
# MC Reproducibility Property
# =============================================================================


class TestMCReproducibility:
    """MC with same seed produces same result."""

    @given(
        spot=spot_strategy,
        strike=strike_strategy,
        rate=rate_strategy,
        dividend=dividend_strategy,
        vol=vol_strategy,
        time=time_strategy,
    )
    @settings(max_examples=20)
    def test_mc_deterministic_with_seed(
        self, spot: float, strike: float, rate: float, dividend: float, vol: float, time: float
    ) -> None:
        """Same seed produces identical MC prices."""
        price1 = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=10_000,
            option_type="call",
            seed=12345,
        )
        price2 = monte_carlo_price(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=time,
            n_paths=10_000,
            option_type="call",
            seed=12345,
        )

        assert price1 == price2, f"MC not deterministic with same seed: {price1} != {price2}"
