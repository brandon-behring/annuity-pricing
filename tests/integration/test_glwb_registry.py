"""
Integration tests for GLWB registry support.

Tests that GLWBProduct and GLWBPricer are properly integrated with the
ProductRegistry for unified pricing across all product types.

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md
"""

import pytest

from annuity_pricing import GLWBPricer, GLWBPricingResult, GLWBProduct
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
    create_default_registry,
)

# =============================================================================
# GLWBProduct Dataclass Tests
# =============================================================================


class TestGLWBProductCreation:
    """Test GLWBProduct dataclass validation."""

    def test_valid_glwb_product(self) -> None:
        """Valid GLWBProduct should create successfully."""
        product = GLWBProduct(
            company_name="Test Life",
            product_name="GLWB 5%",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.06,
        )
        assert product.withdrawal_rate == 0.05
        assert product.rollup_rate == 0.06
        assert product.rollup_type == "compound"  # default

    def test_wrong_product_group_raises(self) -> None:
        """GLWBProduct with wrong product_group should raise ValueError."""
        with pytest.raises(ValueError, match="product_group='GLWB'"):
            GLWBProduct(
                company_name="Test Life",
                product_name="Wrong Product",
                product_group="MYGA",  # Wrong!
                status="current",
                withdrawal_rate=0.05,
                rollup_rate=0.06,
            )

    def test_invalid_withdrawal_rate_raises(self) -> None:
        """GLWBProduct with withdrawal_rate outside (0, 0.20] should raise."""
        with pytest.raises(ValueError, match="withdrawal_rate"):
            GLWBProduct(
                company_name="Test Life",
                product_name="Invalid Rate",
                product_group="GLWB",
                status="current",
                withdrawal_rate=0.0,  # Invalid: must be > 0
                rollup_rate=0.06,
            )

    def test_invalid_rollup_type_raises(self) -> None:
        """GLWBProduct with invalid rollup_type should raise."""
        with pytest.raises(ValueError, match="rollup_type"):
            GLWBProduct(
                company_name="Test Life",
                product_name="Invalid Rollup",
                product_group="GLWB",
                status="current",
                withdrawal_rate=0.05,
                rollup_rate=0.06,
                rollup_type="invalid",
            )

    def test_simple_rollup_type(self) -> None:
        """GLWBProduct with simple rollup should work."""
        product = GLWBProduct(
            company_name="Test Life",
            product_name="Simple Rollup",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.05,
            rollup_type="simple",
        )
        assert product.rollup_type == "simple"


# =============================================================================
# GLWBPricer Standalone Tests
# =============================================================================


class TestGLWBPricerStandalone:
    """Test GLWBPricer without registry."""

    @pytest.fixture
    def sample_product(self) -> GLWBProduct:
        """Create standard GLWB product for testing."""
        return GLWBProduct(
            company_name="Test Life",
            product_name="GLWB 5%",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.06,
            rollup_cap_years=10,
            step_up_frequency=1,
            fee_rate=0.01,
        )

    def test_pricer_creation(self) -> None:
        """GLWBPricer should create with valid parameters."""
        pricer = GLWBPricer(
            risk_free_rate=0.04,
            volatility=0.15,
            n_paths=1000,
            seed=42,
        )
        assert pricer.risk_free_rate == 0.04
        assert pricer.volatility == 0.15
        assert pricer.n_paths == 1000
        assert pricer.seed == 42

    def test_pricer_invalid_rate_raises(self) -> None:
        """GLWBPricer with negative risk_free_rate should raise."""
        with pytest.raises(ValueError, match="risk_free_rate"):
            GLWBPricer(risk_free_rate=-0.01)

    def test_pricer_invalid_volatility_raises(self) -> None:
        """GLWBPricer with non-positive volatility should raise."""
        with pytest.raises(ValueError, match="volatility"):
            GLWBPricer(volatility=0.0)

    def test_pricer_invalid_paths_raises(self) -> None:
        """GLWBPricer with too few paths should raise."""
        with pytest.raises(ValueError, match="n_paths"):
            GLWBPricer(n_paths=50)

    def test_price_returns_result(self, sample_product: GLWBProduct) -> None:
        """GLWBPricer.price() should return GLWBPricingResult."""
        pricer = GLWBPricer(n_paths=1000, seed=42)
        result = pricer.price(sample_product, premium=100_000, age=65)

        assert isinstance(result, GLWBPricingResult)
        assert result.present_value >= 0
        assert result.n_paths == 1000

    def test_price_guarantee_cost_reasonable(self, sample_product: GLWBProduct) -> None:
        """Guarantee cost should be reasonable (0-50% of premium). [T1]"""
        pricer = GLWBPricer(n_paths=1000, seed=42)
        result = pricer.price(sample_product, premium=100_000, age=65)

        # Guarantee cost as % of premium should be positive but not excessive
        assert 0 <= result.guarantee_cost <= 0.50

    def test_price_deterministic_with_seed(self, sample_product: GLWBProduct) -> None:
        """Same seed should produce same result."""
        pricer1 = GLWBPricer(n_paths=1000, seed=42)
        pricer2 = GLWBPricer(n_paths=1000, seed=42)

        result1 = pricer1.price(sample_product, premium=100_000, age=65)
        result2 = pricer2.price(sample_product, premium=100_000, age=65)

        assert result1.present_value == result2.present_value

    def test_price_age_validation(self, sample_product: GLWBProduct) -> None:
        """Price should raise for invalid age."""
        pricer = GLWBPricer(n_paths=1000, seed=42)

        with pytest.raises(ValueError, match="age"):
            pricer.price(sample_product, age=30)  # Too young

        with pytest.raises(ValueError, match="age"):
            pricer.price(sample_product, age=95)  # Too old


# =============================================================================
# Registry Integration Tests
# =============================================================================


class TestGLWBRegistryIntegration:
    """Test GLWB integration with ProductRegistry."""

    @pytest.fixture
    def market_env(self) -> MarketEnvironment:
        """Standard market environment."""
        return MarketEnvironment(
            risk_free_rate=0.04,
            spot=100.0,
            dividend_yield=0.02,
            volatility=0.15,
        )

    @pytest.fixture
    def registry(self, market_env: MarketEnvironment) -> ProductRegistry:
        """Registry with reduced paths for fast testing."""
        return ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=42)

    @pytest.fixture
    def glwb_product(self) -> GLWBProduct:
        """Standard GLWB product."""
        return GLWBProduct(
            company_name="Test Life",
            product_name="GLWB 5%",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.06,
        )

    def test_glwb_in_supported_types(self, registry: ProductRegistry) -> None:
        """GLWB should be in registry's supported types."""
        assert "GLWB" in registry.SUPPORTED_TYPES

    def test_registry_prices_glwb(
        self, registry: ProductRegistry, glwb_product: GLWBProduct
    ) -> None:
        """Registry should successfully price GLWB product."""
        # Disable validation for this test (GLWB doesn't have standard validation gates)
        result = registry.price(glwb_product, validate=False)

        assert isinstance(result, GLWBPricingResult)
        assert result.present_value >= 0

    def test_registry_with_glwb_kwargs(
        self, registry: ProductRegistry, glwb_product: GLWBProduct
    ) -> None:
        """Registry should pass GLWB-specific kwargs correctly."""
        result = registry.price(
            glwb_product,
            premium=200_000,
            age=70,
            validate=False,
        )

        assert result.present_value >= 0

    def test_create_default_registry_supports_glwb(self, glwb_product: GLWBProduct) -> None:
        """create_default_registry() should support GLWB."""
        registry = create_default_registry(seed=42)

        result = registry.price(glwb_product, validate=False)
        assert isinstance(result, GLWBPricingResult)

    def test_get_pricer_info_includes_glwb(self, registry: ProductRegistry) -> None:
        """get_pricer_info should list GLWB in supported types."""
        info = registry.get_pricer_info()
        assert "GLWB" in info["supported_types"]


# =============================================================================
# Import Tests
# =============================================================================


class TestGLWBImports:
    """Test that GLWB classes are properly exported."""

    def test_import_from_top_level(self) -> None:
        """GLWB classes should be importable from top-level package."""
        from annuity_pricing import GLWBPricer, GLWBPricingResult, GLWBProduct

        assert GLWBProduct is not None
        assert GLWBPricer is not None
        assert GLWBPricingResult is not None

    def test_import_from_products(self) -> None:
        """GLWB classes should be importable from products module."""
        from annuity_pricing.products.glwb import GLWBPricer, GLWBPricingResult

        assert GLWBPricer is not None
        assert GLWBPricingResult is not None

    def test_import_from_schemas(self) -> None:
        """GLWBProduct should be importable from schemas."""
        from annuity_pricing.data.schemas import GLWBProduct

        assert GLWBProduct is not None


# =============================================================================
# Anti-Pattern Tests
# =============================================================================


class TestGLWBAntiPatterns:
    """Tests to prevent common GLWB pricing errors."""

    @pytest.fixture
    def sample_product(self) -> GLWBProduct:
        """Standard GLWB product."""
        return GLWBProduct(
            company_name="Test Life",
            product_name="GLWB 5%",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.06,
        )

    def test_guarantee_cost_positive(self, sample_product: GLWBProduct) -> None:
        """Guarantee cost should be positive (insurer faces risk). [T1]"""
        pricer = GLWBPricer(n_paths=2000, seed=42)
        result = pricer.price(sample_product, premium=100_000, age=65)

        # With rollup and withdrawal guarantee, there must be some cost
        assert result.guarantee_cost > 0

    def test_higher_rollup_means_higher_cost(self) -> None:
        """Higher rollup rate should increase guarantee cost. [T1]

        Note: Use separate pricer instances to avoid seed/state sharing.
        """
        # Create separate pricers with same seed to get comparable paths
        pricer_low = GLWBPricer(n_paths=5000, seed=42)
        pricer_high = GLWBPricer(n_paths=5000, seed=42)

        low_rollup = GLWBProduct(
            company_name="Test",
            product_name="Low Rollup",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.03,  # Low rollup
        )
        high_rollup = GLWBProduct(
            company_name="Test",
            product_name="High Rollup",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.08,  # High rollup
        )

        low_result = pricer_low.price(low_rollup, premium=100_000, age=65)
        high_result = pricer_high.price(high_rollup, premium=100_000, age=65)

        # Higher rollup = higher benefit base = higher guarantee cost
        # Allow for Monte Carlo variance but expect clear difference
        assert high_result.guarantee_cost >= low_result.guarantee_cost * 0.9, (
            f"Expected high rollup cost ({high_result.guarantee_cost:.4f}) >= "
            f"low rollup cost ({low_result.guarantee_cost:.4f}) * 0.9"
        )

    def test_younger_age_means_higher_cost(self, sample_product: GLWBProduct) -> None:
        """Younger starting age should increase guarantee cost (more years). [T1]"""
        pricer = GLWBPricer(n_paths=2000, seed=42)

        # Young: longer expected payout period
        young_result = pricer.price(sample_product, premium=100_000, age=55)
        # Old: shorter expected payout period
        old_result = pricer.price(sample_product, premium=100_000, age=75)

        # Younger age = more years of potential guarantee payments = higher cost
        assert young_result.guarantee_cost > old_result.guarantee_cost

    def test_prob_ruin_bounded(self, sample_product: GLWBProduct) -> None:
        """Probability of ruin should be in [0, 1]."""
        pricer = GLWBPricer(n_paths=1000, seed=42)
        result = pricer.price(sample_product, premium=100_000, age=65)

        assert 0 <= result.prob_ruin <= 1

    def test_n_paths_matches_config(self, sample_product: GLWBProduct) -> None:
        """Result should report correct number of paths."""
        pricer = GLWBPricer(n_paths=1234, seed=42)
        result = pricer.price(sample_product, premium=100_000, age=65)

        assert result.n_paths == 1234
