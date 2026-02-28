"""
Property-based tests for FIA and RILA payoffs.

Uses Hypothesis to verify payoff invariants hold across randomly
generated inputs. Tests the fundamental contractual guarantees.

Properties tested:
1. FIA floor: credited_return >= 0 (principal protection)
2. FIA cap: credited_return <= cap_rate
3. Buffer absorption: -buffer <= loss <= 0 → credited_return = 0
4. Buffer pass-through: loss > buffer → credited_return = loss + buffer
5. Floor protection: credited_return >= floor_rate always
6. Participation scaling: credited_return = participation × index_return (for positive)
7. Spread deduction: credited_return = index_return - spread (for positive)
8. Trigger binary: credited_return ∈ {floor_rate, trigger_rate}

References:
    [T1] SEC RILA Final Rule 2024
    [T1] Buffer vs Floor mechanism documentation

See: docs/knowledge/domain/buffer_floor.md
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
    BUFFER_ABSORPTION_TOLERANCE,
    CAP_ENFORCEMENT_TOLERANCE,
    FLOOR_ENFORCEMENT_TOLERANCE,
)
from annuity_pricing.options.payoffs.fia import (
    CappedCallPayoff,
    ParticipationPayoff,
    SpreadPayoff,
    TriggerPayoff,
)
from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    FloorPayoff,
)

# =============================================================================
# Strategy Definitions
# =============================================================================

# Index return: realistic range
return_strategy = st.floats(min_value=-0.50, max_value=0.50, allow_nan=False, allow_infinity=False)

# Cap rate: positive, typical FIA range
cap_strategy = st.floats(min_value=0.01, max_value=0.30, allow_nan=False, allow_infinity=False)

# Buffer rate: positive, typical RILA range
buffer_strategy = st.floats(min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False)

# Floor rate: negative, typical RILA range
floor_strategy = st.floats(min_value=-0.30, max_value=-0.01, allow_nan=False, allow_infinity=False)

# Participation rate: typically 50% to 150%
participation_strategy = st.floats(
    min_value=0.50, max_value=1.50, allow_nan=False, allow_infinity=False
)

# Spread rate: small positive
spread_strategy = st.floats(min_value=0.005, max_value=0.05, allow_nan=False, allow_infinity=False)

# Trigger rate: fixed bonus
trigger_strategy = st.floats(min_value=0.02, max_value=0.10, allow_nan=False, allow_infinity=False)


# =============================================================================
# FIA Cap Properties
# =============================================================================


class TestCappedCallProperties:
    """[T1] Capped call payoff: max(floor, min(index_return, cap))."""

    @given(
        index_return=return_strategy,
        cap_rate=cap_strategy,
    )
    @settings(max_examples=200)
    def test_floor_enforced(self, index_return: float, cap_rate: float) -> None:
        """[T1] FIA floor is always 0% (principal protection)."""
        payoff = CappedCallPayoff(cap_rate=cap_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert result.credited_return >= -FLOOR_ENFORCEMENT_TOLERANCE, (
            f"FIA floor violated: credited={result.credited_return}, expected >= 0"
        )

    @given(
        index_return=return_strategy,
        cap_rate=cap_strategy,
    )
    @settings(max_examples=200)
    def test_cap_enforced(self, index_return: float, cap_rate: float) -> None:
        """[T1] Credited return never exceeds cap."""
        payoff = CappedCallPayoff(cap_rate=cap_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert result.credited_return <= cap_rate + CAP_ENFORCEMENT_TOLERANCE, (
            f"Cap violated: credited={result.credited_return}, cap={cap_rate}"
        )

    @given(
        index_return=st.floats(
            min_value=0.0, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        cap_rate=cap_strategy,
    )
    @settings(max_examples=200)
    def test_positive_return_capped(self, index_return: float, cap_rate: float) -> None:
        """[T1] Positive returns are min(index_return, cap)."""
        payoff = CappedCallPayoff(cap_rate=cap_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)
        expected = min(index_return, cap_rate)

        assert abs(result.credited_return - expected) < ANTI_PATTERN_TOLERANCE, (
            f"Capped return incorrect: got {result.credited_return}, expected {expected}"
        )


# =============================================================================
# FIA Participation Properties
# =============================================================================


class TestParticipationProperties:
    """[T1] Participation payoff: max(floor, participation × max(0, return))."""

    @given(
        index_return=return_strategy,
        participation_rate=participation_strategy,
    )
    @settings(max_examples=200)
    def test_floor_enforced(self, index_return: float, participation_rate: float) -> None:
        """[T1] Participation payoff never below floor."""
        payoff = ParticipationPayoff(participation_rate=participation_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert result.credited_return >= -FLOOR_ENFORCEMENT_TOLERANCE, (
            f"Floor violated: credited={result.credited_return}"
        )

    @given(
        index_return=st.floats(
            min_value=0.01, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        participation_rate=participation_strategy,
    )
    @settings(max_examples=200)
    def test_participation_scaling(self, index_return: float, participation_rate: float) -> None:
        """[T1] Positive returns scaled by participation rate."""
        payoff = ParticipationPayoff(participation_rate=participation_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)
        expected = participation_rate * index_return

        assert abs(result.credited_return - expected) < ANTI_PATTERN_TOLERANCE, (
            f"Participation scaling wrong: got {result.credited_return}, "
            f"expected {expected} = {participation_rate} × {index_return}"
        )

    @given(
        index_return=st.floats(
            min_value=-0.30, max_value=-0.01, allow_nan=False, allow_infinity=False
        ),
        participation_rate=participation_strategy,
    )
    @settings(max_examples=200)
    def test_negative_return_floored(self, index_return: float, participation_rate: float) -> None:
        """[T1] Negative returns give floor (0%)."""
        payoff = ParticipationPayoff(participation_rate=participation_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return) < ANTI_PATTERN_TOLERANCE, (
            f"Negative return not floored: got {result.credited_return}, expected 0"
        )


# =============================================================================
# FIA Spread Properties
# =============================================================================


class TestSpreadProperties:
    """[T1] Spread payoff: max(floor, return - spread) for positive returns."""

    @given(
        index_return=return_strategy,
        spread_rate=spread_strategy,
    )
    @settings(max_examples=200)
    def test_floor_enforced(self, index_return: float, spread_rate: float) -> None:
        """[T1] Spread payoff never below floor."""
        payoff = SpreadPayoff(spread_rate=spread_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert result.credited_return >= -FLOOR_ENFORCEMENT_TOLERANCE, (
            f"Floor violated: credited={result.credited_return}"
        )

    @given(
        index_return=st.floats(
            min_value=0.10, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        spread_rate=spread_strategy,
    )
    @settings(max_examples=200)
    def test_spread_deduction(self, index_return: float, spread_rate: float) -> None:
        """[T1] Positive returns reduced by spread."""
        # Ensure return > spread to avoid floor
        assume(index_return > spread_rate)

        payoff = SpreadPayoff(spread_rate=spread_rate, floor_rate=0.0)
        result = payoff.calculate(index_return)
        expected = index_return - spread_rate

        assert abs(result.credited_return - expected) < ANTI_PATTERN_TOLERANCE, (
            f"Spread deduction wrong: got {result.credited_return}, "
            f"expected {expected} = {index_return} - {spread_rate}"
        )


# =============================================================================
# FIA Trigger Properties
# =============================================================================


class TestTriggerProperties:
    """[T1] Trigger payoff: trigger_rate if threshold met, else floor."""

    @given(
        index_return=return_strategy,
        trigger_rate=trigger_strategy,
    )
    @settings(max_examples=200)
    def test_trigger_binary(self, index_return: float, trigger_rate: float) -> None:
        """[T1] Trigger returns exactly trigger_rate or floor_rate."""
        payoff = TriggerPayoff(trigger_rate=trigger_rate, trigger_threshold=0.0, floor_rate=0.0)
        result = payoff.calculate(index_return)

        valid_values = [0.0, trigger_rate]
        min_dist = min(abs(result.credited_return - v) for v in valid_values)

        assert min_dist < ANTI_PATTERN_TOLERANCE, (
            f"Trigger not binary: got {result.credited_return}, expected one of {valid_values}"
        )

    @given(
        index_return=st.floats(
            min_value=0.001, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        trigger_rate=trigger_strategy,
    )
    @settings(max_examples=200)
    def test_trigger_met(self, index_return: float, trigger_rate: float) -> None:
        """[T1] Positive return meets trigger threshold."""
        payoff = TriggerPayoff(trigger_rate=trigger_rate, trigger_threshold=0.0, floor_rate=0.0)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return - trigger_rate) < ANTI_PATTERN_TOLERANCE, (
            f"Trigger should be met: got {result.credited_return}, expected {trigger_rate}"
        )


# =============================================================================
# RILA Buffer Properties
# =============================================================================


class TestBufferProperties:
    """[T1] Buffer payoff: absorbs first X% of losses."""

    @given(
        index_return=st.floats(
            min_value=-0.50, max_value=-0.001, allow_nan=False, allow_infinity=False
        ),
        buffer_rate=buffer_strategy,
    )
    @settings(max_examples=200)
    def test_buffer_absorption_within_buffer(self, index_return: float, buffer_rate: float) -> None:
        """[T1] Losses within buffer result in 0% credited return."""
        # Only test when loss is within buffer
        assume(-index_return <= buffer_rate)

        payoff = BufferPayoff(buffer_rate=buffer_rate)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return) < BUFFER_ABSORPTION_TOLERANCE, (
            f"Buffer should absorb loss: return={index_return}, buffer={buffer_rate}, "
            f"credited={result.credited_return}, expected 0"
        )

    @given(
        index_return=st.floats(
            min_value=-0.50, max_value=-0.001, allow_nan=False, allow_infinity=False
        ),
        buffer_rate=buffer_strategy,
    )
    @settings(max_examples=200)
    def test_buffer_pass_through_beyond_buffer(
        self, index_return: float, buffer_rate: float
    ) -> None:
        """[T1] Losses beyond buffer pass through dollar-for-dollar."""
        # Only test when loss exceeds buffer
        assume(-index_return > buffer_rate)

        payoff = BufferPayoff(buffer_rate=buffer_rate)
        result = payoff.calculate(index_return)
        expected = index_return + buffer_rate  # Loss minus buffer absorption

        assert abs(result.credited_return - expected) < BUFFER_ABSORPTION_TOLERANCE, (
            f"Buffer pass-through wrong: return={index_return}, buffer={buffer_rate}, "
            f"credited={result.credited_return}, expected={expected}"
        )

    @given(
        index_return=st.floats(
            min_value=0.0, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        buffer_rate=buffer_strategy,
    )
    @settings(max_examples=200)
    def test_buffer_full_upside(self, index_return: float, buffer_rate: float) -> None:
        """[T1] Positive returns get full upside (no cap in basic buffer)."""
        payoff = BufferPayoff(buffer_rate=buffer_rate)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return - index_return) < ANTI_PATTERN_TOLERANCE, (
            f"Buffer should give full upside: return={index_return}, "
            f"credited={result.credited_return}"
        )


# =============================================================================
# RILA Floor Properties
# =============================================================================


class TestFloorProperties:
    """[T1] Floor payoff: limits maximum loss."""

    @given(
        index_return=return_strategy,
        floor_rate=floor_strategy,
    )
    @settings(max_examples=200)
    def test_floor_enforced(self, index_return: float, floor_rate: float) -> None:
        """[T1] Credited return never below floor."""
        payoff = FloorPayoff(floor_rate=floor_rate)
        result = payoff.calculate(index_return)

        assert result.credited_return >= floor_rate - FLOOR_ENFORCEMENT_TOLERANCE, (
            f"Floor violated: credited={result.credited_return}, floor={floor_rate}"
        )

    @given(
        index_return=st.floats(
            min_value=-0.50, max_value=-0.001, allow_nan=False, allow_infinity=False
        ),
        floor_rate=floor_strategy,
    )
    @settings(max_examples=200)
    def test_floor_kicks_in(self, index_return: float, floor_rate: float) -> None:
        """[T1] Losses beyond floor are capped at floor."""
        assume(index_return < floor_rate)

        payoff = FloorPayoff(floor_rate=floor_rate)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return - floor_rate) < FLOOR_ENFORCEMENT_TOLERANCE, (
            f"Floor should cap loss: return={index_return}, floor={floor_rate}, "
            f"credited={result.credited_return}"
        )

    @given(
        index_return=st.floats(
            min_value=0.0, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        floor_rate=floor_strategy,
    )
    @settings(max_examples=200)
    def test_floor_full_upside(self, index_return: float, floor_rate: float) -> None:
        """[T1] Positive returns pass through fully (no cap in basic floor)."""
        payoff = FloorPayoff(floor_rate=floor_rate)
        result = payoff.calculate(index_return)

        assert abs(result.credited_return - index_return) < ANTI_PATTERN_TOLERANCE, (
            f"Floor should give full upside: return={index_return}, "
            f"credited={result.credited_return}"
        )


# =============================================================================
# Buffer vs Floor Comparison Properties
# =============================================================================


class TestBufferVsFloorProperties:
    """[T1] Buffer and Floor have distinct behavior patterns."""

    @given(
        index_return=st.floats(
            min_value=-0.15, max_value=-0.05, allow_nan=False, allow_infinity=False
        ),
        protection_rate=st.floats(
            min_value=0.10, max_value=0.20, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200)
    def test_buffer_better_for_small_losses(
        self, index_return: float, protection_rate: float
    ) -> None:
        """[T1] Buffer better than floor for losses smaller than buffer rate."""
        # Only test losses within buffer
        assume(-index_return <= protection_rate)

        buffer_payoff = BufferPayoff(buffer_rate=protection_rate)
        floor_payoff = FloorPayoff(floor_rate=-protection_rate)

        buffer_result = buffer_payoff.calculate(index_return)
        floor_result = floor_payoff.calculate(index_return)

        # Buffer should give 0%, floor gives index_return (which is negative)
        assert (
            buffer_result.credited_return >= floor_result.credited_return - ANTI_PATTERN_TOLERANCE
        ), (
            f"Buffer should be better for small loss: "
            f"return={index_return}, buffer_credit={buffer_result.credited_return}, "
            f"floor_credit={floor_result.credited_return}"
        )

    @given(
        index_return=st.floats(
            min_value=-0.50, max_value=-0.25, allow_nan=False, allow_infinity=False
        ),
        protection_rate=st.floats(
            min_value=0.10, max_value=0.20, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200)
    def test_floor_better_for_large_losses(
        self, index_return: float, protection_rate: float
    ) -> None:
        """[T1] Floor better than buffer for losses larger than both protections."""
        # Only test losses much larger than protection
        assume(-index_return > 2 * protection_rate)

        buffer_payoff = BufferPayoff(buffer_rate=protection_rate)
        floor_payoff = FloorPayoff(floor_rate=-protection_rate)

        buffer_result = buffer_payoff.calculate(index_return)
        floor_result = floor_payoff.calculate(index_return)

        # Floor caps at -protection_rate, buffer gives index_return + protection_rate
        assert (
            floor_result.credited_return >= buffer_result.credited_return - ANTI_PATTERN_TOLERANCE
        ), (
            f"Floor should be better for large loss: "
            f"return={index_return}, buffer_credit={buffer_result.credited_return}, "
            f"floor_credit={floor_result.credited_return}"
        )
