"""
Tests for Scenario Generation - Phase 9.

[T1] Vasicek: dr = κ(θ - r)dt + σ dW
[T1] GBM: dS/S = μdt + σ dW
[T1] Correlation via Cholesky decomposition

See: docs/knowledge/domain/vm21_vm22.md
"""

import pytest
import numpy as np

from annuity_pricing.regulatory.scenarios import (
    ScenarioGenerator,
    EconomicScenario,
    AG43Scenarios,
    VasicekParams,
    EquityParams,
    generate_deterministic_scenarios,
    calculate_scenario_statistics,
)


class TestEconomicScenario:
    """Tests for EconomicScenario dataclass."""

    def test_scenario_creation(self) -> None:
        """Scenario should be created with matching length paths."""
        rates = np.array([0.04, 0.05, 0.06])
        equity = np.array([0.10, -0.05, 0.15])

        scenario = EconomicScenario(rates=rates, equity_returns=equity, scenario_id=0)

        assert len(scenario.rates) == 3
        assert len(scenario.equity_returns) == 3
        assert scenario.scenario_id == 0

    def test_mismatched_lengths_raises(self) -> None:
        """Mismatched path lengths should raise error."""
        rates = np.array([0.04, 0.05])
        equity = np.array([0.10, -0.05, 0.15])

        with pytest.raises(ValueError, match="must match"):
            EconomicScenario(rates=rates, equity_returns=equity, scenario_id=0)


class TestVasicekParams:
    """Tests for VasicekParams dataclass."""

    def test_default_values(self) -> None:
        """Default values should be reasonable."""
        params = VasicekParams()

        assert params.kappa == 0.20
        assert params.theta == 0.04
        assert params.sigma == 0.01

    def test_custom_values(self) -> None:
        """Custom values should be accepted."""
        params = VasicekParams(kappa=0.50, theta=0.05, sigma=0.02)

        assert params.kappa == 0.50
        assert params.theta == 0.05
        assert params.sigma == 0.02


class TestEquityParams:
    """Tests for EquityParams dataclass."""

    def test_default_values(self) -> None:
        """Default values should be reasonable."""
        params = EquityParams()

        assert params.mu == 0.07
        assert params.sigma == 0.18

    def test_custom_values(self) -> None:
        """Custom values should be accepted."""
        params = EquityParams(mu=0.10, sigma=0.25)

        assert params.mu == 0.10
        assert params.sigma == 0.25


class TestScenarioGenerator:
    """Tests for ScenarioGenerator."""

    @pytest.fixture
    def generator(self) -> ScenarioGenerator:
        """Standard generator with fixed seed."""
        return ScenarioGenerator(n_scenarios=100, projection_years=10, seed=42)

    def test_generator_initialization(self, generator: ScenarioGenerator) -> None:
        """Generator should initialize with correct parameters."""
        assert generator.n_scenarios == 100
        assert generator.projection_years == 10
        assert generator.seed == 42

    def test_invalid_n_scenarios_raises(self) -> None:
        """Negative n_scenarios should raise error."""
        with pytest.raises(ValueError, match="positive"):
            ScenarioGenerator(n_scenarios=-1)

    def test_invalid_projection_years_raises(self) -> None:
        """Negative projection_years should raise error."""
        with pytest.raises(ValueError, match="positive"):
            ScenarioGenerator(projection_years=-1)


class TestRateScenarios:
    """Tests for interest rate scenario generation."""

    @pytest.fixture
    def generator(self) -> ScenarioGenerator:
        return ScenarioGenerator(n_scenarios=100, projection_years=10, seed=42)

    def test_rate_scenarios_shape(self, generator: ScenarioGenerator) -> None:
        """Rate scenarios should have correct shape."""
        rates = generator.generate_rate_scenarios()

        assert rates.shape == (100, 10)

    def test_rate_scenarios_non_negative(self, generator: ScenarioGenerator) -> None:
        """Rate scenarios should be non-negative (floored at 0)."""
        rates = generator.generate_rate_scenarios()

        assert np.all(rates >= 0)

    def test_rate_mean_reversion(self) -> None:
        """
        [T1] Vasicek rates should mean-revert to theta.
        """
        gen = ScenarioGenerator(n_scenarios=1000, projection_years=50, seed=42)
        params = VasicekParams(kappa=0.20, theta=0.05, sigma=0.01)
        rates = gen.generate_rate_scenarios(initial_rate=0.02, params=params)

        # Terminal rates should be closer to theta than initial
        terminal_mean = np.mean(rates[:, -1])
        assert abs(terminal_mean - params.theta) < 0.02

    def test_negative_initial_rate_raises(self, generator: ScenarioGenerator) -> None:
        """Negative initial rate should raise error."""
        with pytest.raises(ValueError, match="negative"):
            generator.generate_rate_scenarios(initial_rate=-0.01)


class TestEquityScenarios:
    """Tests for equity scenario generation."""

    @pytest.fixture
    def generator(self) -> ScenarioGenerator:
        return ScenarioGenerator(n_scenarios=100, projection_years=10, seed=42)

    def test_equity_scenarios_shape(self, generator: ScenarioGenerator) -> None:
        """Equity scenarios should have correct shape."""
        returns = generator.generate_equity_scenarios()

        assert returns.shape == (100, 10)

    def test_equity_mean_reasonable(self) -> None:
        """
        [T1] GBM returns should have expected mean.
        """
        gen = ScenarioGenerator(n_scenarios=10000, projection_years=30, seed=42)
        returns = gen.generate_equity_scenarios(mu=0.07, sigma=0.18)

        # Mean annual return should be close to mu
        mean_return = np.mean(returns)
        assert abs(mean_return - 0.07) < 0.02

    def test_negative_volatility_raises(self, generator: ScenarioGenerator) -> None:
        """Negative volatility should raise error."""
        with pytest.raises(ValueError, match="negative"):
            generator.generate_equity_scenarios(sigma=-0.10)


class TestAG43Scenarios:
    """Tests for AG43 scenario generation."""

    @pytest.fixture
    def generator(self) -> ScenarioGenerator:
        return ScenarioGenerator(n_scenarios=100, projection_years=10, seed=42)

    def test_ag43_scenarios_count(self, generator: ScenarioGenerator) -> None:
        """AG43 should generate correct number of scenarios."""
        scenarios = generator.generate_ag43_scenarios()

        assert scenarios.n_scenarios == 100
        assert len(scenarios.scenarios) == 100

    def test_ag43_projection_years(self, generator: ScenarioGenerator) -> None:
        """AG43 scenarios should have correct projection length."""
        scenarios = generator.generate_ag43_scenarios()

        assert scenarios.projection_years == 10
        for s in scenarios.scenarios:
            assert len(s.rates) == 10
            assert len(s.equity_returns) == 10

    def test_ag43_rate_matrix(self, generator: ScenarioGenerator) -> None:
        """get_rate_matrix should return correct shape."""
        scenarios = generator.generate_ag43_scenarios()
        rate_matrix = scenarios.get_rate_matrix()

        assert rate_matrix.shape == (100, 10)

    def test_ag43_equity_matrix(self, generator: ScenarioGenerator) -> None:
        """get_equity_matrix should return correct shape."""
        scenarios = generator.generate_ag43_scenarios()
        equity_matrix = scenarios.get_equity_matrix()

        assert equity_matrix.shape == (100, 10)

    def test_invalid_correlation_raises(self, generator: ScenarioGenerator) -> None:
        """Correlation outside [-1, 1] should raise error."""
        with pytest.raises(ValueError, match="Correlation"):
            generator.generate_ag43_scenarios(correlation=1.5)


class TestCorrelation:
    """Tests for correlated scenario generation."""

    def test_negative_correlation(self) -> None:
        """
        [T1] Negative correlation: rates down → equities up.
        """
        gen = ScenarioGenerator(n_scenarios=1000, projection_years=10, seed=42)
        scenarios = gen.generate_ag43_scenarios(correlation=-0.50)

        rate_matrix = scenarios.get_rate_matrix()
        equity_matrix = scenarios.get_equity_matrix()

        # Calculate sample correlation
        correlations = []
        for t in range(10):
            corr = np.corrcoef(rate_matrix[:, t], equity_matrix[:, t])[0, 1]
            correlations.append(corr)

        # Average correlation should be negative
        avg_corr = np.mean(correlations)
        assert avg_corr < 0

    def test_zero_correlation(self) -> None:
        """Zero correlation should produce uncorrelated paths."""
        gen = ScenarioGenerator(n_scenarios=1000, projection_years=10, seed=42)
        scenarios = gen.generate_ag43_scenarios(correlation=0.0)

        rate_matrix = scenarios.get_rate_matrix()
        equity_matrix = scenarios.get_equity_matrix()

        # Average correlation should be near zero
        correlations = []
        for t in range(10):
            corr = np.corrcoef(rate_matrix[:, t], equity_matrix[:, t])[0, 1]
            correlations.append(corr)

        avg_corr = np.mean(correlations)
        assert abs(avg_corr) < 0.1


class TestDeterministicScenarios:
    """Tests for deterministic scenario generation."""

    def test_generates_three_scenarios(self) -> None:
        """Should generate base, up, and down scenarios."""
        scenarios = generate_deterministic_scenarios()

        assert len(scenarios) == 3

    def test_scenario_lengths(self) -> None:
        """Scenarios should have correct length."""
        scenarios = generate_deterministic_scenarios(n_years=20)

        for s in scenarios:
            assert len(s.rates) == 20
            assert len(s.equity_returns) == 20

    def test_base_scenario(self) -> None:
        """Base scenario should use base values."""
        scenarios = generate_deterministic_scenarios(
            n_years=10, base_rate=0.04, base_equity=0.07
        )

        base = scenarios[0]
        assert np.all(base.rates == 0.04)
        assert np.all(base.equity_returns == 0.07)

    def test_up_scenario(self) -> None:
        """Up scenario should have higher rates."""
        scenarios = generate_deterministic_scenarios(
            n_years=10, base_rate=0.04, base_equity=0.07
        )

        up = scenarios[1]
        assert np.all(up.rates == 0.06)  # +2%

    def test_down_scenario(self) -> None:
        """Down scenario should have lower rates."""
        scenarios = generate_deterministic_scenarios(
            n_years=10, base_rate=0.04, base_equity=0.07
        )

        down = scenarios[2]
        assert np.all(down.rates == 0.02)  # -2%


class TestScenarioStatistics:
    """Tests for scenario statistics calculation."""

    def test_statistics_keys(self) -> None:
        """Statistics should include expected keys."""
        gen = ScenarioGenerator(n_scenarios=100, projection_years=10, seed=42)
        scenarios = gen.generate_ag43_scenarios()
        stats = calculate_scenario_statistics(scenarios)

        expected_keys = [
            "rate_mean",
            "rate_std",
            "equity_return_mean",
            "cumulative_return_mean",
            "n_scenarios",
            "projection_years",
        ]
        for key in expected_keys:
            assert key in stats

    def test_statistics_values_reasonable(self) -> None:
        """Statistics should have reasonable values."""
        gen = ScenarioGenerator(n_scenarios=1000, projection_years=30, seed=42)
        scenarios = gen.generate_ag43_scenarios()
        stats = calculate_scenario_statistics(scenarios)

        # Rate mean should be near theta (0.04)
        assert 0.02 < stats["rate_mean"] < 0.08

        # Equity return mean should be positive
        assert stats["equity_return_mean"] > 0

        # Counts should match
        assert stats["n_scenarios"] == 1000
        assert stats["projection_years"] == 30


class TestReproducibility:
    """Tests for reproducibility with seed."""

    def test_same_seed_same_result(self) -> None:
        """Same seed should produce same scenarios."""
        gen1 = ScenarioGenerator(n_scenarios=100, projection_years=10, seed=12345)
        gen2 = ScenarioGenerator(n_scenarios=100, projection_years=10, seed=12345)

        s1 = gen1.generate_ag43_scenarios()
        s2 = gen2.generate_ag43_scenarios()

        np.testing.assert_array_equal(
            s1.get_rate_matrix(), s2.get_rate_matrix()
        )
        np.testing.assert_array_equal(
            s1.get_equity_matrix(), s2.get_equity_matrix()
        )

    def test_different_seed_different_result(self) -> None:
        """Different seeds should produce different scenarios."""
        gen1 = ScenarioGenerator(n_scenarios=100, projection_years=10, seed=11111)
        gen2 = ScenarioGenerator(n_scenarios=100, projection_years=10, seed=99999)

        s1 = gen1.generate_ag43_scenarios()
        s2 = gen2.generate_ag43_scenarios()

        # Should be different
        assert not np.allclose(s1.get_rate_matrix(), s2.get_rate_matrix())
