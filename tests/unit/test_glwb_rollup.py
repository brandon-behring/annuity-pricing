"""
Tests for Rollup and Ratchet Mechanics - Phase 8.

[T1] Simple rollup: GWB(t) = base × (1 + rate × years)
[T1] Compound rollup: GWB(t) = base × (1 + rate)^years
[T1] Ratchet: GWB(t) = max(GWB(t-1), AV(t))

See: docs/knowledge/domain/glwb_mechanics.md
"""

import pytest
import numpy as np

from annuity_pricing.glwb.rollup import (
    SimpleRollup,
    CompoundRollup,
    RatchetMechanic,
    RollupResult,
    calculate_rollup_with_cap,
    compare_rollup_methods,
)


class TestSimpleRollup:
    """Tests for SimpleRollup."""

    @pytest.fixture
    def rollup(self) -> SimpleRollup:
        return SimpleRollup()

    def test_basic_calculation(self, rollup: SimpleRollup) -> None:
        """
        [T1] GWB(t) = base × (1 + rate × years)
        """
        # $100k, 5 years, 5% rate
        result = rollup.calculate(100_000, 5, 0.05)

        # Expected: 100k × (1 + 0.05 × 5) = 100k × 1.25 = 125k
        assert result == pytest.approx(125_000)

    def test_zero_years(self, rollup: SimpleRollup) -> None:
        """No rollup at year 0."""
        result = rollup.calculate(100_000, 0, 0.05)
        assert result == pytest.approx(100_000)

    def test_zero_rate(self, rollup: SimpleRollup) -> None:
        """No rollup with zero rate."""
        result = rollup.calculate(100_000, 10, 0.0)
        assert result == pytest.approx(100_000)

    def test_high_rate(self, rollup: SimpleRollup) -> None:
        """High rollup rate."""
        result = rollup.calculate(100_000, 10, 0.10)

        # Expected: 100k × (1 + 0.10 × 10) = 100k × 2.0 = 200k
        assert result == pytest.approx(200_000)

    def test_negative_base_raises(self, rollup: SimpleRollup) -> None:
        """Negative base should raise error."""
        with pytest.raises(ValueError, match="negative"):
            rollup.calculate(-100_000, 5, 0.05)

    def test_negative_years_raises(self, rollup: SimpleRollup) -> None:
        """Negative years should raise error."""
        with pytest.raises(ValueError, match="negative"):
            rollup.calculate(100_000, -5, 0.05)

    def test_negative_rate_raises(self, rollup: SimpleRollup) -> None:
        """Negative rate should raise error."""
        with pytest.raises(ValueError, match="negative"):
            rollup.calculate(100_000, 5, -0.05)


class TestCompoundRollup:
    """Tests for CompoundRollup."""

    @pytest.fixture
    def rollup(self) -> CompoundRollup:
        return CompoundRollup()

    def test_basic_calculation(self, rollup: CompoundRollup) -> None:
        """
        [T1] GWB(t) = base × (1 + rate)^years
        """
        result = rollup.calculate(100_000, 5, 0.05)

        # Expected: 100k × 1.05^5 ≈ 127,628.16
        expected = 100_000 * (1.05 ** 5)
        assert result == pytest.approx(expected)

    def test_zero_years(self, rollup: CompoundRollup) -> None:
        """No rollup at year 0."""
        result = rollup.calculate(100_000, 0, 0.05)
        assert result == pytest.approx(100_000)

    def test_zero_rate(self, rollup: CompoundRollup) -> None:
        """No rollup with zero rate."""
        result = rollup.calculate(100_000, 10, 0.0)
        assert result == pytest.approx(100_000)

    def test_high_rate(self, rollup: CompoundRollup) -> None:
        """High rollup rate."""
        result = rollup.calculate(100_000, 10, 0.10)

        # Expected: 100k × 1.10^10 ≈ 259,374.25
        expected = 100_000 * (1.10 ** 10)
        assert result == pytest.approx(expected)

    def test_fractional_years(self, rollup: CompoundRollup) -> None:
        """Fractional years should work."""
        result = rollup.calculate(100_000, 2.5, 0.05)

        expected = 100_000 * (1.05 ** 2.5)
        assert result == pytest.approx(expected)


class TestCompoundVsSimple:
    """Compare compound vs simple rollup."""

    def test_compound_exceeds_simple(self) -> None:
        """Compound should exceed simple for same params."""
        simple = SimpleRollup().calculate(100_000, 10, 0.05)
        compound = CompoundRollup().calculate(100_000, 10, 0.05)

        # Simple: 100k × 1.5 = 150k
        # Compound: 100k × 1.05^10 ≈ 162.9k
        assert compound > simple

    def test_equal_at_year_one(self) -> None:
        """Simple and compound are equal at year 1."""
        simple = SimpleRollup().calculate(100_000, 1, 0.05)
        compound = CompoundRollup().calculate(100_000, 1, 0.05)

        assert simple == pytest.approx(compound)

    def test_compare_rollup_methods(self) -> None:
        """Test comparison function."""
        result = compare_rollup_methods(100_000, 10, 0.05)

        assert result["simple"] == pytest.approx(150_000)
        assert result["compound"] == pytest.approx(100_000 * 1.05**10)
        assert result["difference"] > 0
        assert result["compound_advantage_pct"] > 0


class TestRatchetMechanic:
    """Tests for RatchetMechanic."""

    @pytest.fixture
    def ratchet(self) -> RatchetMechanic:
        return RatchetMechanic()

    def test_step_up_when_av_exceeds_gwb(self, ratchet: RatchetMechanic) -> None:
        """
        [T1] When AV > GWB, step up to AV.
        """
        result = ratchet.apply_ratchet(100_000, 120_000)
        assert result == pytest.approx(120_000)

    def test_no_step_down_when_av_below_gwb(self, ratchet: RatchetMechanic) -> None:
        """
        [T1] When AV < GWB, keep GWB (no step-down).
        """
        result = ratchet.apply_ratchet(100_000, 80_000)
        assert result == pytest.approx(100_000)

    def test_equal_av_gwb(self, ratchet: RatchetMechanic) -> None:
        """When AV = GWB, no change."""
        result = ratchet.apply_ratchet(100_000, 100_000)
        assert result == pytest.approx(100_000)

    def test_negative_gwb_raises(self, ratchet: RatchetMechanic) -> None:
        """Negative GWB should raise error."""
        with pytest.raises(ValueError, match="negative"):
            ratchet.apply_ratchet(-100_000, 50_000)

    def test_negative_av_raises(self, ratchet: RatchetMechanic) -> None:
        """Negative AV should raise error."""
        with pytest.raises(ValueError, match="negative"):
            ratchet.apply_ratchet(100_000, -50_000)


class TestRatchetPath:
    """Tests for path-based ratchet."""

    @pytest.fixture
    def ratchet(self) -> RatchetMechanic:
        return RatchetMechanic()

    def test_ratchet_path_locks_in_gains(self, ratchet: RatchetMechanic) -> None:
        """Ratchet should lock in gains along path."""
        # AV goes up then down
        av_path = np.array([100_000, 120_000, 110_000, 90_000, 130_000])

        gwb_path = ratchet.apply_ratchet_path(100_000, av_path)

        # GWB should step up to 120k at t=1, stay at 120k for t=2,3
        # Then step up to 130k at t=4
        assert gwb_path[0] == pytest.approx(100_000)
        assert gwb_path[1] == pytest.approx(120_000)
        assert gwb_path[2] == pytest.approx(120_000)  # No step-down
        assert gwb_path[3] == pytest.approx(120_000)  # No step-down
        assert gwb_path[4] == pytest.approx(130_000)  # Step up

    def test_ratchet_frequency(self, ratchet: RatchetMechanic) -> None:
        """Ratchet frequency should control when ratchet applies."""
        av_path = np.array([100_000, 120_000, 130_000, 140_000])

        # Ratchet every 2 periods
        gwb_path = ratchet.apply_ratchet_path(100_000, av_path, ratchet_frequency=2)

        # Should ratchet at t=0, t=2, but not t=1, t=3
        assert gwb_path[0] == pytest.approx(100_000)  # Ratchet at t=0
        assert gwb_path[1] == pytest.approx(100_000)  # No ratchet at t=1
        assert gwb_path[2] == pytest.approx(130_000)  # Ratchet at t=2
        assert gwb_path[3] == pytest.approx(130_000)  # No ratchet at t=3


class TestRollupWithCap:
    """Tests for rollup with year cap."""

    def test_cap_limits_rollup_years(self) -> None:
        """Rollup should be capped at cap_years."""
        result = calculate_rollup_with_cap(100_000, 15, 0.05, 10, "compound")

        # Should be same as 10-year rollup
        expected = CompoundRollup().calculate(100_000, 10, 0.05)
        assert result.rolled_up_value == pytest.approx(expected)
        assert result.years == 10.0  # Capped

    def test_no_cap_if_years_below(self) -> None:
        """No cap if years < cap_years."""
        result = calculate_rollup_with_cap(100_000, 5, 0.05, 10, "compound")

        expected = CompoundRollup().calculate(100_000, 5, 0.05)
        assert result.rolled_up_value == pytest.approx(expected)
        assert result.years == 5.0

    def test_simple_rollup_with_cap(self) -> None:
        """Simple rollup with cap."""
        result = calculate_rollup_with_cap(100_000, 15, 0.05, 10, "simple")

        expected = SimpleRollup().calculate(100_000, 10, 0.05)
        assert result.rolled_up_value == pytest.approx(expected)

    def test_result_breakdown(self) -> None:
        """Verify result breakdown."""
        result = calculate_rollup_with_cap(100_000, 5, 0.05, 10, "compound")

        assert result.base_value == 100_000
        assert result.rollup_amount == pytest.approx(result.rolled_up_value - 100_000)
        assert result.effective_rate == pytest.approx(0.05, rel=0.01)

    def test_unknown_rollup_type_raises(self) -> None:
        """Unknown rollup type should raise error."""
        with pytest.raises(ValueError, match="Unknown rollup type"):
            calculate_rollup_with_cap(100_000, 5, 0.05, 10, "unknown")
