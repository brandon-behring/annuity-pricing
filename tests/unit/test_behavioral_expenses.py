"""
Tests for Expense Model - Phase 7.

[T1] Total expense = per_policy × inflation_factor + AV × pct_of_av

See: docs/knowledge/domain/expense_assumptions.md
"""

import numpy as np
import pytest

from annuity_pricing.behavioral.expenses import (
    ExpenseAssumptions,
    ExpenseModel,
)


class TestExpenseAssumptions:
    """Tests for ExpenseAssumptions dataclass."""

    def test_default_values(self) -> None:
        """Default assumptions should be reasonable."""
        assumptions = ExpenseAssumptions()

        assert assumptions.per_policy_annual == 100.0  # $100
        assert assumptions.pct_of_av_annual == 0.0150  # 1.50% M&E
        assert assumptions.acquisition_pct == 0.03  # 3% acquisition
        assert assumptions.inflation_rate == 0.025  # 2.5% inflation

    def test_custom_values(self) -> None:
        """Custom assumptions should be accepted."""
        assumptions = ExpenseAssumptions(
            per_policy_annual=150.0,
            pct_of_av_annual=0.0200,
            acquisition_pct=0.05,
            inflation_rate=0.03,
        )

        assert assumptions.per_policy_annual == 150.0
        assert assumptions.pct_of_av_annual == 0.0200
        assert assumptions.acquisition_pct == 0.05
        assert assumptions.inflation_rate == 0.03


class TestExpenseModel:
    """Tests for ExpenseModel."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        """Standard model with default assumptions."""
        return ExpenseModel(ExpenseAssumptions())

    def test_basic_expense_calculation(self, model: ExpenseModel) -> None:
        """
        [T1] Basic expense = per_policy + AV × pct.
        """
        result = model.calculate_period_expense(
            av=100_000,
            period_years=1.0,
            years_from_issue=0,
        )

        # Per-policy: $100, AV: $100k × 1.5% = $1,500
        # Total: $1,600
        assert result.per_policy_component == pytest.approx(100.0)
        assert result.av_component == pytest.approx(1_500.0)
        assert result.total_expense == pytest.approx(1_600.0)

    def test_partial_year_expense(self, model: ExpenseModel) -> None:
        """
        [T1] Expense scales with period length.
        """
        full_year = model.calculate_period_expense(av=100_000, period_years=1.0)
        half_year = model.calculate_period_expense(av=100_000, period_years=0.5)

        assert half_year.total_expense == pytest.approx(full_year.total_expense / 2)

    def test_inflation_increases_per_policy(self, model: ExpenseModel) -> None:
        """
        [T2] Per-policy expense increases with inflation.
        """
        year_0 = model.calculate_period_expense(av=100_000, years_from_issue=0)
        year_5 = model.calculate_period_expense(av=100_000, years_from_issue=5)
        year_10 = model.calculate_period_expense(av=100_000, years_from_issue=10)

        # Per-policy should increase (AV stays same)
        assert year_5.per_policy_component > year_0.per_policy_component
        assert year_10.per_policy_component > year_5.per_policy_component

        # AV component should be unchanged
        assert year_5.av_component == year_0.av_component
        assert year_10.av_component == year_0.av_component

    def test_inflation_calculation(self) -> None:
        """
        [T2] Verify inflation factor = (1 + r)^t.
        """
        assumptions = ExpenseAssumptions(
            per_policy_annual=100.0,
            pct_of_av_annual=0.0,  # Remove AV component
            inflation_rate=0.025,
        )
        model = ExpenseModel(assumptions)

        result_0 = model.calculate_period_expense(av=0, years_from_issue=0)
        result_5 = model.calculate_period_expense(av=0, years_from_issue=5)

        # Expected: 100 × (1.025)^5 ≈ 113.14
        expected_year_5 = 100.0 * (1.025**5)
        assert result_5.per_policy_component == pytest.approx(expected_year_5, rel=0.001)

    def test_av_component_scales_with_av(self, model: ExpenseModel) -> None:
        """
        [T1] AV component is proportional to account value.
        """
        result_100k = model.calculate_period_expense(av=100_000)
        result_200k = model.calculate_period_expense(av=200_000)

        assert result_200k.av_component == 2 * result_100k.av_component

    def test_negative_av_raises(self, model: ExpenseModel) -> None:
        """Negative AV should raise error."""
        with pytest.raises(ValueError, match="negative"):
            model.calculate_period_expense(av=-100_000)

    def test_zero_period_raises(self, model: ExpenseModel) -> None:
        """Zero or negative period should raise error."""
        with pytest.raises(ValueError, match="positive"):
            model.calculate_period_expense(av=100_000, period_years=0)

        with pytest.raises(ValueError, match="positive"):
            model.calculate_period_expense(av=100_000, period_years=-1.0)


class TestAcquisitionCost:
    """Tests for acquisition cost calculation."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        return ExpenseModel(ExpenseAssumptions())

    def test_acquisition_cost_calculation(self, model: ExpenseModel) -> None:
        """
        [T1] Acquisition cost = premium × acquisition_pct.
        """
        cost = model.calculate_acquisition_cost(premium=100_000)

        # 3% of $100k = $3,000
        assert cost == pytest.approx(3_000.0)

    def test_acquisition_cost_scales(self, model: ExpenseModel) -> None:
        """Acquisition cost is proportional to premium."""
        cost_100k = model.calculate_acquisition_cost(100_000)
        cost_200k = model.calculate_acquisition_cost(200_000)

        assert cost_200k == 2 * cost_100k

    def test_negative_premium_raises(self, model: ExpenseModel) -> None:
        """Negative premium should raise error."""
        with pytest.raises(ValueError, match="negative"):
            model.calculate_acquisition_cost(-100_000)


class TestPathExpenses:
    """Tests for path-based expense calculations."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        return ExpenseModel(ExpenseAssumptions())

    def test_path_expenses_basic(self, model: ExpenseModel) -> None:
        """Calculate expenses along a constant AV path."""
        av_path = np.array([100_000, 100_000, 100_000, 100_000, 100_000])

        expenses = model.calculate_path_expenses(av_path, dt=1.0)

        assert len(expenses) == 5
        assert all(e > 0 for e in expenses)

    def test_path_expenses_inflation_effect(self, model: ExpenseModel) -> None:
        """Expenses should increase due to inflation."""
        av_path = np.array([100_000] * 10)

        expenses = model.calculate_path_expenses(av_path, dt=1.0)

        # Later expenses should be higher (per-policy inflates)
        for i in range(len(expenses) - 1):
            assert expenses[i + 1] >= expenses[i]

    def test_path_expenses_with_varying_av(self, model: ExpenseModel) -> None:
        """Expenses should reflect changing AV."""
        # AV increases over time
        av_path = np.array([100_000, 110_000, 121_000, 133_100, 146_410])

        expenses = model.calculate_path_expenses(av_path, dt=1.0)

        # Higher AV → higher expenses (both inflation and AV effect)
        for i in range(len(expenses) - 1):
            assert expenses[i + 1] > expenses[i]


class TestPVExpenses:
    """Tests for present value of expenses."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        return ExpenseModel(ExpenseAssumptions())

    def test_pv_expenses_basic(self, model: ExpenseModel) -> None:
        """Calculate PV of expenses."""
        av_path = np.array([100_000, 100_000, 100_000])
        survival = np.array([1.0, 0.95, 0.90])

        pv = model.calculate_pv_expenses(
            av_path=av_path,
            survival_probs=survival,
            discount_rate=0.05,
            dt=1.0,
        )

        assert pv > 0

    def test_pv_decreases_with_higher_discount(self, model: ExpenseModel) -> None:
        """Higher discount rate → lower PV."""
        av_path = np.array([100_000] * 10)
        survival = np.ones(10)

        pv_low = model.calculate_pv_expenses(av_path, survival, 0.02, dt=1.0)
        pv_high = model.calculate_pv_expenses(av_path, survival, 0.10, dt=1.0)

        assert pv_high < pv_low

    def test_pv_decreases_with_lower_survival(self, model: ExpenseModel) -> None:
        """Lower survival → lower PV (fewer expected expenses)."""
        av_path = np.array([100_000] * 10)
        high_survival = np.ones(10)
        low_survival = np.linspace(1.0, 0.5, 10)  # Decreasing survival

        pv_high = model.calculate_pv_expenses(av_path, high_survival, 0.05, dt=1.0)
        pv_low = model.calculate_pv_expenses(av_path, low_survival, 0.05, dt=1.0)

        assert pv_low < pv_high

    def test_pv_with_acquisition(self, model: ExpenseModel) -> None:
        """PV should include acquisition cost when requested."""
        av_path = np.array([100_000, 100_000, 100_000])
        survival = np.array([1.0, 0.95, 0.90])
        premium = 100_000

        pv_without = model.calculate_pv_expenses(
            av_path, survival, 0.05, dt=1.0, include_acquisition=False
        )
        pv_with = model.calculate_pv_expenses(
            av_path, survival, 0.05, dt=1.0, include_acquisition=True, premium=premium
        )

        # Should include $3,000 acquisition cost
        acquisition = model.calculate_acquisition_cost(premium)
        assert pv_with == pytest.approx(pv_without + acquisition)

    def test_pv_acquisition_requires_premium(self, model: ExpenseModel) -> None:
        """Must provide premium when include_acquisition=True."""
        av_path = np.array([100_000])
        survival = np.array([1.0])

        with pytest.raises(ValueError, match="Premium required"):
            model.calculate_pv_expenses(av_path, survival, 0.05, include_acquisition=True)

    def test_pv_path_length_mismatch_raises(self, model: ExpenseModel) -> None:
        """Mismatched path lengths should raise error."""
        av_path = np.array([100_000, 100_000, 100_000])
        survival = np.array([1.0, 0.95])  # Different length

        with pytest.raises(ValueError, match="lengths must match"):
            model.calculate_pv_expenses(av_path, survival, 0.05)


class TestAnnualExpenseRate:
    """Tests for annualized expense rate."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        return ExpenseModel(ExpenseAssumptions())

    def test_annual_rate_calculation(self, model: ExpenseModel) -> None:
        """
        Rate = total_expense / AV.
        """
        rate = model.calculate_annual_expense_rate(av=100_000)

        # ($100 + $1,500) / $100,000 = 1.6%
        assert rate == pytest.approx(0.016)

    def test_rate_decreases_with_higher_av(self, model: ExpenseModel) -> None:
        """
        Higher AV dilutes fixed per-policy expense.
        """
        rate_small = model.calculate_annual_expense_rate(av=50_000)
        rate_large = model.calculate_annual_expense_rate(av=200_000)

        # Per-policy is fixed, so rate decreases with AV
        assert rate_large < rate_small

    def test_rate_increases_with_inflation(self, model: ExpenseModel) -> None:
        """Inflation increases the expense rate over time."""
        rate_0 = model.calculate_annual_expense_rate(av=100_000, years_from_issue=0)
        rate_10 = model.calculate_annual_expense_rate(av=100_000, years_from_issue=10)

        assert rate_10 > rate_0

    def test_zero_av_raises(self, model: ExpenseModel) -> None:
        """Zero AV should raise error (divide by zero)."""
        with pytest.raises(ValueError, match="positive"):
            model.calculate_annual_expense_rate(av=0)


class TestExpenseSensitivity:
    """Tests for expense sensitivity analysis."""

    @pytest.fixture
    def model(self) -> ExpenseModel:
        return ExpenseModel(ExpenseAssumptions())

    def test_sensitivity_per_policy(self, model: ExpenseModel) -> None:
        """Sensitivity to per-policy expense."""
        sens = model.expense_sensitivity(av=100_000, parameter="per_policy")

        # Should be ~1 (dollar for dollar impact)
        assert sens == pytest.approx(1.0, rel=0.01)

    def test_sensitivity_pct_of_av(self, model: ExpenseModel) -> None:
        """Sensitivity to % of AV."""
        sens = model.expense_sensitivity(av=100_000, parameter="pct_of_av")

        # 1 bp increase in pct_of_av → $10 increase in expense (for $100k AV)
        # But the sensitivity function uses relative change, so check it's reasonable
        assert sens > 0

    def test_sensitivity_unknown_parameter_raises(self, model: ExpenseModel) -> None:
        """Unknown parameter should raise error."""
        with pytest.raises(ValueError, match="Unknown parameter"):
            model.expense_sensitivity(av=100_000, parameter="unknown")
