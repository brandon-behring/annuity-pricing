"""
Cross-library convergence tests for Black-Scholes pricing.

[T1] Validates three implementations agree within tolerance:
1. Our implementation (annuity_pricing.options.pricing.black_scholes)
2. financepy (financepy.models.black_scholes)
3. QuantLib (ql.AnalyticEuropeanEngine)

This test serves as a "canary" - if three independent implementations
diverge, it indicates a fundamental error in our understanding.

See: Hull (2021) Ch. 15 - Black-Scholes-Merton Model
"""

import numpy as np
import pytest

# Skip if BOTH libraries unavailable
financepy = pytest.importorskip("financepy", reason="financepy required")
ql = pytest.importorskip("QuantLib", reason="QuantLib required")

from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter
from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)

# Tolerance for three-way comparison
# Libraries may differ by ~0.1-0.2% due to date handling conventions
THREE_WAY_RELATIVE_TOLERANCE = 0.003  # 0.3%


class TestThreeWayCallPriceConvergence:
    """
    Three-way call price convergence.

    [T1] All three implementations must agree within tolerance.
    """

    @pytest.fixture
    def adapters(self):
        """Get both adapters."""
        fp = FinancepyAdapter()
        ql = QuantLibAdapter()

        if not fp.is_available or not ql.is_available:
            pytest.skip("Both financepy and QuantLib required")

        return {"financepy": fp, "quantlib": ql}

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spot,strike,rate,dividend,vol,T",
        [
            # Standard ATM
            (100.0, 100.0, 0.05, 0.02, 0.20, 1.0),
            # Hull Example 15.6
            (42.0, 40.0, 0.10, 0.0, 0.20, 0.5),
            # ITM
            (100.0, 90.0, 0.05, 0.02, 0.20, 1.0),
            # OTM
            (100.0, 110.0, 0.05, 0.02, 0.20, 1.0),
            # High vol
            (100.0, 100.0, 0.05, 0.02, 0.40, 1.0),
            # Short term
            (100.0, 100.0, 0.05, 0.02, 0.20, 0.25),
            # Long term
            (100.0, 100.0, 0.05, 0.02, 0.20, 3.0),
            # Zero dividend
            (100.0, 100.0, 0.05, 0.0, 0.20, 1.0),
            # High dividend
            (100.0, 100.0, 0.05, 0.05, 0.20, 1.0),
        ],
        ids=[
            "ATM-standard",
            "Hull-15.6",
            "ITM",
            "OTM",
            "high-vol",
            "short-term",
            "long-term",
            "zero-div",
            "high-div",
        ],
    )
    def test_call_three_way_convergence(self, adapters, spot, strike, rate, dividend, vol, T):
        """
        [T1] Our BS, financepy, QuantLib must all agree on call price.

        Test uses THREE_WAY_RELATIVE_TOLERANCE as maximum pairwise difference.
        """
        # Our implementation
        our_price = black_scholes_call(spot, strike, rate, dividend, vol, T)

        # financepy
        fp_price = adapters["financepy"].price_call(spot, strike, rate, dividend, vol, T)

        # QuantLib
        ql_price = adapters["quantlib"].price_european_call(spot, strike, rate, dividend, vol, T)

        prices = {"ours": our_price, "financepy": fp_price, "quantlib": ql_price}

        # All pairwise relative differences must be within tolerance
        pairs = [("ours", "financepy"), ("ours", "quantlib"), ("financepy", "quantlib")]
        for lib1, lib2 in pairs:
            p1, p2 = prices[lib1], prices[lib2]
            ref = max(abs(p1), abs(p2), 0.01)  # Avoid division by zero
            rel_diff = abs(p1 - p2) / ref
            assert rel_diff < THREE_WAY_RELATIVE_TOLERANCE, (
                f"Three-way divergence ({lib1} vs {lib2}): "
                f"{lib1}={p1:.6f}, {lib2}={p2:.6f}, rel_diff={rel_diff:.2%}. "
                f"Params: S={spot}, K={strike}, r={rate}, q={dividend}, σ={vol}, T={T}"
            )


class TestThreeWayPutPriceConvergence:
    """
    Three-way put price convergence.

    [T1] All three implementations must agree on put prices.
    """

    @pytest.fixture
    def adapters(self):
        """Get both adapters."""
        fp = FinancepyAdapter()
        ql = QuantLibAdapter()

        if not fp.is_available or not ql.is_available:
            pytest.skip("Both financepy and QuantLib required")

        return {"financepy": fp, "quantlib": ql}

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spot,strike,rate,dividend,vol,T",
        [
            # Standard ATM
            (100.0, 100.0, 0.05, 0.02, 0.20, 1.0),
            # ITM put (OTM call equivalent strike)
            (100.0, 110.0, 0.05, 0.02, 0.20, 1.0),
            # OTM put
            (100.0, 90.0, 0.05, 0.02, 0.20, 1.0),
            # High vol
            (100.0, 100.0, 0.05, 0.02, 0.40, 1.0),
        ],
        ids=["ATM", "ITM-put", "OTM-put", "high-vol"],
    )
    def test_put_three_way_convergence(self, adapters, spot, strike, rate, dividend, vol, T):
        """
        [T1] Our BS, financepy, QuantLib must all agree on put price.
        """
        # Our implementation
        our_price = black_scholes_put(spot, strike, rate, dividend, vol, T)

        # financepy
        fp_price = adapters["financepy"].price_put(spot, strike, rate, dividend, vol, T)

        # QuantLib
        ql_price = adapters["quantlib"].price_european_put(spot, strike, rate, dividend, vol, T)

        prices = {"ours": our_price, "financepy": fp_price, "quantlib": ql_price}

        # All pairwise relative differences must be within tolerance
        pairs = [("ours", "financepy"), ("ours", "quantlib"), ("financepy", "quantlib")]
        for lib1, lib2 in pairs:
            p1, p2 = prices[lib1], prices[lib2]
            ref = max(abs(p1), abs(p2), 0.01)
            rel_diff = abs(p1 - p2) / ref
            assert rel_diff < THREE_WAY_RELATIVE_TOLERANCE, (
                f"Three-way put divergence ({lib1} vs {lib2}): "
                f"{lib1}={p1:.6f}, {lib2}={p2:.6f}, rel_diff={rel_diff:.2%}"
            )


class TestThreeWayPutCallParity:
    """
    Validates put-call parity holds for all three implementations.

    [T1] C - P = S*e^(-qT) - K*e^(-rT) for each library individually
    AND parity differences agree across libraries.
    """

    @pytest.fixture
    def adapters(self):
        """Get both adapters."""
        fp = FinancepyAdapter()
        ql = QuantLibAdapter()

        if not fp.is_available or not ql.is_available:
            pytest.skip("Both financepy and QuantLib required")

        return {"financepy": fp, "quantlib": ql}

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spot,strike,rate,dividend,vol,T",
        [
            (100.0, 100.0, 0.05, 0.02, 0.20, 1.0),
            (100.0, 90.0, 0.05, 0.02, 0.20, 1.0),
            (100.0, 110.0, 0.05, 0.02, 0.20, 1.0),
        ],
    )
    def test_parity_three_way(self, adapters, spot, strike, rate, dividend, vol, T):
        """
        [T1] Put-call parity must hold for each implementation.

        Verifies: C - P = S*e^(-qT) - K*e^(-rT)
        """
        # Expected parity difference (analytical)
        expected = spot * np.exp(-dividend * T) - strike * np.exp(-rate * T)

        # Our implementation
        our_call = black_scholes_call(spot, strike, rate, dividend, vol, T)
        our_put = black_scholes_put(spot, strike, rate, dividend, vol, T)
        our_diff = our_call - our_put

        # financepy
        fp_call = adapters["financepy"].price_call(spot, strike, rate, dividend, vol, T)
        fp_put = adapters["financepy"].price_put(spot, strike, rate, dividend, vol, T)
        fp_diff = fp_call - fp_put

        # QuantLib
        ql_call = adapters["quantlib"].price_european_call(spot, strike, rate, dividend, vol, T)
        ql_put = adapters["quantlib"].price_european_put(spot, strike, rate, dividend, vol, T)
        ql_diff = ql_call - ql_put

        # Each must satisfy parity (use absolute tolerance since diff may be small)
        parity_tolerance = 0.01  # $0.01 absolute
        for name, actual in [("ours", our_diff), ("financepy", fp_diff), ("quantlib", ql_diff)]:
            error = abs(actual - expected)
            assert error < parity_tolerance, (
                f"{name} violates put-call parity: diff={actual:.6f}, "
                f"expected={expected:.6f}, error={error:.6f}"
            )


class TestFIACapValidationThreeWay:
    """
    Three-way validation for FIA cap (call spread) pricing.

    [T1] FIA cap = ATM call - OTM call (bull spread)
    All three libraries should agree on the spread value.
    """

    @pytest.fixture
    def adapters(self):
        """Get both adapters."""
        fp = FinancepyAdapter()
        ql = QuantLibAdapter()

        if not fp.is_available or not ql.is_available:
            pytest.skip("Both financepy and QuantLib required")

        return {"financepy": fp, "quantlib": ql}

    @pytest.mark.validation
    @pytest.mark.parametrize("cap_rate", [0.05, 0.10, 0.15])
    def test_cap_spread_three_way(self, adapters, cap_rate):
        """
        [T1] FIA cap (call spread) value must agree across libraries.
        """
        spot = 100.0
        rate = 0.05
        dividend = 0.02
        vol = 0.20
        T = 1.0

        atm_strike = spot
        otm_strike = spot * (1 + cap_rate)

        # Our spread
        our_atm = black_scholes_call(spot, atm_strike, rate, dividend, vol, T)
        our_otm = black_scholes_call(spot, otm_strike, rate, dividend, vol, T)
        our_spread = our_atm - our_otm

        # financepy spread
        fp_atm = adapters["financepy"].price_call(spot, atm_strike, rate, dividend, vol, T)
        fp_otm = adapters["financepy"].price_call(spot, otm_strike, rate, dividend, vol, T)
        fp_spread = fp_atm - fp_otm

        # QuantLib spread
        ql_atm = adapters["quantlib"].price_european_call(spot, atm_strike, rate, dividend, vol, T)
        ql_otm = adapters["quantlib"].price_european_call(spot, otm_strike, rate, dividend, vol, T)
        ql_spread = ql_atm - ql_otm

        spreads = {"ours": our_spread, "financepy": fp_spread, "quantlib": ql_spread}

        # Check pairwise
        for lib1, lib2 in [("ours", "financepy"), ("ours", "quantlib")]:
            s1, s2 = spreads[lib1], spreads[lib2]
            ref = max(abs(s1), abs(s2), 0.01)
            rel_diff = abs(s1 - s2) / ref
            assert rel_diff < THREE_WAY_RELATIVE_TOLERANCE, (
                f"Cap spread divergence at cap={cap_rate:.0%}: "
                f"{lib1}={s1:.4f}, {lib2}={s2:.4f}, rel_diff={rel_diff:.2%}"
            )


class TestRILABufferValidationThreeWay:
    """
    Three-way validation for RILA buffer (put spread) pricing.

    [T1] RILA buffer = ATM put - OTM put (bear spread)
    All three libraries should agree on the spread value.
    """

    @pytest.fixture
    def adapters(self):
        """Get both adapters."""
        fp = FinancepyAdapter()
        ql = QuantLibAdapter()

        if not fp.is_available or not ql.is_available:
            pytest.skip("Both financepy and QuantLib required")

        return {"financepy": fp, "quantlib": ql}

    @pytest.mark.validation
    @pytest.mark.parametrize("buffer_rate", [0.10, 0.15, 0.20])
    def test_buffer_spread_three_way(self, adapters, buffer_rate):
        """
        [T1] RILA buffer (put spread) value must agree across libraries.
        """
        spot = 100.0
        rate = 0.05
        dividend = 0.02
        vol = 0.20
        T = 1.0

        atm_strike = spot
        otm_strike = spot * (1 - buffer_rate)

        # Our spread
        our_atm = black_scholes_put(spot, atm_strike, rate, dividend, vol, T)
        our_otm = black_scholes_put(spot, otm_strike, rate, dividend, vol, T)
        our_spread = our_atm - our_otm

        # financepy spread
        fp_atm = adapters["financepy"].price_put(spot, atm_strike, rate, dividend, vol, T)
        fp_otm = adapters["financepy"].price_put(spot, otm_strike, rate, dividend, vol, T)
        fp_spread = fp_atm - fp_otm

        # QuantLib spread
        ql_atm = adapters["quantlib"].price_european_put(spot, atm_strike, rate, dividend, vol, T)
        ql_otm = adapters["quantlib"].price_european_put(spot, otm_strike, rate, dividend, vol, T)
        ql_spread = ql_atm - ql_otm

        spreads = {"ours": our_spread, "financepy": fp_spread, "quantlib": ql_spread}

        # Check pairwise
        for lib1, lib2 in [("ours", "financepy"), ("ours", "quantlib")]:
            s1, s2 = spreads[lib1], spreads[lib2]
            ref = max(abs(s1), abs(s2), 0.01)
            rel_diff = abs(s1 - s2) / ref
            assert rel_diff < THREE_WAY_RELATIVE_TOLERANCE, (
                f"Buffer spread divergence at buffer={buffer_rate:.0%}: "
                f"{lib1}={s1:.4f}, {lib2}={s2:.4f}, rel_diff={rel_diff:.2%}"
            )
