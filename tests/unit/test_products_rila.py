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
