"""
Tests for FIA (Fixed Indexed Annuity) Pricer.

Tests pricing of FIA products with:
- Cap crediting
- Participation crediting
- Spread crediting
- Trigger crediting

See: docs/knowledge/domain/crediting_methods.md
"""

import pytest
import pandas as pd

from annuity_pricing.data.schemas import FIAProduct
from annuity_pricing.products.fia import (
    FIAPricer,
    FIAPricingResult,
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
    """FIA pricer with standard parameters."""
    return FIAPricer(
        market_params=market_params,
        option_budget_pct=0.03,
        n_mc_paths=10000,  # Reduced for faster tests
        seed=42,
    )


@pytest.fixture
def cap_product():
    """FIA product with cap crediting."""
    return FIAProduct(
        company_name="Test Life",
        product_name="S&P 500 Cap",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
        index_used="S&P 500",
    )


@pytest.fixture
def participation_product():
    """FIA product with participation crediting."""
    return FIAProduct(
        company_name="Test Life",
        product_name="S&P 500 Participation",
        product_group="FIA",
        status="current",
        participation_rate=0.80,
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

    def test_invalid_volatility(self):
        """Volatility must be non-negative."""
        with pytest.raises(ValueError, match="volatility must be >= 0"):
            MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=-0.20)


class TestFIAPricerCreation:
    """Tests for FIAPricer initialization."""

    def test_pricer_creation(self, market_params):
        """Pricer should initialize correctly."""
        pricer = FIAPricer(market_params=market_params)
        assert pricer.market_params == market_params
        assert pricer.option_budget_pct == 0.03

    def test_custom_option_budget(self, market_params):
        """Custom option budget should work."""
        pricer = FIAPricer(market_params=market_params, option_budget_pct=0.05)
        assert pricer.option_budget_pct == 0.05

    def test_invalid_option_budget(self, market_params):
        """Negative option budget should fail."""
        with pytest.raises(ValueError, match="option_budget_pct must be >= 0"):
            FIAPricer(market_params=market_params, option_budget_pct=-0.01)


class TestCapPricing:
    """Tests for cap crediting method pricing."""

    def test_cap_pricing_returns_result(self, pricer, cap_product):
        """Cap pricing should return FIAPricingResult."""
        result = pricer.price(cap_product, term_years=1.0)

        assert isinstance(result, FIAPricingResult)
        assert result.present_value > 0

    def test_cap_pricing_embedded_option(self, pricer, cap_product):
        """Cap pricing should calculate embedded option value."""
        result = pricer.price(cap_product, term_years=1.0)

        assert result.embedded_option_value >= 0
        assert result.option_budget > 0

    def test_cap_expected_credit_positive(self, pricer, cap_product):
        """Expected credit should be positive for cap product."""
        result = pricer.price(cap_product, term_years=1.0)

        assert result.expected_credit >= 0  # FIA floor is 0%

    def test_cap_expected_credit_capped(self, pricer, cap_product):
        """Expected credit should be <= cap rate."""
        result = pricer.price(cap_product, term_years=1.0)

        assert result.expected_credit <= cap_product.cap_rate + 0.01  # Small tolerance

    def test_higher_cap_higher_value(self, pricer):
        """Higher cap should give higher expected credit."""
        low_cap = FIAProduct(
            company_name="Test", product_name="Low Cap", product_group="FIA",
            status="current", cap_rate=0.05,
        )
        high_cap = FIAProduct(
            company_name="Test", product_name="High Cap", product_group="FIA",
            status="current", cap_rate=0.15,
        )

        low_result = pricer.price(low_cap, term_years=1.0)
        high_result = pricer.price(high_cap, term_years=1.0)

        assert high_result.expected_credit > low_result.expected_credit


class TestParticipationPricing:
    """Tests for participation crediting method pricing."""

    def test_participation_pricing_returns_result(self, pricer, participation_product):
        """Participation pricing should return FIAPricingResult."""
        result = pricer.price(participation_product, term_years=1.0)

        assert isinstance(result, FIAPricingResult)
        assert result.present_value > 0

    def test_higher_participation_higher_value(self, pricer):
        """Higher participation should give higher expected credit."""
        low_par = FIAProduct(
            company_name="Test", product_name="Low Par", product_group="FIA",
            status="current", participation_rate=0.50,
        )
        high_par = FIAProduct(
            company_name="Test", product_name="High Par", product_group="FIA",
            status="current", participation_rate=1.00,
        )

        low_result = pricer.price(low_par, term_years=1.0)
        high_result = pricer.price(high_par, term_years=1.0)

        assert high_result.expected_credit > low_result.expected_credit


class TestFairTermCalculation:
    """Tests for fair cap/participation calculation."""

    def test_fair_cap_calculated(self, pricer, cap_product):
        """Fair cap should be calculated."""
        result = pricer.price(cap_product, term_years=1.0)

        assert result.fair_cap is not None
        assert result.fair_cap > 0

    def test_fair_participation_calculated(self, pricer, cap_product):
        """Fair participation should be calculated."""
        result = pricer.price(cap_product, term_years=1.0)

        assert result.fair_participation is not None
        assert result.fair_participation > 0

    def test_higher_budget_higher_fair_cap(self, market_params):
        """Higher option budget should give higher fair cap."""
        low_budget_pricer = FIAPricer(
            market_params=market_params, option_budget_pct=0.02, n_mc_paths=5000, seed=42
        )
        high_budget_pricer = FIAPricer(
            market_params=market_params, option_budget_pct=0.05, n_mc_paths=5000, seed=42
        )

        product = FIAProduct(
            company_name="Test", product_name="Test", product_group="FIA",
            status="current", cap_rate=0.10,
        )

        low_result = low_budget_pricer.price(product, term_years=1.0)
        high_result = high_budget_pricer.price(product, term_years=1.0)

        assert high_result.fair_cap > low_result.fair_cap


class TestCompetitivePosition:
    """Tests for competitive positioning."""

    @pytest.fixture
    def market_data(self):
        """Sample FIA market data."""
        return pd.DataFrame({
            "productGroup": ["FIA"] * 10,
            "capRate": [0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15],
            "participationRate": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4],
            "indexUsed": ["S&P 500"] * 10,
        })

    def test_competitive_position_cap(self, pricer, cap_product, market_data):
        """Should calculate percentile for cap product."""
        position = pricer.competitive_position(cap_product, market_data)

        assert 0 <= position.percentile <= 100
        assert position.rate == cap_product.cap_rate

    def test_competitive_position_rank(self, pricer, market_data):
        """Higher cap should have higher percentile."""
        low_cap = FIAProduct(
            company_name="Test", product_name="Low", product_group="FIA",
            status="current", cap_rate=0.06,
        )
        high_cap = FIAProduct(
            company_name="Test", product_name="High", product_group="FIA",
            status="current", cap_rate=0.15,
        )

        low_position = pricer.competitive_position(low_cap, market_data)
        high_position = pricer.competitive_position(high_cap, market_data)

        assert high_position.percentile > low_position.percentile


class TestEdgeCases:
    """Tests for edge cases."""

    def test_wrong_product_type(self, pricer):
        """Should reject non-FIA products."""
        from annuity_pricing.data.schemas import MYGAProduct

        myga = MYGAProduct(
            company_name="Test", product_name="Test", product_group="MYGA",
            status="current", fixed_rate=0.04, guarantee_duration=5,
        )

        with pytest.raises(ValueError, match="Expected FIAProduct"):
            pricer.price(myga)

    def test_no_crediting_method(self, pricer):
        """Product with no crediting method should raise ValueError.

        [NEVER FAIL SILENTLY] - No crediting method is an error, not a default.
        """
        product = FIAProduct(
            company_name="Test", product_name="No Method", product_group="FIA",
            status="current",
        )

        # Should raise - no silent defaults
        with pytest.raises(ValueError, match="has no crediting method"):
            pricer.price(product, term_years=1.0)


class TestPriceMultiple:
    """Tests for batch pricing."""

    def test_price_multiple(self, pricer):
        """Should price multiple products."""
        products = [
            FIAProduct(
                company_name="A", product_name="Cap 8%", product_group="FIA",
                status="current", cap_rate=0.08,
            ),
            FIAProduct(
                company_name="B", product_name="Cap 10%", product_group="FIA",
                status="current", cap_rate=0.10,
            ),
        ]

        results = pricer.price_multiple(products, term_years=1.0)

        assert len(results) == 2
        assert "present_value" in results.columns
        assert "expected_credit" in results.columns
