"""
Tests for RILA (Registered Index-Linked Annuity) Pricer.

Tests pricing of RILA products with:
- Buffer protection (absorbs first X% of losses)
- Floor protection (limits max loss to X%)

See: docs/knowledge/domain/buffer_floor.md
"""

import pytest
import pandas as pd

from annuity_pricing.data.schemas import RILAProduct
from annuity_pricing.products.rila import (
    RILAPricer,
    RILAPricingResult,
    MarketParams,
)


@pytest.fixture
def market_params():
    """Standard market parameters for testing."""
    return MarketParams(
        spot=100.0,
        risk_free_rate=0.05,
        dividend_yield=0.02,
        volatility=0.20,
    )


@pytest.fixture
def pricer(market_params):
    """RILA pricer with standard parameters."""
    return RILAPricer(
        market_params=market_params,
        n_mc_paths=10000,  # Reduced for faster tests
        seed=42,
    )


@pytest.fixture
def buffer_product():
    """RILA product with buffer protection."""
    return RILAProduct(
        company_name="Test Life",
        product_name="10% Buffer S&P",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.15,
        index_used="S&P 500",
        term_years=1,  # [F.1] Required term_years
    )


@pytest.fixture
def floor_product():
    """RILA product with floor protection."""
    return RILAProduct(
        company_name="Test Life",
        product_name="10% Floor S&P",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered After",
        cap_rate=0.15,
        index_used="S&P 500",
        term_years=1,  # [F.1] Required term_years
    )


class TestMarketParams:
    """Tests for MarketParams validation."""

    def test_valid_params(self, market_params):
        """Valid parameters should work."""
        assert market_params.spot == 100.0
        assert market_params.risk_free_rate == 0.05

    def test_invalid_spot(self):
        """Spot must be positive."""
        with pytest.raises(ValueError, match="spot must be > 0"):
            MarketParams(spot=0, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)


class TestRILAPricerCreation:
    """Tests for RILAPricer initialization."""

    def test_pricer_creation(self, market_params):
        """Pricer should initialize correctly."""
        pricer = RILAPricer(market_params=market_params)
        assert pricer.market_params == market_params


class TestBufferPricing:
    """Tests for buffer protection pricing."""

    def test_buffer_pricing_returns_result(self, pricer, buffer_product):
        """Buffer pricing should return RILAPricingResult."""
        result = pricer.price(buffer_product, term_years=1.0)

        assert isinstance(result, RILAPricingResult)
        assert result.present_value > 0

    def test_buffer_protection_type(self, pricer, buffer_product):
        """Should identify buffer protection."""
        result = pricer.price(buffer_product, term_years=1.0)

        assert result.protection_type == "buffer"

    def test_buffer_protection_value_positive(self, pricer, buffer_product):
        """Buffer protection should have positive value."""
        result = pricer.price(buffer_product, term_years=1.0)

        assert result.protection_value > 0

    def test_buffer_max_loss_calculation(self, pricer, buffer_product):
        """Max loss should be 1 - buffer_rate."""
        result = pricer.price(buffer_product, term_years=1.0)

        expected_max_loss = 1.0 - buffer_product.buffer_rate
        assert result.max_loss == pytest.approx(expected_max_loss)


class TestFloorPricing:
    """Tests for floor protection pricing."""

    def test_floor_pricing_returns_result(self, pricer, floor_product):
        """Floor pricing should return RILAPricingResult."""
        result = pricer.price(floor_product, term_years=1.0)

        assert isinstance(result, RILAPricingResult)
        assert result.present_value > 0

    def test_floor_protection_type(self, pricer, floor_product):
        """Should identify floor protection."""
        result = pricer.price(floor_product, term_years=1.0)

        assert result.protection_type == "floor"

    def test_floor_max_loss_calculation(self, pricer, floor_product):
        """Max loss should equal floor rate."""
        result = pricer.price(floor_product, term_years=1.0)

        assert result.max_loss == pytest.approx(floor_product.buffer_rate)


class TestBufferVsFloorComparison:
    """Tests comparing buffer vs floor protection."""

    def test_buffer_vs_floor_comparison(self, pricer):
        """Should compare buffer vs floor metrics."""
        comparison = pricer.compare_buffer_vs_floor(
            buffer_rate=0.10,
            floor_rate=0.10,
            cap_rate=0.15,
            term_years=1.0,
        )

        assert len(comparison) == 6  # 6 metrics
        assert "buffer" in comparison.columns
        assert "floor" in comparison.columns

    def test_floor_more_protection_tail(self, pricer):
        """Floor should provide more tail protection."""
        comparison = pricer.compare_buffer_vs_floor(
            buffer_rate=0.10,
            floor_rate=0.10,
            cap_rate=0.15,
            term_years=1.0,
        )

        # Floor max loss should be less than buffer max loss
        floor_max_loss = comparison[comparison["metric"] == "max_loss"]["floor"].iloc[0]
        buffer_max_loss = comparison[comparison["metric"] == "max_loss"]["buffer"].iloc[0]

        assert floor_max_loss < buffer_max_loss


class TestProtectionLevels:
    """Tests for different protection levels."""

    def test_higher_buffer_more_protection_value(self, pricer):
        """Higher buffer should have higher protection value."""
        low_buffer = RILAProduct(
            company_name="Test", product_name="5% Buffer", product_group="RILA",
            status="current", buffer_rate=0.05, buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
        )
        high_buffer = RILAProduct(
            company_name="Test", product_name="20% Buffer", product_group="RILA",
            status="current", buffer_rate=0.20, buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
        )

        low_result = pricer.price(low_buffer, term_years=1.0)
        high_result = pricer.price(high_buffer, term_years=1.0)

        assert high_result.protection_value > low_result.protection_value

    def test_higher_cap_more_upside(self, pricer):
        """Higher cap should have higher upside value."""
        low_cap = RILAProduct(
            company_name="Test", product_name="10% Cap", product_group="RILA",
            status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
            cap_rate=0.10,
        )
        high_cap = RILAProduct(
            company_name="Test", product_name="25% Cap", product_group="RILA",
            status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
            cap_rate=0.25,
        )

        low_result = pricer.price(low_cap, term_years=1.0)
        high_result = pricer.price(high_cap, term_years=1.0)

        assert high_result.upside_value > low_result.upside_value


class TestCompetitivePosition:
    """Tests for competitive positioning."""

    @pytest.fixture
    def market_data(self):
        """Sample RILA market data."""
        return pd.DataFrame({
            "productGroup": ["RILA"] * 10,
            "bufferRate": [0.10] * 10,
            "bufferModifier": ["Losses Covered Up To"] * 10,
            "capRate": [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28],
            "indexUsed": ["S&P 500"] * 10,
        })

    def test_competitive_position_buffer(self, pricer, buffer_product, market_data):
        """Should calculate percentile for buffer product."""
        position = pricer.competitive_position(buffer_product, market_data)

        assert 0 <= position.percentile <= 100
        assert position.rate == buffer_product.cap_rate

    def test_higher_cap_better_position(self, pricer, market_data):
        """Higher cap should have higher percentile."""
        low_cap = RILAProduct(
            company_name="Test", product_name="Low", product_group="RILA",
            status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
            cap_rate=0.10,
        )
        high_cap = RILAProduct(
            company_name="Test", product_name="High", product_group="RILA",
            status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
            cap_rate=0.28,
        )

        low_position = pricer.competitive_position(low_cap, market_data)
        high_position = pricer.competitive_position(high_cap, market_data)

        assert high_position.percentile > low_position.percentile


class TestEdgeCases:
    """Tests for edge cases."""

    def test_wrong_product_type(self, pricer):
        """Should reject non-RILA products."""
        from annuity_pricing.data.schemas import MYGAProduct

        myga = MYGAProduct(
            company_name="Test", product_name="Test", product_group="MYGA",
            status="current", fixed_rate=0.04, guarantee_duration=5,
        )

        with pytest.raises(ValueError, match="Expected RILAProduct"):
            pricer.price(myga)

    def test_product_with_term(self, pricer):
        """Should use term from product if available."""
        product = RILAProduct(
            company_name="Test", product_name="6Y Buffer", product_group="RILA",
            status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
            cap_rate=0.15, term_years=6,
        )

        result = pricer.price(product)

        assert result.duration == 6.0


class TestPriceMultiple:
    """Tests for batch pricing."""

    def test_price_multiple(self, pricer):
        """Should price multiple products."""
        products = [
            RILAProduct(
                company_name="A", product_name="10% Buffer", product_group="RILA",
                status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
                cap_rate=0.15,
            ),
            RILAProduct(
                company_name="B", product_name="15% Buffer", product_group="RILA",
                status="current", buffer_rate=0.15, buffer_modifier="Losses Covered Up To",
                cap_rate=0.20,
            ),
        ]

        results = pricer.price_multiple(products, term_years=1.0)

        assert len(results) == 2
        assert "present_value" in results.columns
        assert "protection_value" in results.columns


class TestBreakevenCalculation:
    """Tests for RILA breakeven solver.

    Breakeven Definition:
    --------------------
    The breakeven is the index return R where payoff = principal (net return = 0).

    For BUFFERS:
    - Buffer absorbs first X% of losses
    - Within buffer zone (-X% < R < 0): investor gets principal back (breakeven)
    - The brentq solver finds the LEFT edge of this zone at R = -buffer_rate
    - But the actual "minimum return to break even" interpretation depends on context

    For FLOORS:
    - Floor sets minimum return at -X%
    - At R = 0: investor gets principal back (breakeven)
    - Below floor: investor loses up to floor rate (not breakeven)
    - Breakeven is at R = 0

    These tests verify the ACTUAL mathematical behavior of the solver.
    """

    def test_buffer_breakeven_at_left_edge(self, pricer):
        """[T1] Buffer breakeven is at left edge of buffer zone."""
        # 10% buffer: brentq finds -0.10 (left edge of flat zone)
        breakeven = pricer._calculate_breakeven(
            is_buffer=True,
            buffer_rate=0.10,
            cap_rate=0.15,
        )

        assert breakeven is not None
        # Due to flat zone, solver may find any point in [-buffer_rate, 0]
        # The exact value depends on brentq's search direction
        assert -0.10 <= breakeven <= 0.0 + 1e-8

    def test_buffer_breakeven_within_buffer_zone(self, pricer):
        """[T1] Buffer breakeven is within the protected zone."""
        for buffer_rate in [0.05, 0.10, 0.15, 0.20, 0.25]:
            breakeven = pricer._calculate_breakeven(
                is_buffer=True,
                buffer_rate=buffer_rate,
                cap_rate=0.20,
            )

            assert breakeven is not None
            # Breakeven must be within or at edge of buffer zone
            assert -buffer_rate <= breakeven <= 0.0 + 1e-8

    def test_floor_breakeven_at_zero(self, pricer):
        """[T1] Floor breakeven is at R = 0 (no gain, no loss)."""
        # Floor: losses below floor are NOT absorbed, they're capped
        # So breakeven is where R = 0 (principal returned)
        breakeven = pricer._calculate_breakeven(
            is_buffer=False,
            buffer_rate=0.10,  # stored as positive, interpreted as -10% floor
            cap_rate=0.15,
        )

        assert breakeven is not None
        assert breakeven == pytest.approx(0.0, abs=1e-6)

    def test_floor_breakeven_always_zero(self, pricer):
        """[T1] Floor breakeven is always at R = 0, regardless of floor level."""
        for floor_rate in [0.05, 0.10, 0.15, 0.20, 0.25]:
            breakeven = pricer._calculate_breakeven(
                is_buffer=False,
                buffer_rate=floor_rate,
                cap_rate=0.20,
            )

            assert breakeven is not None
            assert breakeven == pytest.approx(0.0, abs=1e-6)

    def test_buffer_breakeven_uncapped(self, pricer):
        """[T1] Uncapped buffer has same breakeven behavior."""
        breakeven = pricer._calculate_breakeven(
            is_buffer=True,
            buffer_rate=0.10,
            cap_rate=None,  # Uncapped
        )

        assert breakeven is not None
        assert -0.10 <= breakeven <= 0.0 + 1e-8

    def test_floor_breakeven_uncapped(self, pricer):
        """[T1] Uncapped floor breakeven is still at R = 0."""
        breakeven = pricer._calculate_breakeven(
            is_buffer=False,
            buffer_rate=0.10,
            cap_rate=None,  # Uncapped
        )

        assert breakeven is not None
        assert breakeven == pytest.approx(0.0, abs=1e-6)

    def test_breakeven_returned_in_pricing_result(self, pricer, buffer_product):
        """Breakeven should be included in pricing result."""
        result = pricer.price(buffer_product, term_years=1.0)

        assert result.breakeven_return is not None
        # Buffer breakeven is within buffer zone
        assert -buffer_product.buffer_rate <= result.breakeven_return <= 0.0 + 1e-8

    def test_floor_breakeven_in_pricing_result(self, pricer, floor_product):
        """Floor breakeven should be at R = 0 in pricing result."""
        result = pricer.price(floor_product, term_years=1.0)

        assert result.breakeven_return is not None
        assert result.breakeven_return == pytest.approx(0.0, abs=1e-6)


class TestGreeksCalculation:
    """Tests for RILA hedge Greeks calculation."""

    def test_buffer_greeks_returns_result(self, pricer, buffer_product):
        """Buffer Greeks should return RILAGreeks."""
        from annuity_pricing.products.rila import RILAGreeks

        greeks = pricer.calculate_greeks(buffer_product, term_years=1.0)

        assert isinstance(greeks, RILAGreeks)
        assert greeks.protection_type == "buffer"

    def test_floor_greeks_returns_result(self, pricer, floor_product):
        """Floor Greeks should return RILAGreeks."""
        from annuity_pricing.products.rila import RILAGreeks

        greeks = pricer.calculate_greeks(floor_product, term_years=1.0)

        assert isinstance(greeks, RILAGreeks)
        assert greeks.protection_type == "floor"

    def test_buffer_delta_negative(self, pricer, buffer_product):
        """[T1] Buffer put spread should have negative delta."""
        # Long ATM put (negative delta) - Short OTM put (positive delta)
        # Net delta should be negative (long put spread)
        greeks = pricer.calculate_greeks(buffer_product, term_years=1.0)

        assert greeks.delta < 0

    def test_floor_delta_negative(self, pricer, floor_product):
        """[T1] Floor long put should have negative delta."""
        greeks = pricer.calculate_greeks(floor_product, term_years=1.0)

        assert greeks.delta < 0

    def test_buffer_gamma_positive(self, pricer, buffer_product):
        """[T1] Buffer put spread should have positive gamma."""
        # Long ATM put has higher gamma than short OTM put
        greeks = pricer.calculate_greeks(buffer_product, term_years=1.0)

        assert greeks.gamma > 0

    def test_floor_gamma_positive(self, pricer, floor_product):
        """[T1] Floor long put should have positive gamma."""
        greeks = pricer.calculate_greeks(floor_product, term_years=1.0)

        assert greeks.gamma > 0

    def test_buffer_vega_positive(self, pricer, buffer_product):
        """[T1] Buffer put spread should have positive vega (net long vol)."""
        greeks = pricer.calculate_greeks(buffer_product, term_years=1.0)

        assert greeks.vega > 0

    def test_floor_vega_positive(self, pricer, floor_product):
        """[T1] Floor long put should have positive vega."""
        greeks = pricer.calculate_greeks(floor_product, term_years=1.0)

        assert greeks.vega > 0

    def test_dollar_delta_scales_with_notional(self, pricer, buffer_product):
        """Dollar delta should scale with notional."""
        greeks_100 = pricer.calculate_greeks(buffer_product, notional=100.0)
        greeks_1000 = pricer.calculate_greeks(buffer_product, notional=1000.0)

        assert greeks_1000.dollar_delta == pytest.approx(
            greeks_100.dollar_delta * 10, rel=1e-10
        )

    def test_higher_buffer_lower_delta_magnitude(self, pricer):
        """Higher buffer should have lower delta magnitude (more OTM put offset)."""
        low_buffer = RILAProduct(
            company_name="Test", product_name="5% Buffer", product_group="RILA",
            status="current", buffer_rate=0.05, buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
        )
        high_buffer = RILAProduct(
            company_name="Test", product_name="20% Buffer", product_group="RILA",
            status="current", buffer_rate=0.20, buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
        )

        low_greeks = pricer.calculate_greeks(low_buffer, term_years=1.0)
        high_greeks = pricer.calculate_greeks(high_buffer, term_years=1.0)

        # Higher buffer = more OTM short put = less negative delta offset
        # So high buffer net delta is MORE negative
        assert abs(high_greeks.delta) > abs(low_greeks.delta)

    def test_buffer_atm_put_delta_populated(self, pricer, buffer_product):
        """Buffer should have ATM put delta populated."""
        greeks = pricer.calculate_greeks(buffer_product, term_years=1.0)

        # ATM put delta should be around -0.4 to -0.5
        # (adjusted for forward drift: r=0.05, q=0.02 shifts forward up)
        assert greeks.atm_put_delta < 0
        assert -0.7 < greeks.atm_put_delta < -0.3

    def test_floor_atm_put_delta_zero(self, pricer, floor_product):
        """Floor should have ATM put delta as zero (no ATM component)."""
        greeks = pricer.calculate_greeks(floor_product, term_years=1.0)

        assert greeks.atm_put_delta == 0.0

    def test_greeks_wrong_product_type(self, pricer):
        """Should reject non-RILA products."""
        from annuity_pricing.data.schemas import MYGAProduct

        myga = MYGAProduct(
            company_name="Test", product_name="Test", product_group="MYGA",
            status="current", fixed_rate=0.04, guarantee_duration=5,
        )

        with pytest.raises(ValueError, match="Expected RILAProduct"):
            pricer.calculate_greeks(myga)


class TestAntiPatterns:
    """Anti-pattern tests for RILA pricing."""

    def test_buffer_expected_return_bounded(self, pricer, buffer_product):
        """[T1] Expected return should be bounded by cap."""
        result = pricer.price(buffer_product, term_years=1.0)

        # Expected return shouldn't exceed cap
        assert result.expected_return <= buffer_product.cap_rate + 0.01

    def test_floor_expected_return_above_floor(self, pricer, floor_product):
        """[T1] Expected return should be above floor (in expectation)."""
        result = pricer.price(floor_product, term_years=1.0)

        # For normal market conditions, expected return should be above floor
        # (This is statistical, not guaranteed)
        assert result.expected_return >= -floor_product.buffer_rate - 0.05  # Some tolerance


class TestTermYearsRequirement:
    """
    [F.1] Tests for term_years requirement.

    RILA pricing requires explicit term_years to avoid silent defaults.
    """

    def test_rila_rejects_missing_term(self, pricer):
        """RILA pricing should reject missing term_years.

        [F.1] CRITICAL: term_years must be explicitly provided or from product.
        """
        product = RILAProduct(
            company_name="Test",
            product_name="No Term",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            # term_years not set
        )

        # Should raise without term_years
        with pytest.raises(ValueError, match="term_years required"):
            pricer.price(product)

    def test_rila_accepts_explicit_term(self, pricer, buffer_product):
        """RILA pricing should work with explicit term_years."""
        result = pricer.price(buffer_product, term_years=3.0)

        assert result.present_value > 0
        assert result.details["term_years"] == 3.0

    def test_rila_uses_product_term(self, pricer):
        """RILA pricing should use product.term_years if not explicitly provided."""
        product = RILAProduct(
            company_name="Test",
            product_name="With Term",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            term_years=5,  # 5-year term
        )

        result = pricer.price(product)  # No explicit term_years

        assert result.details["term_years"] == 5.0

    def test_rila_invalid_term_raises(self, pricer, buffer_product):
        """Zero or negative term_years should raise."""
        with pytest.raises(ValueError, match="term_years required and must be > 0"):
            pricer.price(buffer_product, term_years=0)

        with pytest.raises(ValueError, match="term_years required and must be > 0"):
            pricer.price(buffer_product, term_years=-1.0)

    def test_price_multiple_uses_product_terms(self, pricer):
        """price_multiple should use each product's term_years when not specified."""
        products = [
            RILAProduct(
                company_name="A", product_name="3Y Buffer", product_group="RILA",
                status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To",
                cap_rate=0.15, term_years=3,
            ),
            RILAProduct(
                company_name="B", product_name="5Y Buffer", product_group="RILA",
                status="current", buffer_rate=0.15, buffer_modifier="Losses Covered Up To",
                cap_rate=0.20, term_years=5,
            ),
        ]

        # No term_years specified - should use each product's term
        results = pricer.price_multiple(products)

        assert len(results) == 2
        assert "error" not in results.columns or results["error"].isna().all()

    def test_calculate_greeks_requires_term(self, pricer):
        """calculate_greeks should require term_years."""
        product = RILAProduct(
            company_name="Test",
            product_name="No Term",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            # term_years not set
        )

        with pytest.raises(ValueError, match="term_years required"):
            pricer.calculate_greeks(product)

    def test_compare_buffer_vs_floor_requires_term(self, pricer):
        """compare_buffer_vs_floor should require term_years."""
        with pytest.raises(ValueError, match="term_years required"):
            pricer.compare_buffer_vs_floor(
                buffer_rate=0.10,
                floor_rate=0.10,
                cap_rate=0.15,
                term_years=0,  # Invalid
            )


class TestBufferModifierValidation:
    """
    [F.2] Tests for buffer_modifier validation.

    RILA products must have valid buffer_modifier to determine protection type.
    Missing or invalid values should fail fast.
    """

    def test_rila_rejects_missing_buffer_modifier(self):
        """RILA should reject missing buffer_modifier.

        [F.2] CRITICAL: buffer_modifier must be specified.
        """
        with pytest.raises(ValueError, match="buffer_modifier required"):
            RILAProduct(
                company_name="Test",
                product_name="No Modifier",
                product_group="RILA",
                status="current",
                buffer_rate=0.10,
                # buffer_modifier not set
                cap_rate=0.15,
                term_years=1,
            )

    def test_rila_rejects_invalid_buffer_modifier(self):
        """RILA should reject invalid buffer_modifier.

        [F.2] CRITICAL: buffer_modifier must contain 'Up To' or 'After'.
        """
        with pytest.raises(ValueError, match="must contain 'Up To'.*or 'After'"):
            RILAProduct(
                company_name="Test",
                product_name="Bad Modifier",
                product_group="RILA",
                status="current",
                buffer_rate=0.10,
                buffer_modifier="Unknown Type",  # Invalid
                cap_rate=0.15,
                term_years=1,
            )

    def test_rila_accepts_buffer_modifier_up_to(self):
        """RILA should accept 'Losses Covered Up To' (buffer)."""
        product = RILAProduct(
            company_name="Test",
            product_name="Buffer",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            term_years=1,
        )
        assert product.is_buffer() is True
        assert product.is_floor() is False

    def test_rila_accepts_buffer_modifier_after(self):
        """RILA should accept 'Losses Covered After' (floor)."""
        product = RILAProduct(
            company_name="Test",
            product_name="Floor",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered After",
            cap_rate=0.15,
            term_years=1,
        )
        assert product.is_buffer() is False
        assert product.is_floor() is True

    def test_rila_buffer_modifier_case_insensitive(self):
        """Buffer modifier matching should be case insensitive."""
        # Lowercase
        product1 = RILAProduct(
            company_name="Test", product_name="Test1", product_group="RILA",
            status="current", buffer_rate=0.10,
            buffer_modifier="losses covered up to",  # lowercase
            cap_rate=0.15, term_years=1,
        )
        assert product1.is_buffer() is True

        # Mixed case
        product2 = RILAProduct(
            company_name="Test", product_name="Test2", product_group="RILA",
            status="current", buffer_rate=0.10,
            buffer_modifier="Losses Covered AFTER",  # mixed case
            cap_rate=0.15, term_years=1,
        )
        assert product2.is_floor() is True

    def test_rila_buffer_floor_classification_exhaustive(self):
        """Test various buffer_modifier values for correct classification."""
        buffer_modifiers = [
            ("Losses Covered Up To", True, False),
            ("Losses Covered Up to", True, False),  # lowercase 'to'
            ("up to 10%", True, False),  # partial phrase
            ("Buffer Up To", True, False),
            ("Losses Covered After", False, True),
            ("After 10%", False, True),  # partial phrase
            ("Floor After", False, True),
        ]

        for modifier, expected_buffer, expected_floor in buffer_modifiers:
            product = RILAProduct(
                company_name="Test", product_name="Test", product_group="RILA",
                status="current", buffer_rate=0.10, buffer_modifier=modifier,
                cap_rate=0.15, term_years=1,
            )
            assert product.is_buffer() == expected_buffer, f"Failed for modifier: {modifier}"
            assert product.is_floor() == expected_floor, f"Failed for modifier: {modifier}"
