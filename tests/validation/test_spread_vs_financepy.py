"""
FIA spread crediting validation against financepy.

[T1] Validates that FIA spread crediting matches financepy Black-Scholes.

Spread Crediting Mechanics:
- Spread crediting pays: max(0, index_return - spread_rate)
- Option replication: Long OTM call at strike = S × (1 + spread_rate)
- Value = Call(K = S × (1 + spread)) / S × premium

See: docs/knowledge/domain/crediting_methods.md
"""

import numpy as np
import pytest

# Skip entire module if financepy not available
pytest.importorskip("financepy")

from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter
from annuity_pricing.options.pricing.black_scholes import black_scholes_call

# financepy uses actual calendar dates which introduces ~0.01 differences
# Use relative tolerance of 0.2% for cross-library validation
FINANCEPY_RELATIVE_TOLERANCE = 0.002


class TestFIASpreadComponentsVsFinancepy:
    """
    Validates FIA spread components against financepy.

    [T1] Spread crediting = OTM call at (1 + spread) × spot
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.fixture
    def standard_params(self):
        """Standard market parameters for testing."""
        return {
            "spot": 100.0,
            "rate": 0.05,
            "dividend": 0.02,
            "volatility": 0.20,
            "time_to_expiry": 1.0,
        }

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spread_rate",
        [0.01, 0.02, 0.03, 0.04, 0.05],  # 1% to 5% spreads
    )
    def test_spread_otm_call_matches_financepy(
        self, financepy_adapter, standard_params, spread_rate
    ):
        """
        [T1] OTM call at spread strike matches financepy within CROSS_LIBRARY_TOLERANCE.

        Spread crediting uses Call(K = S × (1 + spread)).
        """
        spot = standard_params["spot"]
        spread_strike = spot * (1 + spread_rate)

        our_price = black_scholes_call(
            spot=spot,
            strike=spread_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        fp_price = financepy_adapter.price_call(
            spot=spot,
            strike=spread_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = abs(our_price - fp_price) / fp_price
        assert rel_error < FINANCEPY_RELATIVE_TOLERANCE, (
            f"Spread OTM call (spread={spread_rate:.0%}) rel_error {rel_error:.2%} exceeds "
            f"tolerance ({FINANCEPY_RELATIVE_TOLERANCE:.1%}). "
            f"Our: {our_price:.6f}, financepy: {fp_price:.6f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spread_rate,time_to_expiry",
        [
            (0.02, 1.0),
            (0.03, 1.0),
            (0.04, 1.0),
            (0.02, 2.0),
            (0.02, 3.0),
        ],
    )
    def test_spread_across_terms(
        self, financepy_adapter, standard_params, spread_rate, time_to_expiry
    ):
        """
        [T1] Spread OTM call matches financepy across different terms.
        """
        spot = standard_params["spot"]
        spread_strike = spot * (1 + spread_rate)

        our_price = black_scholes_call(
            spot=spot,
            strike=spread_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=time_to_expiry,
        )

        fp_price = financepy_adapter.price_call(
            spot=spot,
            strike=spread_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=time_to_expiry,
        )

        rel_error = abs(our_price - fp_price) / fp_price
        assert rel_error < FINANCEPY_RELATIVE_TOLERANCE, (
            f"Spread call (spread={spread_rate:.0%}, T={time_to_expiry}) "
            f"rel_error {rel_error:.2%} exceeds tolerance"
        )


class TestSpreadVsCapComparison:
    """
    Validates economic relationship between spread and cap methods.

    [T1] For same rate:
    - Spread option (OTM call) has HIGHER value than cap option (call spread)
    - Because spread (full OTM call) has unlimited upside while cap (call spread) is capped

    Economic intuition:
    - Cap payoff: min(index_return, cap_rate) → capped upside
    - Spread payoff: max(0, index_return - spread_rate) → unlimited upside above spread
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize("rate", [0.05, 0.08, 0.10])  # Low rates where spread > cap
    def test_spread_more_valuable_than_cap_at_low_rates(self, financepy_adapter, rate):
        """
        [T1] At LOW rates, spread option > cap option value.

        - Spread(X%) = Call(K = S × (1+X)) — single OTM call with unlimited upside
        - Cap(X%) = Call(K = S) - Call(K = S × (1+X)) — call spread (capped upside)

        At low rates (< ~12%), spread captures more value because OTM call
        still has significant time value. At higher rates, the OTM call
        becomes nearly worthless and cap (call spread) dominates.
        """
        spot = 100.0
        r = 0.05
        q = 0.02
        vol = 0.20
        T = 1.0

        atm_strike = spot
        otm_strike = spot * (1 + rate)

        # Spread value: single OTM call (unlimited upside)
        spread_value = financepy_adapter.price_call(
            spot=spot,
            strike=otm_strike,
            rate=r,
            dividend=q,
            volatility=vol,
            time_to_expiry=T,
        )

        # Cap value: call spread = ATM call - OTM call (capped upside)
        atm_call = financepy_adapter.price_call(
            spot=spot,
            strike=atm_strike,
            rate=r,
            dividend=q,
            volatility=vol,
            time_to_expiry=T,
        )
        otm_call = financepy_adapter.price_call(
            spot=spot,
            strike=otm_strike,
            rate=r,
            dividend=q,
            volatility=vol,
            time_to_expiry=T,
        )
        cap_value = atm_call - otm_call  # Bull spread

        assert spread_value > cap_value, (
            f"Spread option ({spread_value:.4f}) should exceed cap option ({cap_value:.4f}) "
            f"at rate={rate:.0%}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("spread_rate", [0.02, 0.03, 0.05])
    def test_spread_value_decreases_with_higher_spread(self, financepy_adapter, spread_rate):
        """
        [T1] Higher spread rate → lower option value (more OTM).

        As spread increases, the call strike increases, making it more OTM.
        """
        spot = 100.0
        r = 0.05
        q = 0.02
        vol = 0.20
        T = 1.0

        base_spread = 0.01  # 1% spread
        base_strike = spot * (1 + base_spread)
        high_strike = spot * (1 + spread_rate)

        base_value = financepy_adapter.price_call(
            spot=spot,
            strike=base_strike,
            rate=r,
            dividend=q,
            volatility=vol,
            time_to_expiry=T,
        )

        high_value = financepy_adapter.price_call(
            spot=spot,
            strike=high_strike,
            rate=r,
            dividend=q,
            volatility=vol,
            time_to_expiry=T,
        )

        assert high_value < base_value, (
            f"Higher spread ({spread_rate:.0%}) should have lower value ({high_value:.4f}) "
            f"than base 1% spread ({base_value:.4f})"
        )


class TestSpreadPricerIntegration:
    """
    End-to-end validation of FIA spread crediting in the pricer.

    [T1] FIAPricer spread embedded option value should match financepy OTM call.
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "spread_rate,term_years",
        [
            (0.02, 1.0),
            (0.03, 1.0),
            (0.04, 1.0),
            (0.02, 2.0),
            (0.03, 3.0),
        ],
    )
    def test_fia_spread_embedded_option_value(self, financepy_adapter, spread_rate, term_years):
        """
        [T1] FIAPricer spread embedded option value matches financepy OTM call.

        The embedded_option_value for spread crediting should equal:
        Call(K = S × (1 + spread)) / S × premium
        """
        from annuity_pricing.data.schemas import FIAProduct
        from annuity_pricing.products.fia import FIAPricer, MarketParams

        market = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = FIAPricer(market_params=market, n_mc_paths=10000, seed=42)

        product = FIAProduct(
            company_name="Test Company",
            product_name="Spread Test FIA",
            product_group="FIA",
            status="current",
            spread_rate=spread_rate,
            indexing_method="Annual Point to Point",
            index_used="S&P 500",
        )

        premium = 100.0
        result = pricer.price(product, term_years=term_years, premium=premium)

        # Calculate expected value from financepy
        spot = 100.0
        spread_strike = spot * (1 + spread_rate)

        fp_call = financepy_adapter.price_call(
            spot=spot,
            strike=spread_strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )

        # Normalize to premium (option value / spot * premium)
        fp_normalized = fp_call / spot * premium

        # Use 1% relative tolerance for end-to-end comparison
        # (pricer uses analytical formula, should match closely)
        rel_error = abs(result.embedded_option_value - fp_normalized) / fp_normalized
        assert rel_error < 0.01, (
            f"FIA spread (rate={spread_rate:.0%}, T={term_years}) "
            f"relative error {rel_error:.2%} exceeds 1% tolerance. "
            f"FIAPricer: {result.embedded_option_value:.4f}, "
            f"financepy: {fp_normalized:.4f}"
        )


class TestSpreadVsCapAtSameOptionBudget:
    """
    Validates that spread and cap methods give different rates for same option budget.

    [T1] Given a fixed option budget:
    - Cap rate will be LOWER than spread rate
    - Because spread (OTM call) is more valuable than cap (call spread)
    - To match the same budget with a spread, need to go MORE OTM (higher spread rate)
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.mark.validation
    def test_spread_rate_higher_than_cap_at_fixed_budget(self, financepy_adapter):
        """
        [T1] For same option budget, spread_rate > cap_rate.

        If we have $3 option budget (per $100 premium):
        - Cap: Call spread worth $3 → cap at ~8% (call spread is cheap)
        - Spread: OTM call worth $3 → spread at ~15% (must go more OTM)

        The spread rate must be higher because:
        - OTM call at lower strike = more expensive
        - Need to go MORE OTM (higher spread rate) to match lower budget
        """
        spot = 100.0
        r = 0.05
        q = 0.02
        vol = 0.20
        T = 1.0
        option_budget = 3.0  # $3 per $100 premium

        # Find cap rate that gives ~$3 cap value
        # Cap value = Call(ATM) - Call(OTM at cap strike)
        atm_call = financepy_adapter.price_call(
            spot=spot, strike=spot, rate=r, dividend=q, volatility=vol, time_to_expiry=T
        )

        # Iterate to find cap rate where cap_value first drops below budget
        found_cap_rate = None
        for cap_rate in np.arange(0.01, 0.50, 0.01):
            cap_strike = spot * (1 + cap_rate)
            otm_call = financepy_adapter.price_call(
                spot=spot,
                strike=cap_strike,
                rate=r,
                dividend=q,
                volatility=vol,
                time_to_expiry=T,
            )
            cap_value = atm_call - otm_call
            if cap_value >= option_budget and found_cap_rate is None:
                found_cap_rate = cap_rate
        if found_cap_rate is None:
            found_cap_rate = 0.01

        # Find spread rate that gives ~$3 spread value
        # Spread value = Call(OTM at spread strike)
        found_spread_rate = None
        for spread_rate in np.arange(0.01, 0.50, 0.01):
            spread_strike = spot * (1 + spread_rate)
            spread_value = financepy_adapter.price_call(
                spot=spot,
                strike=spread_strike,
                rate=r,
                dividend=q,
                volatility=vol,
                time_to_expiry=T,
            )
            if spread_value <= option_budget and found_spread_rate is None:
                found_spread_rate = spread_rate
        if found_spread_rate is None:
            found_spread_rate = 0.50

        # Spread rate should be higher than cap rate for same budget
        # Because spread (OTM call) is more valuable at same strike
        assert found_spread_rate > found_cap_rate, (
            f"Spread rate ({found_spread_rate:.0%}) should exceed cap rate "
            f"({found_cap_rate:.0%}) for same option budget"
        )
