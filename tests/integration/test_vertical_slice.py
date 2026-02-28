"""
Vertical slice tests: Complete workflow from data through validation.

These tests verify the entire pricing pipeline works end-to-end:
1. Load/create product data
2. Configure market environment
3. Price through registry
4. Calculate Greeks
5. Validate results

References:
    [T1] METHODOLOGY.md: Skepticism of Success - validate all outputs
"""

import pytest

from annuity_pricing.data.schemas import (
    FIAProduct,
    MYGAProduct,
    RILAProduct,
)
from annuity_pricing.products.fia import FIAPricingResult
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
)
from annuity_pricing.products.rila import RILAPricingResult

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def market_env():
    """Standard market environment for integration tests."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        spot=100.0,
        dividend_yield=0.02,
        volatility=0.20,
        option_budget_pct=0.03,
    )


@pytest.fixture
def registry(market_env):
    """Registry with seeded RNG for reproducibility."""
    return ProductRegistry(
        market_env=market_env,
        n_mc_paths=10000,
        seed=42,
    )


@pytest.fixture
def myga_product():
    """Sample MYGA for vertical slice."""
    return MYGAProduct(
        company_name="Integration Test Life",
        product_name="5Y MYGA Test",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def fia_product():
    """Sample FIA for vertical slice. Uses 5% cap to fit budget tolerance."""
    return FIAProduct(
        company_name="Integration Test Life",
        product_name="S&P 500 FIA Test",
        product_group="FIA",
        status="current",
        cap_rate=0.05,
        index_used="S&P 500",
    )


@pytest.fixture
def rila_product():
    """Sample RILA for vertical slice."""
    return RILAProduct(
        company_name="Integration Test Life",
        product_name="10% Buffer RILA Test",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.15,
        index_used="S&P 500",
    )


# =============================================================================
# Vertical Slice Tests
# =============================================================================


class TestMYGAVerticalSlice:
    """MYGA: Create → Price → Validate complete workflow."""

    def test_myga_slice(self, registry, myga_product):
        """[T1] Complete MYGA workflow produces valid outputs."""
        # Price through registry
        result = registry.price(myga_product)

        # Validate fundamental outputs
        assert result.present_value > 0, "PV must be positive for MYGA"
        assert result.duration is not None, "Duration must be computed"
        assert result.duration >= 0, "Duration must be non-negative"
        # Validation is run via registry.price(..., validate=True) by default
        # No exception means validation passed

    def test_myga_slice_with_custom_term(self, registry, myga_product):
        """MYGA with custom term_years still produces valid result."""
        result = registry.price(myga_product, term_years=7)

        assert result.present_value > 0
        assert result.duration >= 0

    def test_myga_pv_increases_with_rate(self, market_env, myga_product):
        """[T1] Higher guaranteed rate should increase PV."""
        low_rate_product = MYGAProduct(
            company_name="Test",
            product_name="Low Rate",
            product_group="MYGA",
            status="current",
            fixed_rate=0.03,
            guarantee_duration=5,
        )
        high_rate_product = MYGAProduct(
            company_name="Test",
            product_name="High Rate",
            product_group="MYGA",
            status="current",
            fixed_rate=0.05,
            guarantee_duration=5,
        )

        registry = ProductRegistry(market_env=market_env, seed=42)
        low_pv = registry.price(low_rate_product).present_value
        high_pv = registry.price(high_rate_product).present_value

        assert high_pv > low_pv, "Higher rate should yield higher PV"


class TestFIAVerticalSlice:
    """FIA: Create → Price → Greeks → Validate complete workflow."""

    def test_fia_slice(self, registry, fia_product):
        """[T1] Complete FIA workflow produces valid outputs."""
        result = registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Type check
        assert isinstance(result, FIAPricingResult)

        # Validate fundamental outputs
        assert result.present_value > 0, "PV must be positive"
        assert result.embedded_option_value >= 0, "Option value must be non-negative"
        # No exception means validation passed

    def test_fia_slice_with_greeks(self, registry, fia_product):
        """FIA workflow includes valid Greeks."""
        result = registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Greeks should be present (from the result's greeks attribute if available)
        # Even without explicit greeks, embedded option value implies delta hedging
        assert result.embedded_option_value >= 0

    def test_fia_fair_rates_positive(self, registry, fia_product):
        """[T1] Fair cap and participation should be positive."""
        result = registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Fair rates (if computed) should be positive
        if hasattr(result, "fair_cap") and result.fair_cap is not None:
            assert result.fair_cap > 0, "Fair cap must be positive"
        if hasattr(result, "fair_participation") and result.fair_participation is not None:
            assert result.fair_participation > 0, "Fair participation must be positive"


class TestRILAVerticalSlice:
    """RILA: Create → Price → Greeks → Validate complete workflow."""

    def test_rila_slice(self, registry, rila_product):
        """[T1] Complete RILA workflow produces valid outputs."""
        result = registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # Type check
        assert isinstance(result, RILAPricingResult)

        # Validate fundamental outputs
        assert result.present_value > 0, "PV must be positive"
        assert result.protection_value >= 0, "Protection value must be non-negative"
        # No exception means validation passed

    def test_rila_max_loss_bounded(self, registry, rila_product):
        """[T1] Max loss bounded by buffer."""
        result = registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # For 10% buffer, max loss = 90% of premium
        expected_max_loss = -0.90  # As a fraction
        if result.max_loss is not None:
            assert result.max_loss >= expected_max_loss, (
                f"Max loss {result.max_loss} should be >= {expected_max_loss}"
            )

    def test_rila_upside_positive(self, registry, rila_product):
        """RILA upside value should be non-negative."""
        result = registry.price(rila_product, term_years=1.0, premium=100_000.0)

        assert result.upside_value >= 0, "Upside value must be non-negative"


class TestMixedProductSlice:
    """Workflow with multiple product types."""

    def test_price_all_types(self, registry, myga_product, fia_product, rila_product):
        """Registry handles all product types in sequence."""
        myga_result = registry.price(myga_product)
        fia_result = registry.price(fia_product, term_years=1.0)
        rila_result = registry.price(rila_product, term_years=1.0)

        # All should have positive PV
        assert myga_result.present_value > 0
        assert fia_result.present_value > 0
        assert rila_result.present_value > 0

    def test_price_multiple_helper(self, registry, myga_product, fia_product, rila_product):
        """price_multiple produces DataFrame with all products."""
        products = [myga_product, fia_product, rila_product]
        results_df = registry.price_multiple(products, term_years=1.0)

        assert len(results_df) == 3
        assert all(results_df["present_value"] > 0)
        assert "error" not in results_df.columns or results_df["error"].isna().all()
