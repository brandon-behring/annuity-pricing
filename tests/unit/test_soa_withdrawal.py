"""
Tests for SOA-Calibrated Withdrawal Utilization Model - Phase H.

[T2] Tests SOAWithdrawalModel against known SOA values.

See: docs/assumptions/BEHAVIOR_CALIBRATION.md
"""

import numpy as np
import pytest

from annuity_pricing.behavioral.withdrawal import (
    SOAWithdrawalAssumptions,
    SOAWithdrawalModel,
    UtilizationCalibration,
)


class TestSOAWithdrawalAssumptions:
    """Tests for SOAWithdrawalAssumptions dataclass."""

    def test_default_values(self) -> None:
        """Default assumptions should be reasonable."""
        assumptions = SOAWithdrawalAssumptions()

        assert assumptions.use_duration_curve is True
        assert assumptions.use_age_curve is True
        assert assumptions.use_itm_sensitivity is True
        assert assumptions.use_continuous_itm is True
        assert assumptions.combination_method == "multiplicative"
        assert assumptions.min_utilization == 0.03
        assert assumptions.max_utilization == 1.00

    def test_custom_values(self) -> None:
        """Custom assumptions should be accepted."""
        assumptions = SOAWithdrawalAssumptions(
            use_duration_curve=False,
            use_age_curve=False,
            use_itm_sensitivity=False,
            combination_method="additive",
            min_utilization=0.10,
            max_utilization=0.90,
        )

        assert assumptions.use_duration_curve is False
        assert assumptions.use_age_curve is False
        assert assumptions.use_itm_sensitivity is False
        assert assumptions.combination_method == "additive"


class TestSOAWithdrawalModel:
    """Tests for SOAWithdrawalModel."""

    @pytest.fixture
    def model(self) -> SOAWithdrawalModel:
        """Standard model with default SOA assumptions."""
        return SOAWithdrawalModel(SOAWithdrawalAssumptions())

    def test_calibration_source(self, model: SOAWithdrawalModel) -> None:
        """Model should report SOA 2018 calibration source."""
        assert model.calibration_source == UtilizationCalibration.SOA_2018

    def test_year_1_utilization_low(self, model: SOAWithdrawalModel) -> None:
        """[T2] Year 1 should have low utilization (~11% base)."""
        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=1, age=67
        )
        # Duration util ~11%, age at 67 is reference
        assert result.duration_utilization == 0.111
        # Overall utilization should be low
        assert result.utilization_rate < 0.20

    def test_year_10_utilization_high(self, model: SOAWithdrawalModel) -> None:
        """[T2] Year 10 should have high utilization (~52% base)."""
        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=10, age=67
        )
        # Duration util ~52%
        assert result.duration_utilization == 0.518
        assert result.utilization_rate > 0.40

    def test_age_72_high_utilization(self, model: SOAWithdrawalModel) -> None:
        """[T2] Age 72 should show high utilization (~59%)."""
        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=72
        )
        # Age 72 utilization from SOA 2018
        assert abs(result.age_utilization - 0.59) < 0.02

    def test_young_age_low_utilization(self, model: SOAWithdrawalModel) -> None:
        """Young ages should have low utilization."""
        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=55
        )
        # Age 55 utilization from SOA 2018 is ~5%
        assert result.age_utilization < 0.10

    def test_itm_increases_utilization(self, model: SOAWithdrawalModel) -> None:
        """Deep ITM should increase utilization."""
        # ATM case
        atm_result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        # Deep ITM case (GWB/AV = 1.6 > 1.50 threshold)
        itm_result = model.calculate_withdrawal(
            gwb=160_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )

        assert itm_result.moneyness == 1.6
        assert itm_result.itm_factor > atm_result.itm_factor
        assert itm_result.utilization_rate > atm_result.utilization_rate

    def test_itm_sensitivity_factors_from_soa(self, model: SOAWithdrawalModel) -> None:
        """[T2] ITM sensitivity factors should match SOA 2018."""
        # Not ITM (moneyness <= 1.0)
        result_not_itm = model.calculate_withdrawal(
            gwb=90_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        assert result_not_itm.itm_factor == 1.0
        assert result_not_itm.moneyness < 1.0

        # Shallow ITM (1.0 < moneyness <= 1.25)
        result_shallow = model.calculate_withdrawal(
            gwb=110_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        assert result_shallow.moneyness == 1.1
        assert result_shallow.itm_factor > 1.0

        # Deep ITM (moneyness > 1.50)
        result_deep = model.calculate_withdrawal(
            gwb=200_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        assert result_deep.moneyness == 2.0
        # Should approach 2.11 (but continuous interpolation may vary)
        assert abs(result_deep.itm_factor - 2.11) < 0.15

    def test_withdrawal_amount_calculation(self, model: SOAWithdrawalModel) -> None:
        """Withdrawal amount = max_allowed * utilization_rate."""
        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )

        assert result.max_allowed == 100_000 * 0.05  # 5000
        expected_withdrawal = result.max_allowed * result.utilization_rate
        assert abs(result.withdrawal_amount - expected_withdrawal) < 0.01

    def test_utilization_floor_enforced(self, model: SOAWithdrawalModel) -> None:
        """Utilization should not go below min_utilization."""
        # Very young age + early duration should be low but floored
        assumptions = SOAWithdrawalAssumptions(min_utilization=0.05)
        model = SOAWithdrawalModel(assumptions)

        result = model.calculate_withdrawal(
            gwb=100_000, av=200_000, withdrawal_rate=0.05, duration=1, age=45
        )
        assert result.utilization_rate >= 0.05

    def test_utilization_cap_enforced(self, model: SOAWithdrawalModel) -> None:
        """Utilization should not exceed max_utilization."""
        # Old age + late duration + deep ITM could push above 100%
        result = model.calculate_withdrawal(
            gwb=200_000, av=100_000, withdrawal_rate=0.05, duration=11, age=82
        )
        assert result.utilization_rate <= 1.0

    def test_invalid_gwb_raises(self, model: SOAWithdrawalModel) -> None:
        """Negative GWB should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=-100_000, av=100_000, withdrawal_rate=0.05, duration=1, age=70
            )

    def test_invalid_av_raises(self, model: SOAWithdrawalModel) -> None:
        """Zero or negative AV should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_withdrawal(gwb=100_000, av=0, withdrawal_rate=0.05, duration=1, age=70)
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=100_000, av=-100, withdrawal_rate=0.05, duration=1, age=70
            )

    def test_invalid_withdrawal_rate_raises(self, model: SOAWithdrawalModel) -> None:
        """Invalid withdrawal rate should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=100_000, av=100_000, withdrawal_rate=-0.05, duration=1, age=70
            )
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=100_000, av=100_000, withdrawal_rate=1.5, duration=1, age=70
            )

    def test_invalid_duration_raises(self, model: SOAWithdrawalModel) -> None:
        """Zero or negative duration should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=0, age=70
            )
        with pytest.raises(ValueError):
            model.calculate_withdrawal(
                gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=-1, age=70
            )


class TestSOAWithdrawalModelCombinationMethods:
    """Tests for different utilization combination methods."""

    def test_multiplicative_method(self) -> None:
        """Multiplicative method should scale by age adjustment."""
        model = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                combination_method="multiplicative",
                use_itm_sensitivity=False,  # Isolate for this test
            )
        )

        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=72
        )

        # Duration ~21.5%, age 72 ~59%, reference age 67 ~32%
        # multiplicative: duration * (age_util / reference_age_util)
        expected_adjustment = result.age_utilization / 0.32  # ~1.84
        expected = result.duration_utilization * expected_adjustment
        assert abs(result.utilization_rate - expected) < 0.05

    def test_additive_method(self) -> None:
        """Additive method should average duration and age effects."""
        model = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                combination_method="additive",
                use_itm_sensitivity=False,
            )
        )

        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )

        # Additive: (duration + age) / 2
        expected = (result.duration_utilization + result.age_utilization) / 2
        assert abs(result.utilization_rate - expected) < 0.01


class TestSOAWithdrawalModelPathCalculation:
    """Tests for path-based withdrawal calculations."""

    @pytest.fixture
    def model(self) -> SOAWithdrawalModel:
        """Standard model."""
        return SOAWithdrawalModel(SOAWithdrawalAssumptions())

    def test_path_withdrawal_calculation(self, model: SOAWithdrawalModel) -> None:
        """Should calculate withdrawals along a path."""
        gwb_path = np.array([100_000, 100_000, 100_000])
        av_path = np.array([100_000, 110_000, 90_000])
        ages = np.array([70, 71, 72])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            av_path=av_path,
            ages=ages,
            withdrawal_rate=0.05,
            start_duration=1,
        )

        assert len(withdrawals) == 3
        assert all(w >= 0 for w in withdrawals)
        # Later years should generally have higher utilization
        # (higher duration + older age)

    def test_path_with_deferred_first_withdrawal(self, model: SOAWithdrawalModel) -> None:
        """Should handle deferred first withdrawal."""
        gwb_path = np.array([100_000, 100_000, 100_000, 100_000])
        av_path = np.array([100_000, 105_000, 110_000, 115_000])
        ages = np.array([65, 66, 67, 68])

        withdrawals = model.calculate_path_withdrawals(
            gwb_path=gwb_path,
            av_path=av_path,
            ages=ages,
            withdrawal_rate=0.05,
            start_duration=1,
            first_withdrawal_year=2,  # Defer until year 3
        )

        assert withdrawals[0] == 0.0  # No withdrawal year 1
        assert withdrawals[1] == 0.0  # No withdrawal year 2
        assert withdrawals[2] > 0  # First withdrawal year 3
        assert withdrawals[3] > 0  # Continued withdrawals

    def test_path_mismatched_lengths_raises(self, model: SOAWithdrawalModel) -> None:
        """Mismatched path lengths should raise ValueError."""
        gwb_path = np.array([100_000, 100_000])
        av_path = np.array([100_000, 100_000, 100_000])
        ages = np.array([70, 71])

        with pytest.raises(ValueError):
            model.calculate_path_withdrawals(
                gwb_path=gwb_path,
                av_path=av_path,
                ages=ages,
                withdrawal_rate=0.05,
            )


class TestSOAWithdrawalModelUtilizationProfile:
    """Tests for utilization profile generation."""

    @pytest.fixture
    def model(self) -> SOAWithdrawalModel:
        """Standard model."""
        return SOAWithdrawalModel(SOAWithdrawalAssumptions())

    def test_profile_generation(self, model: SOAWithdrawalModel) -> None:
        """Should generate utilization profile over time."""
        profile = model.get_utilization_profile(
            start_age=65,
            start_duration=1,
            years=10,
            moneyness=1.0,
        )

        assert len(profile) == 10
        assert all(0 <= u <= 1.0 for u in profile.values())

    def test_profile_increases_over_time(self, model: SOAWithdrawalModel) -> None:
        """Utilization should generally increase with duration and age."""
        profile = model.get_utilization_profile(
            start_age=60,
            start_duration=1,
            years=15,
            moneyness=1.0,
        )

        # First year should be lower than later years
        assert profile[0] < profile[10]


class TestSOAWithdrawalModelDisabledFeatures:
    """Tests for model with features disabled."""

    def test_disabled_duration_curve(self) -> None:
        """Disabled duration curve should use flat 50%."""
        model = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_duration_curve=False,
                use_age_curve=False,
                use_itm_sensitivity=False,
            )
        )

        result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=1, age=70
        )
        # With both curves disabled, multiplicative gives: 0.5 * (0.5/0.5) = 0.5
        assert result.duration_utilization == 0.50
        assert result.age_utilization == 0.50

    def test_disabled_itm_sensitivity(self) -> None:
        """Disabled ITM sensitivity should have factor = 1.0."""
        model = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_itm_sensitivity=False,
            )
        )

        result = model.calculate_withdrawal(
            gwb=200_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        assert result.itm_factor == 1.0

    def test_discrete_vs_continuous_itm(self) -> None:
        """Discrete ITM should give step-function values."""
        model_discrete = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_continuous_itm=False,
            )
        )
        model_continuous = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_continuous_itm=True,
            )
        )

        # At boundary (moneyness = 1.1), discrete and continuous may differ
        result_discrete = model_discrete.calculate_withdrawal(
            gwb=110_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        result_continuous = model_continuous.calculate_withdrawal(
            gwb=110_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )

        # Discrete should give exact 1.39 for ITM 100-125%
        assert result_discrete.itm_factor == 1.39
        # Continuous should interpolate (may be different)
        assert result_continuous.itm_factor > 1.0


class TestBackwardCompatibilityWithOriginal:
    """Ensure original WithdrawalModel still works."""

    def test_original_model_unchanged(self) -> None:
        """Original WithdrawalModel should work with old interface."""
        from annuity_pricing.behavioral.withdrawal import (
            WithdrawalAssumptions,
            WithdrawalModel,
        )

        model = WithdrawalModel(WithdrawalAssumptions())
        result = model.calculate_withdrawal(
            gwb=100_000,
            withdrawal_rate=0.05,
            age=70,
        )

        assert result.withdrawal_amount > 0
        assert result.max_allowed == 5000
        assert 0 < result.utilization_rate <= 1.0
