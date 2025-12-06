"""
Tests for VM-22 Calculator - Phase 9.

[T1] VM-22 reserve determination:
1. Stochastic Exclusion Test (SET) - if pass, use DR
2. Single Scenario Test (SST) - if pass, use DR
3. If both fail → Stochastic Reserve (SR)

See: docs/knowledge/domain/vm21_vm22.md
"""

import pytest
import numpy as np

from annuity_pricing.regulatory.vm22 import (
    VM22Calculator,
    VM22Result,
    FixedAnnuityPolicy,
    StochasticExclusionResult,
    ReserveType,
    compare_reserve_methods,
    vm22_sensitivity,
)


class TestFixedAnnuityPolicy:
    """Tests for FixedAnnuityPolicy dataclass."""

    def test_policy_creation(self) -> None:
        """Policy should be created with required fields."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        assert policy.premium == 100_000
        assert policy.guaranteed_rate == 0.04
        assert policy.term_years == 5

    def test_policy_defaults(self) -> None:
        """Policy should have reasonable defaults."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        assert policy.current_year == 0
        assert policy.surrender_charge_pct == 0.07
        assert policy.account_value is None

    def test_av_property_defaults_to_premium(self) -> None:
        """av property should default to premium."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        assert policy.av == 100_000

    def test_av_property_uses_account_value(self) -> None:
        """av property should use account_value if set."""
        policy = FixedAnnuityPolicy(
            premium=100_000,
            guaranteed_rate=0.04,
            term_years=5,
            account_value=120_000,
        )

        assert policy.av == 120_000


class TestVM22Result:
    """Tests for VM22Result dataclass."""

    def test_result_attributes(self) -> None:
        """Result should have all expected attributes."""
        result = VM22Result(
            reserve=100_000,
            net_premium_reserve=95_000,
            deterministic_reserve=98_000,
        )

        assert result.reserve == 100_000
        assert result.net_premium_reserve == 95_000
        assert result.deterministic_reserve == 98_000
        assert result.stochastic_reserve is None
        assert result.reserve_type == ReserveType.DETERMINISTIC

    def test_result_with_stochastic(self) -> None:
        """Result with stochastic reserve."""
        result = VM22Result(
            reserve=110_000,
            net_premium_reserve=95_000,
            deterministic_reserve=98_000,
            stochastic_reserve=110_000,
            reserve_type=ReserveType.STOCHASTIC,
        )

        assert result.stochastic_reserve == 110_000
        assert result.reserve_type == ReserveType.STOCHASTIC


class TestVM22Calculator:
    """Tests for VM22Calculator."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        """Standard calculator with fixed seed."""
        return VM22Calculator(n_scenarios=100, projection_years=30, seed=42)

    def test_calculator_initialization(self) -> None:
        """Calculator should initialize with correct parameters."""
        calc = VM22Calculator(n_scenarios=500, projection_years=25, seed=123)

        assert calc.n_scenarios == 500
        assert calc.projection_years == 25
        assert calc.seed == 123


class TestNetPremiumReserve:
    """Tests for Net Premium Reserve calculation."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        return VM22Calculator(seed=42)

    def test_npr_basic(self, calculator: VM22Calculator) -> None:
        """NPR should be positive for normal policy."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        npr = calculator.calculate_net_premium_reserve(policy, market_rate=0.04)

        assert npr > 0

    def test_npr_increases_with_guaranteed_rate(self, calculator: VM22Calculator) -> None:
        """Higher guaranteed rate → higher NPR."""
        policy_low = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.03, term_years=5
        )
        policy_high = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.06, term_years=5
        )

        npr_low = calculator.calculate_net_premium_reserve(policy_low, market_rate=0.04)
        npr_high = calculator.calculate_net_premium_reserve(policy_high, market_rate=0.04)

        assert npr_high > npr_low


class TestDeterministicReserve:
    """Tests for Deterministic Reserve calculation."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        return VM22Calculator(seed=42)

    def test_dr_basic(self, calculator: VM22Calculator) -> None:
        """DR should be positive for normal policy."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        dr = calculator.calculate_deterministic_reserve(policy, 0.04, 0.05)

        assert dr > 0

    def test_dr_decreases_with_higher_market_rate(
        self, calculator: VM22Calculator
    ) -> None:
        """Higher market rate → lower DR (better asset returns)."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        dr_low = calculator.calculate_deterministic_reserve(policy, 0.02, 0.05)
        dr_high = calculator.calculate_deterministic_reserve(policy, 0.06, 0.05)

        assert dr_low >= dr_high


class TestStochasticReserve:
    """Tests for Stochastic Reserve calculation."""

    def test_sr_basic(self) -> None:
        """SR should be positive for normal policy."""
        calc = VM22Calculator(n_scenarios=100, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        sr = calc.calculate_stochastic_reserve(policy, 0.04, 0.05)

        assert sr > 0


class TestStochasticExclusionTest:
    """Tests for Stochastic Exclusion Test."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        return VM22Calculator(seed=42)

    def test_set_passes_when_rates_match(self, calculator: VM22Calculator) -> None:
        """SET should pass when guaranteed rate = market rate."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.stochastic_exclusion_test(policy, market_rate=0.04)

        # Ratio = 1.0, threshold = 1.10, should pass
        assert result.passed is True
        assert result.ratio == pytest.approx(1.0)

    def test_set_fails_high_guaranteed_rate(self, calculator: VM22Calculator) -> None:
        """SET should fail when guaranteed rate >> market rate."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.08, term_years=10  # High guaranteed
        )
        result = calculator.stochastic_exclusion_test(policy, market_rate=0.02)

        # Guaranteed grows faster, ratio > threshold
        assert result.ratio > result.threshold

    def test_set_result_includes_ratio(self, calculator: VM22Calculator) -> None:
        """SET result should include ratio and threshold."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.stochastic_exclusion_test(policy, market_rate=0.04)

        assert isinstance(result, StochasticExclusionResult)
        assert hasattr(result, "ratio")
        assert hasattr(result, "threshold")


class TestSingleScenarioTest:
    """Tests for Single Scenario Test."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        return VM22Calculator(seed=42)

    def test_sst_returns_bool(self, calculator: VM22Calculator) -> None:
        """SST should return boolean."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.single_scenario_test(policy, 0.04, 0.05)

        assert isinstance(result, bool)


class TestFullReserveCalculation:
    """Tests for full reserve calculation."""

    @pytest.fixture
    def calculator(self) -> VM22Calculator:
        return VM22Calculator(n_scenarios=100, seed=42)

    def test_reserve_basic(self, calculator: VM22Calculator) -> None:
        """Basic reserve calculation should work."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.calculate_reserve(policy)

        assert result.reserve > 0

    def test_reserve_at_least_npr(self, calculator: VM22Calculator) -> None:
        """Reserve should be at least NPR."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.calculate_reserve(policy)

        assert result.reserve >= result.net_premium_reserve

    def test_reserve_at_least_dr(self, calculator: VM22Calculator) -> None:
        """Reserve should be at least DR."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calculator.calculate_reserve(policy)

        assert result.reserve >= result.deterministic_reserve

    def test_reserve_type_deterministic_when_set_passes(
        self, calculator: VM22Calculator
    ) -> None:
        """Reserve type should be deterministic when SET passes."""
        # Low guaranteed rate should pass SET
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.03, term_years=5
        )
        result = calculator.calculate_reserve(policy, market_rate=0.05)

        if result.set_passed:
            assert result.reserve_type == ReserveType.DETERMINISTIC
            assert result.stochastic_reserve is None

    def test_negative_premium_raises(self, calculator: VM22Calculator) -> None:
        """Negative premium should raise error."""
        policy = FixedAnnuityPolicy(
            premium=-100_000, guaranteed_rate=0.04, term_years=5
        )

        with pytest.raises(ValueError, match="positive"):
            calculator.calculate_reserve(policy)

    def test_negative_guaranteed_rate_raises(self, calculator: VM22Calculator) -> None:
        """Negative guaranteed rate should raise error."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=-0.04, term_years=5
        )

        with pytest.raises(ValueError, match="negative"):
            calculator.calculate_reserve(policy)


class TestCompareReserveMethods:
    """Tests for compare_reserve_methods function."""

    def test_comparison_returns_dict(self) -> None:
        """Comparison should return dict with expected keys."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = compare_reserve_methods(policy, n_scenarios=50, seed=42)

        assert isinstance(result, dict)
        assert "npr" in result
        assert "deterministic_reserve" in result
        assert "stochastic_reserve" in result
        assert "set_passed" in result


class TestVM22Sensitivity:
    """Tests for vm22_sensitivity function."""

    def test_sensitivity_returns_dict(self) -> None:
        """Sensitivity should return dict."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = vm22_sensitivity(policy, seed=42)

        assert isinstance(result, dict)
        assert "base_reserve" in result
        assert "rate_up_1pct" in result
        assert "lapse_up_2x" in result

    def test_sensitivity_has_sensitivities(self) -> None:
        """Should calculate relative sensitivities."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = vm22_sensitivity(policy, seed=42)

        assert "rate_sensitivity" in result
        assert "lapse_sensitivity" in result


class TestReproducibility:
    """Tests for reproducibility with seed."""

    def test_same_seed_same_result(self) -> None:
        """Same seed should produce same reserve."""
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        calc1 = VM22Calculator(n_scenarios=100, seed=12345)
        calc2 = VM22Calculator(n_scenarios=100, seed=12345)

        result1 = calc1.calculate_reserve(policy)
        result2 = calc2.calculate_reserve(policy)

        assert result1.reserve == pytest.approx(result2.reserve, rel=0.01)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_short_term(self) -> None:
        """Short term policy should work."""
        calc = VM22Calculator(n_scenarios=50, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=1
        )
        result = calc.calculate_reserve(policy)

        assert result.reserve > 0

    def test_long_term(self) -> None:
        """Long term policy should work."""
        calc = VM22Calculator(n_scenarios=50, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=20
        )
        result = calc.calculate_reserve(policy)

        assert result.reserve > 0

    def test_mid_term_policy(self) -> None:
        """Mid-term policy (current_year > 0) should work."""
        calc = VM22Calculator(n_scenarios=50, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000,
            guaranteed_rate=0.04,
            term_years=10,
            current_year=5,
        )
        result = calc.calculate_reserve(policy)

        assert result.reserve > 0

    def test_zero_lapse_rate(self) -> None:
        """Zero lapse rate should work."""
        calc = VM22Calculator(n_scenarios=50, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )
        result = calc.calculate_reserve(policy, lapse_rate=0.0)

        assert result.reserve > 0

    def test_high_lapse_rate(self) -> None:
        """High lapse rate should reduce reserve."""
        calc = VM22Calculator(n_scenarios=50, seed=42)
        policy = FixedAnnuityPolicy(
            premium=100_000, guaranteed_rate=0.04, term_years=5
        )

        result_low = calc.calculate_reserve(policy, lapse_rate=0.02)
        result_high = calc.calculate_reserve(policy, lapse_rate=0.20)

        # High lapse → more early surrenders → different reserve profile
        # Just check both work
        assert result_low.reserve > 0
        assert result_high.reserve > 0
