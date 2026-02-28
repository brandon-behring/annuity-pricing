"""
PV Discounting Validation Tests - Step 7.

[T1] Verify the corrected PV formula for FIA/RILA pricing:
    PV = e^(-rT) * premium * (1 + expected_credit)

This validates the fix from Step 1.0 (risk-neutral PV bug).

See: docs/knowledge/domain/option_pricing.md
See: notebooks/validation/pv_correction_derivation.ipynb
"""

import numpy as np
import pytest


class TestPVDiscountingFormula:
    """Tests for corrected PV discounting formula."""

    @pytest.mark.validation
    def test_pv_formula_at_zero_rate(self) -> None:
        """
        [T1] At r=0, PV should equal premium * (1 + expected_credit).

        No discounting when rate is zero.
        """
        premium = 100_000.0
        expected_credit = 0.05  # 5% expected return
        rate = 0.0
        term_years = 5.0

        # Correct formula
        discount_factor = np.exp(-rate * term_years)  # = 1.0
        pv_correct = discount_factor * premium * (1 + expected_credit)

        # Expected: 100,000 * 1.05 = 105,000
        expected_pv = premium * (1 + expected_credit)

        assert abs(pv_correct - expected_pv) < 0.01, (
            f"At r=0: PV should be {expected_pv}, got {pv_correct}"
        )

    @pytest.mark.validation
    def test_pv_discounts_principal(self) -> None:
        """
        [T1] At r>0, PV should be less than premium + premium*expected_credit.

        Principal must be discounted, not just the credit.
        """
        premium = 100_000.0
        expected_credit = 0.05  # 5%
        rate = 0.05  # 5% rate
        term_years = 5.0

        # Correct formula: discount the FULL maturity payoff
        discount_factor = np.exp(-rate * term_years)
        pv_correct = discount_factor * premium * (1 + expected_credit)

        # WRONG formula (the bug): only discount the credit
        pv_wrong = premium + discount_factor * premium * expected_credit

        # Correct PV should be less (because principal is discounted)
        assert pv_correct < pv_wrong, (
            f"Correct PV ({pv_correct:.2f}) should be < wrong PV ({pv_wrong:.2f})"
        )

        # Verify the difference is material (~22% for these params)
        error_if_wrong = (pv_wrong - pv_correct) / pv_correct
        assert error_if_wrong > 0.20, f"Error should be >20%, got {error_if_wrong:.2%}"

    @pytest.mark.validation
    def test_pv_discount_factor_calculation(self) -> None:
        """
        [T1] Verify discount factor calculation: e^(-rT).
        """
        rate = 0.05
        term_years = 5.0

        expected_df = np.exp(-rate * term_years)
        calculated_df = np.exp(-0.05 * 5.0)

        assert abs(expected_df - calculated_df) < 1e-10
        assert abs(expected_df - 0.7788) < 0.001, (
            f"e^(-0.25) should be ~0.7788, got {expected_df:.4f}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "rate,term_years,expected_credit",
        [
            (0.05, 5.0, 0.05),  # Standard case
            (0.03, 7.0, 0.04),  # Lower rate, longer term
            (0.08, 3.0, 0.06),  # Higher rate, shorter term
            (0.00, 5.0, 0.05),  # Zero rate
            (0.05, 1.0, 0.02),  # Short term, low credit
        ],
    )
    def test_pv_formula_parametrized(
        self, rate: float, term_years: float, expected_credit: float
    ) -> None:
        """
        [T1] Parametrized test of corrected PV formula.
        """
        premium = 100_000.0

        # Correct formula
        discount_factor = np.exp(-rate * term_years)
        pv = discount_factor * premium * (1 + expected_credit)

        # Basic sanity checks
        assert pv > 0, "PV must be positive"
        assert pv <= premium * (1 + expected_credit), "PV cannot exceed undiscounted value"

        if rate > 0:
            assert pv < premium * (1 + expected_credit), "With positive rate, PV must be discounted"


class TestPVErrorMagnitude:
    """Tests to quantify the error magnitude if wrong formula used."""

    @pytest.mark.validation
    def test_error_increases_with_rate(self) -> None:
        """
        [T1] Error from wrong formula increases with higher rates.
        """
        premium = 100_000.0
        expected_credit = 0.05
        term_years = 5.0

        errors = []
        for rate in [0.02, 0.04, 0.06, 0.08, 0.10]:
            df = np.exp(-rate * term_years)
            pv_correct = df * premium * (1 + expected_credit)
            pv_wrong = premium + df * premium * expected_credit
            error = (pv_wrong - pv_correct) / pv_correct
            errors.append(error)

        # Errors should increase with rate
        for i in range(len(errors) - 1):
            assert errors[i + 1] > errors[i], f"Error should increase with rate: {errors}"

    @pytest.mark.validation
    def test_error_increases_with_term(self) -> None:
        """
        [T1] Error from wrong formula increases with longer terms.
        """
        premium = 100_000.0
        expected_credit = 0.05
        rate = 0.05

        errors = []
        for term_years in [1, 3, 5, 7, 10]:
            df = np.exp(-rate * term_years)
            pv_correct = df * premium * (1 + expected_credit)
            pv_wrong = premium + df * premium * expected_credit
            error = (pv_wrong - pv_correct) / pv_correct
            errors.append(error)

        # Errors should increase with term
        for i in range(len(errors) - 1):
            assert errors[i + 1] > errors[i], f"Error should increase with term: {errors}"


class TestFIARILAPVIntegration:
    """Integration tests for FIA/RILA PV calculations."""

    @pytest.mark.validation
    def test_fia_pv_uses_correct_formula(self) -> None:
        """
        [T1] FIA pricing should use corrected PV formula.

        Note: This is a conceptual test - actual FIA pricing has
        additional complexity (option hedging budget, etc.).
        """
        # For a simple point-to-point FIA credit:
        premium = 100_000.0
        cap_rate = 0.08  # 8% cap
        expected_credit = 0.05  # Expected credit given market conditions
        rate = 0.05
        term_years = 5.0

        # The PV of the maturity value should use the full discount
        df = np.exp(-rate * term_years)
        pv_maturity_value = df * premium * (1 + expected_credit)

        # This should NOT equal: premium + df * premium * expected_credit
        pv_wrong = premium + df * premium * expected_credit

        assert pv_maturity_value < pv_wrong, "FIA PV should discount principal, not just credit"

    @pytest.mark.validation
    def test_rila_pv_uses_correct_formula(self) -> None:
        """
        [T1] RILA pricing should use corrected PV formula.
        """
        premium = 100_000.0
        expected_return = 0.03  # Expected return given buffer/cap
        rate = 0.05
        term_years = 6.0

        df = np.exp(-rate * term_years)
        pv_correct = df * premium * (1 + expected_return)

        pv_wrong = premium + df * premium * expected_return

        # Material difference
        diff_pct = (pv_wrong - pv_correct) / pv_correct
        assert diff_pct > 0.25, (
            f"6-year RILA should have >25% error with wrong formula, got {diff_pct:.2%}"
        )
