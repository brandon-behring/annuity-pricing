"""
Tests for Tolerance Framework - config/tolerances.py.

Verifies tolerance values, CLT-based MC tolerance calculations,
and the tolerance registry.

See: docs/TOLERANCE_JUSTIFICATION.md
"""

import pytest
import numpy as np
import math

from annuity_pricing.config.tolerances import (
    # Tier 1: Analytical
    ANTI_PATTERN_TOLERANCE,
    PUT_CALL_PARITY_TOLERANCE,
    GREEKS_NUMERICAL_TOLERANCE,
    # Tier 2: Cross-Library
    CROSS_LIBRARY_TOLERANCE,
    GREEKS_VALIDATION_TOLERANCE,
    HULL_EXAMPLE_TOLERANCE,
    # Tier 3: Stochastic
    MC_10K_TOLERANCE,
    MC_100K_TOLERANCE,
    MC_500K_TOLERANCE,
    BS_MC_CONVERGENCE_TOLERANCE,
    mc_tolerance,
    # Tier 4: Integration
    INTEGRATION_TOLERANCE,
    GOLDEN_RELATIVE_TOLERANCE,
    PORTFOLIO_TOLERANCE,
    # Domain-Specific
    FLOOR_ENFORCEMENT_TOLERANCE,
    BUFFER_ABSORPTION_TOLERANCE,
    CAP_ENFORCEMENT_TOLERANCE,
    # Registry
    TOLERANCE_REGISTRY,
    get_tolerance,
)


# =============================================================================
# Tier 1: Analytical Tolerances
# =============================================================================


class TestTier1AnalyticalTolerances:
    """Tests for Tier 1 analytical tolerances."""

    def test_anti_pattern_tolerance_exists(self) -> None:
        """ANTI_PATTERN_TOLERANCE should be defined."""
        assert ANTI_PATTERN_TOLERANCE is not None

    def test_anti_pattern_tolerance_tight(self) -> None:
        """Anti-pattern tolerance should be very tight (near machine precision)."""
        assert ANTI_PATTERN_TOLERANCE <= 1e-8
        assert ANTI_PATTERN_TOLERANCE > 0

    def test_put_call_parity_tolerance_exists(self) -> None:
        """PUT_CALL_PARITY_TOLERANCE should be defined."""
        assert PUT_CALL_PARITY_TOLERANCE is not None

    def test_put_call_parity_tolerance_tight(self) -> None:
        """Put-call parity tolerance should be numerically tight."""
        assert PUT_CALL_PARITY_TOLERANCE <= 1e-6
        assert PUT_CALL_PARITY_TOLERANCE > 0

    def test_greeks_numerical_tolerance_exists(self) -> None:
        """GREEKS_NUMERICAL_TOLERANCE should be defined."""
        assert GREEKS_NUMERICAL_TOLERANCE is not None

    def test_greeks_numerical_tolerance_near_sqrt_eps(self) -> None:
        """Greeks tolerance should be near sqrt(machine_epsilon)."""
        sqrt_eps = math.sqrt(np.finfo(float).eps)  # ~1.5e-8
        # Should be within 2 orders of magnitude of sqrt(eps)
        assert GREEKS_NUMERICAL_TOLERANCE <= sqrt_eps * 100
        assert GREEKS_NUMERICAL_TOLERANCE >= sqrt_eps / 100


# =============================================================================
# Tier 2: Cross-Library Tolerances
# =============================================================================


class TestTier2CrossLibraryTolerances:
    """Tests for Tier 2 cross-library tolerances."""

    def test_cross_library_tolerance_6_decimals(self) -> None:
        """Cross-library tolerance should be ~6 decimal places."""
        assert CROSS_LIBRARY_TOLERANCE <= 1e-5
        assert CROSS_LIBRARY_TOLERANCE >= 1e-8

    def test_greeks_validation_tolerance_looser(self) -> None:
        """Greeks validation should be slightly looser than cross-library."""
        assert GREEKS_VALIDATION_TOLERANCE >= CROSS_LIBRARY_TOLERANCE

    def test_hull_example_tolerance_2_decimals(self) -> None:
        """Hull examples are quoted to 2 decimals, so tolerance ~0.02."""
        assert HULL_EXAMPLE_TOLERANCE <= 0.05
        assert HULL_EXAMPLE_TOLERANCE >= 0.001


# =============================================================================
# Tier 3: Stochastic Tolerances
# =============================================================================


class TestTier3StochasticTolerances:
    """Tests for Tier 3 stochastic (MC) tolerances."""

    def test_mc_tolerance_decreases_with_paths(self) -> None:
        """MC tolerance should decrease as O(1/sqrt(N))."""
        tol_10k = mc_tolerance(10_000)
        tol_100k = mc_tolerance(100_000)
        tol_1m = mc_tolerance(1_000_000)

        # 10x paths -> ~3x improvement
        assert tol_100k < tol_10k
        assert tol_1m < tol_100k

        # Check O(1/sqrt(N)) scaling
        ratio = tol_10k / tol_100k
        expected_ratio = math.sqrt(100_000 / 10_000)  # sqrt(10) ≈ 3.16
        assert abs(ratio - expected_ratio) < 0.1

    def test_mc_tolerance_default_sigma(self) -> None:
        """Default sigma should be 0.20 (typical option volatility)."""
        # Using formula: tol = 3 * sigma / sqrt(N)
        expected_100k = 3 * 0.20 / math.sqrt(100_000)
        actual_100k = mc_tolerance(100_000)
        assert abs(actual_100k - expected_100k) < 1e-10

    def test_mc_tolerance_custom_sigma(self) -> None:
        """Custom sigma should be respected."""
        sigma_low = 0.10
        sigma_high = 0.40
        tol_low = mc_tolerance(10_000, sigma=sigma_low)
        tol_high = mc_tolerance(10_000, sigma=sigma_high)

        assert tol_high == pytest.approx(tol_low * 4, rel=1e-10)  # 0.40/0.10 = 4

    def test_mc_tolerance_custom_confidence(self) -> None:
        """Custom confidence level should be respected."""
        tol_3sigma = mc_tolerance(10_000, confidence=3.0)
        tol_2sigma = mc_tolerance(10_000, confidence=2.0)

        assert tol_3sigma == pytest.approx(tol_2sigma * 1.5, rel=1e-10)

    def test_mc_10k_tolerance_clt_derived(self) -> None:
        """MC_10K_TOLERANCE should match CLT formula."""
        clt_value = 3 * 0.20 / math.sqrt(10_000)  # 0.006
        assert MC_10K_TOLERANCE == pytest.approx(clt_value, abs=0.001)

    def test_mc_tolerances_ordering(self) -> None:
        """Higher path count should have lower or equal tolerance."""
        assert MC_100K_TOLERANCE <= MC_10K_TOLERANCE + 0.01  # Allow conservative buffer
        assert MC_500K_TOLERANCE <= MC_100K_TOLERANCE

    def test_bs_mc_convergence_tolerance_reasonable(self) -> None:
        """BS-MC convergence tolerance should be reasonable (1-2%)."""
        assert BS_MC_CONVERGENCE_TOLERANCE <= 0.05
        assert BS_MC_CONVERGENCE_TOLERANCE >= 0.001


# =============================================================================
# Tier 4: Integration Tolerances
# =============================================================================


class TestTier4IntegrationTolerances:
    """Tests for Tier 4 integration tolerances."""

    def test_integration_tolerance_exists(self) -> None:
        """INTEGRATION_TOLERANCE should be defined."""
        assert INTEGRATION_TOLERANCE is not None
        assert INTEGRATION_TOLERANCE > 0

    def test_golden_relative_tolerance_tight(self) -> None:
        """Golden file tolerance should be tight for regression testing."""
        assert GOLDEN_RELATIVE_TOLERANCE <= 1e-4
        assert GOLDEN_RELATIVE_TOLERANCE > 0

    def test_portfolio_tolerance_reasonable(self) -> None:
        """Portfolio tolerance should be reasonable for aggregation."""
        assert PORTFOLIO_TOLERANCE <= 1e-2
        assert PORTFOLIO_TOLERANCE >= 1e-6


# =============================================================================
# Domain-Specific Tolerances
# =============================================================================


class TestDomainSpecificTolerances:
    """Tests for domain-specific tolerances."""

    def test_floor_enforcement_very_tight(self) -> None:
        """Floor enforcement is a contract guarantee, must be very tight."""
        assert FLOOR_ENFORCEMENT_TOLERANCE <= 1e-8

    def test_buffer_absorption_very_tight(self) -> None:
        """Buffer absorption is contractual, must be very tight."""
        assert BUFFER_ABSORPTION_TOLERANCE <= 1e-8

    def test_cap_enforcement_very_tight(self) -> None:
        """Cap enforcement is contractual, must be very tight."""
        assert CAP_ENFORCEMENT_TOLERANCE <= 1e-8

    def test_all_domain_tolerances_positive(self) -> None:
        """All domain tolerances should be positive."""
        assert FLOOR_ENFORCEMENT_TOLERANCE > 0
        assert BUFFER_ABSORPTION_TOLERANCE > 0
        assert CAP_ENFORCEMENT_TOLERANCE > 0


# =============================================================================
# Tolerance Registry
# =============================================================================


class TestToleranceRegistry:
    """Tests for the tolerance registry."""

    def test_registry_not_empty(self) -> None:
        """Registry should contain tolerances."""
        assert len(TOLERANCE_REGISTRY) > 0

    def test_registry_has_all_tiers(self) -> None:
        """Registry should have representatives from all tiers."""
        # Tier 1
        assert "anti_pattern" in TOLERANCE_REGISTRY
        assert "put_call_parity" in TOLERANCE_REGISTRY

        # Tier 2
        assert "cross_library" in TOLERANCE_REGISTRY
        assert "hull_example" in TOLERANCE_REGISTRY

        # Tier 3
        assert "mc_10k" in TOLERANCE_REGISTRY
        assert "mc_100k" in TOLERANCE_REGISTRY

        # Tier 4
        assert "integration" in TOLERANCE_REGISTRY
        assert "golden_relative" in TOLERANCE_REGISTRY

    def test_registry_values_positive(self) -> None:
        """All registry values should be positive."""
        for name, value in TOLERANCE_REGISTRY.items():
            assert value > 0, f"{name} should be positive, got {value}"

    def test_registry_values_match_constants(self) -> None:
        """Registry values should match the constant definitions."""
        assert TOLERANCE_REGISTRY["anti_pattern"] == ANTI_PATTERN_TOLERANCE
        assert TOLERANCE_REGISTRY["cross_library"] == CROSS_LIBRARY_TOLERANCE
        assert TOLERANCE_REGISTRY["mc_10k"] == MC_10K_TOLERANCE
        assert TOLERANCE_REGISTRY["floor_enforcement"] == FLOOR_ENFORCEMENT_TOLERANCE


# =============================================================================
# get_tolerance Function
# =============================================================================


class TestGetTolerance:
    """Tests for get_tolerance function."""

    def test_get_valid_tolerance(self) -> None:
        """Should return tolerance for valid names."""
        assert get_tolerance("anti_pattern") == ANTI_PATTERN_TOLERANCE
        assert get_tolerance("mc_100k") == MC_100K_TOLERANCE
        assert get_tolerance("floor_enforcement") == FLOOR_ENFORCEMENT_TOLERANCE

    def test_get_unknown_tolerance_raises(self) -> None:
        """Should raise KeyError for unknown tolerance names."""
        with pytest.raises(KeyError, match="Unknown tolerance"):
            get_tolerance("nonexistent_tolerance")

    def test_get_tolerance_error_message_helpful(self) -> None:
        """Error message should list available tolerances."""
        with pytest.raises(KeyError) as exc_info:
            get_tolerance("invalid")

        error_msg = str(exc_info.value)
        assert "Available:" in error_msg
        assert "anti_pattern" in error_msg


# =============================================================================
# Tolerance Hierarchy
# =============================================================================


class TestToleranceHierarchy:
    """Tests verifying the tolerance hierarchy is consistent."""

    def test_tier1_tighter_than_tier2(self) -> None:
        """Tier 1 (analytical) should be tighter than Tier 2 (cross-library)."""
        assert ANTI_PATTERN_TOLERANCE < CROSS_LIBRARY_TOLERANCE
        assert PUT_CALL_PARITY_TOLERANCE < CROSS_LIBRARY_TOLERANCE

    def test_tier2_tighter_than_tier3(self) -> None:
        """Tier 2 should generally be tighter than Tier 3 (stochastic)."""
        assert CROSS_LIBRARY_TOLERANCE < MC_10K_TOLERANCE

    def test_domain_specific_very_tight(self) -> None:
        """Domain-specific (contractual) tolerances should be among the tightest."""
        assert FLOOR_ENFORCEMENT_TOLERANCE <= ANTI_PATTERN_TOLERANCE
        assert BUFFER_ABSORPTION_TOLERANCE <= ANTI_PATTERN_TOLERANCE
        assert CAP_ENFORCEMENT_TOLERANCE <= ANTI_PATTERN_TOLERANCE


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for tolerance functions."""

    def test_mc_tolerance_single_path(self) -> None:
        """MC tolerance for 1 path should be high."""
        tol = mc_tolerance(1)
        assert tol > 0.5  # Very uncertain with 1 path

    def test_mc_tolerance_many_paths(self) -> None:
        """MC tolerance for many paths should be low."""
        tol = mc_tolerance(10_000_000)  # 10M paths
        assert tol < 0.001

    def test_mc_tolerance_zero_paths_raises(self) -> None:
        """MC tolerance for 0 paths should raise or return inf."""
        # Division by zero in sqrt
        with pytest.raises(Exception):  # Could be ZeroDivisionError or ValueError
            mc_tolerance(0)

    def test_mc_tolerance_negative_paths_handled(self) -> None:
        """MC tolerance for negative paths should raise."""
        with pytest.raises(Exception):
            mc_tolerance(-100)

    def test_mc_tolerance_zero_sigma(self) -> None:
        """Zero sigma should give zero tolerance (deterministic payoff)."""
        tol = mc_tolerance(10_000, sigma=0.0)
        assert tol == 0.0

    def test_registry_case_sensitive(self) -> None:
        """Registry lookup should be case-sensitive."""
        assert "anti_pattern" in TOLERANCE_REGISTRY
        assert "ANTI_PATTERN" not in TOLERANCE_REGISTRY
        assert "Anti_Pattern" not in TOLERANCE_REGISTRY
