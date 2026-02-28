"""
Validation tests for credit risk module.

Cross-validates CVA calculations against:
[T1] Hull (2018) "Options, Futures, and Other Derivatives" Ch. 24
[T2] Gregory (2015) "The xVA Challenge" Ch. 3-4
[T2] AM Best Impairment Rate Study (1977-2023)

Key validation points:
1. CVA formula consistency with Hull [T1]
2. AM Best impairment rates match published data [T2]
3. Credit spread approximation [T1]
"""

import numpy as np

from annuity_pricing.credit import (
    AMBestRating,
    calculate_cva,
    get_annual_pd,
    get_cumulative_pd,
)
from annuity_pricing.credit.cva import (
    DEFAULT_INSURANCE_LGD,
    calculate_credit_spread,
)
from annuity_pricing.credit.default_prob import (
    get_hazard_rate,
)

# =============================================================================
# AM Best Impairment Rate Validation [T2]
# =============================================================================


class TestAMBestRatesValidation:
    """
    Validate AM Best impairment rates against published study.

    [T2] Source: AM Best "Best's Impairment Rate and Rating Transition Study
    — 1977 to 2023" (published 2024)

    Key published values:
    - A++/A+ combined: 0.01% 1-year, ~2% 10-year cumulative
    - A/A-: 0.02-0.11% 1-year
    - B/B-: 1.35% 1-year
    - C (comparable to "b" rating): 3.29% 1-year
    """

    def test_superior_rating_pd(self):
        """
        [T2] Superior ratings (A++/A+) have very low impairment.

        AM Best study shows ~0.01-0.02% 1-year for superior tier.
        """
        pd_a_plus_plus = get_annual_pd(AMBestRating.A_PLUS_PLUS)
        pd_a_plus = get_annual_pd(AMBestRating.A_PLUS)

        # Should be in 0.01% - 0.05% range
        assert 0.0001 <= pd_a_plus_plus <= 0.0005
        assert 0.0001 <= pd_a_plus <= 0.0005

    def test_excellent_rating_pd(self):
        """
        [T2] Excellent ratings (A, A-) impairment rates.

        AM Best: "a" = 0.02% 1-year, "A-" = 0.11% 1-year
        """
        pd_a = get_annual_pd(AMBestRating.A)
        pd_a_minus = get_annual_pd(AMBestRating.A_MINUS)

        # A should be ~0.02%
        assert 0.0001 <= pd_a <= 0.0005

        # A- should be higher, ~0.11%
        assert 0.0005 <= pd_a_minus <= 0.002

    def test_adequate_rating_pd(self):
        """
        [T2] Adequate ratings (B/B-) have higher impairment.

        AM Best: B/B- combined ~1.35% 1-year
        """
        pd_b = get_annual_pd(AMBestRating.B)
        pd_b_minus = get_annual_pd(AMBestRating.B_MINUS)

        # B should be around 1%
        assert 0.005 <= pd_b <= 0.02

        # B- should be ~1.35%
        assert 0.01 <= pd_b_minus <= 0.02

    def test_weak_rating_pd(self):
        """
        [T2] Weak ratings (C class) have high impairment.

        AM Best: "b" rating (comparable to C) = 3.29% 1-year
        """
        pd_c = get_annual_pd(AMBestRating.C)

        # Should be around 3%
        assert 0.02 <= pd_c <= 0.05

    def test_10_year_cumulative_pd(self):
        """
        [T2] 10-year cumulative PD ranges.

        AM Best study shows:
        - A++/A+: ~2% cumulative
        - A/A-: 2-5% cumulative
        - B++/B+: 7-15% cumulative
        """
        pd_a_plus_10yr = get_cumulative_pd(AMBestRating.A_PLUS, 10)
        pd_a_10yr = get_cumulative_pd(AMBestRating.A, 10)
        pd_b_plus_10yr = get_cumulative_pd(AMBestRating.B_PLUS, 10)

        # A+ 10-year should be ~2%
        assert 0.01 <= pd_a_plus_10yr <= 0.04

        # A 10-year should be ~2-3%
        assert 0.015 <= pd_a_10yr <= 0.05

        # B+ 10-year should be ~10%
        assert 0.05 <= pd_b_plus_10yr <= 0.15


# =============================================================================
# CVA Formula Validation [T1]
# =============================================================================


class TestCVAFormulaValidation:
    """
    Validate CVA formula against Hull textbook.

    [T1] Hull Ch. 24: CVA = LGD × Σ EE(t) × PD(t) × DF(t)

    For simplified single-period: CVA ≈ LGD × EE × (1 - e^(-h×T)) × DF_avg
    """

    def test_cva_basic_formula(self):
        """
        [T1] Test CVA against manual calculation.

        Parameters:
        - Exposure = $100,000
        - Rating = A (annual PD ≈ 0.02%)
        - Term = 1 year
        - LGD = 70%
        - Risk-free rate = 5%

        Expected: CVA ≈ LGD × EE × (1 - e^(-h×1)) × e^(-r×0.5)
        """
        exposure = 100_000
        rating = AMBestRating.A
        lgd = 0.70
        r = 0.05

        # Get hazard rate
        h = get_hazard_rate(rating)

        # Manual calculation
        cum_pd = 1 - np.exp(-h * 1)  # 1-year cumulative PD
        avg_df = np.exp(-r * 0.5)  # Midpoint discount factor
        expected_cva = lgd * exposure * cum_pd * avg_df

        # Module calculation
        result = calculate_cva(
            exposure=exposure,
            rating=rating,
            term_years=1,
            lgd=lgd,
            risk_free_rate=r,
        )

        # Should match within 1%
        assert abs(result.cva_gross - expected_cva) / expected_cva < 0.01

    def test_cva_5_year_formula(self):
        """
        [T1] Test 5-year CVA calculation.
        """
        exposure = 250_000
        rating = AMBestRating.A
        lgd = 0.70
        r = 0.05
        T = 5

        h = get_hazard_rate(rating)
        cum_pd = 1 - np.exp(-h * T)
        avg_df = np.exp(-r * T / 2)
        expected_cva = lgd * exposure * cum_pd * avg_df

        result = calculate_cva(
            exposure=exposure,
            rating=rating,
            term_years=T,
            lgd=lgd,
            risk_free_rate=r,
        )

        # Should match within 1%
        assert abs(result.cva_gross - expected_cva) / expected_cva < 0.01

    def test_cva_lgd_sensitivity(self):
        """
        [T1] CVA scales linearly with LGD.
        """
        exposure = 100_000
        rating = AMBestRating.A

        cva_50_lgd = calculate_cva(
            exposure=exposure, rating=rating, lgd=0.50, term_years=5
        ).cva_gross
        cva_70_lgd = calculate_cva(
            exposure=exposure, rating=rating, lgd=0.70, term_years=5
        ).cva_gross

        # CVA should scale linearly: CVA_70 / CVA_50 = 0.70 / 0.50
        expected_ratio = 0.70 / 0.50
        actual_ratio = cva_70_lgd / cva_50_lgd

        assert abs(actual_ratio - expected_ratio) < 0.01


# =============================================================================
# Credit Spread Validation [T1]
# =============================================================================


class TestCreditSpreadValidation:
    """
    Validate credit spread approximation.

    [T1] Hull: For small PD, credit spread ≈ h × LGD
    where h is hazard rate and LGD is loss given default.
    """

    def test_credit_spread_formula(self):
        """
        [T1] Credit spread equals hazard rate times LGD.
        """
        for rating in [AMBestRating.A, AMBestRating.B, AMBestRating.C]:
            lgd = DEFAULT_INSURANCE_LGD
            h = get_hazard_rate(rating)

            expected_spread = h * lgd
            actual_spread = calculate_credit_spread(rating, lgd)

            assert abs(actual_spread - expected_spread) < 1e-10

    def test_credit_spread_reasonable_values(self):
        """
        [T1] Credit spreads should be in reasonable basis point ranges.

        Industry expectations (insurance):
        - A-rated: 5-20 bps
        - B-rated: 50-150 bps
        - C-rated: 200-500 bps
        """
        spread_a = calculate_credit_spread(AMBestRating.A)
        spread_b = calculate_credit_spread(AMBestRating.B)
        spread_c = calculate_credit_spread(AMBestRating.C)

        # Convert to basis points
        bps_a = spread_a * 10_000
        bps_b = spread_b * 10_000
        bps_c = spread_c * 10_000

        # A-rated should be very low (1-20 bps)
        assert 1 <= bps_a <= 20

        # B-rated should be moderate (50-150 bps)
        assert 30 <= bps_b <= 200

        # C-rated should be higher (150-500 bps)
        assert 100 <= bps_c <= 500


# =============================================================================
# Hazard Rate / Survival Probability Validation [T1]
# =============================================================================


class TestHazardRateValidation:
    """
    Validate hazard rate and survival probability relationships.

    [T1] Hull Ch. 24:
    - S(t) = exp(-h × t) = survival probability to time t
    - P(default by t) = 1 - S(t) = 1 - exp(-h × t)
    - For small h: P(default) ≈ h × t
    """

    def test_hazard_rate_to_pd_relationship(self):
        """
        [T1] Verify P(default by T) = 1 - exp(-h × T).

        Note: Our cumulative PD uses interpolation from AM Best data points
        (1, 5, 10, 15 years), which may differ from constant hazard rate model.
        This test verifies the hazard rate approximation is reasonable.
        """
        rating = AMBestRating.A
        h = get_hazard_rate(rating)

        # For 1-year, hazard rate model and annual PD should be consistent
        pd_1yr_from_h = 1 - np.exp(-h * 1)
        pd_1yr_from_func = get_cumulative_pd(rating, 1)

        # 1-year should match closely (hazard rate derived from annual PD)
        assert abs(pd_1yr_from_h - pd_1yr_from_func) / pd_1yr_from_func < 0.01

        # For longer terms, just verify reasonable relationship
        for T in [5, 10]:
            pd_from_h = 1 - np.exp(-h * T)
            pd_from_func = get_cumulative_pd(rating, T)

            # Both should be positive and finite
            assert pd_from_h > 0
            assert pd_from_func > 0
            # Interpolated values may be higher due to aging effect in AM Best data
            # Just verify same order of magnitude
            assert pd_from_h < pd_from_func * 2  # Not more than 2x different

    def test_small_pd_approximation(self):
        """
        [T1] For small h, P(default in 1 year) ≈ h.
        """
        for rating in [AMBestRating.A_PLUS_PLUS, AMBestRating.A_PLUS, AMBestRating.A]:
            h = get_hazard_rate(rating)
            annual_pd = get_annual_pd(rating)

            # h ≈ -ln(1-PD) ≈ PD for small PD
            # Relative error should be small
            if annual_pd > 0:
                relative_error = abs(h - annual_pd) / annual_pd
                assert relative_error < 0.01  # Within 1%


# =============================================================================
# Insurance Industry Specific Validation [T2]
# =============================================================================


class TestInsuranceIndustryValidation:
    """
    Validate insurance-specific CVA considerations.

    [T2] Insurance companies have:
    - Higher recovery rates than typical corporates (regulatory protection)
    - State guaranty fund coverage
    - AM Best specific rating scale
    """

    def test_insurance_lgd_reasonable(self):
        """
        [T2] Insurance LGD of 70% (30% recovery) is conservative.

        Industry notes:
        - Corporate average LGD: 60-70%
        - Insurance with regulatory protection: 50-70%
        - Our 70% is conservative (favors policyholder protection)
        """
        assert DEFAULT_INSURANCE_LGD == 0.70
        # Recovery = 1 - LGD = 30%
        recovery = 1 - DEFAULT_INSURANCE_LGD
        assert abs(recovery - 0.30) < 1e-10  # Avoid floating point comparison

    def test_guaranty_reduces_effective_cva(self):
        """
        [T2] State guaranty coverage reduces effective CVA exposure.
        """
        # $200k annuity (under $250k limit)
        result_no_guaranty = calculate_cva(
            exposure=200_000,
            rating=AMBestRating.A,
            term_years=5,
        )

        result_with_guaranty = calculate_cva(
            exposure=200_000,
            rating=AMBestRating.A,
            term_years=5,
            state="TX",
        )

        # With full guaranty, net CVA should be zero
        assert result_with_guaranty.cva_net == 0
        assert result_no_guaranty.cva_gross > 0

    def test_large_exposure_partial_guaranty(self):
        """
        [T2] Large exposures are only partially protected.
        """
        # $1M annuity (well over $250k limit)
        result = calculate_cva(
            exposure=1_000_000,
            rating=AMBestRating.A,
            term_years=5,
            state="TX",
        )

        # Coverage ratio should be 25% ($250k / $1M)
        assert abs(result.coverage_ratio - 0.25) < 0.01

        # Net CVA should be 75% of gross
        assert abs(result.cva_net - 0.75 * result.cva_gross) < 1


# =============================================================================
# Numerical Stability Tests
# =============================================================================


class TestNumericalStability:
    """Test numerical stability of credit calculations."""

    def test_very_long_term(self):
        """CVA calculation stable for long terms."""
        result = calculate_cva(
            exposure=100_000,
            rating=AMBestRating.A,
            term_years=30,
        )

        assert result.cva_gross > 0
        assert np.isfinite(result.cva_gross)
        assert result.cva_gross < result.expected_exposure  # CVA < Exposure

    def test_very_low_rated(self):
        """CVA calculation stable for very low ratings."""
        result = calculate_cva(
            exposure=100_000,
            rating=AMBestRating.D,
            term_years=10,
        )

        assert result.cva_gross > 0
        assert np.isfinite(result.cva_gross)

    def test_small_exposure(self):
        """CVA calculation stable for small exposures."""
        result = calculate_cva(
            exposure=1.00,  # $1
            rating=AMBestRating.A,
            term_years=5,
        )

        assert result.cva_gross >= 0
        assert np.isfinite(result.cva_gross)

    def test_large_exposure(self):
        """CVA calculation stable for large exposures."""
        result = calculate_cva(
            exposure=100_000_000,  # $100M
            rating=AMBestRating.A,
            term_years=5,
        )

        assert result.cva_gross > 0
        assert np.isfinite(result.cva_gross)
        # CVA should scale with exposure
        result_1m = calculate_cva(
            exposure=1_000_000,
            rating=AMBestRating.A,
            term_years=5,
        )
        expected_ratio = 100_000_000 / 1_000_000
        actual_ratio = result.cva_gross / result_1m.cva_gross
        assert abs(actual_ratio - expected_ratio) < 0.01
