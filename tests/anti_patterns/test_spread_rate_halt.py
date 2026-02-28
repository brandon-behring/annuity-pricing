"""
Spread rate HALT tests.

[F.4] Validates that extreme or negative spread rates trigger HALT.

Spread rates beyond reasonable bounds indicate data errors or product
misconfiguration. The validation gate should HALT pricing for:
- Negative spread rates (nonsensical)
- Spread rates > 10% (MAX_SPREAD_RATE from ProductParameterSanityGate)

See: codex-audit-report.md Finding 2
See: src/annuity_pricing/validation/gates.py ProductParameterSanityGate
"""

import pytest

from annuity_pricing.data.schemas import FIAProduct
from annuity_pricing.products.registry import ProductRegistry
from annuity_pricing.validation.gates import (
    GateStatus,
    ProductParameterSanityGate,
)


class TestSpreadRateHALT:
    """
    Tests that extreme spread rates trigger HALT.

    [F.4] Spread crediting products with unreasonable spread values
    should be rejected to prevent pricing garbage.
    """

    @pytest.fixture
    def sanity_gate(self):
        """Create a ProductParameterSanityGate instance."""
        return ProductParameterSanityGate()

    @pytest.fixture
    def mock_result(self):
        """Create a minimal pricing result for gate testing."""
        from datetime import date

        from annuity_pricing.products.base import PricingResult

        return PricingResult(
            present_value=100000.0,
            duration=5.0,
            as_of_date=date.today(),
        )

    @pytest.mark.anti_pattern
    def test_negative_spread_rate_halts(self, sanity_gate, mock_result):
        """
        [F.4] Negative spread rate should HALT.

        Spread rates cannot be negative - this indicates data corruption
        or entry error.
        """
        context = {"spread_rate": -0.01}  # -1% spread
        result = sanity_gate.check(mock_result, **context)

        assert result.status == GateStatus.HALT, (
            f"Negative spread_rate -0.01 should HALT, got {result.status}"
        )
        assert "negative" in result.message.lower()

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize(
        "extreme_spread",
        [
            0.11,  # 11% - just over limit
            0.15,  # 15% - clearly excessive
            0.25,  # 25% - absurdly high
            0.50,  # 50% - data error
            1.00,  # 100% - likely decimal error (100% instead of 0.10)
        ],
    )
    def test_excessive_spread_rate_halts(self, sanity_gate, mock_result, extreme_spread):
        """
        [F.4] Spread rates > 10% should HALT.

        ProductParameterSanityGate.MAX_SPREAD_RATE = 0.10 (10%)
        Anything above this is likely a data error.
        """
        context = {"spread_rate": extreme_spread}
        result = sanity_gate.check(mock_result, **context)

        assert result.status == GateStatus.HALT, (
            f"Spread rate {extreme_spread:.0%} should HALT (max 10%), got {result.status}"
        )
        assert "exceeds" in result.message.lower() or "maximum" in result.message.lower()

    @pytest.mark.anti_pattern
    @pytest.mark.parametrize(
        "valid_spread",
        [
            0.00,  # 0% - no spread
            0.005,  # 0.5% - small spread
            0.01,  # 1% - common spread
            0.02,  # 2% - moderate spread
            0.05,  # 5% - high but valid
            0.10,  # 10% - at max limit
        ],
    )
    def test_valid_spread_rates_pass(self, sanity_gate, mock_result, valid_spread):
        """
        [F.4] Valid spread rates (0-10%) should PASS.
        """
        context = {"spread_rate": valid_spread}
        result = sanity_gate.check(mock_result, **context)

        assert result.status == GateStatus.PASS, (
            f"Valid spread rate {valid_spread:.0%} should PASS, "
            f"got {result.status}: {result.message}"
        )


class TestSpreadRateInValidationContext:
    """
    Tests that spread_rate is properly passed to validation context.

    This validates the fix in ProductRegistry._build_validation_context.
    """

    @pytest.mark.anti_pattern
    def test_spread_rate_passed_to_context(self):
        """
        [FIX] spread_rate should be extracted from FIAProduct to context.

        Previously (codex-audit Finding 2), spread_rate was omitted from
        the validation context, allowing invalid spreads to bypass gates.
        """
        from annuity_pricing.products.registry import MarketEnvironment

        # Create FIA with spread crediting
        product = FIAProduct(
            company_name="Test Company",
            product_name="Spread FIA",
            product_group="FIA",
            status="current",
            spread_rate=0.02,  # 2% spread
            index_used="S&P 500",
            indexing_method="Annual Point to Point",
        )

        market_env = MarketEnvironment(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )

        registry = ProductRegistry(market_env)

        # Build context and verify spread_rate is included
        context = registry._build_validation_context(product, premium=100_000)

        assert "spread_rate" in context, "spread_rate should be in validation context after fix"
        assert context["spread_rate"] == 0.02


class TestSpreadRateIntegration:
    """
    End-to-end tests for spread rate validation.
    """

    @pytest.mark.anti_pattern
    def test_excessive_spread_halts_via_gate(self):
        """
        [F.4] FIA with excessive spread should HALT when checked by sanity gate.

        This test directly validates the gate with excessive spread_rate.
        """
        from datetime import date

        from annuity_pricing.products.base import PricingResult

        # Create FIA with excessive spread
        product = FIAProduct(
            company_name="Test Company",
            product_name="Bad Spread FIA",
            product_group="FIA",
            status="current",
            spread_rate=0.50,  # 50% - clearly bad data
            index_used="S&P 500",
            indexing_method="Annual Point to Point",
        )

        # Create a mock pricing result
        mock_result = PricingResult(
            present_value=100000.0,
            duration=5.0,
            as_of_date=date.today(),
        )

        # Check gate directly with excessive spread
        gate = ProductParameterSanityGate()
        context = {"spread_rate": product.spread_rate}
        result = gate.check(mock_result, **context)

        assert result.status == GateStatus.HALT, (
            f"Excessive spread_rate 0.50 should cause HALT, got {result.status}"
        )
