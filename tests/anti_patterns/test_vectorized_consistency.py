"""
Anti-pattern test: Vectorized payoffs must match scalar implementation.

[T1] Both implementations must produce identical results.
This prevents bugs where vectorized version diverges from scalar.

See: Plan Phase 5 - MC Vectorization
"""

import numpy as np
import pytest

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
# Test Data
# =============================================================================

# Test returns including edge cases
TEST_RETURNS = np.array(
    [
        -0.50,  # Large loss
        -0.30,  # Moderate loss
        -0.15,  # Small loss (within typical buffer)
        -0.10,  # Exactly at buffer level
        -0.05,  # Small loss (within buffer)
        0.00,  # Flat
        0.05,  # Small gain
        0.10,  # Moderate gain (typical cap level)
        0.15,  # Above typical cap
        0.30,  # Large gain
        0.50,  # Very large gain
    ]
)


# =============================================================================
# FIA Payoff Vectorization Tests
# =============================================================================


@pytest.mark.anti_pattern
class TestCappedCallVectorizedConsistency:
    """Vectorized CappedCallPayoff must match scalar."""

    @pytest.mark.parametrize("cap_rate", [0.05, 0.10, 0.15, 0.20])
    def test_vectorized_matches_scalar(self, cap_rate: float) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = CappedCallPayoff(cap_rate=cap_rate)

        # Skip if vectorized not implemented yet
        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        # Vectorized calculation
        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)

        # Scalar calculation (one at a time)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg=f"CappedCallPayoff vectorized != scalar for cap={cap_rate}",
        )

    def test_vectorized_preserves_shape(self) -> None:
        """Vectorized output should have same shape as input."""
        payoff = CappedCallPayoff(cap_rate=0.10)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        result = payoff.calculate_vectorized(TEST_RETURNS)
        assert result.shape == TEST_RETURNS.shape


@pytest.mark.anti_pattern
class TestParticipationVectorizedConsistency:
    """Vectorized ParticipationPayoff must match scalar."""

    @pytest.mark.parametrize(
        "participation_rate,cap_rate",
        [
            (0.50, None),
            (0.80, None),
            (1.0, None),
            (0.80, 0.15),
        ],
    )
    def test_vectorized_matches_scalar(self, participation_rate: float, cap_rate: float) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = ParticipationPayoff(
            participation_rate=participation_rate,
            cap_rate=cap_rate,
        )

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg="ParticipationPayoff vectorized != scalar",
        )


@pytest.mark.anti_pattern
class TestSpreadVectorizedConsistency:
    """Vectorized SpreadPayoff must match scalar."""

    @pytest.mark.parametrize("spread_rate", [0.01, 0.02, 0.05])
    def test_vectorized_matches_scalar(self, spread_rate: float) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = SpreadPayoff(spread_rate=spread_rate)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg=f"SpreadPayoff vectorized != scalar for spread={spread_rate}",
        )


@pytest.mark.anti_pattern
class TestTriggerVectorizedConsistency:
    """Vectorized TriggerPayoff must match scalar."""

    def test_vectorized_matches_scalar(self) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = TriggerPayoff(trigger_rate=0.05)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg="TriggerPayoff vectorized != scalar",
        )


# =============================================================================
# RILA Payoff Vectorization Tests
# =============================================================================


@pytest.mark.anti_pattern
class TestBufferVectorizedConsistency:
    """Vectorized BufferPayoff must match scalar."""

    @pytest.mark.parametrize(
        "buffer_rate,cap_rate",
        [
            (0.10, None),
            (0.10, 0.15),
            (0.15, 0.20),
            (0.20, None),
        ],
    )
    def test_vectorized_matches_scalar(self, buffer_rate: float, cap_rate: float) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = BufferPayoff(buffer_rate=buffer_rate, cap_rate=cap_rate)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg=f"BufferPayoff vectorized != scalar for buffer={buffer_rate}",
        )


@pytest.mark.anti_pattern
class TestFloorVectorizedConsistency:
    """Vectorized FloorPayoff must match scalar."""

    @pytest.mark.parametrize(
        "floor_rate,cap_rate",
        [
            (-0.10, None),
            (-0.10, 0.15),
            (-0.15, 0.20),
            (-0.20, None),
        ],
    )
    def test_vectorized_matches_scalar(self, floor_rate: float, cap_rate: float) -> None:
        """Vectorized and scalar must produce identical results."""
        payoff = FloorPayoff(floor_rate=floor_rate, cap_rate=cap_rate)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        vectorized_results = payoff.calculate_vectorized(TEST_RETURNS)
        scalar_results = np.array([payoff.calculate(r).credited_return for r in TEST_RETURNS])

        np.testing.assert_allclose(
            vectorized_results,
            scalar_results,
            rtol=1e-10,
            err_msg=f"FloorPayoff vectorized != scalar for floor={floor_rate}",
        )


# =============================================================================
# Interface Tests
# =============================================================================


@pytest.mark.anti_pattern
class TestVectorizedInterface:
    """Tests for vectorized interface compliance."""

    def test_all_payoffs_have_supports_vectorized(self) -> None:
        """All payoffs should have supports_vectorized() method."""
        payoffs = [
            CappedCallPayoff(cap_rate=0.10),
            ParticipationPayoff(participation_rate=0.80),
            SpreadPayoff(spread_rate=0.02),
            TriggerPayoff(trigger_rate=0.05),
            BufferPayoff(buffer_rate=0.10),
            FloorPayoff(floor_rate=-0.10),
        ]

        for payoff in payoffs:
            if not hasattr(payoff, "supports_vectorized"):
                pytest.skip("supports_vectorized not implemented yet")

            # Method should return bool
            result = payoff.supports_vectorized()
            assert isinstance(result, bool), f"{type(payoff).__name__} doesn't return bool"

    def test_vectorized_returns_numpy_array(self) -> None:
        """calculate_vectorized should return numpy array."""
        payoff = CappedCallPayoff(cap_rate=0.10)

        if not hasattr(payoff, "calculate_vectorized"):
            pytest.skip("calculate_vectorized not implemented yet")

        result = payoff.calculate_vectorized(TEST_RETURNS)
        assert isinstance(result, np.ndarray), "Should return numpy array"
        assert result.dtype == np.float64 or result.dtype == float
