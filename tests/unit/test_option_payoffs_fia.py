"""
Tests for FIA (Fixed Indexed Annuity) payoffs.

Tests crediting methods:
- Cap: Point-to-point with maximum return cap
- Participation: Partial participation in index returns
- Spread: Index return minus spread/margin
- Trigger: Performance triggered bonus

See: docs/knowledge/domain/crediting_methods.md
"""

import numpy as np
import pytest

from annuity_pricing.options.payoffs.base import CreditingMethod, IndexPath
from annuity_pricing.options.payoffs.fia import (
    CappedCallPayoff,
    MonthlyAveragePayoff,
    ParticipationPayoff,
    SpreadPayoff,
    TriggerPayoff,
    create_fia_payoff,
)


class TestCappedCallPayoff:
    """Tests for capped call crediting method."""

    def test_return_below_cap(self):
        """[T1] Returns below cap pass through unchanged."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        result = payoff.calculate(0.08)

        assert result.credited_return == 0.08
        assert not result.cap_applied
        assert not result.floor_applied

    def test_return_above_cap(self):
        """[T1] Returns above cap are capped."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        result = payoff.calculate(0.15)

        assert result.credited_return == 0.10
        assert result.cap_applied

    def test_negative_return_floored(self):
        """[T1] Negative returns floored at 0% (principal protection)."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        result = payoff.calculate(-0.05)

        assert result.credited_return == 0.0
        assert result.floor_applied

    def test_return_exactly_at_cap(self):
        """Return exactly at cap."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        result = payoff.calculate(0.10)

        assert result.credited_return == 0.10
        assert not result.cap_applied  # Not above cap

    def test_zero_return(self):
        """Zero return stays zero."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        result = payoff.calculate(0.0)

        assert result.credited_return == 0.0
        assert not result.floor_applied
        assert not result.cap_applied

    def test_validation_cap_must_be_positive(self):
        """Cap rate must be positive."""
        with pytest.raises(ValueError, match="must be > 0"):
            CappedCallPayoff(cap_rate=0)

        with pytest.raises(ValueError, match="must be > 0"):
            CappedCallPayoff(cap_rate=-0.05)

    def test_validation_floor_cannot_exceed_cap(self):
        """Floor cannot exceed cap."""
        with pytest.raises(ValueError, match="cannot exceed cap_rate"):
            CappedCallPayoff(cap_rate=0.05, floor_rate=0.10)

    def test_method_is_cap(self):
        """Method should be CAP."""
        payoff = CappedCallPayoff(cap_rate=0.10)
        assert payoff.method == CreditingMethod.CAP


class TestParticipationPayoff:
    """Tests for participation rate crediting method."""

    def test_positive_return_participation(self):
        """[T1] Positive returns multiplied by participation rate."""
        payoff = ParticipationPayoff(participation_rate=0.80)
        result = payoff.calculate(0.10)

        assert result.credited_return == pytest.approx(0.08)  # 80% of 10%

    def test_negative_return_floored(self):
        """[T1] Negative returns floored at 0%."""
        payoff = ParticipationPayoff(participation_rate=0.80)
        result = payoff.calculate(-0.10)

        assert result.credited_return == 0.0
        assert result.floor_applied

    def test_zero_return(self):
        """Zero return stays zero."""
        payoff = ParticipationPayoff(participation_rate=0.80)
        result = payoff.calculate(0.0)

        assert result.credited_return == 0.0

    def test_with_cap(self):
        """Participation with cap."""
        payoff = ParticipationPayoff(participation_rate=0.80, cap_rate=0.06)
        result = payoff.calculate(0.10)

        # 80% of 10% = 8%, but capped at 6%
        assert result.credited_return == 0.06
        assert result.cap_applied

    def test_participation_greater_than_100(self):
        """Participation rates can exceed 100%."""
        payoff = ParticipationPayoff(participation_rate=1.20)  # 120%
        result = payoff.calculate(0.10)

        assert result.credited_return == pytest.approx(0.12)  # 120% of 10%

    def test_validation_positive_participation(self):
        """Participation rate must be positive."""
        with pytest.raises(ValueError, match="must be > 0"):
            ParticipationPayoff(participation_rate=0)

    def test_method_is_participation(self):
        """Method should be PARTICIPATION."""
        payoff = ParticipationPayoff(participation_rate=0.80)
        assert payoff.method == CreditingMethod.PARTICIPATION


class TestSpreadPayoff:
    """Tests for spread/margin crediting method."""

    def test_positive_return_minus_spread(self):
        """[T1] Positive returns reduced by spread."""
        payoff = SpreadPayoff(spread_rate=0.02)
        result = payoff.calculate(0.10)

        assert result.credited_return == pytest.approx(0.08)  # 10% - 2%

    def test_return_less_than_spread(self):
        """Return less than spread floors at 0%."""
        payoff = SpreadPayoff(spread_rate=0.02)
        result = payoff.calculate(0.01)

        # 1% - 2% = -1%, but floored at 0%
        assert result.credited_return == 0.0
        assert result.floor_applied

    def test_negative_return_floored(self):
        """[T1] Negative returns floored at 0%."""
        payoff = SpreadPayoff(spread_rate=0.02)
        result = payoff.calculate(-0.05)

        assert result.credited_return == 0.0

    def test_with_cap(self):
        """Spread with cap."""
        payoff = SpreadPayoff(spread_rate=0.02, cap_rate=0.06)
        result = payoff.calculate(0.10)

        # 10% - 2% = 8%, but capped at 6%
        assert result.credited_return == 0.06
        assert result.cap_applied

    def test_zero_spread(self):
        """Zero spread passes through."""
        payoff = SpreadPayoff(spread_rate=0.0)
        result = payoff.calculate(0.10)

        assert result.credited_return == 0.10

    def test_validation_non_negative_spread(self):
        """Spread rate must be non-negative."""
        with pytest.raises(ValueError, match="must be >= 0"):
            SpreadPayoff(spread_rate=-0.01)

    def test_method_is_spread(self):
        """Method should be SPREAD."""
        payoff = SpreadPayoff(spread_rate=0.02)
        assert payoff.method == CreditingMethod.SPREAD


class TestTriggerPayoff:
    """Tests for trigger/bonus crediting method."""

    def test_trigger_met_positive_return(self):
        """[T1] Trigger met when return >= threshold."""
        payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0)
        result = payoff.calculate(0.01)  # Small positive return

        assert result.credited_return == 0.05
        assert result.details["trigger_met"]

    def test_trigger_not_met_negative_return(self):
        """[T1] Trigger not met when return < threshold."""
        payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0)
        result = payoff.calculate(-0.01)

        assert result.credited_return == 0.0
        assert not result.details["trigger_met"]
        assert result.floor_applied

    def test_trigger_exactly_at_threshold(self):
        """Trigger met when return exactly equals threshold."""
        payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0)
        result = payoff.calculate(0.0)

        assert result.credited_return == 0.05
        assert result.details["trigger_met"]

    def test_custom_threshold(self):
        """Custom trigger threshold."""
        payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.02)

        # Below threshold
        result1 = payoff.calculate(0.01)
        assert result1.credited_return == 0.0
        assert not result1.details["trigger_met"]

        # At/above threshold
        result2 = payoff.calculate(0.02)
        assert result2.credited_return == 0.05
        assert result2.details["trigger_met"]

    def test_custom_floor(self):
        """Custom floor when trigger not met."""
        payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0, floor_rate=0.01)
        result = payoff.calculate(-0.10)

        assert result.credited_return == 0.01
        assert result.floor_applied

    def test_validation_non_negative_trigger(self):
        """Trigger rate must be non-negative."""
        with pytest.raises(ValueError, match="must be >= 0"):
            TriggerPayoff(trigger_rate=-0.01)

    def test_method_is_trigger(self):
        """Method should be TRIGGER."""
        payoff = TriggerPayoff(trigger_rate=0.05)
        assert payoff.method == CreditingMethod.TRIGGER


class TestMonthlyAveragePayoff:
    """Tests for monthly averaging crediting method."""

    def test_simple_calculate(self):
        """Simple calculation uses point-to-point."""
        payoff = MonthlyAveragePayoff(cap_rate=0.15)
        result = payoff.calculate(0.10)

        assert result.credited_return == 0.10

    def test_calculate_from_path(self):
        """Calculate from path uses monthly averaging."""
        payoff = MonthlyAveragePayoff(cap_rate=0.20)

        # Simulate a year with monthly observations
        # Initial: 100, monthly values show gradual increase
        initial = 100.0
        values = [100, 102, 105, 103, 108, 110, 112, 115, 113, 118, 120, 122, 125]
        times = [i / 12 for i in range(13)]  # 0, 1/12, 2/12, ..., 1

        path = IndexPath(times=tuple(times), values=tuple(values), initial_value=initial)

        result = payoff.calculate_from_path(path)

        # Average = mean of all values
        avg = np.mean(values)
        expected_return = (avg - initial) / initial
        assert result.credited_return == pytest.approx(expected_return)

    def test_short_path_uses_point_to_point(self):
        """Short paths fall back to point-to-point."""
        payoff = MonthlyAveragePayoff(cap_rate=0.20)

        path = IndexPath(times=(0.0,), values=(100.0,), initial_value=100.0)
        result = payoff.calculate_from_path(path)

        assert result.credited_return == 0.0


class TestCreateFiaPayoff:
    """Tests for factory function."""

    def test_create_cap(self):
        """Create capped call payoff."""
        payoff = create_fia_payoff("cap", cap_rate=0.10)
        assert isinstance(payoff, CappedCallPayoff)
        assert payoff.cap_rate == 0.10

    def test_create_participation(self):
        """Create participation payoff."""
        payoff = create_fia_payoff("participation", participation_rate=0.80)
        assert isinstance(payoff, ParticipationPayoff)
        assert payoff.participation_rate == 0.80

    def test_create_spread(self):
        """Create spread payoff."""
        payoff = create_fia_payoff("spread", spread_rate=0.02)
        assert isinstance(payoff, SpreadPayoff)
        assert payoff.spread_rate == 0.02

    def test_create_trigger(self):
        """Create trigger payoff."""
        payoff = create_fia_payoff("trigger", trigger_rate=0.05)
        assert isinstance(payoff, TriggerPayoff)
        assert payoff.trigger_rate == 0.05

    def test_invalid_method(self):
        """Invalid method raises error."""
        with pytest.raises(ValueError, match="Unknown crediting method"):
            create_fia_payoff("invalid")

    def test_missing_cap_rate(self):
        """Missing cap_rate raises error."""
        with pytest.raises(ValueError, match="cap_rate required"):
            create_fia_payoff("cap")

    def test_missing_participation_rate(self):
        """Missing participation_rate raises error."""
        with pytest.raises(ValueError, match="participation_rate required"):
            create_fia_payoff("participation")


class TestFIAAntiPatterns:
    """Anti-pattern tests for FIA payoffs.

    These tests encode critical invariants for FIA products.
    [T1] FIA products have 0% floor (principal protection).
    """

    def test_fia_never_negative_cap(self):
        """[T1] Capped call never returns negative."""
        payoff = CappedCallPayoff(cap_rate=0.10)

        for r in [-0.50, -0.25, -0.10, -0.01]:
            result = payoff.calculate(r)
            assert result.credited_return >= 0, (
                f"Negative credited return {result.credited_return} for {r}"
            )

    def test_fia_never_negative_participation(self):
        """[T1] Participation never returns negative."""
        payoff = ParticipationPayoff(participation_rate=0.80)

        for r in [-0.50, -0.25, -0.10, -0.01]:
            result = payoff.calculate(r)
            assert result.credited_return >= 0

    def test_fia_never_negative_spread(self):
        """[T1] Spread never returns negative."""
        payoff = SpreadPayoff(spread_rate=0.02)

        for r in [-0.50, -0.25, -0.10, -0.01]:
            result = payoff.calculate(r)
            assert result.credited_return >= 0

    def test_fia_never_negative_trigger(self):
        """[T1] Trigger never returns negative (with default floor)."""
        payoff = TriggerPayoff(trigger_rate=0.05)

        for r in [-0.50, -0.25, -0.10, -0.01]:
            result = payoff.calculate(r)
            assert result.credited_return >= 0

    def test_cap_never_exceeds_cap_rate(self):
        """[T1] Capped return never exceeds cap."""
        payoff = CappedCallPayoff(cap_rate=0.10)

        for r in [0.10, 0.15, 0.50, 1.00]:
            result = payoff.calculate(r)
            assert result.credited_return <= payoff.cap_rate, (
                f"Exceeded cap: {result.credited_return} > {payoff.cap_rate}"
            )

    def test_participation_proportional(self):
        """[T1] Participation return proportional to index return."""
        payoff = ParticipationPayoff(participation_rate=0.80)

        # For positive returns (no cap), should be exactly proportional
        for r in [0.05, 0.10, 0.20]:
            result = payoff.calculate(r)
            expected = r * 0.80
            assert result.credited_return == pytest.approx(expected)
