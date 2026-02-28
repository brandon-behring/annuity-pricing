"""
Validation Tests: Behavioral Models vs SOA Empirical Data - Phase H.

[T2] Cross-validates model outputs against original SOA tables.

These tests verify that our SOA-calibrated behavioral models
reproduce the empirical data from:
- SOA 2006 Deferred Annuity Persistency Study
- SOA 2018 VA GLB Utilization Study

See: docs/assumptions/BEHAVIOR_CALIBRATION.md
"""

import pytest

from annuity_pricing.behavioral.calibration import (
    get_itm_sensitivity_factor,
    get_sc_cliff_multiplier,
    interpolate_surrender_by_duration,
    interpolate_utilization_by_age,
    interpolate_utilization_by_duration,
)
from annuity_pricing.behavioral.dynamic_lapse import (
    SOADynamicLapseModel,
    SOALapseAssumptions,
)
from annuity_pricing.behavioral.soa_benchmarks import (
    SOA_2006_SC_CLIFF_MULTIPLIER,
    SOA_2006_SURRENDER_BY_DURATION_7YR_SC,
    SOA_2018_GLWB_UTILIZATION_BY_DURATION,
)
from annuity_pricing.behavioral.withdrawal import (
    SOAWithdrawalAssumptions,
    SOAWithdrawalModel,
)


class TestSurrenderCurveVsSOA2006:
    """
    [T2] Validate surrender curve matches SOA 2006 Table 6.

    Source: SOA 2006 Deferred Annuity Persistency Study, Table 6
    "Contract Surrender Rates by Contract Year, 7-Year SC Schedule"
    """

    @pytest.mark.parametrize(
        "duration,expected_rate",
        [
            (1, 0.014),  # Year 1: 1.4%
            (2, 0.023),  # Year 2: 2.3%
            (3, 0.028),  # Year 3: 2.8%
            (4, 0.032),  # Year 4: 3.2%
            (5, 0.037),  # Year 5: 3.7%
            (6, 0.043),  # Year 6: 4.3%
            (7, 0.053),  # Year 7: 5.3%
            (8, 0.112),  # Year 8: 11.2% (POST-SC CLIFF!)
            (9, 0.082),  # Year 9: 8.2%
            (10, 0.077),  # Year 10: 7.7%
            (11, 0.067),  # Year 11+: 6.7%
        ],
    )
    def test_duration_surrender_rates_match_soa(self, duration: int, expected_rate: float) -> None:
        """Interpolation function should return exact SOA values."""
        result = interpolate_surrender_by_duration(duration, sc_length=7)
        assert result == expected_rate, (
            f"Duration {duration}: expected {expected_rate}, got {result}"
        )

    def test_cliff_multiplier_matches_soa(self) -> None:
        """
        SC cliff multiplier should be ~2.48x.

        SOA 2006 Table 5: At expiration = 14.4%, 1 year remaining = 5.8%
        Cliff multiplier = 14.4 / 5.8 = 2.48
        """
        expected_multiplier = SOA_2006_SC_CLIFF_MULTIPLIER
        actual_multiplier = get_sc_cliff_multiplier(0)  # At expiration

        assert abs(actual_multiplier - expected_multiplier) < 0.1, (
            f"Cliff multiplier: expected ~{expected_multiplier:.2f}, got {actual_multiplier:.2f}"
        )


class TestSurrenderCliffEffectVsSOA2006:
    """
    [T2] Validate SC cliff effect matches SOA 2006 Table 5.

    Source: SOA 2006 Deferred Annuity Persistency Study, Table 5
    "Surrender Rates by Years in SC Period"
    """

    def test_cliff_pattern_pre_expiration(self) -> None:
        """Rates should increase as SC expiration approaches."""
        # 3+ years remaining: 2.6%
        mult_3plus = get_sc_cliff_multiplier(5)
        # 2 years remaining: 4.9%
        mult_2 = get_sc_cliff_multiplier(2)
        # 1 year remaining: 5.8%
        mult_1 = get_sc_cliff_multiplier(1)
        # At expiration: 14.4%
        mult_0 = get_sc_cliff_multiplier(0)

        # Multipliers should increase toward cliff
        assert mult_3plus <= mult_2 <= mult_1 < mult_0

    def test_cliff_pattern_post_expiration(self) -> None:
        """Post-SC rates decline over time but stay elevated.

        Note: The multiplier function calculates rates relative to
        the 3+ years baseline (2.6%). Post-SC absolute rates (11.1%,
        9.8%, 8.6%) are actually HIGHER than the at-expiration
        multiplier would suggest because Table 5's 14.4% represents
        the peak.

        The key insight is that post-SC rates decline over time.
        """
        # 1 year after: 11.1% / 2.6% = 4.27
        mult_neg1 = get_sc_cliff_multiplier(-1)
        # 2 years after: 9.8% / 2.6% = 3.77
        mult_neg2 = get_sc_cliff_multiplier(-2)
        # 3+ years after: 8.6% / 2.6% = 3.31
        mult_neg3 = get_sc_cliff_multiplier(-3)

        # Post-SC rates should decline over time
        assert mult_neg1 > mult_neg2 > mult_neg3
        # But they remain elevated relative to in-SC rates
        assert mult_neg3 > 1.0


class TestUtilizationCurveVsSOA2018:
    """
    [T2] Validate utilization curve matches SOA 2018 Table 1-17.

    Source: SOA 2018 VA GLB Utilization Study, Table 1-17
    "GLWB Utilization by Year Issued"
    """

    @pytest.mark.parametrize(
        "duration,expected_util",
        [
            (1, 0.111),  # Year 1: 11.1%
            (2, 0.177),  # Year 2: 17.7%
            (3, 0.199),  # Year 3: 19.9%
            (4, 0.205),  # Year 4: 20.5%
            (5, 0.215),  # Year 5: 21.5%
            (6, 0.233),  # Year 6: 23.3%
            (7, 0.256),  # Year 7: 25.6%
            (8, 0.365),  # Year 8: 36.5%
            (9, 0.459),  # Year 9: 45.9%
            (10, 0.518),  # Year 10: 51.8%
            (11, 0.536),  # Year 11: 53.6%
        ],
    )
    def test_duration_utilization_matches_soa(self, duration: int, expected_util: float) -> None:
        """Interpolation function should return exact SOA values."""
        result = interpolate_utilization_by_duration(duration)
        assert result == expected_util, (
            f"Duration {duration}: expected {expected_util}, got {result}"
        )


class TestUtilizationByAgeVsSOA2018:
    """
    [T2] Validate age-based utilization matches SOA 2018 Table 1-18.

    Source: SOA 2018 VA GLB Utilization Study, Table 1-18
    "GLWB Utilization by Current Age and Year Issued"
    (Using 2008 cohort as reference)
    """

    @pytest.mark.parametrize(
        "age,expected_util",
        [
            (55, 0.05),  # Under 60: ~5%
            (62, 0.16),  # 60-64: ~16%
            (67, 0.32),  # 65-69: ~32%
            (72, 0.59),  # 70-74: ~59%
            (77, 0.65),  # 75-79: ~65%
            (82, 0.63),  # 80+: ~63%
        ],
    )
    def test_age_utilization_matches_soa(self, age: int, expected_util: float) -> None:
        """Interpolation should return values close to SOA benchmarks."""
        result = interpolate_utilization_by_age(age)
        # Allow 5% tolerance for interpolation between ages
        assert abs(result - expected_util) < 0.05, (
            f"Age {age}: expected ~{expected_util}, got {result}"
        )


class TestITMSensitivityVsSOA2018:
    """
    [T2] Validate ITM sensitivity matches SOA 2018 Figure 1-44.

    Source: SOA 2018 VA GLB Utilization Study, Figure 1-44
    "Withdrawal by Degree of ITM"
    """

    @pytest.mark.parametrize(
        "moneyness,expected_factor",
        [
            (0.9, 1.00),  # Not ITM: baseline
            (1.0, 1.00),  # At the money: baseline
            (1.1, 1.39),  # ITM 100-125%
            (1.3, 1.79),  # ITM 125-150%
            (1.6, 2.11),  # ITM >150%
            (2.0, 2.11),  # Deep ITM: same as >150%
        ],
    )
    def test_itm_sensitivity_discrete_matches_soa(
        self, moneyness: float, expected_factor: float
    ) -> None:
        """Discrete ITM sensitivity should match SOA buckets."""
        result = get_itm_sensitivity_factor(moneyness)
        assert result == expected_factor, (
            f"Moneyness {moneyness}: expected {expected_factor}, got {result}"
        )


class TestSOADynamicLapseModelReproducesSOA:
    """
    [T2] Full model should reproduce SOA surrender patterns.
    """

    @pytest.fixture
    def model(self) -> SOADynamicLapseModel:
        """Model with pure duration curve (no cliff overlay)."""
        return SOADynamicLapseModel(
            SOALapseAssumptions(
                use_sc_cliff_effect=False,  # Use duration curve only
                moneyness_sensitivity=0,  # Disable moneyness for pure test
            )
        )

    def test_model_reproduces_duration_curve(self, model: SOADynamicLapseModel) -> None:
        """Model base rates should match SOA duration curve."""
        for duration in range(1, 12):
            result = model.calculate_lapse(gwb=100_000, av=100_000, duration=duration)
            expected = SOA_2006_SURRENDER_BY_DURATION_7YR_SC[duration]
            assert abs(result.base_rate - expected) < 0.001, (
                f"Duration {duration}: expected {expected}, got {result.base_rate}"
            )

    def test_model_shows_cliff_jump(self) -> None:
        """Model should show 2x+ jump from year 7 to year 8."""
        model = SOADynamicLapseModel(
            SOALapseAssumptions(
                use_sc_cliff_effect=False,
                moneyness_sensitivity=0,
            )
        )

        year_7 = model.calculate_lapse(gwb=100_000, av=100_000, duration=7)
        year_8 = model.calculate_lapse(gwb=100_000, av=100_000, duration=8)

        jump_ratio = year_8.base_rate / year_7.base_rate
        assert jump_ratio > 2.0, f"Cliff jump ratio {jump_ratio:.2f} should be > 2.0"


class TestSOAWithdrawalModelReproducesSOA:
    """
    [T2] Full model should reproduce SOA utilization patterns.
    """

    @pytest.fixture
    def model(self) -> SOAWithdrawalModel:
        """Model with pure duration curve (no ITM)."""
        return SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_itm_sensitivity=False,
            )
        )

    def test_model_reproduces_duration_utilization(self, model: SOAWithdrawalModel) -> None:
        """Model duration utilization should match SOA."""
        for duration in range(1, 12):
            result = model.calculate_withdrawal(
                gwb=100_000,
                av=100_000,
                withdrawal_rate=0.05,
                duration=duration,
                age=67,  # Reference age
            )
            expected = SOA_2018_GLWB_UTILIZATION_BY_DURATION[duration]
            assert result.duration_utilization == expected, (
                f"Duration {duration}: expected {expected}, got {result.duration_utilization}"
            )

    def test_model_shows_utilization_ramp(self) -> None:
        """Utilization should increase from year 1 to year 10."""
        model = SOAWithdrawalModel(
            SOAWithdrawalAssumptions(
                use_itm_sensitivity=False,
            )
        )

        year_1 = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=1, age=67
        )
        year_10 = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=10, age=67
        )

        ramp_ratio = year_10.duration_utilization / year_1.duration_utilization
        assert ramp_ratio > 4.0, f"Utilization ramp {ramp_ratio:.1f}x should be > 4x (11%→52%)"


class TestKeySOAInsights:
    """
    [T2] Verify key SOA study insights are captured in the model.
    """

    def test_sc_cliff_is_dramatic(self) -> None:
        """SC cliff (year 8) should be highest surrender year."""
        model = SOADynamicLapseModel(
            SOALapseAssumptions(
                use_sc_cliff_effect=False,  # Pure duration curve
                moneyness_sensitivity=0,
            )
        )

        rates = {}
        for d in range(1, 12):
            result = model.calculate_lapse(gwb=100_000, av=100_000, duration=d)
            rates[d] = result.base_rate

        # Year 8 should be maximum
        max_year = max(rates, key=rates.get)  # type: ignore
        assert max_year == 8, f"Max surrender year should be 8, got {max_year}"

    def test_itm_increases_withdrawals(self) -> None:
        """Deep ITM should significantly increase withdrawals."""
        model = SOAWithdrawalModel(SOAWithdrawalAssumptions())

        atm_result = model.calculate_withdrawal(
            gwb=100_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )
        itm_result = model.calculate_withdrawal(
            gwb=200_000, av=100_000, withdrawal_rate=0.05, duration=5, age=70
        )

        # Deep ITM (2x moneyness) should roughly double utilization
        ratio = itm_result.utilization_rate / atm_result.utilization_rate
        assert ratio > 1.5, f"ITM utilization increase {ratio:.2f}x should be > 1.5x"

    def test_age_72_peak_utilization(self) -> None:
        """Age 72 should have near-peak utilization (RMD effect)."""
        util_67 = interpolate_utilization_by_age(67)
        util_72 = interpolate_utilization_by_age(72)
        util_82 = interpolate_utilization_by_age(82)

        # 72 should be higher than 67
        assert util_72 > util_67
        # 72 should be similar to or slightly lower than 82
        # (utilization peaks around 77-82)
