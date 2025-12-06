"""
Integration tests for Validation Gates (HALT/PASS framework).

Tests validation of pricing results across all product types.
"""

import pytest
from datetime import date

from annuity_pricing.products.base import PricingResult
from annuity_pricing.products.fia import FIAPricingResult
from annuity_pricing.products.rila import RILAPricingResult
from annuity_pricing.validation.gates import (
    GateStatus,
    GateResult,
    ValidationReport,
    ValidationGate,
    PresentValueBoundsGate,
    DurationBoundsGate,
    FIAOptionBudgetGate,
    FIAExpectedCreditGate,
    RILAMaxLossGate,
    RILAProtectionValueGate,
    ArbitrageBoundsGate,
    ProductParameterSanityGate,  # [F.4]
    ValidationEngine,
    validate_pricing_result,
    ensure_valid,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def valid_myga_result():
    """Valid MYGA pricing result."""
    return PricingResult(
        present_value=122.62,
        duration=4.5,
        as_of_date=date.today(),
    )


@pytest.fixture
def valid_fia_result():
    """Valid FIA pricing result."""
    return FIAPricingResult(
        present_value=103.50,
        duration=1.0,
        as_of_date=date.today(),
        embedded_option_value=2.50,
        option_budget=3.00,
        fair_cap=0.085,
        fair_participation=0.42,
        expected_credit=0.035,
    )


@pytest.fixture
def valid_rila_result():
    """Valid RILA pricing result."""
    return RILAPricingResult(
        present_value=102.00,
        duration=1.0,
        as_of_date=date.today(),
        protection_value=5.50,
        protection_type="buffer",
        upside_value=3.00,
        expected_return=0.02,
        max_loss=0.90,
    )


# =============================================================================
# Test GateResult and ValidationReport
# =============================================================================

class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_pass_result(self):
        """PASS result should be marked as passed."""
        result = GateResult(
            status=GateStatus.PASS,
            gate_name="test",
            message="All good",
        )
        assert result.passed is True

    def test_halt_result(self):
        """HALT result should not be passed."""
        result = GateResult(
            status=GateStatus.HALT,
            gate_name="test",
            message="Problem found",
            value=0.5,
            threshold=0.1,
        )
        assert result.passed is False
        assert result.value == 0.5

    def test_warn_result(self):
        """WARN result should be passed (not halted)."""
        result = GateResult(
            status=GateStatus.WARN,
            gate_name="test",
            message="Minor concern",
        )
        assert result.passed is True


class TestValidationReport:
    """Tests for ValidationReport."""

    def test_all_pass(self):
        """All PASS should give overall PASS."""
        results = (
            GateResult(status=GateStatus.PASS, gate_name="a", message="ok"),
            GateResult(status=GateStatus.PASS, gate_name="b", message="ok"),
        )
        report = ValidationReport(results=results)
        assert report.overall_status == GateStatus.PASS
        assert report.passed is True

    def test_one_halt(self):
        """One HALT should give overall HALT."""
        results = (
            GateResult(status=GateStatus.PASS, gate_name="a", message="ok"),
            GateResult(status=GateStatus.HALT, gate_name="b", message="fail"),
        )
        report = ValidationReport(results=results)
        assert report.overall_status == GateStatus.HALT
        assert report.passed is False

    def test_warn_without_halt(self):
        """WARN without HALT should give overall WARN."""
        results = (
            GateResult(status=GateStatus.PASS, gate_name="a", message="ok"),
            GateResult(status=GateStatus.WARN, gate_name="b", message="warning"),
        )
        report = ValidationReport(results=results)
        assert report.overall_status == GateStatus.WARN
        assert report.passed is True

    def test_halted_gates(self):
        """Should identify halted gates."""
        results = (
            GateResult(status=GateStatus.PASS, gate_name="a", message="ok"),
            GateResult(status=GateStatus.HALT, gate_name="b", message="fail1"),
            GateResult(status=GateStatus.HALT, gate_name="c", message="fail2"),
        )
        report = ValidationReport(results=results)
        assert len(report.halted_gates) == 2

    def test_to_dict(self):
        """Should convert to dictionary."""
        results = (
            GateResult(status=GateStatus.PASS, gate_name="test", message="ok"),
        )
        report = ValidationReport(results=results)
        d = report.to_dict()
        assert d["overall_status"] == "pass"
        assert d["passed"] is True


# =============================================================================
# Test Individual Gates
# =============================================================================

class TestPresentValueBoundsGate:
    """Tests for PresentValueBoundsGate."""

    def test_valid_pv(self, valid_myga_result):
        """Valid PV should pass."""
        gate = PresentValueBoundsGate()
        result = gate.check(valid_myga_result, premium=100.0)
        assert result.status == GateStatus.PASS

    def test_negative_pv(self):
        """Negative PV should halt."""
        # Note: PricingResult validates PV >= 0, so we test at boundary
        gate = PresentValueBoundsGate(min_pv=1.0)
        result_obj = PricingResult(present_value=0.5, duration=1.0)
        result = gate.check(result_obj, premium=100.0)
        assert result.status == GateStatus.HALT

    def test_excessive_pv(self):
        """PV exceeding 3x premium should halt. [F.4] Default tightened from 10x."""
        gate = PresentValueBoundsGate()  # Uses default max_pv_multiple=3.0
        result_obj = PricingResult(present_value=400.0, duration=1.0)  # 4x premium
        result = gate.check(result_obj, premium=100.0)
        assert result.status == GateStatus.HALT

    def test_excessive_pv_with_10x_override(self):
        """PV check with old 10x limit (for backwards compatibility tests)."""
        gate = PresentValueBoundsGate(max_pv_multiple=10.0)  # Explicit override
        result_obj = PricingResult(present_value=1500.0, duration=1.0)
        result = gate.check(result_obj, premium=100.0)
        assert result.status == GateStatus.HALT


class TestDurationBoundsGate:
    """Tests for DurationBoundsGate."""

    def test_valid_duration(self, valid_myga_result):
        """Valid duration should pass."""
        gate = DurationBoundsGate()
        result = gate.check(valid_myga_result)
        assert result.status == GateStatus.PASS

    def test_no_duration(self):
        """Missing duration should pass (skip)."""
        gate = DurationBoundsGate()
        result_obj = PricingResult(present_value=100.0, duration=None)
        result = gate.check(result_obj)
        assert result.status == GateStatus.PASS

    def test_excessive_duration(self):
        """Duration > 30 years should halt."""
        gate = DurationBoundsGate(max_duration=30.0)
        result_obj = PricingResult(present_value=100.0, duration=35.0)
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT


class TestFIAOptionBudgetGate:
    """Tests for FIAOptionBudgetGate."""

    def test_within_budget(self, valid_fia_result):
        """Option value within budget should pass."""
        gate = FIAOptionBudgetGate()
        result = gate.check(valid_fia_result)
        assert result.status == GateStatus.PASS

    def test_exceeds_budget(self):
        """Option value exceeding budget by >10% should HALT. [F.4] Changed from WARN."""
        gate = FIAOptionBudgetGate()  # Default tolerance=0.10 (10%)
        result_obj = FIAPricingResult(
            present_value=100.0,
            duration=1.0,
            embedded_option_value=3.5,
            option_budget=3.0,  # 17% over budget
            expected_credit=0.03,
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT

    def test_within_budget_tolerance(self):
        """Option value within 10% tolerance should PASS."""
        gate = FIAOptionBudgetGate()  # Default tolerance=0.10
        result_obj = FIAPricingResult(
            present_value=100.0,
            duration=1.0,
            embedded_option_value=3.25,
            option_budget=3.0,  # 8.3% over budget - within tolerance
            expected_credit=0.03,
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.PASS

    def test_non_fia_skipped(self, valid_myga_result):
        """Non-FIA result should be skipped."""
        gate = FIAOptionBudgetGate()
        result = gate.check(valid_myga_result)
        assert result.status == GateStatus.PASS


class TestFIAExpectedCreditGate:
    """Tests for FIAExpectedCreditGate."""

    def test_valid_credit(self, valid_fia_result):
        """Valid expected credit should pass."""
        gate = FIAExpectedCreditGate()
        result = gate.check(valid_fia_result)
        assert result.status == GateStatus.PASS

    def test_negative_credit(self):
        """Negative expected credit should halt (violates 0% floor)."""
        gate = FIAExpectedCreditGate()
        result_obj = FIAPricingResult(
            present_value=100.0,
            duration=1.0,
            expected_credit=-0.05,  # Negative!
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT

    def test_credit_exceeds_cap(self):
        """Credit exceeding cap should halt."""
        gate = FIAExpectedCreditGate()
        result_obj = FIAPricingResult(
            present_value=100.0,
            duration=1.0,
            expected_credit=0.15,
        )
        result = gate.check(result_obj, cap_rate=0.10)
        assert result.status == GateStatus.HALT


class TestRILAMaxLossGate:
    """Tests for RILAMaxLossGate."""

    def test_valid_max_loss(self, valid_rila_result):
        """Valid max loss should pass."""
        gate = RILAMaxLossGate()
        result = gate.check(valid_rila_result)
        assert result.status == GateStatus.PASS

    def test_negative_max_loss(self):
        """Negative max loss should halt."""
        gate = RILAMaxLossGate()
        result_obj = RILAPricingResult(
            present_value=100.0,
            duration=1.0,
            protection_value=5.0,
            protection_type="buffer",
            upside_value=3.0,
            expected_return=0.02,
            max_loss=-0.10,  # Negative!
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT

    def test_max_loss_exceeds_100(self):
        """Max loss > 100% should halt."""
        gate = RILAMaxLossGate()
        result_obj = RILAPricingResult(
            present_value=100.0,
            duration=1.0,
            protection_value=5.0,
            protection_type="buffer",
            upside_value=3.0,
            expected_return=0.02,
            max_loss=1.50,  # 150%!
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT


class TestRILAProtectionValueGate:
    """Tests for RILAProtectionValueGate."""

    def test_valid_protection(self, valid_rila_result):
        """Valid protection value should pass."""
        gate = RILAProtectionValueGate()
        result = gate.check(valid_rila_result, premium=100.0)
        assert result.status == GateStatus.PASS

    def test_negative_protection(self):
        """Negative protection should halt."""
        gate = RILAProtectionValueGate()
        result_obj = RILAPricingResult(
            present_value=100.0,
            duration=1.0,
            protection_value=-5.0,  # Negative!
            protection_type="buffer",
            upside_value=3.0,
            expected_return=0.02,
            max_loss=0.90,
        )
        result = gate.check(result_obj)
        assert result.status == GateStatus.HALT

    def test_excessive_protection(self):
        """Protection > 50% of premium should warn."""
        gate = RILAProtectionValueGate(max_protection_pct=0.50)
        result_obj = RILAPricingResult(
            present_value=100.0,
            duration=1.0,
            protection_value=60.0,  # 60% of premium
            protection_type="buffer",
            upside_value=3.0,
            expected_return=0.02,
            max_loss=0.90,
        )
        result = gate.check(result_obj, premium=100.0)
        assert result.status == GateStatus.WARN


class TestArbitrageBoundsGate:
    """Tests for ArbitrageBoundsGate."""

    def test_fia_no_arbitrage(self, valid_fia_result):
        """Valid FIA result should pass."""
        gate = ArbitrageBoundsGate()
        result = gate.check(valid_fia_result, premium=100.0)
        assert result.status == GateStatus.PASS

    def test_fia_option_exceeds_premium(self):
        """FIA option value exceeding premium should halt."""
        gate = ArbitrageBoundsGate()
        result_obj = FIAPricingResult(
            present_value=100.0,
            duration=1.0,
            embedded_option_value=150.0,  # > premium!
            option_budget=3.0,
            expected_credit=0.05,
        )
        result = gate.check(result_obj, premium=100.0)
        assert result.status == GateStatus.HALT

    def test_rila_no_arbitrage(self, valid_rila_result):
        """Valid RILA result should pass."""
        gate = ArbitrageBoundsGate()
        result = gate.check(valid_rila_result, premium=100.0)
        assert result.status == GateStatus.PASS


class TestProductParameterSanityGate:
    """Tests for ProductParameterSanityGate. [F.4]"""

    def test_valid_parameters(self, valid_fia_result):
        """Valid parameters should pass."""
        gate = ProductParameterSanityGate()
        result = gate.check(
            valid_fia_result,
            cap_rate=0.10,
            participation_rate=0.80,
            buffer_rate=0.10,
            spread_rate=0.02,
        )
        assert result.status == GateStatus.PASS

    def test_no_parameters(self, valid_myga_result):
        """No parameters should pass (nothing to check)."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_myga_result)
        assert result.status == GateStatus.PASS

    def test_cap_rate_exceeds_max(self, valid_fia_result):
        """Cap rate > 30% should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, cap_rate=0.35)
        assert result.status == GateStatus.HALT
        assert "cap_rate" in result.message

    def test_cap_rate_negative(self, valid_fia_result):
        """Negative cap rate should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, cap_rate=-0.05)
        assert result.status == GateStatus.HALT
        assert "negative" in result.message.lower()

    def test_participation_rate_exceeds_max(self, valid_fia_result):
        """Participation rate > 300% should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, participation_rate=3.50)
        assert result.status == GateStatus.HALT
        assert "participation_rate" in result.message

    def test_participation_rate_zero_or_negative(self, valid_fia_result):
        """Participation rate <= 0 should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, participation_rate=0.0)
        assert result.status == GateStatus.HALT
        assert "participation_rate" in result.message

    def test_buffer_rate_exceeds_max(self, valid_rila_result):
        """Buffer rate > 30% should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_rila_result, buffer_rate=0.35)
        assert result.status == GateStatus.HALT
        assert "buffer_rate" in result.message

    def test_buffer_rate_negative(self, valid_rila_result):
        """Negative buffer rate should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_rila_result, buffer_rate=-0.05)
        assert result.status == GateStatus.HALT
        assert "negative" in result.message.lower()

    def test_spread_rate_exceeds_max(self, valid_fia_result):
        """Spread rate > 10% should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, spread_rate=0.15)
        assert result.status == GateStatus.HALT
        assert "spread_rate" in result.message

    def test_spread_rate_negative(self, valid_fia_result):
        """Negative spread rate should halt."""
        gate = ProductParameterSanityGate()
        result = gate.check(valid_fia_result, spread_rate=-0.01)
        assert result.status == GateStatus.HALT
        assert "negative" in result.message.lower()

    def test_multiple_violations(self, valid_fia_result):
        """Multiple violations should all be reported."""
        gate = ProductParameterSanityGate()
        result = gate.check(
            valid_fia_result,
            cap_rate=0.50,  # Too high
            participation_rate=-0.10,  # Negative
        )
        assert result.status == GateStatus.HALT
        # Should have both issues in message
        assert "cap_rate" in result.message
        assert "participation_rate" in result.message


# =============================================================================
# Test Validation Engine
# =============================================================================

class TestValidationEngine:
    """Tests for ValidationEngine."""

    def test_default_gates(self):
        """Should create default gates. [F.4] Now includes ProductParameterSanityGate."""
        engine = ValidationEngine()
        assert len(engine.gates) == 8  # 7 original + ProductParameterSanityGate

    def test_custom_gates(self):
        """Should accept custom gates."""
        custom_gates = [PresentValueBoundsGate()]
        engine = ValidationEngine(gates=custom_gates)
        assert len(engine.gates) == 1

    def test_validate_valid_result(self, valid_myga_result):
        """Valid result should pass all gates."""
        engine = ValidationEngine()
        report = engine.validate(valid_myga_result, premium=100.0)
        assert report.passed is True

    def test_validate_fia_result(self, valid_fia_result):
        """Valid FIA result should pass all gates."""
        engine = ValidationEngine()
        report = engine.validate(valid_fia_result, premium=100.0)
        assert report.passed is True

    def test_validate_rila_result(self, valid_rila_result):
        """Valid RILA result should pass all gates."""
        engine = ValidationEngine()
        report = engine.validate(valid_rila_result, premium=100.0)
        assert report.passed is True

    def test_validate_and_raise_pass(self, valid_myga_result):
        """Should return result if valid."""
        engine = ValidationEngine()
        result = engine.validate_and_raise(valid_myga_result, premium=100.0)
        assert result.present_value == valid_myga_result.present_value

    def test_validate_and_raise_fail(self):
        """Should raise on invalid result. [F.4] Uses 3x limit."""
        engine = ValidationEngine()
        # PV exceeds 3x premium (F.4 tightened from 10x)
        invalid_result = PricingResult(present_value=400.0, duration=1.0)
        with pytest.raises(ValueError, match="Validation failed"):
            engine.validate_and_raise(invalid_result, premium=100.0)


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_pricing_result(self, valid_myga_result):
        """Should validate pricing result."""
        report = validate_pricing_result(valid_myga_result, premium=100.0)
        assert report.passed is True

    def test_ensure_valid_pass(self, valid_myga_result):
        """Should return result if valid."""
        result = ensure_valid(valid_myga_result, premium=100.0)
        assert result.present_value == valid_myga_result.present_value

    def test_ensure_valid_fail(self):
        """Should raise if invalid. [F.4] Uses 3x limit."""
        invalid_result = PricingResult(present_value=400.0, duration=1.0)  # 4x exceeds 3x
        with pytest.raises(ValueError):
            ensure_valid(invalid_result, premium=100.0)


# =============================================================================
# Integration Tests
# =============================================================================

class TestFullValidationPipeline:
    """Integration tests for full validation pipeline."""

    def test_validate_after_pricing(self):
        """Should validate result after pricing."""
        from annuity_pricing.data.schemas import MYGAProduct
        from annuity_pricing.products.registry import create_default_registry

        registry = create_default_registry()
        product = MYGAProduct(
            company_name="Test",
            product_name="5Y MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

        # MYGA uses default principal=100,000
        result = registry.price(product, principal=100.0)
        report = validate_pricing_result(result, premium=100.0)
        assert report.passed is True

    def test_validate_fia_after_pricing(self):
        """Should validate FIA result after pricing.

        [F.4] Uses 5% cap (down from 10%) to produce option value within
        tightened 10% budget tolerance.
        """
        from annuity_pricing.data.schemas import FIAProduct
        from annuity_pricing.products.registry import create_default_registry

        registry = create_default_registry(seed=42)
        product = FIAProduct(
            company_name="Test",
            product_name="5% Cap",
            product_group="FIA",
            status="current",
            cap_rate=0.05,  # [F.4] Reduced from 0.10 to fit within option budget
        )

        result = registry.price(product, term_years=1.0)
        report = validate_pricing_result(result, premium=100.0, cap_rate=0.05)
        assert report.passed is True

    def test_validate_rila_after_pricing(self):
        """Should validate RILA result after pricing."""
        from annuity_pricing.data.schemas import RILAProduct
        from annuity_pricing.products.registry import create_default_registry

        registry = create_default_registry(seed=42)
        product = RILAProduct(
            company_name="Test",
            product_name="10% Buffer",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
        )

        result = registry.price(product, term_years=1.0)
        report = validate_pricing_result(result, premium=100.0, buffer_rate=0.10)
        assert report.passed is True
