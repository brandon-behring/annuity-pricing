"""
Smoke tests for quick CI validation.

These tests verify basic functionality without full coverage.
Run these first to catch obvious breakages before full test suite.

Usage:
    pytest tests/smoke/ -v
"""

import pytest

# =============================================================================
# Import Smoke Tests
# =============================================================================


class TestImportSmoke:
    """Verify core modules import successfully."""

    def test_import_core_packages(self):
        """Core packages should import without error."""
        import annuity_pricing
        import annuity_pricing.data
        import annuity_pricing.options
        import annuity_pricing.products

        assert annuity_pricing is not None

    def test_import_pricing_modules(self):
        """Pricing modules should import successfully."""
        from annuity_pricing.products.myga import MYGAPricer
        from annuity_pricing.products.registry import ProductRegistry

        assert ProductRegistry is not None
        assert MYGAPricer is not None

    def test_import_regulatory_modules(self):
        """Regulatory modules should import (may have warnings)."""
        from annuity_pricing.regulatory import VM21Calculator, VM22Calculator

        assert VM21Calculator is not None
        assert VM22Calculator is not None

    def test_import_stress_testing(self):
        """Stress testing modules should import."""
        from annuity_pricing.stress_testing import (
            CRISIS_2008_GFC,
            StressScenario,
        )

        assert StressScenario is not None
        assert CRISIS_2008_GFC is not None


# =============================================================================
# Quick Pricing Smoke Tests
# =============================================================================


class TestPricingSmoke:
    """Quick pricing functionality tests."""

    def test_myga_prices(self):
        """MYGA should price successfully."""
        from annuity_pricing.data.schemas import MYGAProduct
        from annuity_pricing.products.registry import (
            MarketEnvironment,
            ProductRegistry,
        )

        myga = MYGAProduct(
            company_name="Smoke Test",
            product_name="5Y MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.04,
            guarantee_duration=5,
        )

        registry = ProductRegistry(
            market_env=MarketEnvironment(),
            seed=42,
        )

        result = registry.price(myga)
        assert result.present_value > 0

    def test_fia_prices(self):
        """FIA should price successfully."""
        from annuity_pricing.data.schemas import FIAProduct
        from annuity_pricing.products.registry import (
            MarketEnvironment,
            ProductRegistry,
        )

        fia = FIAProduct(
            company_name="Smoke Test",
            product_name="FIA Cap",
            product_group="FIA",
            status="current",
            cap_rate=0.05,
            index_used="S&P 500",
        )

        registry = ProductRegistry(
            market_env=MarketEnvironment(),
            n_mc_paths=1000,  # Minimal for speed
            seed=42,
        )

        result = registry.price(fia, term_years=1.0)
        assert result.present_value > 0

    def test_rila_prices(self):
        """RILA should price successfully."""
        from annuity_pricing.data.schemas import RILAProduct
        from annuity_pricing.products.registry import (
            MarketEnvironment,
            ProductRegistry,
        )

        rila = RILAProduct(
            company_name="Smoke Test",
            product_name="10% Buffer",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            index_used="S&P 500",
        )

        registry = ProductRegistry(
            market_env=MarketEnvironment(),
            n_mc_paths=1000,
            seed=42,
        )

        result = registry.price(rila, term_years=1.0)
        assert result.present_value > 0


# =============================================================================
# Black-Scholes Smoke Tests
# =============================================================================


class TestBlackScholesSmoke:
    """Quick Black-Scholes functionality tests."""

    def test_bs_call_price(self):
        """Black-Scholes call should compute."""
        from annuity_pricing.options.pricing.black_scholes import black_scholes_call

        price = black_scholes_call(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        assert price > 0
        assert price < 100  # Call can't exceed spot

    def test_bs_greeks(self):
        """Black-Scholes Greeks should compute."""
        from annuity_pricing.options.payoffs.base import OptionType
        from annuity_pricing.options.pricing.black_scholes import black_scholes_greeks

        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.CALL,
        )

        assert 0 <= greeks.delta <= 1
        assert greeks.gamma >= 0
        assert greeks.vega >= 0


# =============================================================================
# Payoff Smoke Tests
# =============================================================================


class TestPayoffSmoke:
    """Quick payoff functionality tests."""

    def test_buffer_payoff(self):
        """Buffer payoff should compute."""
        from annuity_pricing.options.payoffs.rila import BufferPayoff

        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(-0.15)

        assert result.credited_return == pytest.approx(-0.05)

    def test_floor_payoff(self):
        """Floor payoff should compute."""
        from annuity_pricing.options.payoffs.rila import FloorPayoff

        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(-0.15)

        assert result.credited_return == pytest.approx(-0.10)

    def test_capped_call_payoff(self):
        """Capped call payoff should compute."""
        from annuity_pricing.options.payoffs.fia import CappedCallPayoff

        payoff = CappedCallPayoff(cap_rate=0.10, floor_rate=0.0)
        result = payoff.calculate(0.15)

        assert result.credited_return == pytest.approx(0.10)


# =============================================================================
# Configuration Smoke Tests
# =============================================================================


class TestConfigSmoke:
    """Quick configuration tests."""

    def test_tolerances_import(self):
        """Tolerance constants should be importable."""
        from annuity_pricing.config.tolerances import (
            ANTI_PATTERN_TOLERANCE,
            PUT_CALL_PARITY_TOLERANCE,
        )

        assert ANTI_PATTERN_TOLERANCE < 1e-6
        assert PUT_CALL_PARITY_TOLERANCE < 1e-4

    def test_settings_import(self):
        """Settings should be importable."""
        from annuity_pricing.config.settings import Settings

        settings = Settings()
        assert settings is not None


# =============================================================================
# Quick Full Stack Smoke Test
# =============================================================================


class TestFullStackSmoke:
    """Complete stack test - single product through entire pipeline."""

    def test_full_stack_myga(self):
        """MYGA: Create → Configure → Price → Validate."""
        from annuity_pricing.data.schemas import MYGAProduct
        from annuity_pricing.products.registry import (
            MarketEnvironment,
            ProductRegistry,
        )

        # 1. Create product
        myga = MYGAProduct(
            company_name="Full Stack Test",
            product_name="MYGA Full Stack",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

        # 2. Configure market
        market = MarketEnvironment(risk_free_rate=0.05)

        # 3. Create registry
        registry = ProductRegistry(market_env=market, seed=42)

        # 4. Price
        result = registry.price(myga)

        # 5. Validate (no exception means validation passed)
        assert result.present_value > 0
        assert result.duration >= 0
