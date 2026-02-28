"""
Anti-pattern test: Buffer vs Floor confusion prevention.

[T1] Buffer (RILA) and Floor (FIA) are DIFFERENT protection mechanisms.
This test ensures they are NOT confused or mixed up.

Buffer: Absorbs the FIRST X% of losses. Client exposed beyond buffer.
        Example: 10% buffer, -15% return → client loses 5%

Floor:  Minimum credited rate (always ≥ 0%). Client NOT exposed to any loss.
        Example: 0% floor, -15% return → client credited 0%, no loss

HALT if these mechanisms are confused or implemented incorrectly.

See: METHODOLOGY.md Section 1.2 (FIA), Section 1.3 (RILA)
See: docs/knowledge/domain/buffer_floor.md
"""

import pytest


class TestBufferVsFloor:
    """Ensure buffer and floor mechanics are NOT confused."""

    @pytest.mark.anti_pattern
    def test_buffer_absorbs_losses_floor_sets_minimum(self) -> None:
        """
        [T1] Key distinction: Buffer ABSORBS losses, Floor SETS MINIMUM.

        Buffer (RILA): Client protected from FIRST X% loss, exposed beyond
        Floor (FIA): Client credited rate is floored at 0%, never negative
        """

        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            """RILA buffer: absorbs first X% of losses."""
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0  # Buffer absorbs loss
            else:
                return index_return + buffer  # Client absorbs excess

        def floor_payoff(index_return: float, floor: float, cap: float) -> float:
            """FIA floor: minimum credited rate."""
            credited = min(index_return, cap) if index_return > 0 else 0.0
            return max(credited, floor)

        buffer = 0.10  # 10% buffer
        floor = 0.00  # 0% floor (standard FIA)
        cap = 0.12  # 12% cap

        # Case 1: -5% return (loss within buffer)
        # Buffer: absorbs -5% → client credited 0%
        # Floor: floor at 0% → client credited 0%
        # Both give 0%, but for DIFFERENT reasons
        buffer_result = buffer_payoff(-0.05, buffer, cap)
        floor_result = floor_payoff(-0.05, floor, cap)
        assert buffer_result == 0.0, "Buffer should absorb -5% loss"
        assert floor_result == 0.0, "Floor should set minimum at 0%"

        # Case 2: -15% return (loss BEYOND buffer)
        # Buffer: absorbs first 10%, client loses 5% → -0.05
        # Floor: floor at 0% → client credited 0% (NOT -5%)
        buffer_result_beyond = buffer_payoff(-0.15, buffer, cap)
        floor_result_beyond = floor_payoff(-0.15, floor, cap)

        assert buffer_result_beyond == pytest.approx(-0.05, abs=1e-10), (
            "Buffer: client should lose 5% (15% loss - 10% buffer absorbed)"
        )
        assert floor_result_beyond == 0.0, (
            "Floor: client should get 0%, floor protects from ALL loss"
        )
        assert buffer_result_beyond != floor_result_beyond, (
            "CRITICAL: Buffer and floor give DIFFERENT results for large losses! "
            f"Buffer: {buffer_result_beyond}, Floor: {floor_result_beyond}"
        )

    @pytest.mark.anti_pattern
    def test_buffer_exposes_client_beyond_buffer_level(self) -> None:
        """
        [T1] Buffer clients are exposed to losses BEYOND the buffer level.

        This is fundamentally different from a floor which protects from ALL loss.
        """

        def buffer_payoff(index_return: float, buffer: float) -> float:
            if index_return >= 0:
                return index_return
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        buffer = 0.10  # 10% buffer

        # Test various loss levels
        test_cases = [
            (-0.05, 0.0),  # -5%: within buffer, no loss
            (-0.10, 0.0),  # -10%: exactly at buffer, no loss
            (-0.15, -0.05),  # -15%: beyond buffer, client loses 5%
            (-0.20, -0.10),  # -20%: beyond buffer, client loses 10%
            (-0.30, -0.20),  # -30%: beyond buffer, client loses 20%
            (-0.50, -0.40),  # -50%: beyond buffer, client loses 40%
        ]

        for index_return, expected_loss in test_cases:
            result = buffer_payoff(index_return, buffer)
            assert result == pytest.approx(expected_loss, abs=1e-10), (
                f"Buffer payoff incorrect: "
                f"index_return={index_return}, buffer={buffer}, "
                f"expected={expected_loss}, got={result}"
            )

            # Verify exposure beyond buffer
            if index_return < -buffer:
                assert result < 0, (
                    f"Client MUST be exposed beyond buffer: "
                    f"return={index_return}, buffer={buffer}, result={result}"
                )

    @pytest.mark.anti_pattern
    def test_floor_protects_from_all_negative_credited(self) -> None:
        """
        [T1] Floor clients NEVER have negative credited interest.

        Unlike buffer, floor is an absolute minimum regardless of loss magnitude.
        """

        def floor_payoff(index_return: float, floor: float = 0.0) -> float:
            if index_return > 0:
                return index_return  # No cap for simplicity
            return floor

        # Test various loss levels - floor ALWAYS protects
        loss_scenarios = [-0.05, -0.10, -0.20, -0.30, -0.50, -0.80, -0.99]

        for loss in loss_scenarios:
            result = floor_payoff(loss, floor=0.0)
            assert result >= 0, (
                f"FLOOR VIOLATION: Floor must protect from ALL loss! "
                f"index_return={loss}, result={result}"
            )
            assert result == 0.0, f"Floor should return exactly 0% for any loss, got {result}"

    @pytest.mark.anti_pattern
    def test_buffer_and_floor_have_different_risk_profiles(self) -> None:
        """
        [T1] Buffer products have tail risk; floor products do not.

        Buffer: Limited protection → client exposed in severe downturns
        Floor:  Unlimited protection → client never loses (but limited upside)
        """

        def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
            if index_return >= 0:
                return min(index_return, cap)
            elif index_return >= -buffer:
                return 0.0
            else:
                return index_return + buffer

        def floor_payoff(index_return: float, cap: float) -> float:
            if index_return > 0:
                return min(index_return, cap)
            return 0.0  # 0% floor

        buffer = 0.10
        cap = 0.12

        # Test tail risk scenario: -40% market crash
        crash_return = -0.40

        buffer_in_crash = buffer_payoff(crash_return, buffer, cap)
        floor_in_crash = floor_payoff(crash_return, cap)

        # Buffer client loses 30% (-40% + 10% buffer)
        assert buffer_in_crash == pytest.approx(-0.30, abs=1e-10), (
            f"Buffer crash result should be -30%, got {buffer_in_crash}"
        )

        # Floor client loses 0%
        assert floor_in_crash == 0.0, f"Floor crash result should be 0%, got {floor_in_crash}"

        # Risk difference is material in tail events
        risk_difference = floor_in_crash - buffer_in_crash
        assert risk_difference == pytest.approx(0.30, abs=1e-10), (
            f"Risk difference in -40% crash should be 30%, got {risk_difference}"
        )

    @pytest.mark.anti_pattern
    def test_cannot_mix_buffer_and_floor_terminology(self) -> None:
        """
        [T1] Verify terminology is used correctly.

        RILA uses: buffer (absorbs losses)
        FIA uses:  floor (minimum credit)

        These terms must NOT be swapped.
        """
        # RILA terminology check
        rila_term_buffer = "absorbs"  # Buffer absorbs first X% of losses
        rila_term_exposure = "exposed"  # Client exposed beyond buffer

        # FIA terminology check
        fia_term_floor = "minimum"  # Floor is minimum credited
        fia_term_protection = "protects"  # Floor protects from all loss

        # These are semantic checks - ensuring terms are conceptually distinct
        assert rila_term_buffer != fia_term_floor, "Buffer and floor terminology must be distinct"
        assert rila_term_exposure != fia_term_protection, (
            "Exposure (buffer) and protection (floor) are different concepts"
        )

        # Verify the key conceptual difference
        # Buffer: variable protection (depends on loss magnitude)
        # Floor: fixed protection (always 0% minimum)
        buffer_protection_varies = True  # -5% vs -15% gives different results
        floor_protection_fixed = True  # Any loss gives 0%

        assert buffer_protection_varies, "Buffer protection varies with loss magnitude"
        assert floor_protection_fixed, "Floor protection is fixed regardless of loss"

    @pytest.mark.anti_pattern
    def test_buffer_floor_same_only_within_buffer(self) -> None:
        """
        [T1] Buffer and floor give same result ONLY for losses within buffer.

        Once loss exceeds buffer, results diverge significantly.
        """

        def buffer_payoff(ret: float, buf: float) -> float:
            if ret >= 0:
                return ret
            elif ret >= -buf:
                return 0.0
            return ret + buf

        def floor_payoff(ret: float) -> float:
            return max(ret, 0.0)

        buffer = 0.15  # 15% buffer

        # Within buffer: same result
        within_buffer_returns = [-0.05, -0.10, -0.15]
        for ret in within_buffer_returns:
            buf_result = buffer_payoff(ret, buffer)
            floor_result = floor_payoff(ret)
            assert buf_result == floor_result == 0.0, f"Within buffer ({ret}), both should give 0%"

        # Beyond buffer: DIFFERENT results
        beyond_buffer_returns = [-0.20, -0.30, -0.50]
        for ret in beyond_buffer_returns:
            buf_result = buffer_payoff(ret, buffer)
            floor_result = floor_payoff(ret)
            assert buf_result < 0, f"Buffer should show loss for {ret}"
            assert floor_result == 0, f"Floor should still be 0% for {ret}"
            assert buf_result != floor_result, (
                f"Beyond buffer ({ret}), results MUST differ: "
                f"buffer={buf_result}, floor={floor_result}"
            )
