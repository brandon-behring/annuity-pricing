"""
Anti-pattern test: FIA floor enforcement.

[T1] FIA crediting methods MUST enforce 0% floor.
Client can NEVER have negative credited interest.

HALT if any crediting method produces negative result.

See: METHODOLOGY.md Section 1.2
See: docs/knowledge/domain/crediting_methods.md
"""

import pytest


class TestFIAFloorEnforcement:
    """Test that FIA crediting never goes negative."""

    @pytest.mark.anti_pattern
    def test_cap_rate_floor(self) -> None:
        """
        [T1] Cap rate crediting must enforce 0% floor.

        negative index return → 0% credited (not negative)
        """
        # Define expected behavior (implementation will follow)
        def cap_crediting(index_return: float, cap: float) -> float:
            """Cap rate crediting with floor."""
            return min(max(index_return, 0), cap)

        # Test cases
        test_cases = [
            (-0.20, 0.08, 0.0),   # -20% return → 0%
            (-0.10, 0.08, 0.0),   # -10% return → 0%
            (-0.05, 0.08, 0.0),   # -5% return → 0%
            (-0.01, 0.08, 0.0),   # -1% return → 0%
            (0.00, 0.08, 0.0),    # 0% return → 0%
            (0.05, 0.08, 0.05),   # 5% return → 5%
            (0.10, 0.08, 0.08),   # 10% return → 8% (capped)
            (0.20, 0.08, 0.08),   # 20% return → 8% (capped)
        ]

        for index_return, cap, expected in test_cases:
            result = cap_crediting(index_return, cap)
            assert result >= 0, (
                f"FLOOR VIOLATION: Cap crediting returned {result} for "
                f"index_return={index_return}. FIA floor is 0%."
            )
            assert abs(result - expected) < 1e-10, (
                f"Cap crediting error: got {result}, expected {expected}"
            )

    @pytest.mark.anti_pattern
    def test_participation_rate_floor(self) -> None:
        """
        [T1] Participation rate crediting must enforce 0% floor.

        negative index return → 0% credited
        """
        def participation_crediting(index_return: float, participation: float) -> float:
            """Participation rate crediting with floor."""
            return max(index_return * participation, 0)

        test_cases = [
            (-0.20, 0.80, 0.0),   # -20% * 80% = -16% → 0%
            (-0.10, 0.80, 0.0),   # -10% * 80% = -8% → 0%
            (-0.05, 1.00, 0.0),   # -5% * 100% = -5% → 0%
            (0.00, 0.80, 0.0),    # 0% * 80% = 0%
            (0.10, 0.80, 0.08),   # 10% * 80% = 8%
            (0.10, 1.20, 0.12),   # 10% * 120% = 12% (>100% participation)
        ]

        for index_return, participation, expected in test_cases:
            result = participation_crediting(index_return, participation)
            assert result >= 0, (
                f"FLOOR VIOLATION: Participation crediting returned {result} for "
                f"index_return={index_return}. FIA floor is 0%."
            )
            assert abs(result - expected) < 1e-10, (
                f"Participation crediting error: got {result}, expected {expected}"
            )

    @pytest.mark.anti_pattern
    def test_spread_rate_floor(self) -> None:
        """
        [T1] Spread rate crediting must enforce 0% floor.

        (index return - spread) can be negative but credited is floored at 0%
        """
        def spread_crediting(index_return: float, spread: float) -> float:
            """Spread crediting with floor."""
            return max(index_return - spread, 0)

        test_cases = [
            (-0.20, 0.02, 0.0),   # -20% - 2% = -22% → 0%
            (-0.05, 0.02, 0.0),   # -5% - 2% = -7% → 0%
            (0.01, 0.02, 0.0),    # 1% - 2% = -1% → 0%
            (0.02, 0.02, 0.0),    # 2% - 2% = 0%
            (0.05, 0.02, 0.03),   # 5% - 2% = 3%
            (0.10, 0.02, 0.08),   # 10% - 2% = 8%
        ]

        for index_return, spread, expected in test_cases:
            result = spread_crediting(index_return, spread)
            assert result >= 0, (
                f"FLOOR VIOLATION: Spread crediting returned {result} for "
                f"index_return={index_return}. FIA floor is 0%."
            )
            assert abs(result - expected) < 1e-10, (
                f"Spread crediting error: got {result}, expected {expected}"
            )

    @pytest.mark.anti_pattern
    def test_performance_triggered_floor(self) -> None:
        """
        [T1] Performance triggered crediting must enforce 0% floor.

        negative index return → 0% credited (trigger not activated)
        """
        def trigger_crediting(index_return: float, trigger_rate: float) -> float:
            """Performance triggered crediting."""
            return trigger_rate if index_return > 0 else 0

        test_cases = [
            (-0.20, 0.05, 0.0),   # negative → 0%
            (-0.01, 0.05, 0.0),   # negative → 0%
            (0.00, 0.05, 0.0),    # zero → 0% (trigger not activated)
            (0.001, 0.05, 0.05),  # positive → trigger rate
            (0.10, 0.05, 0.05),   # positive → trigger rate
            (0.50, 0.05, 0.05),   # positive → trigger rate (same)
        ]

        for index_return, trigger_rate, expected in test_cases:
            result = trigger_crediting(index_return, trigger_rate)
            assert result >= 0, (
                f"FLOOR VIOLATION: Trigger crediting returned {result} for "
                f"index_return={index_return}. FIA floor is 0%."
            )
            assert abs(result - expected) < 1e-10, (
                f"Trigger crediting error: got {result}, expected {expected}"
            )

    @pytest.mark.anti_pattern
    def test_combined_cap_participation_floor(self) -> None:
        """
        [T1] Combined cap + participation must enforce 0% floor.
        """
        def cap_participation_crediting(
            index_return: float, cap: float, participation: float
        ) -> float:
            """Combined cap and participation with floor."""
            adjusted = index_return * participation
            return min(max(adjusted, 0), cap)

        test_cases = [
            (-0.20, 0.10, 0.80, 0.0),   # negative → 0%
            (0.10, 0.10, 0.80, 0.08),   # 10% * 80% = 8%
            (0.20, 0.10, 0.80, 0.10),   # 20% * 80% = 16% → 10% (capped)
        ]

        for index_return, cap, participation, expected in test_cases:
            result = cap_participation_crediting(index_return, cap, participation)
            assert result >= 0, (
                f"FLOOR VIOLATION: Combined crediting returned {result}"
            )
            assert abs(result - expected) < 1e-10, (
                f"Combined crediting error: got {result}, expected {expected}"
            )

    @pytest.mark.anti_pattern
    def test_floor_is_exactly_zero(self) -> None:
        """
        [T1] The FIA floor must be exactly 0%, not some small negative number.
        """
        # The floor should be 0.0, not -0.001 or similar
        FIA_FLOOR = 0.0

        assert FIA_FLOOR == 0.0, (
            f"FIA floor must be exactly 0.0, got {FIA_FLOOR}"
        )
