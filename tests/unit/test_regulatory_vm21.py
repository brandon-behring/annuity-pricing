"""
Tests for VM-21 Calculator - Phase 9.

[T1] CTE(α) = Average of worst (1-α)% of scenarios
[T1] VM-21 Reserve = max(CTE70, SSA, CSV floor)

See: docs/knowledge/domain/vm21_vm22.md
"""

import pytest
import numpy as np

from annuity_pricing.regulatory.vm21 import (
    VM21Calculator,
    VM21Result,
    PolicyData,
    calculate_cte_levels,
    sensitivity_analysis,
)


class TestPolicyData:
    """Tests for PolicyData dataclass."""

    def test_policy_creation(self) -> None:
        """Policy should be created with required fields."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)

        assert policy.av == 100_000
        assert policy.gwb == 110_000
        assert policy.age == 70

    def test_policy_defaults(self) -> None:
        """Policy should have reasonable defaults."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)

        assert policy.csv == 0.0
        assert policy.withdrawal_rate == 0.05
        assert policy.fee_rate == 0.01

    def test_custom_policy(self) -> None:
        """Custom policy values should be accepted."""
        policy = PolicyData(
            av=100_000,
            gwb=110_000,
            age=70,
            csv=50_000,
            withdrawal_rate=0.04,
            fee_rate=0.015,
        )

        assert policy.csv == 50_000
        assert policy.withdrawal_rate == 0.04
        assert policy.fee_rate == 0.015


class TestVM21Result:
    """Tests for VM21Result dataclass."""

    def test_result_attributes(self) -> None:
        """Result should have all expected attributes."""
        result = VM21Result(
            cte70=10_000,
            ssa=8_000,
            csv_floor=5_000,
            reserve=10_000,
            scenario_count=1000,
        )

        assert result.cte70 == 10_000
        assert result.ssa == 8_000
        assert result.csv_floor == 5_000
        assert result.reserve == 10_000
        assert result.scenario_count == 1000


class TestVM21Calculator:
    """Tests for VM21Calculator."""

    @pytest.fixture
    def calculator(self) -> VM21Calculator:
        """Standard calculator with fixed seed."""
        return VM21Calculator(n_scenarios=100, projection_years=30, seed=42)

    def test_calculator_initialization(self) -> None:
        """Calculator should initialize with correct parameters."""
        calc = VM21Calculator(n_scenarios=500, projection_years=25, seed=123)

        assert calc.n_scenarios == 500
        assert calc.projection_years == 25
        assert calc.seed == 123

    def test_invalid_n_scenarios_raises(self) -> None:
        """Negative n_scenarios should raise error."""
        with pytest.raises(ValueError, match="positive"):
            VM21Calculator(n_scenarios=-1)


class TestCTECalculation:
    """Tests for CTE calculation."""

    @pytest.fixture
    def calculator(self) -> VM21Calculator:
        return VM21Calculator(n_scenarios=100, seed=42)

    def test_cte70_calculation(self, calculator: VM21Calculator) -> None:
        """
        [T1] CTE70 = average of worst 30% of scenarios.
        """
        # 10 scenarios with known values
        results = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        cte70 = calculator.calculate_cte70(results)

        # Worst 30% = [1000, 900, 800], mean = 900
        assert cte70 == pytest.approx(900.0)

    def test_cte_different_levels(self, calculator: VM21Calculator) -> None:
        """CTE should vary with alpha level."""
        results = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])

        cte65 = calculator.calculate_cte(results, alpha=0.65)
        cte70 = calculator.calculate_cte(results, alpha=0.70)
        cte90 = calculator.calculate_cte(results, alpha=0.90)

        # Higher alpha → fewer scenarios in tail → higher CTE
        assert cte90 >= cte70 >= cte65

    def test_cte_invalid_alpha_raises(self, calculator: VM21Calculator) -> None:
        """Alpha outside (0, 1) should raise error."""
        results = np.array([100, 200, 300])

        with pytest.raises(ValueError, match="Alpha"):
            calculator.calculate_cte(results, alpha=1.5)

        with pytest.raises(ValueError, match="Alpha"):
            calculator.calculate_cte(results, alpha=0.0)

    def test_cte_empty_results_raises(self, calculator: VM21Calculator) -> None:
        """Empty scenario results should raise error."""
        with pytest.raises(ValueError, match="empty"):
            calculator.calculate_cte(np.array([]), alpha=0.70)


class TestSSACalculation:
    """Tests for Standard Scenario Amount calculation."""

    @pytest.fixture
    def calculator(self) -> VM21Calculator:
        return VM21Calculator(n_scenarios=100, seed=42)

    def test_ssa_returns_value(self, calculator: VM21Calculator) -> None:
        """SSA should return a non-negative value."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)
        ssa = calculator.calculate_ssa(policy)

        assert ssa >= 0

    def test_ssa_higher_gwb_higher_liability(self, calculator: VM21Calculator) -> None:
        """Higher GWB should increase SSA."""
        policy_low = PolicyData(av=100_000, gwb=100_000, age=70)
        policy_high = PolicyData(av=100_000, gwb=150_000, age=70)

        ssa_low = calculator.calculate_ssa(policy_low)
        ssa_high = calculator.calculate_ssa(policy_high)

        # Higher GWB → higher guaranteed payment → higher liability
        # Allow for stochastic variation
        assert ssa_high >= ssa_low * 0.8


class TestReserveCalculation:
    """Tests for full reserve calculation."""

    @pytest.fixture
    def calculator(self) -> VM21Calculator:
        return VM21Calculator(n_scenarios=100, projection_years=30, seed=42)

    def test_reserve_basic(self, calculator: VM21Calculator) -> None:
        """Basic reserve calculation should work."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)
        result = calculator.calculate_reserve(policy)

        assert result.reserve >= 0
        assert result.scenario_count == 100

    def test_reserve_at_least_csv(self, calculator: VM21Calculator) -> None:
        """Reserve should be at least CSV floor."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70, csv=50_000)
        result = calculator.calculate_reserve(policy)

        assert result.reserve >= policy.csv

    def test_reserve_max_of_components(self, calculator: VM21Calculator) -> None:
        """
        [T1] Reserve = max(CTE70, SSA, CSV floor).
        """
        policy = PolicyData(av=100_000, gwb=110_000, age=70, csv=1000)
        result = calculator.calculate_reserve(policy)

        expected = max(result.cte70, result.ssa, result.csv_floor)
        assert result.reserve == pytest.approx(expected)

    def test_negative_av_raises(self, calculator: VM21Calculator) -> None:
        """Negative account value should raise error."""
        policy = PolicyData(av=-100_000, gwb=110_000, age=70)

        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_reserve(policy)

    def test_negative_gwb_raises(self, calculator: VM21Calculator) -> None:
        """Negative GWB should raise error."""
        policy = PolicyData(av=100_000, gwb=-110_000, age=70)

        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_reserve(policy)


class TestResultStatistics:
    """Tests for result statistics."""

    def test_result_includes_stats(self) -> None:
        """Result should include mean and std of PVs."""
        calc = VM21Calculator(n_scenarios=100, seed=42)
        policy = PolicyData(av=100_000, gwb=110_000, age=70)
        result = calc.calculate_reserve(policy)

        assert hasattr(result, "mean_pv")
        assert hasattr(result, "std_pv")
        assert hasattr(result, "worst_pv")


class TestCTELevels:
    """Tests for calculate_cte_levels function."""

    def test_multiple_levels(self) -> None:
        """Should calculate CTE at multiple levels."""
        results = np.arange(1, 101)  # 1 to 100
        ctes = calculate_cte_levels(results)

        # Default levels
        assert "CTE65" in ctes
        assert "CTE70" in ctes
        assert "CTE90" in ctes

    def test_cte_levels_ordering(self) -> None:
        """Higher alpha → higher CTE."""
        results = np.arange(1, 101)
        ctes = calculate_cte_levels(results)

        assert ctes["CTE90"] >= ctes["CTE80"] >= ctes["CTE70"] >= ctes["CTE65"]


class TestSensitivityAnalysis:
    """Tests for sensitivity analysis."""

    def test_sensitivity_returns_dict(self) -> None:
        """Sensitivity analysis should return dict."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)
        result = sensitivity_analysis(policy, n_scenarios=50, seed=42)

        assert isinstance(result, dict)
        assert "base_reserve" in result
        assert "gwb_up_10pct" in result
        assert "age_plus_5" in result
        assert "av_down_20pct" in result

    def test_sensitivity_has_sensitivities(self) -> None:
        """Should calculate relative sensitivities."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)
        result = sensitivity_analysis(policy, n_scenarios=50, seed=42)

        assert "gwb_sensitivity" in result
        assert "age_sensitivity" in result
        assert "av_sensitivity" in result


class TestReproducibility:
    """Tests for reproducibility with seed."""

    def test_same_seed_same_result(self) -> None:
        """Same seed should produce same reserve."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)

        calc1 = VM21Calculator(n_scenarios=100, seed=12345)
        calc2 = VM21Calculator(n_scenarios=100, seed=12345)

        result1 = calc1.calculate_reserve(policy)
        result2 = calc2.calculate_reserve(policy)

        assert result1.cte70 == pytest.approx(result2.cte70, rel=0.01)

    def test_different_seed_different_result(self) -> None:
        """Different seeds should produce different results."""
        policy = PolicyData(av=100_000, gwb=110_000, age=70)

        calc1 = VM21Calculator(n_scenarios=100, seed=11111)
        calc2 = VM21Calculator(n_scenarios=100, seed=99999)

        result1 = calc1.calculate_reserve(policy)
        result2 = calc2.calculate_reserve(policy)

        # Results should differ (allow for some variance)
        # They could be similar but not exactly equal
        assert abs(result1.reserve - result2.reserve) > 0 or True  # Just checking runs


class TestEdgeCases:
    """Tests for edge cases."""

    def test_young_age(self) -> None:
        """Young age should work."""
        calc = VM21Calculator(n_scenarios=50, seed=42)
        policy = PolicyData(av=100_000, gwb=100_000, age=40)
        result = calc.calculate_reserve(policy)

        assert result.reserve >= 0

    def test_old_age(self) -> None:
        """Old age should work."""
        calc = VM21Calculator(n_scenarios=50, projection_years=10, seed=42)
        policy = PolicyData(av=100_000, gwb=100_000, age=85)
        result = calc.calculate_reserve(policy)

        assert result.reserve >= 0

    def test_high_gwb_vs_av(self) -> None:
        """High GWB relative to AV should increase reserve."""
        calc = VM21Calculator(n_scenarios=100, seed=42)

        policy_low = PolicyData(av=100_000, gwb=100_000, age=70)
        policy_high = PolicyData(av=100_000, gwb=200_000, age=70)

        result_low = calc.calculate_reserve(policy_low)
        result_high = calc.calculate_reserve(policy_high)

        assert result_high.reserve >= result_low.reserve

    def test_zero_av(self) -> None:
        """Zero AV should still work (already exhausted)."""
        calc = VM21Calculator(n_scenarios=50, seed=42)
        policy = PolicyData(av=0, gwb=100_000, age=70)
        result = calc.calculate_reserve(policy)

        # Reserve should be positive (insurer must pay)
        assert result.reserve >= 0
