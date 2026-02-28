"""
Stress testing workflow integration tests.

Tests that stress testing modules are importable and have expected structures.

References:
    [T2] ORSA guidelines for stress scenario calibration
"""

import pytest

from annuity_pricing.stress_testing import (
    ALL_HISTORICAL_CRISES,
    ALL_ORSA_SCENARIOS,
    # Historical crises
    CRISIS_2008_GFC,
    CRISIS_2020_COVID,
    ORSA_EXTREMELY_ADVERSE,
    ORSA_MODERATE_ADVERSE,
    ORSA_SEVERELY_ADVERSE,
    # Reverse stress
    RESERVE_EXHAUSTION,
    RESERVE_INCREASE_50,
    ScenarioType,
    # Scenarios
    StressScenario,
    create_custom_scenario,
    crisis_to_scenario,
    get_crisis_by_name,
    # Sensitivity
    get_default_sensitivity_parameters,
)

# =============================================================================
# Historical Crisis Tests
# =============================================================================


class TestHistoricalCrises:
    """Test historical crisis definitions and conversions."""

    def test_all_crises_defined(self):
        """All expected historical crises should be defined."""
        assert len(ALL_HISTORICAL_CRISES) >= 7
        crisis_names = {c.name for c in ALL_HISTORICAL_CRISES}
        expected = {"2008_gfc", "2020_covid", "2000_dotcom"}
        assert expected.issubset(crisis_names)

    def test_gfc_2008_exists(self):
        """GFC 2008 crisis should be defined."""
        assert CRISIS_2008_GFC.name == "2008_gfc"

    def test_covid_2020_exists(self):
        """COVID 2020 crisis should be defined."""
        assert CRISIS_2020_COVID.name == "2020_covid"

    def test_crisis_lookup(self):
        """get_crisis_by_name should work for all crises."""
        for crisis in ALL_HISTORICAL_CRISES:
            found = get_crisis_by_name(crisis.name)
            assert found is not None
            assert found.name == crisis.name

    def test_crisis_to_scenario_conversion(self):
        """Historical crisis should convert to stress scenario."""
        scenario = crisis_to_scenario(CRISIS_2008_GFC)

        assert isinstance(scenario, StressScenario)
        assert scenario.equity_shock < 0
        assert scenario.scenario_type == ScenarioType.HISTORICAL
        assert scenario.source_crisis == "2008_gfc"


# =============================================================================
# ORSA Scenario Tests
# =============================================================================


class TestORSAScenarios:
    """Test ORSA standard scenarios."""

    def test_orsa_scenarios_ordered_by_severity(self):
        """ORSA scenarios should increase in severity."""
        assert abs(ORSA_MODERATE_ADVERSE.equity_shock) < abs(ORSA_SEVERELY_ADVERSE.equity_shock)
        assert abs(ORSA_SEVERELY_ADVERSE.equity_shock) < abs(ORSA_EXTREMELY_ADVERSE.equity_shock)

    def test_orsa_moderate_parameters(self):
        """Moderate scenario should have mild shocks."""
        assert -0.20 <= ORSA_MODERATE_ADVERSE.equity_shock < 0
        assert ORSA_MODERATE_ADVERSE.vol_shock >= 1.0
        assert ORSA_MODERATE_ADVERSE.lapse_multiplier >= 1.0

    def test_orsa_severe_parameters(self):
        """Severe scenario should have significant shocks."""
        assert -0.40 <= ORSA_SEVERELY_ADVERSE.equity_shock < -0.20
        assert ORSA_SEVERELY_ADVERSE.vol_shock > ORSA_MODERATE_ADVERSE.vol_shock

    def test_orsa_extreme_parameters(self):
        """Extreme scenario should have severe shocks."""
        assert ORSA_EXTREMELY_ADVERSE.equity_shock < -0.40
        assert ORSA_EXTREMELY_ADVERSE.vol_shock > ORSA_SEVERELY_ADVERSE.vol_shock

    def test_all_orsa_scenarios_valid(self):
        """All ORSA scenarios should be valid StressScenario instances."""
        for scenario in ALL_ORSA_SCENARIOS:
            assert isinstance(scenario, StressScenario)
            assert scenario.scenario_type == ScenarioType.ORSA


# =============================================================================
# Custom Scenario Tests
# =============================================================================


class TestCustomScenarios:
    """Test custom scenario creation."""

    def test_create_custom_scenario(self):
        """Custom scenarios should be creatable."""
        scenario = create_custom_scenario(
            name="test_custom",
            display_name="Test Custom Scenario",
            equity_shock=-0.25,
            rate_shock=-0.01,
        )

        assert scenario.name == "test_custom"
        assert scenario.equity_shock == -0.25
        assert scenario.rate_shock == -0.01
        assert scenario.scenario_type == ScenarioType.CUSTOM

    def test_invalid_vol_shock_raises(self):
        """Negative vol_shock should raise ValueError."""
        with pytest.raises(ValueError, match="vol_shock"):
            create_custom_scenario(
                name="invalid",
                display_name="Invalid",
                equity_shock=-0.10,
                rate_shock=0.0,
                vol_shock=-0.5,
            )


# =============================================================================
# Sensitivity Analysis Tests
# =============================================================================


class TestSensitivityAnalysis:
    """Test sensitivity analysis workflows."""

    def test_default_parameters_defined(self):
        """Default sensitivity parameters should be defined."""
        params = get_default_sensitivity_parameters()
        assert len(params) >= 3  # At least equity, rate, vol

        param_names = {p.name for p in params}
        # Check that at least some shock parameters are defined
        assert any(name in param_names for name in ["equity_shock", "rate_shock", "vol_shock"])


# =============================================================================
# Reverse Stress Testing Tests
# =============================================================================


class TestReverseStressTesting:
    """Test reverse stress testing workflows."""

    def test_predefined_targets_defined(self):
        """Predefined reverse stress targets should be available."""
        assert RESERVE_EXHAUSTION is not None
        assert RESERVE_INCREASE_50 is not None


# =============================================================================
# Stress Workflow Integration Tests
# =============================================================================


class TestStressWorkflowIntegration:
    """Test complete stress testing workflows."""

    def test_crisis_to_scenario_to_pricing(self):
        """Complete flow: crisis → scenario works."""
        # Convert historical crisis to scenario
        scenario = crisis_to_scenario(CRISIS_2008_GFC)

        # Scenario should have meaningful shocks
        assert scenario.equity_shock < -0.20  # GFC had major equity drop
        assert scenario.vol_shock >= 1.0  # Vol increased

    def test_orsa_scenarios_complete(self):
        """All ORSA scenarios should be accessible and valid."""
        for scenario in ALL_ORSA_SCENARIOS:
            assert isinstance(scenario, StressScenario)
            assert scenario.equity_shock < 0  # All adverse scenarios have negative equity shock
            assert scenario.vol_shock >= 1.0  # All have elevated or normal vol
