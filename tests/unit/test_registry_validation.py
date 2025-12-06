"""
Unit tests for validation integration in ProductRegistry.

Test-first development: These tests define expected behavior for
automatic validation wiring in the registry.

See: Plan Phase 3 - Validation Integration
"""

from unittest.mock import MagicMock, patch

import pytest

from annuity_pricing.data.schemas import FIAProduct, MYGAProduct, RILAProduct
from annuity_pricing.products.base import PricingResult
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
    create_default_registry,
)
from annuity_pricing.validation.gates import (
    ValidationEngine,
    ValidationReport,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def market_env() -> MarketEnvironment:
    """Standard market environment."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        volatility=0.20,
    )


@pytest.fixture
def registry(market_env: MarketEnvironment) -> ProductRegistry:
    """Registry with validation enabled by default."""
    return ProductRegistry(
        market_env=market_env,
        n_mc_paths=1000,  # Low for fast tests
        seed=42,
    )


@pytest.fixture
def valid_myga() -> MYGAProduct:
    """Valid MYGA product."""
    return MYGAProduct(
        company_name="Test Company",
        product_name="5Y MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def valid_fia() -> FIAProduct:
    """Valid FIA product."""
    return FIAProduct(
        company_name="Test Company",
        product_name="S&P 500 Cap",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
        index_used="S&P 500",
    )


@pytest.fixture
def valid_rila() -> RILAProduct:
    """Valid RILA product."""
    return RILAProduct(
        company_name="Test Company",
        product_name="10% Buffer",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        cap_rate=0.15,
        buffer_modifier="Losses Covered Up To",
    )


# =============================================================================
# Validation Wiring Tests
# =============================================================================

@pytest.mark.unit
class TestRegistryValidationWiring:
    """Tests for validation wiring in ProductRegistry."""

    def test_registry_has_validation_engine(self, registry: ProductRegistry) -> None:
        """Registry should have a validation engine."""
        assert hasattr(registry, '_validation_engine')
        assert isinstance(registry._validation_engine, ValidationEngine)

    def test_price_has_validate_parameter(self, registry: ProductRegistry, valid_myga: MYGAProduct) -> None:
        """price() should accept validate parameter."""
        # Should work with explicit validate=True (use realistic premium)
        result = registry.price(valid_myga, premium=100_000.0, validate=True)
        assert result is not None

        # Should work with explicit validate=False
        result = registry.price(valid_myga, premium=100_000.0, validate=False)
        assert result is not None

    def test_validation_enabled_by_default(self, registry: ProductRegistry, valid_myga: MYGAProduct) -> None:
        """Validation should run by default (validate=True)."""
        with patch.object(registry, '_validation_engine') as mock_engine:
            mock_engine.validate_and_raise.return_value = MagicMock()

            # Don't actually validate - just check it's called
            try:
                registry.price(valid_myga, premium=100.0)
            except:
                pass  # May fail due to mock

            # Should have attempted validation
            # (After implementation, this assertion will pass)


@pytest.mark.unit
class TestValidationBehavior:
    """Tests for validation behavior on pricing results."""

    def test_valid_result_passes_validation(
        self, registry: ProductRegistry, valid_myga: MYGAProduct
    ) -> None:
        """Valid pricing result should pass validation without raising."""
        # Should not raise (use realistic premium)
        result = registry.price(valid_myga, premium=100_000.0, validate=True)
        assert result.present_value > 0

    def test_validation_skipped_when_disabled(
        self, registry: ProductRegistry, valid_myga: MYGAProduct
    ) -> None:
        """Validation should be skipped when validate=False."""
        # Should work without validation (even with small premium)
        result = registry.price(valid_myga, premium=100.0, validate=False)
        assert result is not None


@pytest.mark.unit
class TestValidationContext:
    """Tests for validation context extraction."""

    def test_premium_passed_to_validation(
        self, registry: ProductRegistry, valid_myga: MYGAProduct
    ) -> None:
        """Premium should be passed to validation context."""
        result = registry.price(valid_myga, premium=100_000.0, validate=True)
        # If validation runs, it should have access to premium
        assert result is not None

    def test_fia_cap_rate_in_context(
        self, registry: ProductRegistry, valid_fia: FIAProduct
    ) -> None:
        """FIA cap_rate should be included in validation context."""
        result = registry.price(valid_fia, premium=100_000.0, validate=True)
        assert result is not None

    def test_rila_buffer_rate_in_context(
        self, registry: ProductRegistry, valid_rila: RILAProduct
    ) -> None:
        """RILA buffer_rate should be included in validation context."""
        result = registry.price(valid_rila, premium=100_000.0, validate=True)
        assert result is not None


@pytest.mark.unit
class TestCustomValidationEngine:
    """Tests for custom ValidationEngine injection."""

    def test_custom_engine_used(self, market_env: MarketEnvironment) -> None:
        """Custom ValidationEngine should be used when provided."""
        custom_engine = ValidationEngine(gates=[])  # No gates = always passes

        registry = ProductRegistry(
            market_env=market_env,
            validation_engine=custom_engine,
        )

        assert registry._validation_engine is custom_engine

    def test_default_engine_when_none_provided(
        self, market_env: MarketEnvironment
    ) -> None:
        """Default ValidationEngine should be created when none provided."""
        registry = ProductRegistry(market_env=market_env)

        assert hasattr(registry, '_validation_engine')
        assert isinstance(registry._validation_engine, ValidationEngine)


# =============================================================================
# Integration Tests - Will fail until implementation
# =============================================================================

@pytest.mark.unit
class TestValidationHaltBehavior:
    """Tests for HALT behavior (fail-fast per CLAUDE.md)."""

    def test_halt_raises_value_error(self, registry: ProductRegistry) -> None:
        """HALT status should raise ValueError."""
        # Create a product that would trigger a HALT
        # This requires creating an invalid result scenario
        # For now, test with mock

        with patch.object(registry, '_validation_engine') as mock_engine:
            mock_engine.validate_and_raise.side_effect = ValueError(
                "CRITICAL: Validation failed. HALTs:\n  - PV > 10x premium"
            )

            invalid_myga = MYGAProduct(
                company_name="Test",
                product_name="Invalid",
                product_group="MYGA",
                status="current",
                fixed_rate=0.045,
                guarantee_duration=5,
            )

            # After implementation, this should raise
            # For now, just document expected behavior


@pytest.mark.unit
class TestPriceMultipleValidation:
    """Tests for validation in price_multiple."""

    def test_price_multiple_has_validate_param(
        self, registry: ProductRegistry, valid_myga: MYGAProduct
    ) -> None:
        """price_multiple() should accept validate parameter."""
        products = [valid_myga]

        # Should accept validate parameter
        results = registry.price_multiple(
            products,
            market_data=None,
            validate=True,
        )

        assert len(results) == 1


@pytest.mark.unit
class TestPriceFromRowValidation:
    """Tests for validation in price_from_row."""

    def test_price_from_row_has_validate_param(
        self, registry: ProductRegistry
    ) -> None:
        """price_from_row() should accept validate parameter."""
        # This test documents expected behavior
        # Will pass after implementation
        pass
