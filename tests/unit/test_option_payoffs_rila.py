"""
Tests for RILA (Registered Index-Linked Annuity) payoffs.

Tests buffer and floor protection mechanics:
- Buffer: Absorbs FIRST X% of losses
- Floor: Limits MAXIMUM loss to X%

See: docs/knowledge/domain/buffer_floor.md
"""

import numpy as np
import pytest

from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    BufferWithFloorPayoff,
    FloorPayoff,
    StepRateBufferPayoff,
    compare_buffer_vs_floor,
    create_rila_payoff,
)
from annuity_pricing.options.payoffs.base import CreditingMethod


class TestBufferPayoff:
    """Tests for buffer protection mechanism."""

    def test_buffer_positive_return_no_cap(self):
        """[T1] Positive returns pass through unchanged without cap."""
        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(0.15)

        assert result.credited_return == 0.15
        assert result.index_return == 0.15
        assert not result.cap_applied
        assert not result.floor_applied

    def test_buffer_positive_return_with_cap(self):
        """[T1] Positive returns capped when exceeding cap_rate."""
        payoff = BufferPayoff(buffer_rate=0.10, cap_rate=0.12)
        result = payoff.calculate(0.15)

        assert result.credited_return == 0.12
        assert result.cap_applied

    def test_buffer_fully_absorbs_small_loss(self):
        """[T1] Buffer absorbs losses smaller than buffer rate."""
        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(-0.08)

        # -8% loss fully absorbed by 10% buffer
        assert result.credited_return == 0.0
        assert result.details["buffer_applied"]
        assert result.details["buffer_benefit"] == 0.08

    def test_buffer_partial_protection_large_loss(self):
        """[T1] Buffer absorbs first X%, then dollar-for-dollar."""
        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(-0.15)

        # -15% loss: buffer absorbs 10%, policyholder takes 5%
        assert result.credited_return == pytest.approx(-0.05)
        assert result.details["buffer_applied"]
        assert result.details["buffer_benefit"] == 0.10

    def test_buffer_zero_return(self):
        """Zero return stays zero."""
        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(0.0)

        assert result.credited_return == 0.0
        assert not result.details["buffer_applied"]

    def test_buffer_exactly_at_buffer_rate(self):
        """Loss exactly equal to buffer rate results in 0%."""
        payoff = BufferPayoff(buffer_rate=0.10)
        result = payoff.calculate(-0.10)

        assert result.credited_return == 0.0
        assert result.details["buffer_applied"]

    def test_buffer_validation_positive_buffer(self):
        """Buffer rate must be positive."""
        with pytest.raises(ValueError, match="must be > 0"):
            BufferPayoff(buffer_rate=0)

        with pytest.raises(ValueError, match="must be > 0"):
            BufferPayoff(buffer_rate=-0.10)

    def test_buffer_validation_max_100_percent(self):
        """Buffer rate cannot exceed 100%."""
        with pytest.raises(ValueError, match="must be <= 1"):
            BufferPayoff(buffer_rate=1.5)

    def test_buffer_method_is_buffer(self):
        """Method should be BUFFER."""
        payoff = BufferPayoff(buffer_rate=0.10)
        assert payoff.method == CreditingMethod.BUFFER


class TestFloorPayoff:
    """Tests for floor protection mechanism."""

    def test_floor_positive_return_no_cap(self):
        """[T1] Positive returns pass through unchanged."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(0.15)

        assert result.credited_return == 0.15
        assert not result.floor_applied

    def test_floor_positive_return_with_cap(self):
        """[T1] Positive returns capped when exceeding cap_rate."""
        payoff = FloorPayoff(floor_rate=-0.10, cap_rate=0.12)
        result = payoff.calculate(0.15)

        assert result.credited_return == 0.12
        assert result.cap_applied

    def test_floor_no_protection_small_loss(self):
        """[T1] Small losses pass through (no protection until floor)."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(-0.08)

        # -8% loss, floor is -10%, so no protection
        assert result.credited_return == -0.08
        assert not result.floor_applied

    def test_floor_protection_large_loss(self):
        """[T1] Large losses floored at floor_rate."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(-0.15)

        # -15% loss floored to -10%
        assert result.credited_return == -0.10
        assert result.floor_applied
        assert result.details["floor_benefit"] == pytest.approx(-0.10 - (-0.15))

    def test_floor_exactly_at_floor_rate(self):
        """Loss exactly at floor rate."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(-0.10)

        # Exactly at floor - no protection applied
        assert result.credited_return == -0.10
        assert not result.floor_applied

    def test_floor_zero_return(self):
        """Zero return stays zero."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(0.0)

        assert result.credited_return == 0.0

    def test_floor_validation_must_be_negative(self):
        """Floor rate must be <= 0 for loss protection."""
        with pytest.raises(ValueError, match="should be <= 0"):
            FloorPayoff(floor_rate=0.10)

    def test_floor_validation_min_negative_100(self):
        """Floor rate cannot be less than -100%."""
        with pytest.raises(ValueError, match="cannot be < -1"):
            FloorPayoff(floor_rate=-1.5)

    def test_floor_method_is_floor(self):
        """Method should be FLOOR."""
        payoff = FloorPayoff(floor_rate=-0.10)
        assert payoff.method == CreditingMethod.FLOOR


class TestBufferVsFloorComparison:
    """Tests comparing buffer vs floor mechanics."""

    def test_buffer_better_for_small_losses(self):
        """[T1] Buffer outperforms floor for small losses."""
        # 10% buffer vs -10% floor
        buffer = BufferPayoff(buffer_rate=0.10)
        floor = FloorPayoff(floor_rate=-0.10)

        # -5% loss
        buffer_result = buffer.calculate(-0.05)
        floor_result = floor.calculate(-0.05)

        # Buffer: 0% (absorbed), Floor: -5% (no protection)
        assert buffer_result.credited_return == 0.0
        assert floor_result.credited_return == -0.05
        assert buffer_result.credited_return > floor_result.credited_return

    def test_floor_better_for_large_losses(self):
        """[T1] Floor outperforms buffer for large losses (tail protection)."""
        # 10% buffer vs -10% floor
        buffer = BufferPayoff(buffer_rate=0.10)
        floor = FloorPayoff(floor_rate=-0.10)

        # -25% loss
        buffer_result = buffer.calculate(-0.25)
        floor_result = floor.calculate(-0.25)

        # Buffer: -15% (only first 10% absorbed), Floor: -10% (floored)
        assert buffer_result.credited_return == pytest.approx(-0.15)
        assert floor_result.credited_return == -0.10
        assert floor_result.credited_return > buffer_result.credited_return

    def test_equal_at_crossover_point(self):
        """Buffer and floor give same result at crossover point."""
        # 10% buffer vs -10% floor
        # Crossover: loss where buffer result = floor result
        # Buffer: return + 0.10 = Floor: max(return, -0.10)
        # At -20%: Buffer gives -10%, Floor gives -10%
        buffer = BufferPayoff(buffer_rate=0.10)
        floor = FloorPayoff(floor_rate=-0.10)

        buffer_result = buffer.calculate(-0.20)
        floor_result = floor.calculate(-0.20)

        assert buffer_result.credited_return == pytest.approx(-0.10)
        assert floor_result.credited_return == -0.10

    def test_compare_buffer_vs_floor_function(self):
        """Test comparison helper function."""
        returns = np.linspace(-0.30, 0.30, 61)
        comparison = compare_buffer_vs_floor(
            buffer_rate=0.10, floor_rate=-0.10, index_returns=returns
        )

        assert len(comparison["buffer_credits"]) == 61
        assert len(comparison["floor_credits"]) == 61
        assert comparison["buffer_rate"] == 0.10
        assert comparison["floor_rate"] == -0.10


class TestBufferWithFloorPayoff:
    """Tests for combined buffer + floor protection."""

    def test_combined_positive_return(self):
        """Positive returns pass through (subject to cap)."""
        payoff = BufferWithFloorPayoff(buffer_rate=0.10, floor_rate=-0.20)
        result = payoff.calculate(0.12)

        assert result.credited_return == 0.12

    def test_combined_small_loss_buffer_absorbs(self):
        """Small losses absorbed by buffer."""
        payoff = BufferWithFloorPayoff(buffer_rate=0.10, floor_rate=-0.20)
        result = payoff.calculate(-0.08)

        assert result.credited_return == 0.0
        assert result.details["buffer_applied"]
        assert not result.floor_applied

    def test_combined_medium_loss_partial_buffer(self):
        """Medium losses: buffer absorbs first X%."""
        payoff = BufferWithFloorPayoff(buffer_rate=0.10, floor_rate=-0.20)
        result = payoff.calculate(-0.25)

        # -25% + 10% buffer = -15% (within floor)
        assert result.credited_return == pytest.approx(-0.15)
        assert result.details["buffer_applied"]
        assert not result.floor_applied

    def test_combined_large_loss_hits_floor(self):
        """Large losses hit floor after buffer."""
        payoff = BufferWithFloorPayoff(buffer_rate=0.10, floor_rate=-0.20)
        result = payoff.calculate(-0.35)

        # -35% + 10% buffer = -25%, but floored to -20%
        assert result.credited_return == -0.20
        assert result.details["buffer_applied"]
        assert result.floor_applied


class TestStepRateBufferPayoff:
    """Tests for tiered buffer protection."""

    def test_tier1_full_protection(self):
        """Losses within tier 1 fully absorbed."""
        payoff = StepRateBufferPayoff(
            tier1_buffer=0.10, tier2_buffer=0.10, tier2_protection=0.50
        )
        result = payoff.calculate(-0.08)

        assert result.credited_return == 0.0

    def test_tier2_partial_protection(self):
        """Losses in tier 2 get partial protection."""
        payoff = StepRateBufferPayoff(
            tier1_buffer=0.10, tier2_buffer=0.10, tier2_protection=0.50
        )
        # -15% loss: tier 1 absorbs 10%, tier 2 absorbs 50% of next 5%
        result = payoff.calculate(-0.15)

        # -15% + 10% (tier1) + 2.5% (tier2: 50% of 5%) = -2.5%
        assert result.credited_return == pytest.approx(-0.025)

    def test_beyond_tier2(self):
        """Losses beyond tier 2 are dollar-for-dollar."""
        payoff = StepRateBufferPayoff(
            tier1_buffer=0.10, tier2_buffer=0.10, tier2_protection=0.50
        )
        # -25% loss: tier 1 absorbs 10%, tier 2 absorbs 5% (50% of 10%),
        # beyond: 5% dollar-for-dollar
        result = payoff.calculate(-0.25)

        # Loss calculation: 25% total
        # Tier 1: absorbs 10% → 15% remaining
        # Tier 2: 10% at 50% protection → absorbs 5%, 5% remains
        # Beyond: 5% remaining
        # Total absorbed: 15%, policyholder: 10%
        assert result.credited_return == pytest.approx(-0.10)


class TestCreateRilaPayoff:
    """Tests for factory function."""

    def test_create_buffer(self):
        """Create buffer payoff."""
        payoff = create_rila_payoff("buffer", buffer_rate=0.10)
        assert isinstance(payoff, BufferPayoff)
        assert payoff.buffer_rate == 0.10

    def test_create_floor(self):
        """Create floor payoff."""
        payoff = create_rila_payoff("floor", floor_rate=-0.10)
        assert isinstance(payoff, FloorPayoff)
        assert payoff.floor_rate == -0.10

    def test_create_buffer_floor(self):
        """Create combined buffer+floor payoff."""
        payoff = create_rila_payoff("buffer_floor", buffer_rate=0.10, floor_rate=-0.20)
        assert isinstance(payoff, BufferWithFloorPayoff)

    def test_create_with_cap(self):
        """Create payoff with cap."""
        payoff = create_rila_payoff("buffer", buffer_rate=0.10, cap_rate=0.15)
        assert payoff.cap_rate == 0.15

    def test_invalid_protection_type(self):
        """Invalid protection type raises error."""
        with pytest.raises(ValueError, match="Unknown protection type"):
            create_rila_payoff("invalid")

    def test_missing_buffer_rate(self):
        """Missing buffer_rate raises error."""
        with pytest.raises(ValueError, match="buffer_rate required"):
            create_rila_payoff("buffer")

    def test_missing_floor_rate(self):
        """Missing floor_rate raises error."""
        with pytest.raises(ValueError, match="floor_rate required"):
            create_rila_payoff("floor")


class TestAntiPatterns:
    """Anti-pattern tests for RILA payoffs.

    These tests encode critical bugs we must prevent.
    See: docs/episodes/bugs/
    """

    def test_buffer_never_credits_positive_from_negative_return(self):
        """[T1] Buffer cannot make negative return positive beyond 0%."""
        payoff = BufferPayoff(buffer_rate=0.50)  # Large buffer
        result = payoff.calculate(-0.08)

        # Even with 50% buffer on -8% return, max is 0%
        assert result.credited_return == 0.0
        assert result.credited_return <= 0.0  # Never positive from negative

    def test_floor_never_increases_positive_return(self):
        """[T1] Floor cannot increase positive returns."""
        payoff = FloorPayoff(floor_rate=-0.10)
        result = payoff.calculate(0.05)

        assert result.credited_return == 0.05
        assert result.credited_return == result.index_return

    def test_buffer_protection_monotonic(self):
        """[T1] Buffer protection is monotonically increasing with loss."""
        payoff = BufferPayoff(buffer_rate=0.10)

        returns = [-0.05, -0.10, -0.15, -0.20, -0.25]
        credits = [payoff.calculate(r).credited_return for r in returns]

        # Credited returns should be decreasing (more loss = worse outcome)
        for i in range(len(credits) - 1):
            assert credits[i] >= credits[i + 1], f"Non-monotonic at {returns[i]}"

    def test_floor_protection_monotonic(self):
        """[T1] Floor protection is monotonically increasing with loss until floor."""
        payoff = FloorPayoff(floor_rate=-0.10)

        returns = [-0.05, -0.10, -0.15, -0.20, -0.25]
        credits = [payoff.calculate(r).credited_return for r in returns]

        # After floor, all should equal floor
        for c in credits[1:]:  # After -10%
            assert c == -0.10

    def test_buffer_dollar_for_dollar_after_exhaustion(self):
        """[T1] After buffer exhausted, losses are dollar-for-dollar."""
        payoff = BufferPayoff(buffer_rate=0.10)

        # Two points after buffer exhausted
        result1 = payoff.calculate(-0.20)  # -10% after buffer
        result2 = payoff.calculate(-0.25)  # -15% after buffer

        # Difference should equal 5%
        diff = result1.credited_return - result2.credited_return
        assert diff == pytest.approx(0.05)
