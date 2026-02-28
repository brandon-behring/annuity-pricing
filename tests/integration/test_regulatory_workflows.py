"""
Regulatory workflow integration tests.

Tests VM-21, VM-22, and scenario generation imports and basic structure.

IMPORTANT: These tests are for EDUCATIONAL purposes only.
This module is NOT suitable for production regulatory filings.

References:
    [T1] NAIC VM-21/VM-22 regulatory framework

Golden baseline tests validate that regulatory calculations produce
consistent, known-correct values. See:
    tests/golden/outputs/vm21_baseline.json
    tests/golden/outputs/vm22_baseline.json
"""

import json
from pathlib import Path

import numpy as np
import pytest

# =============================================================================
# Import Tests
# =============================================================================


class TestRegulatoryImports:
    """Test that regulatory modules are importable."""

    def test_import_scenarios(self):
        """Scenario generation should be importable."""
        from annuity_pricing.regulatory import (
            AG43Scenarios,
            EconomicScenario,
            ScenarioGenerator,
        )

        assert ScenarioGenerator is not None
        assert EconomicScenario is not None
        assert AG43Scenarios is not None

    def test_import_vm21(self):
        """VM-21 calculator should be importable."""
        from annuity_pricing.regulatory import (
            PolicyData,
            VM21Calculator,
            VM21Result,
        )

        assert VM21Calculator is not None
        assert VM21Result is not None
        assert PolicyData is not None

    def test_import_vm22(self):
        """VM-22 calculator should be importable."""
        from annuity_pricing.regulatory import (
            ReserveType,
            VM22Calculator,
            VM22Result,
        )

        assert VM22Calculator is not None
        assert VM22Result is not None
        assert ReserveType is not None


# =============================================================================
# CTE Level Tests
# =============================================================================


class TestCTELevels:
    """Test CTE level calculations."""

    def test_cte_levels_function(self):
        """calculate_cte_levels should compute percentiles."""
        import numpy as np

        from annuity_pricing.regulatory import calculate_cte_levels

        losses = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        cte_levels = calculate_cte_levels(losses)

        # Should have CTE levels (uppercase keys)
        assert "CTE70" in cte_levels or "cte_70" in cte_levels
        assert "CTE90" in cte_levels or "cte_90" in cte_levels


# =============================================================================
# Reserve Type Tests
# =============================================================================


class TestReserveTypes:
    """Test reserve type enumeration."""

    def test_reserve_types_defined(self):
        """ReserveType should have expected values."""
        from annuity_pricing.regulatory import ReserveType

        # Should have common reserve types
        assert hasattr(ReserveType, "STOCHASTIC") or hasattr(ReserveType, "stochastic")


# =============================================================================
# Disclaimer Tests
# =============================================================================


class TestRegulatoryDisclaimers:
    """Ensure regulatory disclaimers are present."""

    def test_init_disclaimer(self):
        """Regulatory __init__ should include disclaimer."""
        import annuity_pricing.regulatory as reg

        assert "NOT FOR PRODUCTION" in reg.__doc__ or "EDUCATIONAL" in reg.__doc__


# =============================================================================
# Golden Baseline Tests
# =============================================================================

GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "outputs"


def load_golden(filename: str) -> dict:
    """Load a golden file."""
    filepath = GOLDEN_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Golden file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)


@pytest.mark.integration
class TestVM21GoldenBaseline:
    """
    [T1] VM-21 golden baseline tests.

    Validates that VM-21 reserve calculations match known-correct values.
    These tests ensure regulatory calculations remain consistent across
    code changes.

    DISCLAIMER: Educational implementation only.
    """

    @pytest.fixture(scope="class")
    def vm21_data(self) -> dict:
        """Load VM-21 golden file."""
        return load_golden("vm21_baseline.json")

    def test_va_glwb_cte70(self, vm21_data: dict) -> None:
        """[P1] CTE70 calculation should match baseline."""
        from annuity_pricing.regulatory.vm21 import PolicyData, VM21Calculator

        product_data = vm21_data["va_sample_glwb"]
        params = product_data["parameters"]
        settings = product_data["calculation_settings"]

        policy = PolicyData(
            av=params["av"],
            gwb=params["gwb"],
            age=params["age"],
            csv=params["csv"],
            withdrawal_rate=params["withdrawal_rate"],
            fee_rate=params["fee_rate"],
        )

        calc = VM21Calculator(
            n_scenarios=settings["n_scenarios"],
            projection_years=settings["projection_years"],
            seed=settings["seed"],
        )

        result = calc.calculate_reserve(policy)

        expected_cte70 = product_data["expected"]["cte70"]
        tolerance = product_data["tolerances"]["cte_relative"]
        rel_error = abs(result.cte70 - expected_cte70) / expected_cte70

        assert rel_error < tolerance, (
            f"VM-21 CTE70 mismatch: got {result.cte70:.2f}, "
            f"expected {expected_cte70:.2f}, error={rel_error:.2%}"
        )

    def test_va_glwb_reserve(self, vm21_data: dict) -> None:
        """[P1] Reserve calculation should match baseline."""
        from annuity_pricing.regulatory.vm21 import PolicyData, VM21Calculator

        product_data = vm21_data["va_sample_glwb"]
        params = product_data["parameters"]
        settings = product_data["calculation_settings"]

        policy = PolicyData(
            av=params["av"],
            gwb=params["gwb"],
            age=params["age"],
            csv=params["csv"],
            withdrawal_rate=params["withdrawal_rate"],
            fee_rate=params["fee_rate"],
        )

        calc = VM21Calculator(
            n_scenarios=settings["n_scenarios"],
            projection_years=settings["projection_years"],
            seed=settings["seed"],
        )

        result = calc.calculate_reserve(policy)

        expected_reserve = product_data["expected"]["reserve"]
        tolerance = product_data["tolerances"]["reserve_relative"]
        rel_error = abs(result.reserve - expected_reserve) / expected_reserve

        assert rel_error < tolerance, (
            f"VM-21 reserve mismatch: got {result.reserve:.2f}, "
            f"expected {expected_reserve:.2f}, error={rel_error:.2%}"
        )

    def test_cte_calculation_known_input(self, vm21_data: dict) -> None:
        """[P1] CTE calculation with known input should be exact."""
        from annuity_pricing.regulatory.vm21 import VM21Calculator

        cte_data = vm21_data["cte_calculation"]
        scenario_results = np.array(cte_data["parameters"]["scenario_results"])
        alpha = cte_data["parameters"]["alpha"]
        expected = cte_data["expected"]["cte70"]

        calc = VM21Calculator(n_scenarios=100, seed=42)
        result = calc.calculate_cte(scenario_results, alpha=alpha)

        assert abs(result - expected) < 1e-6, (
            f"CTE calculation mismatch: got {result}, expected {expected}"
        )


@pytest.mark.integration
class TestVM22GoldenBaseline:
    """
    [T1] VM-22 golden baseline tests.

    Validates that VM-22 reserve calculations match known-correct values.
    These tests ensure regulatory calculations remain consistent across
    code changes.

    DISCLAIMER: Educational implementation only.
    VM-22 mandatory compliance begins January 1, 2029.
    """

    @pytest.fixture(scope="class")
    def vm22_data(self) -> dict:
        """Load VM-22 golden file."""
        return load_golden("vm22_baseline.json")

    @pytest.mark.parametrize(
        "product_key",
        [
            "fixed_annuity_5yr",
            "fixed_annuity_10yr",
        ],
    )
    def test_fixed_annuity_reserve(self, vm22_data: dict, product_key: str) -> None:
        """[P1] Reserve calculation should match baseline."""
        from annuity_pricing.regulatory.vm22 import FixedAnnuityPolicy, VM22Calculator

        if product_key not in vm22_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = vm22_data[product_key]
        params = product_data["parameters"]
        settings = product_data["calculation_settings"]

        policy = FixedAnnuityPolicy(
            premium=params["premium"],
            guaranteed_rate=params["guaranteed_rate"],
            term_years=params["term_years"],
            current_year=params["current_year"],
            surrender_charge_pct=params["surrender_charge_pct"],
        )

        calc = VM22Calculator(
            n_scenarios=settings["n_scenarios"],
            projection_years=settings["projection_years"],
            seed=settings["seed"],
        )

        result = calc.calculate_reserve(
            policy,
            market_rate=settings.get("market_rate"),
            lapse_rate=settings.get("lapse_rate", 0.05),
        )

        expected_reserve = product_data["expected"]["reserve"]
        tolerance = product_data["tolerances"]["reserve_relative"]
        rel_error = abs(result.reserve - expected_reserve) / expected_reserve

        assert rel_error < tolerance, (
            f"VM-22 {product_key} reserve mismatch: got {result.reserve:.2f}, "
            f"expected {expected_reserve:.2f}, error={rel_error:.2%}"
        )

    @pytest.mark.parametrize(
        "product_key",
        [
            "fixed_annuity_5yr",
            "fixed_annuity_10yr",
        ],
    )
    def test_deterministic_reserve(self, vm22_data: dict, product_key: str) -> None:
        """[P1] Deterministic reserve should match baseline."""
        from annuity_pricing.regulatory.vm22 import FixedAnnuityPolicy, VM22Calculator

        if product_key not in vm22_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = vm22_data[product_key]
        params = product_data["parameters"]
        settings = product_data["calculation_settings"]

        policy = FixedAnnuityPolicy(
            premium=params["premium"],
            guaranteed_rate=params["guaranteed_rate"],
            term_years=params["term_years"],
            current_year=params["current_year"],
            surrender_charge_pct=params["surrender_charge_pct"],
        )

        calc = VM22Calculator(
            n_scenarios=settings["n_scenarios"],
            projection_years=settings["projection_years"],
            seed=settings["seed"],
        )

        result = calc.calculate_reserve(
            policy,
            market_rate=settings.get("market_rate"),
            lapse_rate=settings.get("lapse_rate", 0.05),
        )

        expected_dr = product_data["expected"]["deterministic_reserve"]
        tolerance = product_data["tolerances"]["reserve_relative"]
        rel_error = abs(result.deterministic_reserve - expected_dr) / expected_dr

        assert rel_error < tolerance, (
            f"VM-22 {product_key} DR mismatch: got {result.deterministic_reserve:.2f}, "
            f"expected {expected_dr:.2f}, error={rel_error:.2%}"
        )

    def test_set_passes_for_simple_product(self, vm22_data: dict) -> None:
        """[P1] Stochastic Exclusion Test should pass for simple fixed annuity."""
        from annuity_pricing.regulatory.vm22 import FixedAnnuityPolicy, VM22Calculator

        product_data = vm22_data["fixed_annuity_5yr"]
        params = product_data["parameters"]
        settings = product_data["calculation_settings"]

        policy = FixedAnnuityPolicy(
            premium=params["premium"],
            guaranteed_rate=params["guaranteed_rate"],
            term_years=params["term_years"],
            current_year=params["current_year"],
            surrender_charge_pct=params["surrender_charge_pct"],
        )

        calc = VM22Calculator(
            n_scenarios=settings["n_scenarios"],
            projection_years=settings["projection_years"],
            seed=settings["seed"],
        )

        result = calc.calculate_reserve(
            policy,
            market_rate=settings.get("market_rate"),
            lapse_rate=settings.get("lapse_rate", 0.05),
        )

        expected_set = product_data["expected"]["set_passed"]
        assert result.set_passed == expected_set, (
            f"SET mismatch: got {result.set_passed}, expected {expected_set}"
        )
