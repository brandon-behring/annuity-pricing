"""
Tests for SOA Benchmark Data - Phase H.

[T2] Verifies extracted SOA data integrity.

See: docs/assumptions/BEHAVIOR_CALIBRATION.md
"""

from annuity_pricing.behavioral.soa_benchmarks import (
    DATA_QUALITY_NOTES,
    SOA_2006_FULL_SURRENDER_BY_AGE,
    SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE,
    SOA_2006_POST_SC_DECAY,
    SOA_2006_SC_CLIFF_EFFECT,
    SOA_2006_SC_CLIFF_MULTIPLIER,
    SOA_2006_SURRENDER_BY_DURATION_7YR_SC,
    SOA_2018_GLWB_UTILIZATION_BY_AGE,
    SOA_2018_GLWB_UTILIZATION_BY_DURATION,
    SOA_2018_ITM_SENSITIVITY,
    SOA_2018_ITM_VS_NOT_ITM_BY_AGE,
    SOA_KEY_INSIGHTS,
)


class TestSOA2006SurrenderByDuration:
    """Tests for SOA 2006 Table 6 data."""

    def test_has_all_duration_years(self) -> None:
        """Table should have years 1-11."""
        for year in range(1, 12):
            assert year in SOA_2006_SURRENDER_BY_DURATION_7YR_SC

    def test_year_1_rate_matches_soa(self) -> None:
        """[T2] Year 1 surrender rate should be 1.4%."""
        assert SOA_2006_SURRENDER_BY_DURATION_7YR_SC[1] == 0.014

    def test_year_8_cliff_rate_matches_soa(self) -> None:
        """[T2] Year 8 (post-SC) should be 11.2%."""
        assert SOA_2006_SURRENDER_BY_DURATION_7YR_SC[8] == 0.112

    def test_rates_increase_during_sc_period(self) -> None:
        """Rates should generally increase during years 1-7."""
        for year in range(1, 7):
            assert (
                SOA_2006_SURRENDER_BY_DURATION_7YR_SC[year]
                <= SOA_2006_SURRENDER_BY_DURATION_7YR_SC[year + 1]
            )

    def test_cliff_at_year_8(self) -> None:
        """Year 8 should be significantly higher than year 7 (cliff)."""
        year_7 = SOA_2006_SURRENDER_BY_DURATION_7YR_SC[7]
        year_8 = SOA_2006_SURRENDER_BY_DURATION_7YR_SC[8]
        # At least 2x jump
        assert year_8 / year_7 > 2.0

    def test_rates_decrease_after_cliff(self) -> None:
        """Rates should decrease from year 8 to year 11."""
        for year in range(8, 11):
            assert (
                SOA_2006_SURRENDER_BY_DURATION_7YR_SC[year]
                >= SOA_2006_SURRENDER_BY_DURATION_7YR_SC[year + 1]
            )

    def test_all_rates_between_0_and_1(self) -> None:
        """All rates should be valid decimals."""
        for rate in SOA_2006_SURRENDER_BY_DURATION_7YR_SC.values():
            assert 0 < rate < 1


class TestSOA2006SCCliffEffect:
    """Tests for SOA 2006 Table 5 cliff effect data."""

    def test_has_all_periods(self) -> None:
        """Table should have all time periods."""
        expected_keys = {
            "years_remaining_3plus",
            "years_remaining_2",
            "years_remaining_1",
            "at_expiration",
            "post_sc_year_1",
            "post_sc_year_2",
            "post_sc_year_3plus",
        }
        assert set(SOA_2006_SC_CLIFF_EFFECT.keys()) == expected_keys

    def test_cliff_rate_matches_soa(self) -> None:
        """[T2] At expiration rate should be 14.4%."""
        assert SOA_2006_SC_CLIFF_EFFECT["at_expiration"] == 0.144

    def test_pre_cliff_rate_matches_soa(self) -> None:
        """[T2] Year remaining 1 rate should be 5.8%."""
        assert SOA_2006_SC_CLIFF_EFFECT["years_remaining_1"] == 0.058

    def test_cliff_multiplier_calculation(self) -> None:
        """Cliff multiplier should be ~2.48x."""
        assert abs(SOA_2006_SC_CLIFF_MULTIPLIER - 2.48) < 0.1

    def test_rates_increase_toward_cliff(self) -> None:
        """Rates should increase as SC approaches expiration."""
        assert (
            SOA_2006_SC_CLIFF_EFFECT["years_remaining_3plus"]
            < SOA_2006_SC_CLIFF_EFFECT["years_remaining_2"]
        )
        assert (
            SOA_2006_SC_CLIFF_EFFECT["years_remaining_2"]
            < SOA_2006_SC_CLIFF_EFFECT["years_remaining_1"]
        )
        assert (
            SOA_2006_SC_CLIFF_EFFECT["years_remaining_1"]
            < SOA_2006_SC_CLIFF_EFFECT["at_expiration"]
        )


class TestSOA2006SurrenderByAge:
    """Tests for SOA 2006 Table 8 age-based data."""

    def test_full_surrender_has_multiple_ages(self) -> None:
        """Should have data for multiple age groups."""
        assert len(SOA_2006_FULL_SURRENDER_BY_AGE) >= 5

    def test_full_surrender_relatively_flat(self) -> None:
        """[T2] Full surrender should be relatively flat by age (~5%)."""
        rates = list(SOA_2006_FULL_SURRENDER_BY_AGE.values())
        # All should be between 4% and 7%
        for rate in rates:
            assert 0.04 <= rate <= 0.07

    def test_partial_withdrawal_increases_with_age(self) -> None:
        """[T2] Partial withdrawal increases dramatically with age."""
        young_rate = SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE[35]
        peak_rate = SOA_2006_PARTIAL_WITHDRAWAL_BY_AGE[72]
        # Should increase significantly (RMD effect)
        assert peak_rate > young_rate * 5  # At least 5x increase


class TestSOA2018GLWBUtilization:
    """Tests for SOA 2018 utilization data."""

    def test_duration_utilization_has_years_1_to_11(self) -> None:
        """Should have data for years 1-11."""
        for year in range(1, 12):
            assert year in SOA_2018_GLWB_UTILIZATION_BY_DURATION

    def test_year_1_utilization_matches_soa(self) -> None:
        """[T2] Year 1 utilization should be 11.1%."""
        assert SOA_2018_GLWB_UTILIZATION_BY_DURATION[1] == 0.111

    def test_year_10_utilization_matches_soa(self) -> None:
        """[T2] Year 10 utilization should be ~51.8%."""
        assert abs(SOA_2018_GLWB_UTILIZATION_BY_DURATION[10] - 0.518) < 0.01

    def test_utilization_generally_increases_with_duration(self) -> None:
        """Utilization should generally increase over time."""
        year_1 = SOA_2018_GLWB_UTILIZATION_BY_DURATION[1]
        year_10 = SOA_2018_GLWB_UTILIZATION_BY_DURATION[10]
        assert year_10 > year_1 * 3  # At least 3x increase

    def test_age_utilization_has_multiple_ages(self) -> None:
        """Should have data for multiple age groups."""
        assert len(SOA_2018_GLWB_UTILIZATION_BY_AGE) >= 5

    def test_age_72_utilization_matches_soa(self) -> None:
        """[T2] Age 72 utilization should be ~59%."""
        assert abs(SOA_2018_GLWB_UTILIZATION_BY_AGE[72] - 0.59) < 0.01


class TestSOA2018ITMSensitivity:
    """Tests for SOA 2018 ITM sensitivity data."""

    def test_has_all_itm_buckets(self) -> None:
        """Should have all ITM sensitivity buckets."""
        expected_keys = {"not_itm", "itm_100_125", "itm_125_150", "itm_150_plus"}
        assert set(SOA_2018_ITM_SENSITIVITY.keys()) == expected_keys

    def test_not_itm_baseline_is_1(self) -> None:
        """Not-ITM should be baseline (1.0)."""
        assert SOA_2018_ITM_SENSITIVITY["not_itm"] == 1.0

    def test_deep_itm_sensitivity_matches_soa(self) -> None:
        """[T2] Deep ITM (>150%) sensitivity should be ~2.11x."""
        assert abs(SOA_2018_ITM_SENSITIVITY["itm_150_plus"] - 2.11) < 0.05

    def test_itm_sensitivity_increases_with_depth(self) -> None:
        """Sensitivity should increase with ITM depth."""
        assert SOA_2018_ITM_SENSITIVITY["not_itm"] < SOA_2018_ITM_SENSITIVITY["itm_100_125"]
        assert SOA_2018_ITM_SENSITIVITY["itm_100_125"] < SOA_2018_ITM_SENSITIVITY["itm_125_150"]
        assert SOA_2018_ITM_SENSITIVITY["itm_125_150"] < SOA_2018_ITM_SENSITIVITY["itm_150_plus"]


class TestSOA2018ITMByAge:
    """Tests for SOA 2018 Figure 1-43 ITM by age data."""

    def test_has_multiple_age_groups(self) -> None:
        """Should have data for multiple age groups."""
        assert len(SOA_2018_ITM_VS_NOT_ITM_BY_AGE) >= 5

    def test_each_age_has_itm_and_not_itm(self) -> None:
        """Each age group should have both ITM and not-ITM rates."""
        for age, data in SOA_2018_ITM_VS_NOT_ITM_BY_AGE.items():
            assert "itm" in data
            assert "not_itm" in data

    def test_older_ages_have_higher_rates(self) -> None:
        """Older ages should generally have higher withdrawal rates."""
        young_itm = SOA_2018_ITM_VS_NOT_ITM_BY_AGE[52]["itm"]
        old_itm = SOA_2018_ITM_VS_NOT_ITM_BY_AGE[82]["itm"]
        assert old_itm > young_itm * 5


class TestSOAPostSCDecay:
    """Tests for post-SC decay factors."""

    def test_has_years_0_to_3(self) -> None:
        """Should have decay factors for years 0-3."""
        for year in range(4):
            assert year in SOA_2006_POST_SC_DECAY

    def test_year_0_is_baseline(self) -> None:
        """Year 0 (cliff) should be 1.0."""
        assert SOA_2006_POST_SC_DECAY[0] == 1.0

    def test_decay_decreases_over_time(self) -> None:
        """Decay factors should decrease after cliff."""
        assert SOA_2006_POST_SC_DECAY[0] > SOA_2006_POST_SC_DECAY[1]
        assert SOA_2006_POST_SC_DECAY[1] > SOA_2006_POST_SC_DECAY[2]
        assert SOA_2006_POST_SC_DECAY[2] > SOA_2006_POST_SC_DECAY[3]


class TestKeyInsightsAndNotes:
    """Tests for documentation strings."""

    def test_key_insights_not_empty(self) -> None:
        """Should have documented key insights."""
        assert len(SOA_KEY_INSIGHTS) >= 3

    def test_data_quality_notes_not_empty(self) -> None:
        """Should have documented data quality notes."""
        assert len(DATA_QUALITY_NOTES) >= 3

    def test_insights_contain_key_findings(self) -> None:
        """Insights should mention key findings."""
        insights_text = " ".join(SOA_KEY_INSIGHTS.values())
        # Check for surrender charge effect
        assert "sc" in insights_text.lower() or "surrender" in insights_text.lower()
        # Check for ITM mention
        assert "itm" in insights_text.lower() or "ITM" in insights_text
