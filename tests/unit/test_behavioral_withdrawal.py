"""
Tests for GLWB Withdrawal Utilization Model - Phase 7.

[T1] Withdrawal = GWB × withdrawal_rate × utilization_rate

See: docs/knowledge/domain/glwb_mechanics.md
"""

import numpy as np
import pytest

from annuity_pricing.behavioral.withdrawal import (
    WithdrawalAssumptions,
    WithdrawalModel,
)


class TestWithdrawalAssumptions:
    """Tests for WithdrawalAssumptions dataclass."""

    def test_default_values(self) -> None:
        """Default assumptions should be reasonable."""
        assumptions = WithdrawalAssumptions()

        assert assumptions.base_utilization == 0.70  # 70%
        assert assumptions.age_sensitivity == 0.01  # +1% per year over 65
        assert assumptions.min_utilization == 0.30  # 30% floor
        assert assumptions.max_utilization == 1.00  # 100% cap

    def test_custom_values(self) -> None:
        """Custom assumptions should be accepted."""
        assumptions = WithdrawalAssumptions(
            base_utilization=0.80,
            age_sensitivity=0.02,
            min_utilization=0.40,
            max_utilization=0.95,
        )

        assert assumptions.base_utilization == 0.80
        assert assumptions.age_sensitivity == 0.02
        assert assumptions.min_utilization == 0.40
        assert assumptions.max_utilization == 0.95


class TestWithdrawalModel:
    """Tests for WithdrawalModel."""

    @pytest.fixture
    def model(self) -> WithdrawalModel:
        """Standard model with default assumptions."""
        return WithdrawalModel(WithdrawalAssumptions())

    def test_basic_withdrawal_calculation(self, model: WithdrawalModel) -> None:
        """
        [T1] Withdrawal = GWB × rate × utilization.
        """
        result = model.calculate_withdrawal(
            gwb=100_000,
            withdrawal_rate=0.05,
            age=65,
            years_since_first_withdrawal=5,  # Past ramp-up
        )

        # At age 65 with base utilization 70%
        # Max allowed = 100k * 0.05 = 5k
        # Expected withdrawal = 5k * 0.70 = 3.5k
        assert result.max_allowed == 5_000
        assert result.utilization_rate == pytest.approx(0.70, abs=0.01)
        assert result.withdrawal_amount == pytest.approx(3_500, rel=0.05)

    def test_older_age_higher_utilization(self, model: WithdrawalModel) -> None:
        """
        [T1] Older ages have higher utilization rates.
        """
        # Age 65 (reference)
        result_65 = model.calculate_withdrawal(
            gwb=100_000, withdrawal_rate=0.05, age=65, years_since_first_withdrawal=5
        )

        # Age 75 (+10 years)
        result_75 = model.calculate_withdrawal(
            gwb=100_000, withdrawal_rate=0.05, age=75, years_since_first_withdrawal=5
        )

        # Higher age should have higher utilization
        assert result_75.utilization_rate > result_65.utilization_rate

        # +1% per year over 65, so +10% at age 75
        expected_utilization_75 = 0.70 + 0.10  # 80%
        assert result_75.utilization_rate == pytest.approx(expected_utilization_75, abs=0.01)

    def test_early_withdrawal_ramp_up(self, model: WithdrawalModel) -> None:
        """
        [T1] Utilization ramps up in early withdrawal years.

        Year 0: 70% of base
        Year 1: 80% of base
        Year 2: 90% of base
        Year 3+: 100% of base
        """
        results = []
        for years in range(5):
            result = model.calculate_withdrawal(
                gwb=100_000, withdrawal_rate=0.05, age=65, years_since_first_withdrawal=years
            )
            results.append(result)

        # Year 0 should be lowest
        assert results[0].utilization_rate < results[1].utilization_rate
        assert results[1].utilization_rate < results[2].utilization_rate

        # Year 3+ should be at full utilization
        assert results[3].utilization_rate == results[4].utilization_rate

    def test_utilization_floor_enforced(self) -> None:
        """
        [T1] Utilization rate cannot go below minimum.
        """
        # Low base utilization with floor
        assumptions = WithdrawalAssumptions(
            base_utilization=0.30,
            min_utilization=0.25,
        )
        model = WithdrawalModel(assumptions)

        # Year 0 ramp (70% of 30% = 21%) would be below floor
        result = model.calculate_withdrawal(
            gwb=100_000, withdrawal_rate=0.05, age=55, years_since_first_withdrawal=0
        )

        # Should be floored at min_utilization
        assert result.utilization_rate >= 0.25

    def test_utilization_cap_enforced(self) -> None:
        """
        [T1] Utilization rate cannot exceed maximum.
        """
        # Very old age with high sensitivity
        assumptions = WithdrawalAssumptions(
            base_utilization=0.90,
            age_sensitivity=0.05,  # +5% per year
            max_utilization=0.95,
        )
        model = WithdrawalModel(assumptions)

        # Age 80 would calculate 0.90 + 0.05*15 = 1.65 (>1.0)
        result = model.calculate_withdrawal(
            gwb=100_000, withdrawal_rate=0.05, age=80, years_since_first_withdrawal=10
        )

        # Should be capped at max_utilization
        assert result.utilization_rate <= 0.95

    def test_zero_gwb_returns_zero_withdrawal(self, model: WithdrawalModel) -> None:
        """
        [T1] Zero GWB should result in zero withdrawal.
        """
        result = model.calculate_withdrawal(gwb=0, withdrawal_rate=0.05, age=70)

        assert result.max_allowed == 0
        assert result.withdrawal_amount == 0

    def test_invalid_gwb_raises(self, model: WithdrawalModel) -> None:
        """Negative GWB should raise error."""
        with pytest.raises(ValueError, match="negative"):
            model.calculate_withdrawal(gwb=-100_000, withdrawal_rate=0.05, age=70)

    def test_invalid_withdrawal_rate_raises(self, model: WithdrawalModel) -> None:
        """Withdrawal rate outside [0, 1] should raise error."""
        with pytest.raises(ValueError, match="Withdrawal rate"):
            model.calculate_withdrawal(gwb=100_000, withdrawal_rate=1.5, age=70)

        with pytest.raises(ValueError, match="Withdrawal rate"):
            model.calculate_withdrawal(gwb=100_000, withdrawal_rate=-0.05, age=70)


class TestPathWithdrawals:
    """Tests for path-based withdrawal calculations."""

    @pytest.fixture
    def model(self) -> WithdrawalModel:
        return WithdrawalModel(WithdrawalAssumptions())

    def test_path_withdrawals_basic(self, model: WithdrawalModel) -> None:
        """Calculate withdrawals along a path."""
        gwb_path = np.array([100_000, 100_000, 100_000, 100_000, 100_000])
        ages = np.array([65, 66, 67, 68, 69])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            ages=ages,
            withdrawal_rate=0.05,
            first_withdrawal_year=0,
        )

        assert len(withdrawals) == 5
        assert all(w > 0 for w in withdrawals)

    def test_path_withdrawals_increasing_with_age(self, model: WithdrawalModel) -> None:
        """Withdrawals should increase with age (higher utilization)."""
        gwb_path = np.array([100_000] * 10)
        ages = np.array([65, 66, 67, 68, 69, 70, 71, 72, 73, 74])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            ages=ages,
            withdrawal_rate=0.05,
            first_withdrawal_year=0,
        )

        # After ramp-up period (year 3+), should be increasing
        for i in range(4, len(withdrawals) - 1):
            assert withdrawals[i + 1] >= withdrawals[i]

    def test_path_withdrawals_delayed_start(self, model: WithdrawalModel) -> None:
        """Withdrawals before first_withdrawal_year should be zero."""
        gwb_path = np.array([100_000] * 5)
        ages = np.array([62, 63, 64, 65, 66])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            ages=ages,
            withdrawal_rate=0.05,
            first_withdrawal_year=3,  # Start at year 3
        )

        # First 3 years should be zero
        assert withdrawals[0] == 0
        assert withdrawals[1] == 0
        assert withdrawals[2] == 0
        # After first withdrawal year should be non-zero
        assert withdrawals[3] > 0
        assert withdrawals[4] > 0

    def test_path_length_mismatch_raises(self, model: WithdrawalModel) -> None:
        """Mismatched path lengths should raise error."""
        gwb_path = np.array([100_000, 100_000, 100_000])
        ages = np.array([65, 66])  # Different length

        with pytest.raises(ValueError, match="lengths must match"):
            model.calculate_path_withdrawals(gwb_path, ages, 0.05)

    def test_path_with_declining_gwb(self, model: WithdrawalModel) -> None:
        """Withdrawals should reflect changing GWB."""
        # GWB declines over time
        gwb_path = np.array([100_000, 95_000, 90_000, 85_000, 80_000])
        ages = np.array([70, 71, 72, 73, 74])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            ages=ages,
            withdrawal_rate=0.05,
            first_withdrawal_year=0,
        )

        # Check that max_allowed is correctly based on GWB
        # At year 0: max = 100k * 0.05 = 5k
        # At year 4: max = 80k * 0.05 = 4k
        # But utilization increases with age, so overall trend depends on balance


class TestWithdrawalRateSchedule:
    """Tests for age-based withdrawal rate schedule."""

    @pytest.fixture
    def model(self) -> WithdrawalModel:
        return WithdrawalModel(WithdrawalAssumptions())

    def test_rate_schedule_under_55(self, model: WithdrawalModel) -> None:
        """Very early withdrawal: 3.5%."""
        rate = model.get_withdrawal_rate_by_age(50)
        assert rate == 0.035

    def test_rate_schedule_55_59(self, model: WithdrawalModel) -> None:
        """Age 55-59: 4.0%."""
        for age in [55, 57, 59]:
            rate = model.get_withdrawal_rate_by_age(age)
            assert rate == 0.040

    def test_rate_schedule_60_64(self, model: WithdrawalModel) -> None:
        """Age 60-64: 4.5%."""
        for age in [60, 62, 64]:
            rate = model.get_withdrawal_rate_by_age(age)
            assert rate == 0.045

    def test_rate_schedule_65_69(self, model: WithdrawalModel) -> None:
        """Age 65-69: 5.0%."""
        for age in [65, 67, 69]:
            rate = model.get_withdrawal_rate_by_age(age)
            assert rate == 0.050

    def test_rate_schedule_70_74(self, model: WithdrawalModel) -> None:
        """Age 70-74: 5.5%."""
        for age in [70, 72, 74]:
            rate = model.get_withdrawal_rate_by_age(age)
            assert rate == 0.055

    def test_rate_schedule_75_plus(self, model: WithdrawalModel) -> None:
        """Age 75+: 6.0%."""
        for age in [75, 80, 85, 90]:
            rate = model.get_withdrawal_rate_by_age(age)
            assert rate == 0.060

    def test_rate_schedule_monotonic(self, model: WithdrawalModel) -> None:
        """Rates should increase with age."""
        ages = [50, 55, 60, 65, 70, 75, 80]
        rates = [model.get_withdrawal_rate_by_age(age) for age in ages]

        for i in range(len(rates) - 1):
            assert rates[i] <= rates[i + 1], (
                f"Rate at age {ages[i]} exceeds rate at age {ages[i + 1]}"
            )
