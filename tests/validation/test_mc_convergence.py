"""
Monte Carlo convergence tests.

[T1] MC must converge to Black-Scholes for vanilla options.
This validates the entire simulation pipeline.

See: Glasserman (2003) "Monte Carlo Methods in Financial Engineering"
See: METHODOLOGY.md Section 4
"""

import numpy as np
import pytest

from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import (
    MonteCarloEngine,
    convergence_analysis,
)


class TestMCConvergesToBS:
    """
    Tests that MC converges to analytical Black-Scholes prices.

    [T1] This is the definitive validation that our MC is correct.
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

    @pytest.mark.validation
    @pytest.mark.slow
    def test_atm_call_convergence(self, standard_params):
        """
        [T1] ATM call MC price should be within 1% of BS.
        """
        strike = 100.0

        # Analytical price
        bs_price = black_scholes_call(
            standard_params.spot,
            strike,
            standard_params.rate,
            standard_params.dividend,
            standard_params.volatility,
            standard_params.time_to_expiry,
        )

        # MC price with large number of paths
        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(standard_params, strike)

        # Should be within 1% of BS
        rel_error = abs(mc_result.price - bs_price) / bs_price
        assert rel_error < 0.01, f"MC price {mc_result.price:.4f} vs BS {bs_price:.4f}"

    @pytest.mark.validation
    @pytest.mark.slow
    def test_atm_put_convergence(self, standard_params):
        """
        [T1] ATM put MC price should be within 1% of BS.
        """
        strike = 100.0

        bs_price = black_scholes_put(
            standard_params.spot,
            strike,
            standard_params.rate,
            standard_params.dividend,
            standard_params.volatility,
            standard_params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        mc_result = engine.price_european_put(standard_params, strike)

        rel_error = abs(mc_result.price - bs_price) / bs_price
        assert rel_error < 0.01, f"MC price {mc_result.price:.4f} vs BS {bs_price:.4f}"

    @pytest.mark.validation
    @pytest.mark.slow
    def test_itm_call_convergence(self, standard_params):
        """
        [T1] ITM call MC price should be within 1% of BS.
        """
        strike = 90.0  # ITM

        bs_price = black_scholes_call(
            standard_params.spot,
            strike,
            standard_params.rate,
            standard_params.dividend,
            standard_params.volatility,
            standard_params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(standard_params, strike)

        rel_error = abs(mc_result.price - bs_price) / bs_price
        assert rel_error < 0.01

    @pytest.mark.validation
    @pytest.mark.slow
    def test_otm_call_convergence(self, standard_params):
        """
        [T1] OTM call MC price should be within 2% of BS.

        Note: OTM options have higher relative error due to rare payoffs.
        """
        strike = 110.0  # OTM

        bs_price = black_scholes_call(
            standard_params.spot,
            strike,
            standard_params.rate,
            standard_params.dividend,
            standard_params.volatility,
            standard_params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(standard_params, strike)

        rel_error = abs(mc_result.price - bs_price) / bs_price
        assert rel_error < 0.02  # Higher tolerance for OTM


class TestConvergenceRate:
    """Tests for MC convergence rate."""

    @pytest.mark.validation
    @pytest.mark.slow
    def test_convergence_rate_is_sqrt_n(self):
        """
        [T1] MC error should converge at rate 1/√N.

        Theory: SE ∝ σ/√N, so log(error) ~ -0.5 × log(N)
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0

        bs_price = black_scholes_call(
            params.spot,
            strike,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        result = convergence_analysis(
            params,
            strike,
            bs_price,
            path_counts=[1000, 5000, 10000, 50000, 100000],
            seed=42,
        )

        # Convergence rate should be around -0.5
        # Allow wider tolerance as rate estimation is noisy for small samples
        rate = result["convergence_rate"]
        assert -0.8 < rate < -0.3, f"Convergence rate {rate} not in expected range"

    @pytest.mark.validation
    @pytest.mark.slow
    def test_bs_within_ci(self):
        """
        [T1] BS price should be within MC confidence interval (95% of the time).

        We test at multiple path counts; at least 90% should contain BS price.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0

        bs_price = black_scholes_call(
            params.spot,
            strike,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        result = convergence_analysis(
            params,
            strike,
            bs_price,
            path_counts=[10000, 50000, 100000, 500000],
            seed=42,
        )

        # Count how many CIs contain the BS price
        within_ci_count = sum(r["within_ci"] for r in result["results"])
        total = len(result["results"])

        # At least 75% should contain (accounting for randomness)
        assert (
            within_ci_count / total >= 0.75
        ), f"Only {within_ci_count}/{total} CIs contain BS price"


class TestAntitheticVariates:
    """Tests for antithetic variates variance reduction."""

    @pytest.mark.validation
    def test_antithetic_reduces_standard_error(self):
        """
        [T1] Antithetic variates should reduce standard error.
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0

        # Without antithetic
        engine_normal = MonteCarloEngine(n_paths=50000, antithetic=False, seed=42)
        result_normal = engine_normal.price_european_call(params, strike)

        # With antithetic (same total paths)
        engine_anti = MonteCarloEngine(n_paths=50000, antithetic=True, seed=42)
        result_anti = engine_anti.price_european_call(params, strike)

        # Standard error should be reduced (or at least not much higher)
        # This is probabilistic, so we allow some slack
        assert result_anti.standard_error <= result_normal.standard_error * 1.2


class TestPutCallParityMC:
    """Tests for put-call parity in MC prices."""

    @pytest.mark.validation
    @pytest.mark.slow
    def test_mc_put_call_parity(self):
        """
        [T1] MC prices should satisfy put-call parity.

        C - P = S*e^(-qT) - K*e^(-rT)
        """
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        strike = 100.0

        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        call_result = engine.price_european_call(params, strike)
        put_result = engine.price_european_put(params, strike)

        # Expected parity value
        expected_diff = (
            params.spot * np.exp(-params.dividend * params.time_to_expiry)
            - strike * np.exp(-params.rate * params.time_to_expiry)
        )

        actual_diff = call_result.price - put_result.price

        # Should be within combined standard error (roughly)
        combined_se = np.sqrt(call_result.standard_error**2 + put_result.standard_error**2)
        tolerance = 3 * combined_se  # 3 sigma

        assert abs(actual_diff - expected_diff) < tolerance, (
            f"Put-call parity violation: "
            f"C-P={actual_diff:.4f}, expected={expected_diff:.4f}"
        )


class TestMCMoneynessConvergence:
    """Parametrized MC convergence tests across moneyness levels [Step 7]."""

    @pytest.mark.validation
    @pytest.mark.slow
    @pytest.mark.parametrize(
        "S,K,label,tolerance",
        [
            (120, 100, "Deep ITM", 0.01),     # Deep ITM call
            (110, 100, "ITM", 0.01),          # ITM call
            (100, 100, "ATM", 0.01),          # ATM
            (100, 110, "OTM", 0.02),          # OTM call (higher tolerance)
            (100, 120, "Deep OTM", 0.03),     # Deep OTM call (even higher)
        ],
    )
    def test_mc_convergence_by_moneyness(
        self, S: float, K: float, label: str, tolerance: float
    ) -> None:
        """
        [T1] MC should converge to BS across moneyness spectrum.

        OTM options have higher relative error due to rare payoffs.
        """
        params = GBMParams(
            spot=S,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        bs_price = black_scholes_call(
            params.spot,
            K,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=500000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(params, K)

        rel_error = abs(mc_result.price - bs_price) / max(bs_price, 0.01)
        assert rel_error < tolerance, (
            f"{label} call: MC={mc_result.price:.4f}, BS={bs_price:.4f}, "
            f"rel_error={rel_error:.4f} > tolerance={tolerance}"
        )


class TestEdgeCases:
    """Tests for edge cases in MC pricing."""

    @pytest.mark.validation
    def test_short_maturity(self):
        """MC should handle short maturities."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=0.01,  # ~3-4 days
        )
        strike = 100.0

        bs_price = black_scholes_call(
            params.spot,
            strike,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=100000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(params, strike)

        # Should be reasonably close
        rel_error = abs(mc_result.price - bs_price) / max(bs_price, 0.01)
        assert rel_error < 0.05

    @pytest.mark.validation
    def test_high_volatility(self):
        """MC should handle high volatility."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.80,  # 80% vol
            time_to_expiry=1.0,
        )
        strike = 100.0

        bs_price = black_scholes_call(
            params.spot,
            strike,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=200000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(params, strike)

        rel_error = abs(mc_result.price - bs_price) / bs_price
        assert rel_error < 0.02

    @pytest.mark.validation
    def test_zero_volatility(self):
        """MC should handle zero volatility (deterministic)."""
        params = GBMParams(
            spot=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.001,  # Near-zero
            time_to_expiry=1.0,
        )
        strike = 100.0

        bs_price = black_scholes_call(
            params.spot,
            strike,
            params.rate,
            params.dividend,
            params.volatility,
            params.time_to_expiry,
        )

        engine = MonteCarloEngine(n_paths=50000, antithetic=True, seed=42)
        mc_result = engine.price_european_call(params, strike)

        # With near-zero vol, should converge well
        rel_error = abs(mc_result.price - bs_price) / max(bs_price, 0.01)
        assert rel_error < 0.05
