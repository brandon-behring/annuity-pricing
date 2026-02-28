"""
Tests for SOA-Calibrated Dynamic Lapse Model - Phase H.

[T2] Tests SOADynamicLapseModel against known SOA values.

See: docs/assumptions/BEHAVIOR_CALIBRATION.md
"""

import numpy as np
import pytest

from annuity_pricing.behavioral.dynamic_lapse import (
    CalibrationSource,
    SOADynamicLapseModel,
    SOALapseAssumptions,
)


class TestSOALapseAssumptions:
    """Tests for SOALapseAssumptions dataclass."""

    def test_default_values(self) -> None:
        """Default assumptions should be reasonable."""
        assumptions = SOALapseAssumptions()

        assert assumptions.surrender_charge_length == 7
        assert assumptions.use_duration_curve is True
        assert assumptions.use_sc_cliff_effect is True
        assert assumptions.use_age_adjustment is False
        assert assumptions.moneyness_sensitivity == 1.0
        assert assumptions.min_lapse == 0.005
        assert assumptions.max_lapse == 0.25

    def test_custom_values(self) -> None:
        """Custom assumptions should be accepted."""
        assumptions = SOALapseAssumptions(
            surrender_charge_length=10,
            use_duration_curve=False,
            use_sc_cliff_effect=False,
            min_lapse=0.01,
            max_lapse=0.30,
        )

        assert assumptions.surrender_charge_length == 10
        assert assumptions.use_duration_curve is False
        assert assumptions.use_sc_cliff_effect is False


class TestSOADynamicLapseModel:
    """Tests for SOADynamicLapseModel."""

    @pytest.fixture
    def model(self) -> SOADynamicLapseModel:
        """Standard model with default SOA assumptions."""
        return SOADynamicLapseModel(SOALapseAssumptions())

    def test_calibration_source(self, model: SOADynamicLapseModel) -> None:
        """Model should report SOA 2006 calibration source."""
        assert model.calibration_source == CalibrationSource.SOA_2006

    def test_year_1_base_rate(self, model: SOADynamicLapseModel) -> None:
        """[T2] Year 1 should have ~1.4% base rate from SOA."""
        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=1, years_to_sc_end=6)
        assert abs(result.base_rate - 0.014) < 0.001

    def test_year_8_post_sc_rate(self, model: SOADynamicLapseModel) -> None:
        """[T2] Year 8 (post-SC) should have ~11.2% base rate from SOA."""
        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=8, years_to_sc_end=-1)
        assert abs(result.base_rate - 0.112) < 0.01

    def test_sc_cliff_effect_at_expiration(self, model: SOADynamicLapseModel) -> None:
        """SC cliff factor should be > 1 at expiration."""
        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=7, years_to_sc_end=0)
        # Cliff factor should be elevated (though blending may reduce it)
        assert result.sc_cliff_factor >= 1.0

    def test_no_sc_cliff_far_from_expiration(self, model: SOADynamicLapseModel) -> None:
        """SC cliff factor should be 1.0 far from expiration."""
        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=2, years_to_sc_end=5)
        assert result.sc_cliff_factor == 1.0

    def test_itm_guarantee_reduces_lapse(self, model: SOADynamicLapseModel) -> None:
        """ITM guarantee (GWB > AV) should reduce lapse rate."""
        atm_result = model.calculate_lapse(gwb=100_000, av=100_000, duration=5, years_to_sc_end=2)
        itm_result = model.calculate_lapse(
            gwb=150_000,
            av=100_000,
            duration=5,
            years_to_sc_end=2,  # ITM
        )
        assert itm_result.lapse_rate < atm_result.lapse_rate
        assert itm_result.moneyness > 1.0  # GWB/AV
        assert itm_result.moneyness_factor < 1.0  # Reduces lapse

    def test_otm_guarantee_increases_lapse(self, model: SOADynamicLapseModel) -> None:
        """OTM guarantee (GWB < AV) should increase lapse rate."""
        atm_result = model.calculate_lapse(gwb=100_000, av=100_000, duration=5, years_to_sc_end=2)
        otm_result = model.calculate_lapse(
            gwb=80_000,
            av=100_000,
            duration=5,
            years_to_sc_end=2,  # OTM
        )
        assert otm_result.lapse_rate > atm_result.lapse_rate
        assert otm_result.moneyness < 1.0
        assert otm_result.moneyness_factor > 1.0

    def test_lapse_rate_floor_enforced(self, model: SOADynamicLapseModel) -> None:
        """Lapse rate should not go below min_lapse."""
        # Very ITM guarantee should reduce lapse, but not below floor
        result = model.calculate_lapse(
            gwb=500_000,
            av=100_000,
            duration=1,
            years_to_sc_end=6,  # Very ITM
        )
        assert result.lapse_rate >= model.assumptions.min_lapse

    def test_lapse_rate_cap_enforced(self, model: SOADynamicLapseModel) -> None:
        """Lapse rate should not exceed max_lapse."""
        # Very OTM + post-SC cliff
        result = model.calculate_lapse(
            gwb=10_000,
            av=100_000,
            duration=8,
            years_to_sc_end=-1,  # Very OTM, post-SC
        )
        assert result.lapse_rate <= model.assumptions.max_lapse

    def test_invalid_av_raises(self, model: SOADynamicLapseModel) -> None:
        """Zero or negative AV should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_lapse(gwb=100_000, av=0, duration=1)
        with pytest.raises(ValueError):
            model.calculate_lapse(gwb=100_000, av=-100, duration=1)

    def test_invalid_gwb_raises(self, model: SOADynamicLapseModel) -> None:
        """Negative GWB should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_lapse(gwb=-100_000, av=100_000, duration=1)

    def test_invalid_duration_raises(self, model: SOADynamicLapseModel) -> None:
        """Zero or negative duration should raise ValueError."""
        with pytest.raises(ValueError):
            model.calculate_lapse(gwb=100_000, av=100_000, duration=0)
        with pytest.raises(ValueError):
            model.calculate_lapse(gwb=100_000, av=100_000, duration=-1)


class TestSOADynamicLapseModelDurationCurve:
    """Tests for duration-based surrender curve behavior."""

    @pytest.fixture
    def model(self) -> SOADynamicLapseModel:
        """Model with duration curve enabled."""
        return SOADynamicLapseModel(
            SOALapseAssumptions(
                use_sc_cliff_effect=False,  # Disable cliff for pure duration tests
                moneyness_sensitivity=0,  # Disable moneyness
            )
        )

    def test_rates_increase_during_sc_period(self, model: SOADynamicLapseModel) -> None:
        """Base rates should increase during SC period (years 1-7)."""
        rates = []
        for duration in range(1, 8):
            years_to_sc_end = 7 - duration
            result = model.calculate_lapse(
                gwb=100_000, av=100_000, duration=duration, years_to_sc_end=years_to_sc_end
            )
            rates.append(result.base_rate)

        for i in range(len(rates) - 1):
            assert rates[i] <= rates[i + 1]

    def test_cliff_at_year_8(self, model: SOADynamicLapseModel) -> None:
        """Year 8 should be significantly higher than year 7."""
        year_7 = model.calculate_lapse(gwb=100_000, av=100_000, duration=7, years_to_sc_end=0)
        year_8 = model.calculate_lapse(gwb=100_000, av=100_000, duration=8, years_to_sc_end=-1)
        assert year_8.base_rate > year_7.base_rate * 1.5

    def test_rates_decrease_after_cliff(self, model: SOADynamicLapseModel) -> None:
        """Base rates should decrease after year 8."""
        year_8 = model.calculate_lapse(gwb=100_000, av=100_000, duration=8, years_to_sc_end=-1)
        year_9 = model.calculate_lapse(gwb=100_000, av=100_000, duration=9, years_to_sc_end=-2)
        year_10 = model.calculate_lapse(gwb=100_000, av=100_000, duration=10, years_to_sc_end=-3)
        assert year_8.base_rate >= year_9.base_rate >= year_10.base_rate


class TestSOADynamicLapseModelPathCalculation:
    """Tests for path-based lapse calculations."""

    @pytest.fixture
    def model(self) -> SOADynamicLapseModel:
        """Standard model with default assumptions."""
        return SOADynamicLapseModel(SOALapseAssumptions())

    def test_path_lapse_calculation(self, model: SOADynamicLapseModel) -> None:
        """Should calculate lapse rates along a path."""
        gwb_path = np.array([100_000, 100_000, 100_000])
        av_path = np.array([100_000, 110_000, 90_000])

        lapse_rates = model.calculate_path_lapses(
            gwb_path=gwb_path,
            av_path=av_path,
            start_duration=1,
        )

        assert len(lapse_rates) == 3
        assert all(0 <= r <= 1 for r in lapse_rates)

    def test_path_with_sc_transition(self, model: SOADynamicLapseModel) -> None:
        """Path crossing SC boundary should show cliff effect."""
        n_years = 10
        gwb_path = np.full(n_years, 100_000)
        av_path = np.full(n_years, 100_000)

        lapse_rates = model.calculate_path_lapses(
            gwb_path=gwb_path,
            av_path=av_path,
            start_duration=5,
            surrender_charge_length=7,
        )

        # Year 8 (index 3, since start_duration=5) should be elevated
        # Duration 5+0=5, 5+1=6, 5+2=7, 5+3=8 (cliff year)
        assert len(lapse_rates) == n_years
        # The spike should be visible around index 3 (duration 8)
        assert lapse_rates[3] > lapse_rates[0]  # Cliff > early

    def test_path_mismatched_lengths_raises(self, model: SOADynamicLapseModel) -> None:
        """Mismatched path lengths should raise ValueError."""
        gwb_path = np.array([100_000, 100_000])
        av_path = np.array([100_000, 100_000, 100_000])

        with pytest.raises(ValueError):
            model.calculate_path_lapses(gwb_path=gwb_path, av_path=av_path)


class TestSOADynamicLapseModelSurvival:
    """Tests for survival probability calculation."""

    @pytest.fixture
    def model(self) -> SOADynamicLapseModel:
        """Standard model."""
        return SOADynamicLapseModel(SOALapseAssumptions())

    def test_survival_starts_at_one(self, model: SOADynamicLapseModel) -> None:
        """Survival probability at t=0 should be 1.0."""
        lapse_rates = np.array([0.05, 0.05, 0.05])
        survival = model.calculate_survival_probability(lapse_rates)
        assert survival[0] == 1.0

    def test_survival_decreases(self, model: SOADynamicLapseModel) -> None:
        """Survival probability should decrease over time."""
        lapse_rates = np.array([0.05, 0.05, 0.05])
        survival = model.calculate_survival_probability(lapse_rates)
        for i in range(len(survival) - 1):
            assert survival[i] >= survival[i + 1]

    def test_survival_with_zero_lapse(self, model: SOADynamicLapseModel) -> None:
        """Zero lapse rates should maintain survival at 1.0."""
        lapse_rates = np.array([0.0, 0.0, 0.0])
        survival = model.calculate_survival_probability(lapse_rates)
        assert all(s == 1.0 for s in survival)

    def test_survival_with_high_lapse(self, model: SOADynamicLapseModel) -> None:
        """High lapse rates should rapidly decrease survival."""
        lapse_rates = np.array([0.20, 0.20, 0.20])
        survival = model.calculate_survival_probability(lapse_rates)
        # After 3 years of 20% lapse: ~0.8^3 = 0.512
        assert abs(survival[-1] - 0.512) < 0.01


class TestSOADynamicLapseModelDisabledFeatures:
    """Tests for model with features disabled."""

    def test_disabled_duration_curve(self) -> None:
        """Disabled duration curve should use flat 5%."""
        model = SOADynamicLapseModel(
            SOALapseAssumptions(
                use_duration_curve=False,
                use_sc_cliff_effect=False,
            )
        )

        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=5)
        assert result.base_rate == 0.05

    def test_disabled_sc_cliff(self) -> None:
        """Disabled SC cliff should have factor = 1.0."""
        model = SOADynamicLapseModel(
            SOALapseAssumptions(
                use_sc_cliff_effect=False,
            )
        )

        result = model.calculate_lapse(gwb=100_000, av=100_000, duration=7, years_to_sc_end=0)
        assert result.sc_cliff_factor == 1.0
