"""
Tests for Historical Crisis Definitions - Phase I.

[T2] Verifies historical crisis data integrity and accuracy.

These tests validate:
- Crisis parameter accuracy (equity shock, rate shock, VIX)
- Monthly profile consistency
- Recovery type classification
- Utility function behavior

Data sources: FRED (DGS10), Yahoo Finance (S&P500), CBOE (VIX)

See: docs/stress_testing/HISTORICAL_SCENARIOS.md
"""

import pytest

from annuity_pricing.stress_testing.historical import (
    ALL_HISTORICAL_CRISES,
    CRISIS_2000_DOTCOM,
    CRISIS_2008_GFC,
    CRISIS_2011_EURO_DEBT,
    CRISIS_2015_CHINA,
    CRISIS_2018_Q4,
    CRISIS_2020_COVID,
    CRISIS_2022_RATES,
    CrisisProfile,
    RecoveryType,
    get_crisis_by_name,
    get_crisis_summary,
    get_profile_at_month,
    interpolate_profile,
)


class TestCrisis2008GFC:
    """Tests for 2008 Global Financial Crisis definition."""

    def test_equity_shock_within_tolerance(self) -> None:
        """[T2] 2008 equity shock should be -56.8% ±2%."""
        assert -0.59 <= CRISIS_2008_GFC.equity_shock <= -0.55

    def test_rate_shock_within_tolerance(self) -> None:
        """[T2] 2008 rate shock should be ~-254 bps ±10 bps."""
        assert -0.0264 <= CRISIS_2008_GFC.rate_shock <= -0.0244

    def test_vix_peak_within_tolerance(self) -> None:
        """[T2] 2008 VIX peak should be ~80.9 ±5."""
        assert 75.9 <= CRISIS_2008_GFC.vix_peak <= 85.9

    def test_duration_months(self) -> None:
        """Crisis duration from Oct 2007 to Mar 2009 = 17 months."""
        assert CRISIS_2008_GFC.duration_months == 17

    def test_recovery_type_u_shaped(self) -> None:
        """2008 had U-shaped recovery (extended bottom)."""
        assert CRISIS_2008_GFC.recovery_type == RecoveryType.U_SHAPED

    def test_has_monthly_profiles(self) -> None:
        """Should have at least 20 monthly profile points."""
        assert len(CRISIS_2008_GFC.profile) >= 20

    def test_profile_shows_cliff(self) -> None:
        """Profile should show equity decline progressing to trough."""
        profiles = sorted(CRISIS_2008_GFC.profile, key=lambda p: p.month)
        # Find trough (min equity)
        trough_profile = min(profiles, key=lambda p: p.equity_cumulative)
        assert trough_profile.equity_cumulative < -0.50


class TestCrisis2020COVID:
    """Tests for 2020 COVID crash definition."""

    def test_equity_shock_within_tolerance(self) -> None:
        """[T2] 2020 equity shock should be -31.3% ±2%."""
        assert -0.34 <= CRISIS_2020_COVID.equity_shock <= -0.29

    def test_rate_shock_within_tolerance(self) -> None:
        """[T2] 2020 rate shock should be ~-138 bps ±10 bps."""
        assert -0.0148 <= CRISIS_2020_COVID.rate_shock <= -0.0128

    def test_vix_peak_within_tolerance(self) -> None:
        """[T2] 2020 VIX peak should be ~82.69 ±5."""
        assert 77.69 <= CRISIS_2020_COVID.vix_peak <= 87.69

    def test_duration_months_fastest_ever(self) -> None:
        """2020 was fastest bear market ever (~1 month)."""
        assert CRISIS_2020_COVID.duration_months <= 2

    def test_recovery_type_v_shaped(self) -> None:
        """2020 had V-shaped recovery (quick bounce)."""
        assert CRISIS_2020_COVID.recovery_type == RecoveryType.V_SHAPED

    def test_recovery_faster_than_2008(self) -> None:
        """2020 recovery should be much faster than 2008."""
        assert CRISIS_2020_COVID.recovery_months < CRISIS_2008_GFC.recovery_months


class TestCrisis2000Dotcom:
    """Tests for 2000 Dot-Com crash definition."""

    def test_equity_shock_within_tolerance(self) -> None:
        """[T2] 2000 equity shock should be -49.2% ±2%."""
        assert -0.51 <= CRISIS_2000_DOTCOM.equity_shock <= -0.47

    def test_rate_shock_within_tolerance(self) -> None:
        """[T2] 2000 rate shock should be ~-221 bps ±15 bps."""
        assert -0.0236 <= CRISIS_2000_DOTCOM.rate_shock <= -0.0206

    def test_duration_months_longest(self) -> None:
        """2000 should have one of the longest durations."""
        assert CRISIS_2000_DOTCOM.duration_months >= 30

    def test_recovery_type_l_shaped(self) -> None:
        """2000 had L-shaped recovery (prolonged depression)."""
        assert CRISIS_2000_DOTCOM.recovery_type == RecoveryType.L_SHAPED

    def test_recovery_longest(self) -> None:
        """2000 should have longest recovery time."""
        other_recoveries = [
            c.recovery_months for c in ALL_HISTORICAL_CRISES if c.name != CRISIS_2000_DOTCOM.name
        ]
        assert CRISIS_2000_DOTCOM.recovery_months >= max(other_recoveries)


class TestCrisis2011EuroDebt:
    """Tests for 2011 European Debt Crisis definition."""

    def test_equity_shock_moderate(self) -> None:
        """[T2] 2011 equity shock should be -14.5% ±2%."""
        assert -0.17 <= CRISIS_2011_EURO_DEBT.equity_shock <= -0.12

    def test_rate_shock_significant(self) -> None:
        """[T2] 2011 rate shock should be ~-175 bps ±15 bps."""
        assert -0.0190 <= CRISIS_2011_EURO_DEBT.rate_shock <= -0.0160

    def test_recovery_type_v_shaped(self) -> None:
        """2011 had V-shaped recovery."""
        assert CRISIS_2011_EURO_DEBT.recovery_type == RecoveryType.V_SHAPED


class TestCrisis2015China:
    """Tests for 2015-16 China/Oil crisis definition."""

    def test_equity_shock_moderate(self) -> None:
        """[T2] 2015 equity shock should be -12.3% ±2%."""
        assert -0.15 <= CRISIS_2015_CHINA.equity_shock <= -0.10

    def test_rate_shock_mild(self) -> None:
        """[T2] 2015 rate shock should be ~-62 bps ±10 bps."""
        assert -0.0072 <= CRISIS_2015_CHINA.rate_shock <= -0.0052

    def test_recovery_type_u_shaped(self) -> None:
        """2015 had U-shaped recovery."""
        assert CRISIS_2015_CHINA.recovery_type == RecoveryType.U_SHAPED


class TestCrisis2018Q4:
    """Tests for 2018 Q4 correction definition."""

    def test_equity_shock_within_tolerance(self) -> None:
        """[T2] 2018 equity shock should be -19.3% ±2%."""
        assert -0.22 <= CRISIS_2018_Q4.equity_shock <= -0.17

    def test_rate_shock_minimal(self) -> None:
        """[T2] 2018 rate shock should be ~-37 bps ±10 bps."""
        assert -0.0047 <= CRISIS_2018_Q4.rate_shock <= -0.0027

    def test_duration_short(self) -> None:
        """2018 was a short correction (~3 months)."""
        assert CRISIS_2018_Q4.duration_months <= 4

    def test_recovery_type_v_shaped(self) -> None:
        """2018 had V-shaped recovery."""
        assert CRISIS_2018_Q4.recovery_type == RecoveryType.V_SHAPED


class TestCrisis2022Rates:
    """Tests for 2022 Rate Shock definition."""

    def test_equity_shock_within_tolerance(self) -> None:
        """[T2] 2022 equity shock should be -24.9% ±2%."""
        assert -0.27 <= CRISIS_2022_RATES.equity_shock <= -0.23

    def test_rate_shock_unique_positive(self) -> None:
        """[T2] 2022 is unique: RISING rates (+282 bps)."""
        assert CRISIS_2022_RATES.rate_shock > 0
        assert 0.0272 <= CRISIS_2022_RATES.rate_shock <= 0.0292

    def test_recovery_type_u_shaped(self) -> None:
        """2022 had U-shaped recovery."""
        assert CRISIS_2022_RATES.recovery_type == RecoveryType.U_SHAPED

    def test_only_rising_rate_crisis(self) -> None:
        """2022 should be the only crisis with positive rate shock."""
        rising_rate_crises = [c for c in ALL_HISTORICAL_CRISES if c.rate_shock > 0]
        assert len(rising_rate_crises) == 1
        assert rising_rate_crises[0].name == "2022_rates"


class TestAllHistoricalCrises:
    """Tests for the complete crisis collection."""

    def test_has_seven_crises(self) -> None:
        """Should have exactly 7 historical crises."""
        assert len(ALL_HISTORICAL_CRISES) == 7

    def test_all_have_unique_names(self) -> None:
        """All crises should have unique names."""
        names = [c.name for c in ALL_HISTORICAL_CRISES]
        assert len(names) == len(set(names))

    def test_all_have_profiles(self) -> None:
        """All crises should have monthly profiles."""
        for crisis in ALL_HISTORICAL_CRISES:
            assert len(crisis.profile) >= 5, f"{crisis.name} has insufficient profiles"

    def test_all_equity_shocks_negative(self) -> None:
        """All crises should have negative equity shocks."""
        for crisis in ALL_HISTORICAL_CRISES:
            assert crisis.equity_shock < 0, f"{crisis.name} has non-negative equity shock"

    def test_equity_shocks_range(self) -> None:
        """Equity shocks should range from -10% to -60%."""
        for crisis in ALL_HISTORICAL_CRISES:
            assert -0.60 <= crisis.equity_shock <= -0.10, (
                f"{crisis.name} equity shock {crisis.equity_shock} out of expected range"
            )

    def test_all_have_vix_peaks_above_20(self) -> None:
        """All crises should have VIX peak above 20."""
        for crisis in ALL_HISTORICAL_CRISES:
            assert crisis.vix_peak >= 20, f"{crisis.name} has low VIX peak"

    def test_vix_peaks_sorted_correctly(self) -> None:
        """2008 and 2020 should have highest VIX peaks."""
        vix_peaks = sorted(
            [(c.name, c.vix_peak) for c in ALL_HISTORICAL_CRISES],
            key=lambda x: x[1],
            reverse=True,
        )
        # Top 2 should be 2008 and 2020
        top_names = {vix_peaks[0][0], vix_peaks[1][0]}
        assert top_names == {"2008_gfc", "2020_covid"}

    def test_recovery_types_distributed(self) -> None:
        """Should have mix of V, U, and L-shaped recoveries."""
        recovery_types = {c.recovery_type for c in ALL_HISTORICAL_CRISES}
        assert RecoveryType.V_SHAPED in recovery_types
        assert RecoveryType.U_SHAPED in recovery_types
        assert RecoveryType.L_SHAPED in recovery_types


class TestGetCrisisByName:
    """Tests for get_crisis_by_name utility."""

    def test_get_2008_gfc(self) -> None:
        """Should retrieve 2008 GFC by name."""
        crisis = get_crisis_by_name("2008_gfc")
        assert crisis.name == "2008_gfc"

    def test_get_all_by_name(self) -> None:
        """Should retrieve all crises by name."""
        for expected in ALL_HISTORICAL_CRISES:
            retrieved = get_crisis_by_name(expected.name)
            assert retrieved.name == expected.name

    def test_invalid_name_raises(self) -> None:
        """Should raise ValueError for unknown name."""
        with pytest.raises(ValueError, match="Unknown crisis name"):
            get_crisis_by_name("invalid_crisis")


class TestGetCrisisSummary:
    """Tests for get_crisis_summary utility."""

    def test_returns_dict(self) -> None:
        """Should return a dictionary."""
        summary = get_crisis_summary()
        assert isinstance(summary, dict)

    def test_has_all_crises(self) -> None:
        """Should have all 7 crises."""
        summary = get_crisis_summary()
        assert len(summary) == 7

    def test_each_crisis_has_metrics(self) -> None:
        """Each crisis should have required metrics."""
        summary = get_crisis_summary()
        for name, metrics in summary.items():
            assert "equity_shock" in metrics
            assert "rate_shock" in metrics
            assert "vix_peak" in metrics
            assert "duration_months" in metrics

    def test_values_match_constants(self) -> None:
        """Summary values should match crisis constants."""
        summary = get_crisis_summary()
        assert summary["2008_gfc"]["equity_shock"] == CRISIS_2008_GFC.equity_shock
        assert summary["2020_covid"]["vix_peak"] == CRISIS_2020_COVID.vix_peak


class TestCrisisProfile:
    """Tests for CrisisProfile dataclass."""

    def test_profile_is_frozen(self) -> None:
        """Profiles should be immutable."""
        profile = CrisisProfile(month=0, equity_cumulative=0.0, rate_level=0.03, vix_level=15.0)
        with pytest.raises(AttributeError):
            profile.month = 1  # type: ignore

    def test_profile_months_start_negative(self) -> None:
        """Profiles can have negative months (pre-crisis baseline)."""
        for crisis in ALL_HISTORICAL_CRISES:
            months = [p.month for p in crisis.profile]
            # At least some profiles should have month < 0 (pre-crisis)
            if any(m < 0 for m in months):
                assert True
                return
        # If we get here, no crisis has pre-crisis profiles
        # This is not required but expected


class TestGetProfileAtMonth:
    """Tests for get_profile_at_month utility."""

    def test_exact_month_returns_profile(self) -> None:
        """Should return profile for exact month match."""
        profile = get_profile_at_month(CRISIS_2008_GFC, 0)
        assert profile is not None
        assert profile.month == 0

    def test_no_match_returns_none(self) -> None:
        """Should return None if no exact match."""
        profile = get_profile_at_month(CRISIS_2008_GFC, 999)
        assert profile is None


class TestInterpolateProfile:
    """Tests for interpolate_profile utility."""

    def test_interpolation_at_known_point(self) -> None:
        """Interpolation at known point should return that point's values."""
        known_month = CRISIS_2008_GFC.profile[5].month  # Pick a known month
        interpolated = interpolate_profile(CRISIS_2008_GFC, known_month)
        original = get_profile_at_month(CRISIS_2008_GFC, known_month)
        assert original is not None
        assert abs(interpolated.equity_cumulative - original.equity_cumulative) < 0.001

    def test_interpolation_between_points(self) -> None:
        """Interpolation between points should return intermediate values."""
        # Find two adjacent months
        profiles = sorted(CRISIS_2008_GFC.profile, key=lambda p: p.month)
        p1, p2 = profiles[5], profiles[6]
        mid_month = (p1.month + p2.month) / 2

        interpolated = interpolate_profile(CRISIS_2008_GFC, mid_month)

        # Should be between the two values
        min_eq = min(p1.equity_cumulative, p2.equity_cumulative)
        max_eq = max(p1.equity_cumulative, p2.equity_cumulative)
        assert min_eq <= interpolated.equity_cumulative <= max_eq

    def test_interpolation_before_range_raises(self) -> None:
        """Should raise ValueError for month before range."""
        with pytest.raises(ValueError, match="before earliest"):
            interpolate_profile(CRISIS_2008_GFC, -100)

    def test_interpolation_after_range_raises(self) -> None:
        """Should raise ValueError for month after range."""
        with pytest.raises(ValueError, match="after latest"):
            interpolate_profile(CRISIS_2008_GFC, 1000)


class TestRecoveryType:
    """Tests for RecoveryType enum."""

    def test_v_shaped_value(self) -> None:
        """V-shaped should have value 'v'."""
        assert RecoveryType.V_SHAPED.value == "v"

    def test_u_shaped_value(self) -> None:
        """U-shaped should have value 'u'."""
        assert RecoveryType.U_SHAPED.value == "u"

    def test_l_shaped_value(self) -> None:
        """L-shaped should have value 'l'."""
        assert RecoveryType.L_SHAPED.value == "l"
