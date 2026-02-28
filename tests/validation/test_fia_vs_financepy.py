"""
FIA pricing validation against financepy.

[T1] Validates that FIA capped call pricing matches external oracle (financepy).

FIA cap crediting is implemented as a call spread:
- Long ATM call (participates in index gains)
- Short OTM call at cap strike (gives up gains above cap)

This test validates:
1. Individual option components match financepy within 1%
2. Call spread (capped call) structure produces correct value
3. FIA fair cap calculation is consistent with option replication

See: Hull (2021) Ch. 11 - Trading Strategies Involving Options (Bull Spreads)
See: docs/knowledge/domain/crediting_methods.md
"""

import pytest

# Skip entire module if financepy not available
pytest.importorskip("financepy")


class TestFIACappedCallVsFinancepy:
    """
    Validates FIA capped call against financepy Black-Scholes.

    [T1] A capped call with cap C% is replicated as:
    - Long ATM call: strike = spot
    - Short OTM call: strike = spot * (1 + cap_rate)

    Value = Call(K=S) - Call(K=S*(1+C))
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

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
    def test_atm_call_matches_financepy(self, financepy_adapter, standard_params):
        """
        [T1] ATM call (long leg of capped call) matches financepy within 1%.
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_call

        spot = standard_params["spot"]
        our_price = black_scholes_call(
            spot=spot,
            strike=spot,  # ATM
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        fp_price = financepy_adapter.price_call(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = abs(our_price - fp_price) / fp_price
        assert rel_error < 0.01, (
            f"ATM call error {rel_error:.2%} exceeds 1% tolerance. "
            f"Our: {our_price:.4f}, financepy: {fp_price:.4f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "cap_rate",
        [0.05, 0.10, 0.15, 0.20, 0.25],  # 5% to 25% caps
    )
    def test_otm_call_at_cap_matches_financepy(self, financepy_adapter, standard_params, cap_rate):
        """
        [T1] OTM call at cap strike (short leg) matches financepy within 1%.
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_call

        spot = standard_params["spot"]
        cap_strike = spot * (1 + cap_rate)

        our_price = black_scholes_call(
            spot=spot,
            strike=cap_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        fp_price = financepy_adapter.price_call(
            spot=spot,
            strike=cap_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = (
            abs(our_price - fp_price) / fp_price if fp_price > 0.01 else abs(our_price - fp_price)
        )
        assert rel_error < 0.01, (
            f"OTM call at cap {cap_rate:.0%} error {rel_error:.2%} exceeds 1% tolerance. "
            f"Our: {our_price:.4f}, financepy: {fp_price:.4f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "cap_rate",
        [0.05, 0.10, 0.15, 0.20],
    )
    def test_capped_call_spread_matches_financepy(
        self, financepy_adapter, standard_params, cap_rate
    ):
        """
        [T1] Capped call (call spread) matches financepy within 1%.

        Capped call value = Call(ATM) - Call(OTM at cap)
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_call

        spot = standard_params["spot"]
        cap_strike = spot * (1 + cap_rate)

        # Our implementation
        our_atm = black_scholes_call(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        our_otm = black_scholes_call(
            spot=spot,
            strike=cap_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        our_spread = our_atm - our_otm

        # Financepy
        fp_atm = financepy_adapter.price_call(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        fp_otm = financepy_adapter.price_call(
            spot=spot,
            strike=cap_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        fp_spread = fp_atm - fp_otm

        rel_error = (
            abs(our_spread - fp_spread) / fp_spread
            if fp_spread > 0.01
            else abs(our_spread - fp_spread)
        )
        assert rel_error < 0.01, (
            f"Capped call (cap={cap_rate:.0%}) error {rel_error:.2%} exceeds 1% tolerance. "
            f"Our spread: {our_spread:.4f}, financepy spread: {fp_spread:.4f}"
        )


class TestFIAPricerVsFinancepy:
    """
    End-to-end validation of FIAPricer embedded option value.

    [T1] FIAPricer._price_capped_call should produce values consistent
    with the call spread replication priced by financepy.
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.fixture
    def fia_pricer(self):
        """Create FIAPricer with standard params."""
        from annuity_pricing.products.fia import FIAPricer, MarketParams

        market = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        return FIAPricer(market_params=market, n_mc_paths=10000, seed=42)

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "cap_rate,term_years",
        [
            (0.05, 1.0),
            (0.10, 1.0),
            (0.15, 1.0),
            (0.10, 2.0),
            (0.10, 3.0),
        ],
    )
    def test_fia_embedded_option_value(self, financepy_adapter, fia_pricer, cap_rate, term_years):
        """
        [T1] FIAPricer embedded option value matches financepy call spread.

        The embedded_option_value in FIAPricingResult should equal the
        call spread value (normalized to premium).
        """
        from annuity_pricing.data.schemas import FIAProduct

        product = FIAProduct(
            company_name="Test Company",
            product_name="Cap Test FIA",
            product_group="FIA",
            status="current",
            cap_rate=cap_rate,
            indexing_method="Annual Point to Point",
            index_used="S&P 500",
        )

        # Price with FIAPricer
        premium = 100.0
        result = fia_pricer.price(product, term_years=term_years, premium=premium)

        # Calculate expected value from financepy
        spot = 100.0
        cap_strike = spot * (1 + cap_rate)

        fp_atm = financepy_adapter.price_call(
            spot=spot,
            strike=spot,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )
        fp_otm = financepy_adapter.price_call(
            spot=spot,
            strike=cap_strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )
        fp_spread = fp_atm - fp_otm
        fp_normalized = fp_spread / spot * premium  # Normalize to premium

        # Compare
        rel_error = (
            abs(result.embedded_option_value - fp_normalized) / fp_normalized
            if fp_normalized > 0.01
            else abs(result.embedded_option_value - fp_normalized)
        )
        assert rel_error < 0.01, (
            f"FIA embedded option (cap={cap_rate:.0%}, T={term_years}) "
            f"error {rel_error:.2%} exceeds 1% tolerance. "
            f"FIAPricer: {result.embedded_option_value:.4f}, "
            f"financepy spread: {fp_normalized:.4f}"
        )


class TestFIAFairCapVsFinancepy:
    """
    Validates FIA fair cap calculation against financepy.

    [T1] Given an option budget, the fair cap should produce
    a call spread value equal to the budget.
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "option_budget_pct",
        [0.02, 0.03, 0.04, 0.05],  # 2% to 5% budgets
    )
    def test_fair_cap_produces_budget_value(self, financepy_adapter, option_budget_pct):
        """
        [T1] Fair cap should produce call spread equal to option budget.

        If fair cap = 10% given 3% budget, then:
        Call(ATM) - Call(1.10*S) ≈ 3% of spot
        """
        from annuity_pricing.products.fia import FIAPricer, MarketParams

        market = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = FIAPricer(
            market_params=market,
            option_budget_pct=option_budget_pct,
            n_mc_paths=10000,
            seed=42,
        )

        # Calculate fair cap using private solver method
        premium = 100.0
        option_budget = premium * option_budget_pct
        fair_cap = pricer._solve_fair_cap(
            term_years=1.0,
            option_budget=option_budget,
            premium=premium,
        )

        # Verify call spread at fair cap equals budget
        spot = 100.0
        cap_strike = spot * (1 + fair_cap)

        fp_atm = financepy_adapter.price_call(
            spot=spot,
            strike=spot,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        fp_otm = financepy_adapter.price_call(
            spot=spot,
            strike=cap_strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        spread_value = fp_atm - fp_otm
        spread_as_pct = spread_value / spot

        # Budget should match spread (within 5% for solver precision)
        rel_error = abs(spread_as_pct - option_budget_pct) / option_budget_pct
        assert rel_error < 0.05, (
            f"Fair cap {fair_cap:.2%} produces spread {spread_as_pct:.2%}, "
            f"expected budget {option_budget_pct:.2%}. "
            f"Error: {rel_error:.2%}"
        )


class TestFIAParticipationVsFinancepy:
    """
    Validates FIA participation rate pricing against financepy.

    [T1] Participation crediting uses: participation_rate * max(0, R)
    where R is index return. This is equivalent to holding
    participation_rate units of an ATM call.
    """

    @pytest.fixture
    def financepy_adapter(self):
        """Get financepy adapter."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

        adapter = FinancepyAdapter()
        if not adapter.is_available:
            pytest.skip("financepy not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "participation_rate",
        [0.50, 0.75, 1.00, 1.25, 1.50],
    )
    def test_participation_matches_scaled_call(self, financepy_adapter, participation_rate):
        """
        [T1] Participation value = participation_rate * ATM call.
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_call

        spot = 100.0
        rate = 0.05
        dividend = 0.02
        vol = 0.20
        term = 1.0

        # Our participation value
        atm_call = black_scholes_call(
            spot=spot,
            strike=spot,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=term,
        )
        our_value = participation_rate * atm_call

        # Financepy participation value
        fp_call = financepy_adapter.price_call(
            spot=spot,
            strike=spot,
            rate=rate,
            dividend=dividend,
            volatility=vol,
            time_to_expiry=term,
        )
        fp_value = participation_rate * fp_call

        rel_error = abs(our_value - fp_value) / fp_value
        assert rel_error < 0.01, (
            f"Participation {participation_rate:.0%} error {rel_error:.2%} exceeds 1%. "
            f"Our: {our_value:.4f}, financepy: {fp_value:.4f}"
        )
