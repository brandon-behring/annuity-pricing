"""
Anti-pattern test: RILA buffer mechanics.

[T1] Buffer absorbs the FIRST X% of losses.
This is NOT the same as a floor.

HALT if buffer/floor are confused or implemented incorrectly.

See: CONSTITUTION.md Section 1.3
See: docs/knowledge/domain/buffer_floor.md
"""

import pytest


class TestBufferMechanics:
    """Test RILA buffer payoff mechanics."""

    @pytest.mark.anti_pattern
    def test_buffer_absorbs_first_losses(self) -> None:
        """
        [T1] Buffer absorbs FIRST X% of losses, not last X%.

        With 10% buffer:
        - -5% return → 0% loss (buffer absorbs)
        - -10% return → 0% loss (buffer absorbs)
        - -15% return → -5% loss (client absorbs 15%-10%)
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            """RILA buffer payoff."""
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0  # Buffer absorbs
            else:
                return index_return + buffer  # Client absorbs excess

        buffer = 0.10  # 10% buffer
        cap = 0.15     # 15% cap

        # Buffer should absorb small losses completely
        assert buffer_payoff(-0.05, buffer, cap) == 0.0, (
            "Buffer should absorb -5% loss completely (within 10% buffer)"
        )
        assert buffer_payoff(-0.10, buffer, cap) == 0.0, (
            "Buffer should absorb -10% loss completely (exactly at buffer)"
        )

        # Client absorbs losses beyond buffer
        result = buffer_payoff(-0.15, buffer, cap)
        expected = -0.05  # -15% + 10% buffer = -5%
        assert abs(result - expected) < 1e-10, (
            f"Client should absorb -5% (15% loss - 10% buffer), got {result}"
        )

        result = buffer_payoff(-0.25, buffer, cap)
        expected = -0.15  # -25% + 10% buffer = -15%
        assert abs(result - expected) < 1e-10, (
            f"Client should absorb -15% (25% loss - 10% buffer), got {result}"
        )

    @pytest.mark.anti_pattern
    def test_buffer_upside_capped(self) -> None:
        """
        [T1] Buffer products have capped upside.
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        buffer = 0.10
        cap = 0.12

        # Upside should be capped
        assert buffer_payoff(0.05, buffer, cap) == 0.05, (
            "5% gain should pass through (below cap)"
        )
        assert buffer_payoff(0.12, buffer, cap) == 0.12, (
            "12% gain should equal cap"
        )
        assert buffer_payoff(0.20, buffer, cap) == 0.12, (
            "20% gain should be capped at 12%"
        )

    @pytest.mark.anti_pattern
    def test_buffer_zero_return(self) -> None:
        """
        [T1] Zero return should result in zero payoff.
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        assert buffer_payoff(0.0, 0.10, 0.15) == 0.0

    @pytest.mark.anti_pattern
    def test_buffer_boundary_conditions(self) -> None:
        """
        [T1] Test exact boundary conditions for buffer.
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        buffer = 0.10

        # Exactly at buffer boundary
        assert buffer_payoff(-0.10, buffer, 0.15) == 0.0, (
            "At exactly -buffer, payoff should be 0"
        )

        # Just beyond buffer (should start losing)
        result = buffer_payoff(-0.1001, buffer, 0.15)
        assert result < 0, (
            f"Just beyond buffer, client should lose. Got {result}"
        )

    @pytest.mark.anti_pattern
    def test_common_buffer_levels(self) -> None:
        """
        [T2] Test common buffer levels from WINK data.

        Common buffers: 10%, 15%, 20%
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        cap = 0.15

        # 10% buffer
        assert buffer_payoff(-0.08, 0.10, cap) == 0.0
        assert abs(buffer_payoff(-0.12, 0.10, cap) - (-0.02)) < 1e-10

        # 15% buffer
        assert buffer_payoff(-0.12, 0.15, cap) == 0.0
        assert abs(buffer_payoff(-0.18, 0.15, cap) - (-0.03)) < 1e-10

        # 20% buffer
        assert buffer_payoff(-0.18, 0.20, cap) == 0.0
        assert abs(buffer_payoff(-0.25, 0.20, cap) - (-0.05)) < 1e-10


class TestFloorMechanics:
    """Test RILA floor payoff mechanics."""

    @pytest.mark.anti_pattern
    def test_floor_limits_max_loss(self) -> None:
        """
        [T1] Floor limits maximum loss to X%.

        With -10% floor:
        - -5% return → -5% loss (client absorbs)
        - -10% return → -10% loss (at floor)
        - -25% return → -10% loss (floor limits)
        """
        def floor_payoff(index_return: float, floor: float, cap: float) -> float:
            """RILA floor payoff."""
            if index_return >= 0:
                return min(index_return, cap)
            else:
                return max(index_return, -floor)

        floor = 0.10  # -10% floor
        cap = 0.15

        # Client absorbs small losses
        assert floor_payoff(-0.05, floor, cap) == -0.05, (
            "Client should absorb -5% loss (above floor)"
        )

        # Floor limits large losses
        assert floor_payoff(-0.10, floor, cap) == -0.10, (
            "At floor, loss should be exactly -10%"
        )
        assert floor_payoff(-0.15, floor, cap) == -0.10, (
            "Floor should limit -15% loss to -10%"
        )
        assert floor_payoff(-0.30, floor, cap) == -0.10, (
            "Floor should limit -30% loss to -10%"
        )

    @pytest.mark.anti_pattern
    def test_floor_upside_capped(self) -> None:
        """
        [T1] Floor products also have capped upside.
        """
        def floor_payoff(index_return: float, floor: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            else:
                return max(index_return, -floor)

        floor = 0.10
        cap = 0.12

        assert floor_payoff(0.08, floor, cap) == 0.08
        assert floor_payoff(0.15, floor, cap) == 0.12


class TestBufferVsFloor:
    """Test that buffer and floor are NOT confused."""

    @pytest.mark.anti_pattern
    def test_buffer_not_floor(self) -> None:
        """
        [T1] Buffer and floor give DIFFERENT results for same inputs.

        Buffer: Protects against SMALL losses
        Floor: Protects against LARGE losses
        """
        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        def floor_payoff(index_return: float, floor: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            else:
                return max(index_return, -floor)

        # Same parameters
        protection = 0.10
        cap = 0.15

        # Small loss: Buffer is better
        small_loss = -0.05
        buffer_result = buffer_payoff(small_loss, protection, cap)
        floor_result = floor_payoff(small_loss, protection, cap)

        assert buffer_result == 0.0, "Buffer should absorb small loss"
        assert floor_result == -0.05, "Floor doesn't help with small loss"
        assert buffer_result != floor_result, (
            "Buffer and floor should give different results for small losses"
        )

        # Large loss: Floor is better
        large_loss = -0.25
        buffer_result = buffer_payoff(large_loss, protection, cap)
        floor_result = floor_payoff(large_loss, protection, cap)

        assert buffer_result == -0.15, "Buffer: client absorbs 25%-10%=15%"
        assert floor_result == -0.10, "Floor: loss limited to 10%"
        assert buffer_result != floor_result, (
            "Buffer and floor should give different results for large losses"
        )

    @pytest.mark.anti_pattern
    def test_identify_buffer_vs_floor_from_modifier(self) -> None:
        """
        [T2] WINK uses bufferModifier to distinguish buffer from floor.

        "Losses Covered Up To" → Buffer
        "Losses Covered After" → Floor
        """
        def is_buffer(modifier: str) -> bool:
            return "up to" in modifier.lower()

        def is_floor(modifier: str) -> bool:
            return "after" in modifier.lower()

        # Buffer modifiers
        assert is_buffer("Losses Covered Up To 10%") is True
        assert is_floor("Losses Covered Up To 10%") is False

        # Floor modifiers
        assert is_floor("Losses Covered After 10%") is True
        assert is_buffer("Losses Covered After 10%") is False
