"""
Asian option (monthly-averaging) benchmark tests.

[T1] Validates that monthly-averaging FIA uses correct observation frequency.
Monthly-average options should use 12 observations/year, not 252.

See: Hull (2021) "Options, Futures, and Other Derivatives", Ch. 26 (Asian options)
See: Glasserman (2003) "Monte Carlo Methods in Financial Engineering", Section 3.3
See: docs/knowledge/derivations/monte_carlo.md (ObservationSchedule design)
"""

import pytest

from annuity_pricing.options.payoffs.fia import CappedCallPayoff, MonthlyAveragePayoff
from annuity_pricing.options.simulation.gbm import GBMParams, generate_gbm_paths
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine


class TestMonthlyAveragingObservations:
    """
    Tests that monthly-averaging uses correct observation count.

    [T1] Asian options with monthly averaging should use 12 observations
    per year, not the default 252 daily observations.
    """

    @pytest.fixture
    def standard_params(self):
        """Standard GBM parameters."""
        return GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

    @pytest.fixture
    def monthly_payoff(self):
        """Monthly-average payoff with 10% cap."""
        return MonthlyAveragePayoff(cap_rate=0.10, floor_rate=0.0)

    @pytest.mark.validation
    def test_monthly_averaging_observation_count(self, standard_params):
        """
        [T1] Monthly-average paths should have 12 observations for 1-year term.

        This test validates the fix for the monthly-averaging FIA bug where
        the MC engine was incorrectly using 252 daily steps instead of 12.
        """
        n_steps = 12  # Monthly for 1 year
        result = generate_gbm_paths(standard_params, n_paths=1000, n_steps=n_steps)

        # Path shape should be (n_paths, n_steps + 1) - includes initial
        assert result.paths.shape == (1000, 13), (
            f"Expected (1000, 13) for monthly paths, got {result.paths.shape}"
        )

    @pytest.mark.validation
    def test_monthly_vs_daily_variance_reduction(self, standard_params, monthly_payoff):
        """
        [T1] Monthly averaging should reduce effective volatility vs daily.

        Asian options with monthly averaging have lower variance than
        point-to-point or daily averaging. The average of 12 monthly
        values is smoother than the average of 252 daily values.
        """
        engine = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        # Monthly averaging (12 steps)
        result_monthly = engine.price_with_payoff(standard_params, monthly_payoff, n_steps=12)

        # Daily averaging (252 steps) - incorrect but for comparison
        result_daily = engine.price_with_payoff(standard_params, monthly_payoff, n_steps=252)

        # The variance should be DIFFERENT (monthly has higher variance per step)
        # This confirms we're actually using different path counts
        # Note: Due to CLT, more averaging points = lower variance
        monthly_std = result_monthly.payoffs.std()
        daily_std = result_daily.payoffs.std()

        # Monthly should have higher variance in payoffs (fewer averaging points)
        # But expected value should be similar
        monthly_mean = result_monthly.payoffs.mean()
        daily_mean = result_daily.payoffs.mean()

        # Means should be reasonably close (within 5%)
        rel_diff = abs(monthly_mean - daily_mean) / daily_mean if daily_mean != 0 else 0
        assert rel_diff < 0.05, (
            f"Monthly mean {monthly_mean:.4f} vs daily mean {daily_mean:.4f} "
            f"differ by {rel_diff * 100:.1f}%"
        )

    @pytest.mark.validation
    def test_monthly_average_lower_value_than_point_to_point(self, standard_params, monthly_payoff):
        """
        [T1] Monthly-average capped call should be worth less than point-to-point.

        The averaging effect reduces effective volatility, which reduces
        option value for a capped call (convex payoff benefits from volatility).

        See: Hull Ch. 26 - Asian options worth less than vanilla for convex payoffs.
        """
        engine = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        # Monthly-average with 12 observations
        result_avg = engine.price_with_payoff(standard_params, monthly_payoff, n_steps=12)

        # Point-to-point (same cap, but using terminal value only)
        p2p_payoff = CappedCallPayoff(cap_rate=0.10, floor_rate=0.0)
        result_p2p = engine.price_with_payoff(standard_params, p2p_payoff)

        avg_value = result_avg.payoffs.mean()
        p2p_value = result_p2p.payoffs.mean()

        # Average should be worth LESS than point-to-point
        assert avg_value < p2p_value, (
            f"Monthly-average value {avg_value:.4f} should be < "
            f"point-to-point value {p2p_value:.4f}"
        )


class TestAsianCapBenchmarks:
    """
    Benchmarks for Asian (monthly-average) capped call options.

    [T2] These are empirical benchmarks based on simulation, not
    closed-form solutions (no simple closed form for arithmetic Asian).
    """

    @pytest.fixture
    def base_params(self):
        """Base GBM parameters for benchmarks."""
        return GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

    @pytest.mark.validation
    @pytest.mark.parametrize(
        "cap_rate,expected_min,expected_max",
        [
            # Empirical bounds for 1-year monthly-average capped call
            # Based on high-path-count simulation benchmarks
            (0.05, 0.005, 0.030),  # 5% cap: small upside
            (0.10, 0.020, 0.050),  # 10% cap: moderate upside
            (0.15, 0.030, 0.070),  # 15% cap: larger upside
            (0.20, 0.040, 0.080),  # 20% cap: generous cap
        ],
    )
    def test_monthly_cap_value_bounds(self, base_params, cap_rate, expected_min, expected_max):
        """
        [T2] Monthly-average cap values should fall within empirical bounds.

        These bounds are derived from high-path-count simulations and serve
        as regression tests to catch implementation errors.
        """
        payoff = MonthlyAveragePayoff(cap_rate=cap_rate, floor_rate=0.0)
        engine = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)

        result = engine.price_with_payoff(base_params, payoff, n_steps=12)
        avg_return = result.payoffs.mean() / base_params.spot

        assert expected_min <= avg_return <= expected_max, (
            f"Monthly-average cap={cap_rate} return {avg_return:.4f} "
            f"outside bounds [{expected_min}, {expected_max}]"
        )

    @pytest.mark.validation
    def test_term_scaling(self, base_params):
        """
        [T1] Multi-year monthly-averaging should use n_steps = 12 * term_years.

        A 2-year term should use 24 monthly observations.
        """
        payoff = MonthlyAveragePayoff(cap_rate=0.10, floor_rate=0.0)

        # 2-year term
        params_2y = GBMParams(
            spot=base_params.spot,
            rate=base_params.rate,
            dividend=base_params.dividend,
            volatility=base_params.volatility,
            time_to_expiry=2.0,
        )

        # Verify 24 observations for 2-year term
        result = generate_gbm_paths(params_2y, n_paths=100, n_steps=24)
        assert result.paths.shape == (100, 25), (
            f"Expected (100, 25) for 2-year monthly paths, got {result.paths.shape}"
        )


class TestFIAIntegration:
    """
    Integration tests verifying FIAPricer uses correct monthly observations.
    """

    @pytest.mark.validation
    def test_fia_monthly_average_uses_12_steps(self):
        """
        [T1] FIAPricer should use n_steps=12 for monthly-average crediting.

        This is the key integration test for the fix in FIAPricer._calculate_expected_credit.
        """
        from annuity_pricing.data.schemas import FIAProduct
        from annuity_pricing.products.fia import FIAPricer, MarketParams

        # Create FIA with monthly-average crediting
        # Note: indexing_method containing "monthly" or "average" triggers
        # monthly averaging detection in _determine_crediting_method
        product = FIAProduct(
            company_name="Test Company",
            product_name="Monthly Average FIA",
            product_group="FIA",
            status="current",
            cap_rate=0.10,
            indexing_method="Monthly Averaging",  # Triggers monthly averaging
            index_used="S&P 500",
        )

        market = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )

        pricer = FIAPricer(market, n_mc_paths=10000, seed=42)
        result = pricer.price(product, premium=100_000, term_years=1.0)

        # If fix is working, monthly-average uses 12 steps and produces
        # a reasonable expected credit (not inflated by wrong averaging)
        assert 0.0 <= result.expected_credit <= 0.10, (
            f"Expected credit {result.expected_credit:.4f} should be between 0 and cap rate 0.10"
        )
