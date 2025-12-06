"""
Integration tests for ProductRegistry.

Tests unified dispatch across all product types (MYGA, FIA, RILA).
"""

import pytest
import pandas as pd

from annuity_pricing.data.schemas import (
    FIAProduct,
    MYGAProduct,
    RILAProduct,
)
from annuity_pricing.products.registry import (
    ProductRegistry,
    MarketEnvironment,
    create_default_registry,
    price_product,
)
from annuity_pricing.products.fia import FIAPricingResult
from annuity_pricing.products.rila import RILAPricingResult


@pytest.fixture
def market_env():
    """Standard market environment."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        spot=100.0,
        dividend_yield=0.02,
        volatility=0.20,
        option_budget_pct=0.03,
    )


@pytest.fixture
def registry(market_env):
    """Product registry with standard market environment."""
    return ProductRegistry(
        market_env=market_env,
        n_mc_paths=10000,  # Reduced for faster tests
        seed=42,
    )


@pytest.fixture
def myga_product():
    """Sample MYGA product."""
    return MYGAProduct(
        company_name="Test Life",
        product_name="5-Year MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def fia_product():
    """Sample FIA product. [F.4] Uses 5% cap to fit within tightened budget tolerance."""
    return FIAProduct(
        company_name="Test Life",
        product_name="S&P 500 Cap",
        product_group="FIA",
        status="current",
        cap_rate=0.05,  # [F.4] Reduced from 0.10 to fit 10% budget tolerance
        index_used="S&P 500",
    )


@pytest.fixture
def rila_product():
    """Sample RILA product."""
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


class TestMarketEnvironment:
    """Tests for MarketEnvironment."""

    def test_valid_environment(self, market_env):
        """Valid environment should work."""
        assert market_env.risk_free_rate == 0.05
        assert market_env.spot == 100.0

    def test_invalid_risk_free_rate(self):
        """Extreme risk-free rate should fail."""
        with pytest.raises(ValueError, match="risk_free_rate"):
            MarketEnvironment(risk_free_rate=0.60)

    def test_invalid_spot(self):
        """Non-positive spot should fail."""
        with pytest.raises(ValueError, match="spot must be > 0"):
            MarketEnvironment(spot=0)

    def test_to_fia_market_params(self, market_env):
        """Should convert to FIA market params."""
        fia_params = market_env.to_fia_market_params()
        assert fia_params.spot == market_env.spot
        assert fia_params.risk_free_rate == market_env.risk_free_rate

    def test_to_rila_market_params(self, market_env):
        """Should convert to RILA market params."""
        rila_params = market_env.to_rila_market_params()
        assert rila_params.spot == market_env.spot
        assert rila_params.volatility == market_env.volatility


class TestRegistryCreation:
    """Tests for registry creation."""

    def test_registry_creation(self, market_env):
        """Registry should initialize correctly."""
        registry = ProductRegistry(market_env=market_env)
        assert registry.market_env == market_env

    def test_registry_with_seed(self, market_env):
        """Registry should accept seed."""
        registry = ProductRegistry(market_env=market_env, seed=42)
        assert registry.seed == 42

    def test_get_pricer_info(self, registry):
        """Should return pricer info."""
        info = registry.get_pricer_info()
        assert "MYGA" in info["supported_types"]
        assert "FIA" in info["supported_types"]
        assert "RILA" in info["supported_types"]


class TestUnifiedPricing:
    """Tests for unified pricing across product types."""

    def test_price_myga(self, registry, myga_product):
        """Should price MYGA product."""
        result = registry.price(myga_product)
        assert result.present_value > 0
        assert result.duration is not None

    def test_price_fia(self, registry, fia_product):
        """Should price FIA product."""
        result = registry.price(fia_product, term_years=1.0)
        assert isinstance(result, FIAPricingResult)
        assert result.present_value > 0
        assert result.expected_credit >= 0

    def test_price_rila(self, registry, rila_product):
        """Should price RILA product."""
        result = registry.price(rila_product, term_years=1.0)
        assert isinstance(result, RILAPricingResult)
        assert result.present_value > 0
        assert result.protection_value > 0

    def test_unsupported_product_type(self, registry):
        """Should reject unsupported product types."""
        class UnsupportedProduct:
            pass

        with pytest.raises(ValueError, match="Unsupported product type"):
            registry.price(UnsupportedProduct())


class TestPriceMultiple:
    """Tests for batch pricing."""

    def test_price_multiple_same_type(self, registry):
        """Should price multiple products of same type."""
        products = [
            MYGAProduct(
                company_name="A", product_name="MYGA A",
                product_group="MYGA", status="current",
                fixed_rate=0.04, guarantee_duration=3,
            ),
            MYGAProduct(
                company_name="B", product_name="MYGA B",
                product_group="MYGA", status="current",
                fixed_rate=0.05, guarantee_duration=5,
            ),
        ]

        results = registry.price_multiple(products)
        assert len(results) == 2
        assert "present_value" in results.columns
        assert all(results["present_value"] > 0)

    def test_price_multiple_mixed_types(self, registry, myga_product, fia_product, rila_product):
        """Should price multiple products of different types."""
        products = [myga_product, fia_product, rila_product]
        results = registry.price_multiple(products, term_years=1.0)

        assert len(results) == 3
        assert set(results["product_group"]) == {"MYGA", "FIA", "RILA"}


class TestPriceFromRow:
    """Tests for pricing from WINK row."""

    def test_price_myga_from_row(self, registry):
        """Should price MYGA from row dict."""
        row = {
            "companyName": "Test Life",
            "productName": "5Y MYGA",
            "status": "current",
            "fixedRate": 0.045,
            "guaranteeDuration": 5,
        }

        result = registry.price_from_row(row, "MYGA")
        assert result.present_value > 0

    def test_price_fia_from_row(self, registry):
        """Should price FIA from row dict. [F.4] Uses 5% cap for budget tolerance."""
        row = {
            "companyName": "Test Life",
            "productName": "S&P Cap",
            "status": "current",
            "capRate": 0.05,  # [F.4] Reduced from 0.10 to fit 10% budget tolerance
            "indexUsed": "S&P 500",
        }

        result = registry.price_from_row(row, "FIA", term_years=1.0)
        assert isinstance(result, FIAPricingResult)

    def test_price_rila_from_row(self, registry):
        """Should price RILA from row dict."""
        row = {
            "companyName": "Test Life",
            "productName": "10% Buffer",
            "status": "current",
            "bufferRate": 0.10,
            "bufferModifier": "Losses Covered Up To",
            "capRate": 0.15,
        }

        result = registry.price_from_row(row, "RILA", term_years=1.0)
        assert isinstance(result, RILAPricingResult)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_default_registry(self):
        """Should create default registry."""
        registry = create_default_registry()
        info = registry.get_pricer_info()
        assert info["market_environment"]["risk_free_rate"] == 0.05

    def test_create_default_registry_with_params(self):
        """Should create registry with custom params."""
        registry = create_default_registry(
            risk_free_rate=0.04,
            volatility=0.25,
            seed=123,
        )
        info = registry.get_pricer_info()
        assert info["market_environment"]["risk_free_rate"] == 0.04
        assert info["market_environment"]["volatility"] == 0.25
        assert info["seed"] == 123

    def test_price_product_function(self, myga_product):
        """Should price single product with convenience function."""
        result = price_product(myga_product)
        assert result.present_value > 0


class TestCompetitivePosition:
    """Tests for competitive positioning."""

    @pytest.fixture
    def myga_market_data(self):
        """Sample MYGA market data."""
        return pd.DataFrame({
            "productGroup": ["MYGA"] * 10,
            "fixedRate": [0.03, 0.035, 0.04, 0.042, 0.045,
                         0.047, 0.05, 0.052, 0.055, 0.06],
            "guaranteeDuration": [5] * 10,
        })

    @pytest.fixture
    def fia_market_data(self):
        """Sample FIA market data."""
        return pd.DataFrame({
            "productGroup": ["FIA"] * 10,
            "capRate": [0.06, 0.07, 0.08, 0.09, 0.10,
                       0.11, 0.12, 0.13, 0.14, 0.15],
            "indexUsed": ["S&P 500"] * 10,
        })

    def test_myga_competitive_position(self, registry, myga_product, myga_market_data):
        """Should calculate MYGA competitive position."""
        position = registry.competitive_position(myga_product, myga_market_data)
        assert 0 <= position.percentile <= 100

    def test_fia_competitive_position(self, registry, fia_product, fia_market_data):
        """Should calculate FIA competitive position."""
        position = registry.competitive_position(fia_product, fia_market_data)
        assert 0 <= position.percentile <= 100


class TestReproducibility:
    """Tests for reproducibility with seeds."""

    def test_reproducible_fia_pricing(self, market_env, fia_product):
        """FIA pricing should be reproducible with same seed."""
        registry1 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        registry2 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)

        result1 = registry1.price(fia_product, term_years=1.0)
        result2 = registry2.price(fia_product, term_years=1.0)

        assert result1.expected_credit == pytest.approx(result2.expected_credit)

    def test_different_seeds_different_results(self, market_env, fia_product):
        """Different seeds should give different MC results."""
        registry1 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        registry2 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=123)

        result1 = registry1.price(fia_product, term_years=1.0)
        result2 = registry2.price(fia_product, term_years=1.0)

        # Should be close but not identical
        assert result1.expected_credit != result2.expected_credit
        assert abs(result1.expected_credit - result2.expected_credit) < 0.01
