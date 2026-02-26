"""
Unit tests for MYGA valuation module.

Tests myga_pv.py: PV, duration, convexity, sensitivity analysis.
See: METHODOLOGY.md Section 4.1
"""


import pytest

from annuity_pricing.valuation.myga_pv import (
    CashFlow,
    MYGAValuation,
    calculate_convexity,
    calculate_dollar_duration,
    calculate_effective_duration,
    calculate_macaulay_duration,
    calculate_modified_duration,
    calculate_myga_maturity_value,
    calculate_present_value,
    sensitivity_analysis,
    value_myga,
)


class TestMaturityValue:
    """Test maturity value calculation."""

    def test_annual_compounding(self) -> None:
        """
        [T1] FV = P × (1 + r)^n for annual compounding.

        $100,000 at 4.5% for 5 years = $100,000 × 1.045^5 = $124,618.19
        """
        result = calculate_myga_maturity_value(
            principal=100_000,
            rate=0.045,
            years=5,
            compounding_frequency=1,
        )

        expected = 100_000 * (1.045) ** 5  # 124618.19...
        assert abs(result - expected) < 0.01

    def test_semi_annual_compounding(self) -> None:
        """
        [T1] FV = P × (1 + r/2)^(2n) for semi-annual compounding.
        """
        result = calculate_myga_maturity_value(
            principal=100_000,
            rate=0.045,
            years=5,
            compounding_frequency=2,
        )

        expected = 100_000 * (1 + 0.045/2) ** (2*5)
        assert abs(result - expected) < 0.01

    def test_quarterly_compounding(self) -> None:
        """
        [T1] FV = P × (1 + r/4)^(4n) for quarterly compounding.
        """
        result = calculate_myga_maturity_value(
            principal=100_000,
            rate=0.045,
            years=5,
            compounding_frequency=4,
        )

        expected = 100_000 * (1 + 0.045/4) ** (4*5)
        assert abs(result - expected) < 0.01

    def test_higher_frequency_yields_more(self) -> None:
        """
        [T1] More frequent compounding yields higher maturity value.
        """
        annual = calculate_myga_maturity_value(100_000, 0.045, 5, 1)
        semi = calculate_myga_maturity_value(100_000, 0.045, 5, 2)
        quarterly = calculate_myga_maturity_value(100_000, 0.045, 5, 4)

        assert quarterly > semi > annual

    def test_validates_positive_principal(self) -> None:
        """Should raise ValueError for non-positive principal."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_myga_maturity_value(principal=0, rate=0.045, years=5)

        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_myga_maturity_value(principal=-1000, rate=0.045, years=5)

    def test_validates_non_negative_rate(self) -> None:
        """Should raise ValueError for negative rate."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_myga_maturity_value(principal=100_000, rate=-0.01, years=5)

    def test_validates_positive_years(self) -> None:
        """Should raise ValueError for non-positive years."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_myga_maturity_value(principal=100_000, rate=0.045, years=0)


class TestPresentValue:
    """Test present value calculation."""

    def test_basic_discounting(self) -> None:
        """
        [T1] PV = FV / (1 + r)^n

        $100,000 discounted at 4% for 5 years = $100,000 / 1.04^5 = $82,192.71
        """
        result = calculate_present_value(
            future_value=100_000,
            discount_rate=0.04,
            years=5,
            compounding_frequency=1,
        )

        expected = 100_000 / (1.04) ** 5
        assert abs(result - expected) < 0.01

    def test_higher_discount_rate_lower_pv(self) -> None:
        """
        [T1] Higher discount rate → lower present value.
        """
        pv_low = calculate_present_value(100_000, 0.03, 5)
        pv_high = calculate_present_value(100_000, 0.05, 5)

        assert pv_high < pv_low

    def test_longer_term_lower_pv(self) -> None:
        """
        [T1] Longer term → lower present value.
        """
        pv_short = calculate_present_value(100_000, 0.04, 3)
        pv_long = calculate_present_value(100_000, 0.04, 10)

        assert pv_long < pv_short

    def test_validates_non_negative_fv(self) -> None:
        """Should raise ValueError for negative future value."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_present_value(future_value=-100, discount_rate=0.04, years=5)


class TestMacaulayDuration:
    """Test Macaulay duration calculation."""

    def test_single_cash_flow_duration(self) -> None:
        """
        [T1] For single cash flow at time T, Macaulay duration = T.
        """
        cash_flows = [CashFlow(time=5.0, amount=100_000)]
        result = calculate_macaulay_duration(cash_flows, discount_rate=0.04)

        assert abs(result - 5.0) < 1e-6

    def test_multiple_cash_flows(self) -> None:
        """
        [T1] Duration = Σ(t × PV(CF_t)) / Σ(PV(CF_t))
        """
        # Two equal payments at t=1 and t=2
        cash_flows = [
            CashFlow(time=1.0, amount=100),
            CashFlow(time=2.0, amount=100),
        ]
        result = calculate_macaulay_duration(cash_flows, discount_rate=0.04)

        # Calculate manually
        pv1 = 100 / 1.04
        pv2 = 100 / (1.04**2)
        expected = (1 * pv1 + 2 * pv2) / (pv1 + pv2)

        assert abs(result - expected) < 1e-6

    def test_duration_increases_with_term(self) -> None:
        """
        [T1] Duration increases with cash flow timing.
        """
        short = calculate_macaulay_duration([CashFlow(3.0, 100)], 0.04)
        long = calculate_macaulay_duration([CashFlow(10.0, 100)], 0.04)

        assert long > short

    def test_validates_empty_cash_flows(self) -> None:
        """Should raise ValueError for empty cash flows."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_macaulay_duration([], discount_rate=0.04)


class TestModifiedDuration:
    """Test modified duration calculation."""

    def test_modified_duration_formula(self) -> None:
        """
        [T1] ModD = MacD / (1 + r/n)
        """
        mac_duration = 5.0
        discount_rate = 0.04

        result = calculate_modified_duration(mac_duration, discount_rate)

        expected = 5.0 / 1.04
        assert abs(result - expected) < 1e-6

    def test_modified_less_than_macaulay(self) -> None:
        """
        [T1] Modified duration < Macaulay duration (for positive rates).
        """
        mac_duration = 5.0
        mod_duration = calculate_modified_duration(mac_duration, 0.04)

        assert mod_duration < mac_duration


class TestConvexity:
    """Test convexity calculation."""

    def test_single_cash_flow_convexity(self) -> None:
        """
        [T1] Convexity = T(T+1)/(1+r)^2 for zero-coupon.
        """
        cash_flows = [CashFlow(time=5.0, amount=100_000)]
        result = calculate_convexity(cash_flows, discount_rate=0.04)

        expected = 5 * 6 / (1.04) ** 2
        assert abs(result - expected) < 0.01

    def test_convexity_positive(self) -> None:
        """
        [T1] Convexity is always positive for standard bonds.
        """
        cash_flows = [CashFlow(time=5.0, amount=100_000)]
        result = calculate_convexity(cash_flows, discount_rate=0.04)

        assert result > 0

    def test_validates_empty_cash_flows(self) -> None:
        """Should raise ValueError for empty cash flows."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_convexity([], discount_rate=0.04)


class TestDollarDuration:
    """Test dollar duration (DV01) calculation."""

    def test_dv01_formula(self) -> None:
        """
        [T1] DV01 ≈ PV × ModD × 0.0001
        """
        pv = 100_000
        mod_duration = 4.8  # ~5 year modified duration

        result = calculate_dollar_duration(pv, mod_duration)

        expected = 100_000 * 4.8 * 0.0001  # $48
        assert abs(result - expected) < 1e-6

    def test_dv01_scales_with_pv(self) -> None:
        """
        [T1] DV01 scales linearly with present value.
        """
        dv01_100k = calculate_dollar_duration(100_000, 5.0)
        dv01_200k = calculate_dollar_duration(200_000, 5.0)

        assert abs(dv01_200k - 2 * dv01_100k) < 1e-6


class TestEffectiveDuration:
    """Test effective duration calculation."""

    def test_effective_duration_formula(self) -> None:
        """
        [T1] EffD = (PV_down - PV_up) / (2 × PV_base × Δr)
        """
        pv_base = 100_000
        pv_up = 95_000    # PV when rates up
        pv_down = 105_000  # PV when rates down
        rate_shift = 0.01

        result = calculate_effective_duration(pv_up, pv_down, pv_base, rate_shift)

        expected = (105_000 - 95_000) / (2 * 100_000 * 0.01)
        assert abs(result - expected) < 1e-6

    def test_validates_zero_base_pv(self) -> None:
        """Should raise ValueError for zero base PV."""
        with pytest.raises(ValueError, match="CRITICAL"):
            calculate_effective_duration(95_000, 105_000, 0, 0.01)


class TestValueMyga:
    """Test complete MYGA valuation."""

    def test_returns_myga_valuation(self) -> None:
        """Should return complete MYGAValuation object."""
        result = value_myga(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            discount_rate=0.04,
        )

        assert isinstance(result, MYGAValuation)
        assert result.present_value > 0
        assert result.maturity_value > 0
        assert result.macaulay_duration > 0
        assert result.modified_duration > 0
        assert result.convexity > 0
        assert result.dollar_duration > 0
        assert result.effective_duration is not None

    def test_consistent_calculations(self) -> None:
        """
        Verify internal consistency of valuation.

        For single-payment MYGA:
        - Macaulay duration = guarantee duration
        - Modified duration = Mac duration / (1 + disc)
        """
        result = value_myga(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            discount_rate=0.04,
        )

        # Macaulay duration = 5 for single payment at t=5
        assert abs(result.macaulay_duration - 5.0) < 1e-6

        # Modified duration = 5 / 1.04
        expected_mod_dur = 5.0 / 1.04
        assert abs(result.modified_duration - expected_mod_dur) < 1e-6

    def test_pv_greater_when_rate_exceeds_discount(self) -> None:
        """
        [T1] PV > Principal when fixed_rate > discount_rate.
        """
        result = value_myga(
            principal=100_000,
            fixed_rate=0.05,    # Higher
            guarantee_duration=5,
            discount_rate=0.04,  # Lower
        )

        assert result.present_value > 100_000

    def test_pv_less_when_discount_exceeds_rate(self) -> None:
        """
        [T1] PV < Principal when discount_rate > fixed_rate.
        """
        result = value_myga(
            principal=100_000,
            fixed_rate=0.04,    # Lower
            guarantee_duration=5,
            discount_rate=0.05,  # Higher
        )

        assert result.present_value < 100_000

    def test_effective_duration_close_to_modified(self) -> None:
        """
        [T1] For option-free MYGA, effective duration ≈ modified duration.
        """
        result = value_myga(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            discount_rate=0.04,
        )

        # Should be within 1% of modified duration
        rel_diff = abs(result.effective_duration - result.modified_duration) / result.modified_duration
        assert rel_diff < 0.01, (
            f"Effective duration {result.effective_duration:.4f} should be close to "
            f"modified duration {result.modified_duration:.4f}"
        )


class TestSensitivityAnalysis:
    """Test sensitivity analysis function."""

    def test_returns_rate_pv_pairs(self) -> None:
        """Should return list of (rate, pv, pct_change) tuples."""
        results = sensitivity_analysis(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            base_discount_rate=0.04,
        )

        assert len(results) > 0
        assert all(len(r) == 3 for r in results)

    def test_pv_decreases_as_rate_increases(self) -> None:
        """
        [T1] PV decreases as discount rate increases.
        """
        results = sensitivity_analysis(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            base_discount_rate=0.04,
        )

        # Extract rates and PVs
        sorted_results = sorted(results, key=lambda x: x[0])

        # Check PV decreases as rate increases
        for i in range(1, len(sorted_results)):
            assert sorted_results[i][1] < sorted_results[i-1][1], (
                f"PV should decrease as rate increases: "
                f"rate {sorted_results[i][0]} has PV {sorted_results[i][1]} >= "
                f"rate {sorted_results[i-1][0]} PV {sorted_results[i-1][1]}"
            )

    def test_base_rate_has_zero_pct_change(self) -> None:
        """At base rate, percentage change should be 0."""
        results = sensitivity_analysis(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            base_discount_rate=0.04,
        )

        # Find the result at base rate
        base_result = [r for r in results if abs(r[0] - 0.04) < 1e-6]
        assert len(base_result) == 1
        assert abs(base_result[0][2]) < 1e-6, "Pct change at base rate should be 0"

    def test_custom_rate_shifts(self) -> None:
        """Should use custom rate shifts if provided."""
        custom_shifts = [-0.02, 0.0, 0.02]
        results = sensitivity_analysis(
            principal=100_000,
            fixed_rate=0.045,
            guarantee_duration=5,
            base_discount_rate=0.04,
            rate_shifts=custom_shifts,
        )

        rates = [r[0] for r in results]
        assert 0.02 in rates
        assert 0.04 in rates
        assert 0.06 in rates


class TestCashFlowDataclass:
    """Test CashFlow dataclass."""

    def test_cash_flow_immutable(self) -> None:
        """CashFlow should be immutable (frozen)."""
        cf = CashFlow(time=5.0, amount=100_000)

        with pytest.raises(AttributeError):
            cf.time = 6.0  # type: ignore

    def test_cash_flow_attributes(self) -> None:
        """Should store time and amount."""
        cf = CashFlow(time=5.0, amount=100_000)

        assert cf.time == 5.0
        assert cf.amount == 100_000


class TestMYGAValuationDataclass:
    """Test MYGAValuation dataclass."""

    def test_valuation_immutable(self) -> None:
        """MYGAValuation should be immutable (frozen)."""
        val = MYGAValuation(
            present_value=100_000,
            maturity_value=120_000,
            macaulay_duration=5.0,
            modified_duration=4.8,
            convexity=27.0,
            dollar_duration=48.0,
        )

        with pytest.raises(AttributeError):
            val.present_value = 110_000  # type: ignore

    def test_effective_duration_optional(self) -> None:
        """Effective duration should be optional."""
        val = MYGAValuation(
            present_value=100_000,
            maturity_value=120_000,
            macaulay_duration=5.0,
            modified_duration=4.8,
            convexity=27.0,
            dollar_duration=48.0,
        )

        assert val.effective_duration is None
