"""
Unit tests for credit risk module.

Tests cover:
- AM Best rating to PD mapping (default_prob.py)
- State guaranty fund coverage (guaranty_funds.py)
- CVA calculation (cva.py)
"""

import numpy as np
import pytest

from annuity_pricing.credit import (
    AMBestRating,
    CVAResult,
    RatingPD,
    calculate_covered_amount,
    calculate_credit_adjusted_price,
    calculate_cva,
    get_annual_pd,
    get_cumulative_pd,
    get_state_coverage,
    rating_from_string,
)
from annuity_pricing.credit.cva import (
    DEFAULT_INSURANCE_LGD,
    calculate_credit_spread,
    calculate_cva_term_structure,
    calculate_exposure_profile,
)
from annuity_pricing.credit.default_prob import (
    AM_BEST_IMPAIRMENT_RATES,
    get_hazard_rate,
    get_pd_term_structure,
)
from annuity_pricing.credit.guaranty_funds import (
    CoverageType,
    calculate_uncovered_amount,
    get_coverage_ratio,
)

# =============================================================================
# Tests for default_prob.py
# =============================================================================


class TestAMBestRating:
    """Tests for AM Best rating enum and parsing."""

    def test_all_ratings_defined(self):
        """All expected AM Best ratings are in the enum."""
        expected = [
            "A++",
            "A+",
            "A",
            "A-",
            "B++",
            "B+",
            "B",
            "B-",
            "C++",
            "C+",
            "C",
            "C-",
            "D",
            "E",
            "F",
            "S",
        ]
        for rating_str in expected:
            rating = rating_from_string(rating_str)
            assert rating.value == rating_str

    def test_rating_from_string_case_insensitive(self):
        """Rating parsing is case-insensitive."""
        assert rating_from_string("a++") == AMBestRating.A_PLUS_PLUS
        assert rating_from_string("A++") == AMBestRating.A_PLUS_PLUS
        assert rating_from_string("  A++  ") == AMBestRating.A_PLUS_PLUS

    def test_rating_from_string_invalid(self):
        """Invalid rating strings raise ValueError."""
        with pytest.raises(ValueError, match="Unknown AM Best rating"):
            rating_from_string("AAA")
        with pytest.raises(ValueError, match="Unknown AM Best rating"):
            rating_from_string("XYZ")

    def test_all_ratings_have_impairment_data(self):
        """Every rating enum has corresponding impairment rate data."""
        for rating in AMBestRating:
            assert rating in AM_BEST_IMPAIRMENT_RATES
            pd_data = AM_BEST_IMPAIRMENT_RATES[rating]
            assert isinstance(pd_data, RatingPD)


class TestDefaultProbability:
    """Tests for probability of default calculations."""

    def test_annual_pd_ordering(self):
        """Higher (better) ratings have lower annual PD."""
        pd_a_plus_plus = get_annual_pd(AMBestRating.A_PLUS_PLUS)
        pd_a_plus = get_annual_pd(AMBestRating.A_PLUS)
        pd_a = get_annual_pd(AMBestRating.A)
        pd_b = get_annual_pd(AMBestRating.B)
        pd_c = get_annual_pd(AMBestRating.C)
        pd_d = get_annual_pd(AMBestRating.D)

        assert pd_a_plus_plus < pd_a_plus <= pd_a < pd_b < pd_c < pd_d

    def test_annual_pd_a_rated(self):
        """A-rated insurers have very low PD (~0.02%)."""
        pd = get_annual_pd(AMBestRating.A)
        assert 0.0001 <= pd <= 0.001  # 0.01% to 0.1%

    def test_annual_pd_b_minus(self):
        """B- rated insurers have higher PD (~1.35%)."""
        pd = get_annual_pd(AMBestRating.B_MINUS)
        assert 0.01 <= pd <= 0.02  # 1% to 2%

    def test_annual_pd_f_rating(self):
        """F rating (in liquidation) has 100% PD."""
        pd = get_annual_pd(AMBestRating.F)
        assert pd == 1.0

    def test_cumulative_pd_increases_with_time(self):
        """Cumulative PD increases with time horizon."""
        rating = AMBestRating.A
        pd_1 = get_cumulative_pd(rating, 1)
        pd_5 = get_cumulative_pd(rating, 5)
        pd_10 = get_cumulative_pd(rating, 10)
        pd_15 = get_cumulative_pd(rating, 15)

        assert pd_1 < pd_5 < pd_10 < pd_15

    def test_cumulative_pd_1_year_equals_annual(self):
        """1-year cumulative PD equals annual PD."""
        for rating in [AMBestRating.A, AMBestRating.B, AMBestRating.C]:
            assert get_cumulative_pd(rating, 1) == get_annual_pd(rating)

    def test_cumulative_pd_interpolation(self):
        """Cumulative PD interpolates smoothly."""
        rating = AMBestRating.A
        pd_data = AM_BEST_IMPAIRMENT_RATES[rating]

        # 5-year should match exactly
        assert get_cumulative_pd(rating, 5) == pd_data.pd_5yr

        # 3-year should be between 1-year and 5-year
        pd_3 = get_cumulative_pd(rating, 3)
        assert pd_data.annual_pd < pd_3 < pd_data.pd_5yr

    def test_cumulative_pd_extrapolation_capped(self):
        """Cumulative PD extrapolation doesn't exceed 100%."""
        # Even for bad ratings over long horizons
        pd_30 = get_cumulative_pd(AMBestRating.C, 30)
        assert pd_30 <= 1.0

    def test_cumulative_pd_invalid_years(self):
        """Invalid year values raise ValueError."""
        with pytest.raises(ValueError, match="years must be >= 1"):
            get_cumulative_pd(AMBestRating.A, 0)
        with pytest.raises(ValueError, match="years must be >= 1"):
            get_cumulative_pd(AMBestRating.A, -5)

    def test_hazard_rate_positive(self):
        """Hazard rates are positive for all non-default ratings."""
        for rating in AMBestRating:
            if rating != AMBestRating.F:
                h = get_hazard_rate(rating)
                assert h > 0

    def test_hazard_rate_relationship_to_pd(self):
        """Hazard rate approximates annual PD for small PD."""
        # For small PD: h ≈ PD
        rating = AMBestRating.A
        pd = get_annual_pd(rating)
        h = get_hazard_rate(rating)
        # Should be very close for small PD
        assert abs(h - pd) / pd < 0.01  # Within 1%

    def test_pd_term_structure_shape(self):
        """PD term structure has correct shape."""
        term_structure = get_pd_term_structure(AMBestRating.A, max_years=20)
        assert len(term_structure) == 20
        assert np.all(np.diff(term_structure) >= 0)  # Monotonically increasing


# =============================================================================
# Tests for guaranty_funds.py
# =============================================================================


class TestGuarantyFunds:
    """Tests for state guaranty fund coverage."""

    def test_standard_limits(self):
        """Standard NOLHGA limits are correct."""
        # Use a state without specific limits (falls back to standard)
        coverage = get_state_coverage("OH")  # Ohio uses standard limits
        assert coverage.annuity_deferred == 250_000
        assert coverage.annuity_payout == 300_000
        assert coverage.life_death_benefit == 300_000
        assert coverage.group_annuity == 5_000_000

    def test_california_80_percent(self):
        """California covers 80% of benefits."""
        coverage = get_state_coverage("CA")
        assert coverage.coverage_percentage == 0.80
        assert coverage.annuity_deferred == 250_000

    def test_new_york_higher_limits(self):
        """New York has higher annuity limits ($500k)."""
        coverage = get_state_coverage("NY")
        assert coverage.annuity_deferred == 500_000
        assert coverage.coverage_percentage == 1.0

    def test_state_code_case_insensitive(self):
        """State codes are case-insensitive."""
        ca1 = get_state_coverage("CA")
        ca2 = get_state_coverage("ca")
        ca3 = get_state_coverage("  CA  ")
        assert ca1 == ca2 == ca3

    def test_unknown_state_uses_standard(self):
        """Unknown states use standard limits."""
        coverage = get_state_coverage("ZZ")  # Fake state
        assert coverage.state == "ZZ"
        assert coverage.annuity_deferred == 250_000  # Standard limit


class TestCoverageCalculations:
    """Tests for coverage amount calculations."""

    def test_full_coverage_under_limit(self):
        """Amount under limit is fully covered (100% states)."""
        # $100k annuity in Texas (100% coverage, $250k limit)
        covered = calculate_covered_amount(100_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert covered == 100_000

    def test_partial_coverage_over_limit(self):
        """Amount over limit is partially covered."""
        # $500k annuity in Texas (100% coverage, $250k limit)
        covered = calculate_covered_amount(500_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert covered == 250_000

    def test_california_80_percent_coverage(self):
        """California applies 80% to covered amount."""
        # $300k annuity in CA (80% coverage, $250k limit)
        covered = calculate_covered_amount(300_000, "CA", CoverageType.ANNUITY_DEFERRED)
        # min(300k, 250k) * 80% = 250k * 0.8 = 200k
        assert covered == 200_000

    def test_california_under_limit(self):
        """California 80% applies even under limit."""
        # $100k annuity in CA
        covered = calculate_covered_amount(100_000, "CA", CoverageType.ANNUITY_DEFERRED)
        # min(100k, 250k) * 80% = 100k * 0.8 = 80k
        assert covered == 80_000

    def test_uncovered_amount(self):
        """Uncovered amount is total minus covered."""
        # $500k in Texas
        uncovered = calculate_uncovered_amount(500_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert uncovered == 250_000  # 500k - 250k limit

    def test_uncovered_amount_fully_covered(self):
        """Fully covered amount has zero uncovered."""
        uncovered = calculate_uncovered_amount(100_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert uncovered == 0

    def test_coverage_ratio_full(self):
        """Coverage ratio is 1.0 when fully covered."""
        ratio = get_coverage_ratio(100_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert ratio == 1.0

    def test_coverage_ratio_partial(self):
        """Coverage ratio reflects partial coverage."""
        # $500k in Texas with $250k limit
        ratio = get_coverage_ratio(500_000, "TX", CoverageType.ANNUITY_DEFERRED)
        assert ratio == 0.5  # 250k / 500k

    def test_coverage_ratio_zero_benefit(self):
        """Zero benefit returns zero ratio."""
        ratio = get_coverage_ratio(0, "TX", CoverageType.ANNUITY_DEFERRED)
        assert ratio == 0.0

    def test_different_coverage_types(self):
        """Different coverage types have different limits."""
        # Annuity payout has $300k limit in TX
        payout_covered = calculate_covered_amount(400_000, "TX", CoverageType.ANNUITY_PAYOUT)
        assert payout_covered == 300_000

        # Group annuity has $5M limit
        group_covered = calculate_covered_amount(3_000_000, "TX", CoverageType.GROUP_ANNUITY)
        assert group_covered == 3_000_000


# =============================================================================
# Tests for cva.py
# =============================================================================


class TestCVACalculation:
    """Tests for CVA calculation."""

    def test_cva_basic_calculation(self):
        """CVA is calculated correctly for basic case."""
        result = calculate_cva(
            exposure=250_000,
            rating=AMBestRating.A,
            term_years=5,
            lgd=0.70,
            risk_free_rate=0.05,
        )

        assert isinstance(result, CVAResult)
        assert result.cva_gross > 0
        assert result.cva_net > 0
        assert result.expected_exposure == 250_000
        assert result.lgd == 0.70
        assert result.rating == AMBestRating.A

    def test_cva_increases_with_term(self):
        """CVA increases with longer term."""
        cva_1yr = calculate_cva(250_000, AMBestRating.A, term_years=1).cva_gross
        cva_5yr = calculate_cva(250_000, AMBestRating.A, term_years=5).cva_gross
        cva_10yr = calculate_cva(250_000, AMBestRating.A, term_years=10).cva_gross

        assert cva_1yr < cva_5yr < cva_10yr

    def test_cva_increases_with_worse_rating(self):
        """CVA increases with worse (lower) rating."""
        cva_a = calculate_cva(250_000, AMBestRating.A, term_years=5).cva_gross
        cva_b = calculate_cva(250_000, AMBestRating.B, term_years=5).cva_gross
        cva_c = calculate_cva(250_000, AMBestRating.C, term_years=5).cva_gross

        assert cva_a < cva_b < cva_c

    def test_cva_scales_with_exposure(self):
        """CVA scales linearly with exposure."""
        cva_100k = calculate_cva(100_000, AMBestRating.A, term_years=5).cva_gross
        cva_200k = calculate_cva(200_000, AMBestRating.A, term_years=5).cva_gross

        assert abs(cva_200k - 2 * cva_100k) < 1  # Within $1

    def test_cva_with_guaranty_adjustment(self):
        """CVA is reduced by guaranty fund coverage."""
        result_no_state = calculate_cva(
            exposure=250_000,
            rating=AMBestRating.A,
            term_years=5,
        )
        result_with_state = calculate_cva(
            exposure=250_000,
            rating=AMBestRating.A,
            term_years=5,
            state="TX",
        )

        # With full guaranty coverage, net CVA should be zero
        assert result_with_state.cva_net == 0
        assert result_with_state.coverage_ratio == 1.0
        assert result_with_state.guaranty_adjustment == result_no_state.cva_gross

    def test_cva_partial_guaranty_adjustment(self):
        """CVA is partially reduced when over guaranty limit."""
        result = calculate_cva(
            exposure=500_000,  # Over $250k limit
            rating=AMBestRating.A,
            term_years=5,
            state="TX",
        )

        # 50% covered, so net CVA should be 50% of gross
        assert result.coverage_ratio == 0.5
        assert abs(result.cva_net - 0.5 * result.cva_gross) < 1

    def test_cva_california_80_percent(self):
        """California 80% coverage affects CVA adjustment."""
        result = calculate_cva(
            exposure=250_000,
            rating=AMBestRating.A,
            term_years=5,
            state="CA",
        )

        # California covers 80% of $250k = $200k
        assert result.covered_exposure == 200_000
        assert result.uncovered_exposure == 50_000
        assert result.coverage_ratio == 0.8
        # Net CVA should be 20% of gross
        assert abs(result.cva_net - 0.2 * result.cva_gross) < 1

    def test_cva_invalid_exposure(self):
        """Zero or negative exposure raises ValueError."""
        with pytest.raises(ValueError, match="exposure must be > 0"):
            calculate_cva(0, AMBestRating.A, term_years=5)
        with pytest.raises(ValueError, match="exposure must be > 0"):
            calculate_cva(-100_000, AMBestRating.A, term_years=5)

    def test_cva_invalid_term(self):
        """Term less than 1 raises ValueError."""
        with pytest.raises(ValueError, match="term_years must be >= 1"):
            calculate_cva(250_000, AMBestRating.A, term_years=0)

    def test_cva_invalid_lgd(self):
        """LGD outside (0, 1] raises ValueError."""
        with pytest.raises(ValueError, match="lgd must be in"):
            calculate_cva(250_000, AMBestRating.A, lgd=0)
        with pytest.raises(ValueError, match="lgd must be in"):
            calculate_cva(250_000, AMBestRating.A, lgd=1.5)


class TestCreditAdjustedPricing:
    """Tests for credit-adjusted pricing."""

    def test_credit_adjusted_price_less_than_base(self):
        """Credit-adjusted price is less than base price."""
        base_price = 100_000
        adj_price = calculate_credit_adjusted_price(
            base_price=base_price,
            rating=AMBestRating.A,
            term_years=5,
        )

        assert adj_price < base_price

    def test_credit_adjusted_price_with_guaranty(self):
        """Credit-adjusted price considers guaranty coverage."""
        base_price = 100_000

        # Without state adjustment
        adj_no_state = calculate_credit_adjusted_price(
            base_price=base_price,
            rating=AMBestRating.A,
            term_years=5,
        )

        # With state adjustment (full coverage)
        adj_with_state = calculate_credit_adjusted_price(
            base_price=base_price,
            rating=AMBestRating.A,
            term_years=5,
            state="TX",
        )

        # With full guaranty coverage, price should equal base
        assert adj_with_state == base_price
        assert adj_with_state > adj_no_state


class TestExposureProfile:
    """Tests for exposure profile calculation."""

    def test_exposure_profile_shape(self):
        """Exposure profile has correct length."""
        profile = calculate_exposure_profile(
            principal=100_000,
            rate=0.04,
            term_years=5,
            payment_frequency=1,
        )
        assert len(profile) == 5

    def test_exposure_profile_monthly(self):
        """Monthly payment frequency gives 12x periods."""
        profile = calculate_exposure_profile(
            principal=100_000,
            rate=0.04,
            term_years=5,
            payment_frequency=12,
        )
        assert len(profile) == 60

    def test_exposure_profile_increasing(self):
        """Exposure generally increases over time for MYGA."""
        profile = calculate_exposure_profile(
            principal=100_000,
            rate=0.04,
            term_years=5,
        )
        # Early periods should have lower exposure than later
        assert profile[0] < profile[-1]


class TestCVATermStructure:
    """Tests for CVA with full term structure."""

    def test_cva_term_structure_positive(self):
        """CVA with term structure is positive."""
        profile = calculate_exposure_profile(100_000, 0.04, 5)
        cva = calculate_cva_term_structure(
            exposure_profile=profile,
            rating=AMBestRating.A,
        )
        assert cva > 0

    def test_cva_term_structure_increases_with_exposure(self):
        """Higher exposure profile gives higher CVA."""
        profile_100k = calculate_exposure_profile(100_000, 0.04, 5)
        profile_200k = calculate_exposure_profile(200_000, 0.04, 5)

        cva_100k = calculate_cva_term_structure(profile_100k, AMBestRating.A)
        cva_200k = calculate_cva_term_structure(profile_200k, AMBestRating.A)

        assert cva_200k > cva_100k


class TestCreditSpread:
    """Tests for implied credit spread calculation."""

    def test_credit_spread_positive(self):
        """Credit spread is positive for all ratings."""
        for rating in [AMBestRating.A, AMBestRating.B, AMBestRating.C]:
            spread = calculate_credit_spread(rating)
            assert spread > 0

    def test_credit_spread_increases_with_worse_rating(self):
        """Credit spread increases with worse rating."""
        spread_a = calculate_credit_spread(AMBestRating.A)
        spread_b = calculate_credit_spread(AMBestRating.B)
        spread_c = calculate_credit_spread(AMBestRating.C)

        assert spread_a < spread_b < spread_c

    def test_credit_spread_formula(self):
        """Credit spread equals hazard_rate * LGD."""
        rating = AMBestRating.A
        lgd = 0.70
        h = get_hazard_rate(rating)
        expected_spread = h * lgd
        actual_spread = calculate_credit_spread(rating, lgd)

        assert abs(actual_spread - expected_spread) < 1e-10


class TestDefaultLGD:
    """Tests for default LGD value."""

    def test_default_lgd_value(self):
        """Default LGD is 70% (30% recovery for insurers)."""
        assert DEFAULT_INSURANCE_LGD == 0.70

    def test_default_lgd_used(self):
        """Default LGD is used when not specified."""
        result = calculate_cva(250_000, AMBestRating.A, term_years=5)
        assert result.lgd == 0.70


# =============================================================================
# Integration Tests
# =============================================================================


class TestCreditModuleIntegration:
    """Integration tests across credit module components."""

    def test_full_cva_workflow(self):
        """Test complete CVA calculation workflow."""
        # Scenario: $500k annuity from A-rated insurer in California
        exposure = 500_000
        rating = AMBestRating.A
        term = 10
        state = "CA"

        # 1. Get PD data
        annual_pd = get_annual_pd(rating)
        assert annual_pd < 0.001  # A-rated should be <0.1%

        # 2. Get guaranty coverage
        coverage = get_state_coverage(state)
        assert coverage.coverage_percentage == 0.80

        # 3. Calculate covered amount
        covered = calculate_covered_amount(exposure, state, CoverageType.ANNUITY_DEFERRED)
        # CA limit = $250k * 80% = $200k
        assert covered == 200_000

        # 4. Calculate CVA
        result = calculate_cva(
            exposure=exposure,
            rating=rating,
            term_years=term,
            state=state,
        )

        # Verify all fields
        assert result.expected_exposure == exposure
        assert result.covered_exposure == covered
        assert result.uncovered_exposure == exposure - covered
        assert result.coverage_ratio == covered / exposure
        assert result.cva_net < result.cva_gross  # Net should be lower
        assert result.guaranty_adjustment > 0

    def test_cva_sensitivity_to_rating(self):
        """CVA sensitivity to rating changes."""
        base_params = {
            "exposure": 250_000,
            "term_years": 5,
            "lgd": 0.70,
        }

        # Calculate CVA for each secure rating
        # Note: A++ and A+ have same PD in AM Best data, so use <=
        cvas = {}
        for rating in [
            AMBestRating.A_PLUS_PLUS,
            AMBestRating.A_PLUS,
            AMBestRating.A,
            AMBestRating.A_MINUS,
            AMBestRating.B_PLUS_PLUS,
            AMBestRating.B_PLUS,
        ]:
            cvas[rating] = calculate_cva(rating=rating, **base_params).cva_gross

        # Each step down should (weakly) increase CVA
        # Note: A++ and A+ have identical PD in AM Best data
        ratings_order = list(cvas.keys())
        for i in range(len(ratings_order) - 1):
            assert cvas[ratings_order[i]] <= cvas[ratings_order[i + 1]]

        # But at least some increase across the full range
        assert cvas[AMBestRating.A_PLUS_PLUS] < cvas[AMBestRating.B_PLUS]

    def test_practical_scenario_myga_pricing(self):
        """Practical scenario: MYGA with credit adjustment."""
        # 5-year MYGA, $100k premium, 4% rate, A-rated insurer
        principal = 100_000
        rate = 0.04
        term = 5

        # Base maturity value (no credit risk)
        maturity_value = principal * (1 + rate) ** term
        assert abs(maturity_value - 121665.29) < 0.01

        # Credit-adjusted maturity value
        adj_value = calculate_credit_adjusted_price(
            base_price=maturity_value,
            rating=AMBestRating.A,
            term_years=term,
            state="TX",  # Full guaranty coverage under $250k
        )

        # With full guaranty coverage, should equal base
        assert adj_value == maturity_value

        # Without guaranty coverage
        adj_value_no_guaranty = calculate_credit_adjusted_price(
            base_price=maturity_value,
            rating=AMBestRating.A,
            term_years=term,
        )

        # Should be slightly less due to credit risk
        assert adj_value_no_guaranty < maturity_value
        # But not by much for A-rated insurer
        credit_discount = (maturity_value - adj_value_no_guaranty) / maturity_value
        assert credit_discount < 0.01  # Less than 1% for A-rated, 5-year
