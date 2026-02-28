"""
RILA pricing validation against QuantLib.

[T1] Validates that RILA buffer/floor pricing matches external oracle (QuantLib).

RILA protection is implemented via option replication:
- Buffer: Long ATM put - Short OTM put (put spread)
- Floor: Long OTM put

This test validates:
1. Individual put components match QuantLib within 1%
2. Put spread (buffer) structure produces correct value
3. Floor (OTM put) structure produces correct value

See: Hull (2021) Ch. 11 - Trading Strategies Involving Options
See: docs/knowledge/derivations/put_spread_buffer.md
"""

import pytest

# Skip entire module if QuantLib not available
pytest.importorskip("QuantLib")


class TestRILAPutComponentsVsQuantLib:
    """
    Validates RILA put components against QuantLib.

    [T1] Buffer = Long ATM put - Short OTM put
    [T1] Floor = Long OTM put
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
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
    def test_atm_put_matches_quantlib(self, quantlib_adapter, standard_params):
        """
        [T1] ATM put (long leg of buffer) matches QuantLib within 1%.
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_put

        spot = standard_params["spot"]
        our_price = black_scholes_put(
            spot=spot,
            strike=spot,  # ATM
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        ql_price = quantlib_adapter.price_european_put(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = abs(our_price - ql_price) / ql_price
        assert rel_error < 0.01, (
            f"ATM put error {rel_error:.2%} exceeds 1% tolerance. "
            f"Our: {our_price:.4f}, QuantLib: {ql_price:.4f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "buffer_rate",
        [0.05, 0.10, 0.15, 0.20, 0.25],  # 5% to 25% buffers
    )
    def test_otm_put_at_buffer_matches_quantlib(
        self, quantlib_adapter, standard_params, buffer_rate
    ):
        """
        [T1] OTM put at buffer strike (short leg) matches QuantLib within 1%.
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_put

        spot = standard_params["spot"]
        buffer_strike = spot * (1 - buffer_rate)

        our_price = black_scholes_put(
            spot=spot,
            strike=buffer_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        ql_price = quantlib_adapter.price_european_put(
            spot=spot,
            strike=buffer_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = (
            abs(our_price - ql_price) / ql_price if ql_price > 0.01 else abs(our_price - ql_price)
        )
        assert rel_error < 0.01, (
            f"OTM put at buffer {buffer_rate:.0%} error {rel_error:.2%} exceeds 1% tolerance. "
            f"Our: {our_price:.4f}, QuantLib: {ql_price:.4f}"
        )


class TestRILABufferVsQuantLib:
    """
    Validates RILA buffer (put spread) against QuantLib.

    [T1] Buffer = Long ATM put - Short OTM put at (1 - buffer_rate) * S
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
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
        "buffer_rate",
        [0.10, 0.15, 0.20, 0.25],  # 10% to 25% buffers
    )
    def test_buffer_put_spread_matches_quantlib(
        self, quantlib_adapter, standard_params, buffer_rate
    ):
        """
        [T1] Buffer put spread matches QuantLib within 1%.

        Buffer value = ATM put - OTM put at (1 - buffer) * S
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_put

        spot = standard_params["spot"]
        buffer_strike = spot * (1 - buffer_rate)

        # Our implementation
        our_atm = black_scholes_put(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        our_otm = black_scholes_put(
            spot=spot,
            strike=buffer_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        our_spread = our_atm - our_otm

        # QuantLib
        ql_atm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=spot,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        ql_otm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=buffer_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )
        ql_spread = ql_atm - ql_otm

        rel_error = (
            abs(our_spread - ql_spread) / ql_spread
            if ql_spread > 0.01
            else abs(our_spread - ql_spread)
        )
        assert rel_error < 0.01, (
            f"Buffer {buffer_rate:.0%} put spread error {rel_error:.2%} exceeds 1%. "
            f"Our spread: {our_spread:.4f}, QuantLib spread: {ql_spread:.4f}"
        )


class TestRILAFloorVsQuantLib:
    """
    Validates RILA floor (OTM put) against QuantLib.

    [T1] Floor = Long OTM put at (1 - floor_rate) * S
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
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
        "floor_rate",
        [0.10, 0.15, 0.20, 0.25],  # 10% to 25% floors
    )
    def test_floor_otm_put_matches_quantlib(self, quantlib_adapter, standard_params, floor_rate):
        """
        [T1] Floor OTM put matches QuantLib within 1%.

        Floor value = Put at strike (1 - floor_rate) * S
        """
        from annuity_pricing.options.pricing.black_scholes import black_scholes_put

        spot = standard_params["spot"]
        floor_strike = spot * (1 - floor_rate)

        our_price = black_scholes_put(
            spot=spot,
            strike=floor_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        ql_price = quantlib_adapter.price_european_put(
            spot=spot,
            strike=floor_strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
        )

        rel_error = (
            abs(our_price - ql_price) / ql_price if ql_price > 0.01 else abs(our_price - ql_price)
        )
        assert rel_error < 0.01, (
            f"Floor {floor_rate:.0%} OTM put error {rel_error:.2%} exceeds 1%. "
            f"Our: {our_price:.4f}, QuantLib: {ql_price:.4f}"
        )


class TestRILAPricerVsQuantLib:
    """
    End-to-end validation of RILAPricer protection values.

    [T1] RILAPricer._price_protection should produce values consistent
    with QuantLib put pricing.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.fixture
    def rila_pricer(self):
        """Create RILAPricer with standard params."""
        from annuity_pricing.products.rila import MarketParams, RILAPricer

        market = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        return RILAPricer(market_params=market, n_mc_paths=10000, seed=42)

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "buffer_rate,term_years",
        [
            (0.10, 1.0),
            (0.15, 1.0),
            (0.20, 1.0),
            (0.10, 2.0),
            (0.10, 3.0),
        ],
    )
    def test_rila_buffer_protection_value(
        self, quantlib_adapter, rila_pricer, buffer_rate, term_years
    ):
        """
        [T1] RILAPricer buffer protection value matches QuantLib put spread.
        """
        from annuity_pricing.data.schemas import RILAProduct

        product = RILAProduct(
            company_name="Test Company",
            product_name="Buffer Test RILA",
            product_group="RILA",
            status="current",
            buffer_rate=buffer_rate,
            buffer_modifier="Losses Covered Up To",  # Buffer product
            cap_rate=0.15,
            term_years=int(term_years),
        )

        # Price with RILAPricer
        premium = 100.0
        result = rila_pricer.price(product, term_years=term_years, premium=premium)

        # Calculate expected value from QuantLib
        spot = 100.0
        buffer_strike = spot * (1 - buffer_rate)

        ql_atm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=spot,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )
        ql_otm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=buffer_strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )
        ql_spread = ql_atm - ql_otm
        ql_normalized = ql_spread / spot * premium  # Normalize to premium

        # Compare
        rel_error = (
            abs(result.protection_value - ql_normalized) / ql_normalized
            if ql_normalized > 0.01
            else abs(result.protection_value - ql_normalized)
        )
        assert rel_error < 0.01, (
            f"RILA buffer (rate={buffer_rate:.0%}, T={term_years}) "
            f"error {rel_error:.2%} exceeds 1% tolerance. "
            f"RILAPricer: {result.protection_value:.4f}, "
            f"QuantLib spread: {ql_normalized:.4f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "floor_rate,term_years",
        [
            (0.10, 1.0),
            (0.15, 1.0),
            (0.20, 1.0),
            (0.10, 2.0),
        ],
    )
    def test_rila_floor_protection_value(
        self, quantlib_adapter, rila_pricer, floor_rate, term_years
    ):
        """
        [T1] RILAPricer floor protection value matches QuantLib OTM put.
        """
        from annuity_pricing.data.schemas import RILAProduct

        product = RILAProduct(
            company_name="Test Company",
            product_name="Floor Test RILA",
            product_group="RILA",
            status="current",
            buffer_rate=floor_rate,  # Floor stored in buffer_rate field
            buffer_modifier="Losses Covered After",  # Floor product
            cap_rate=0.15,
            term_years=int(term_years),
        )

        # Price with RILAPricer
        premium = 100.0
        result = rila_pricer.price(product, term_years=term_years, premium=premium)

        # Calculate expected value from QuantLib
        spot = 100.0
        floor_strike = spot * (1 - floor_rate)

        ql_put = quantlib_adapter.price_european_put(
            spot=spot,
            strike=floor_strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=term_years,
        )
        ql_normalized = ql_put / spot * premium  # Normalize to premium

        # Compare
        rel_error = (
            abs(result.protection_value - ql_normalized) / ql_normalized
            if ql_normalized > 0.01
            else abs(result.protection_value - ql_normalized)
        )
        assert rel_error < 0.01, (
            f"RILA floor (rate={floor_rate:.0%}, T={term_years}) "
            f"error {rel_error:.2%} exceeds 1% tolerance. "
            f"RILAPricer: {result.protection_value:.4f}, "
            f"QuantLib put: {ql_normalized:.4f}"
        )


class TestBufferVsFloorValueComparison:
    """
    Validates buffer vs floor value relationship.

    [T1] For same protection level, buffer should be more expensive than floor
    because buffer absorbs first X% while floor only kicks in after X%.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "protection_rate",
        [0.10, 0.15, 0.20],
    )
    def test_buffer_more_valuable_than_floor(self, quantlib_adapter, protection_rate):
        """
        [T1] Buffer (put spread) should be worth more than floor (OTM put).

        At same protection level X%:
        - Buffer: Absorbs first X% of losses (put spread ATM-OTM)
        - Floor: Only protects after X% loss (single OTM put)

        Buffer provides more valuable protection (first dollars vs last).
        """
        spot = 100.0
        strike = spot * (1 - protection_rate)

        # Buffer = ATM put - OTM put
        ql_atm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=spot,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        ql_otm = quantlib_adapter.price_european_put(
            spot=spot,
            strike=strike,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        buffer_value = ql_atm - ql_otm

        # Floor = OTM put
        floor_value = ql_otm

        assert buffer_value > floor_value, (
            f"Buffer ({protection_rate:.0%}) should be > Floor ({protection_rate:.0%}). "
            f"Buffer: {buffer_value:.4f}, Floor: {floor_value:.4f}"
        )
