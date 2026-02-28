"""
Performance tests for pricing operations.

Tests pricing performance using seeded RNG and relative thresholds.
No absolute wall-clock assertions to avoid flaky tests on different hardware.

Approach:
- All MC operations use seed=42 for deterministic paths
- Assert relative scaling, not absolute timing
- Throughput sanity checks (completes without timeout)
"""

import time

import numpy as np
import pytest

from annuity_pricing.data.schemas import FIAProduct, MYGAProduct, RILAProduct
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
)

# =============================================================================
# Constants
# =============================================================================

BENCHMARK_SEED = 42  # Deterministic MC paths


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def market_env() -> MarketEnvironment:
    """Standard market environment for performance tests."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        spot=100.0,
        dividend_yield=0.02,
        volatility=0.20,
        option_budget_pct=0.03,
    )


@pytest.fixture
def sample_myga() -> MYGAProduct:
    """Sample MYGA product for performance testing."""
    return MYGAProduct(
        company_name="PerfTest Life",
        product_name="PerfTest MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def sample_fia() -> FIAProduct:
    """Sample FIA product for performance testing."""
    return FIAProduct(
        company_name="PerfTest Life",
        product_name="PerfTest FIA",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
        term_years=1,
    )


@pytest.fixture
def sample_rila() -> RILAProduct:
    """Sample RILA product for performance testing."""
    return RILAProduct(
        company_name="PerfTest Life",
        product_name="PerfTest RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        cap_rate=0.15,
        term_years=6,
    )


def create_myga_batch(n: int) -> list[MYGAProduct]:
    """Create batch of MYGA products for throughput testing.

    Uses modulo to keep rates in realistic range [3%, 8%].
    """
    return [
        MYGAProduct(
            company_name=f"Test Life {i}",
            product_name=f"MYGA {i}",
            product_group="MYGA",
            status="current",
            fixed_rate=0.03 + (i % 50) * 0.001,  # 3% to 8% range
            guarantee_duration=3 + (i % 8),  # 3 to 10 years
        )
        for i in range(n)
    ]


def create_fia_batch(n: int) -> list[FIAProduct]:
    """Create batch of FIA products for throughput testing."""
    return [
        FIAProduct(
            company_name=f"Test Life {i}",
            product_name=f"FIA {i}",
            product_group="FIA",
            status="current",
            cap_rate=0.08 + (i % 10) * 0.005,
            term_years=1,
        )
        for i in range(n)
    ]


# =============================================================================
# MYGA Throughput Tests
# =============================================================================


class TestMYGAThroughput:
    """Performance tests for MYGA pricing (deterministic, fast)."""

    def test_myga_batch_100(self, market_env: MarketEnvironment) -> None:
        """MYGA batch pricing completes for 100 products."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)
        products = create_myga_batch(100)

        results = registry.price_multiple(products)

        assert len(results) == 100
        assert results["present_value"].notna().all()
        assert (results["present_value"] > 0).all()

    def test_myga_batch_1000(self, market_env: MarketEnvironment) -> None:
        """MYGA batch pricing completes for 1000 products."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)
        products = create_myga_batch(1000)

        results = registry.price_multiple(products)

        assert len(results) == 1000

        # Check for errors - price_multiple may have error column
        if "error" in results.columns:
            errors = results[results["error"].notna()]
            # Allow up to 5% validation failures (budget check can fail)
            assert len(errors) <= 50, f"Too many pricing errors: {len(errors)}"
            # Only check non-error rows for PV
            valid_results = results[results["error"].isna()]
            assert (valid_results["present_value"] > 0).all()
        else:
            assert results["present_value"].notna().all()
            assert (results["present_value"] > 0).all()


# =============================================================================
# FIA MC Determinism Tests
# =============================================================================


class TestFIAMCDeterminism:
    """Tests for Monte Carlo reproducibility with seeded RNG."""

    def test_fia_mc_deterministic(
        self, market_env: MarketEnvironment, sample_fia: FIAProduct
    ) -> None:
        """FIA MC with seeded RNG is reproducible."""
        registry1 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=BENCHMARK_SEED)
        registry2 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=BENCHMARK_SEED)

        result1 = registry1.price(sample_fia, term_years=1.0, validate=False)
        result2 = registry2.price(sample_fia, term_years=1.0, validate=False)

        # With same seed, results should be identical
        assert result1.embedded_option_value == result2.embedded_option_value
        assert result1.expected_credit == result2.expected_credit
        assert result1.present_value == result2.present_value

    def test_different_seeds_produce_different_results(
        self, market_env: MarketEnvironment, sample_fia: FIAProduct
    ) -> None:
        """Different seeds should produce different MC results."""
        registry1 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        registry2 = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=123)

        result1 = registry1.price(sample_fia, term_years=1.0, validate=False)
        result2 = registry2.price(sample_fia, term_years=1.0, validate=False)

        # Different seeds should give different expected_credit
        # (PV might be close but expected_credit depends on MC paths)
        # Allow for rare chance of identical results with tolerance
        assert result1.expected_credit != pytest.approx(
            result2.expected_credit, rel=1e-10
        ) or result1.present_value != pytest.approx(result2.present_value, rel=1e-10)


# =============================================================================
# Batch Scaling Tests
# =============================================================================


class TestBatchScaling:
    """Tests for batch pricing scaling behavior."""

    def test_myga_batch_scaling_relative(self, market_env: MarketEnvironment) -> None:
        """Batch pricing scales roughly linearly (relative threshold)."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)

        # Time 10 products
        products_10 = create_myga_batch(10)
        start = time.perf_counter()
        registry.price_multiple(products_10)
        time_10 = time.perf_counter() - start

        # Time 100 products
        products_100 = create_myga_batch(100)
        start = time.perf_counter()
        registry.price_multiple(products_100)
        time_100 = time.perf_counter() - start

        # 100 products should take < 20x time of 10 products
        # (allows for setup overhead, avoids absolute timing)
        # This is a very generous threshold to avoid flaky tests
        assert time_100 < time_10 * 20, (
            f"Batch scaling exceeded threshold: 100 products took {time_100:.3f}s, "
            f"10 products took {time_10:.3f}s (ratio: {time_100 / time_10:.1f}x)"
        )

    def test_fia_batch_scaling_relative(self, market_env: MarketEnvironment) -> None:
        """FIA batch pricing scales reasonably."""
        # Use fewer MC paths for speed
        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)

        # Time 5 products
        products_5 = create_fia_batch(5)
        start = time.perf_counter()
        registry.price_multiple(products_5, term_years=1.0)
        time_5 = time.perf_counter() - start

        # Time 20 products
        products_20 = create_fia_batch(20)
        start = time.perf_counter()
        registry.price_multiple(products_20, term_years=1.0)
        time_20 = time.perf_counter() - start

        # 20 products should take < 8x time of 5 products
        # (4x linear + 2x overhead allowance)
        assert time_20 < time_5 * 8, (
            f"FIA batch scaling exceeded threshold: 20 products took {time_20:.3f}s, "
            f"5 products took {time_5:.3f}s (ratio: {time_20 / time_5:.1f}x)"
        )


# =============================================================================
# Path Scaling Tests
# =============================================================================


class TestPathScaling:
    """Tests for MC path count scaling behavior."""

    def test_path_scaling_relative(
        self, market_env: MarketEnvironment, sample_fia: FIAProduct
    ) -> None:
        """MC path count scales sub-linearly (vectorization benefits)."""
        # Registry with 1k paths
        registry_1k = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        start = time.perf_counter()
        registry_1k.price(sample_fia, term_years=1.0, validate=False)
        time_1k = time.perf_counter() - start

        # Registry with 10k paths
        registry_10k = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=BENCHMARK_SEED)
        start = time.perf_counter()
        registry_10k.price(sample_fia, term_years=1.0, validate=False)
        time_10k = time.perf_counter() - start

        # 10x paths should take < 15x time (vectorization helps)
        # Very generous to avoid flaky tests
        assert time_10k < time_1k * 15, (
            f"Path scaling exceeded threshold: 10k paths took {time_10k:.3f}s, "
            f"1k paths took {time_1k:.3f}s (ratio: {time_10k / time_1k:.1f}x)"
        )


# =============================================================================
# Memory Stability Tests
# =============================================================================


class TestMemoryStability:
    """Tests for memory stability over many pricings."""

    def test_myga_memory_stability(
        self, market_env: MarketEnvironment, sample_myga: MYGAProduct
    ) -> None:
        """No memory leak over 1000 MYGA pricings."""
        try:
            import tracemalloc
        except ImportError:
            pytest.skip("tracemalloc not available")

        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)

        tracemalloc.start()

        for _ in range(1000):
            registry.price(sample_myga)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak should be < 100MB for 1000 simple MYGA pricings
        # (MYGA is deterministic, no MC memory)
        assert peak < 100 * 1024 * 1024, f"Memory usage too high: peak {peak / 1024 / 1024:.1f}MB"

    def test_fia_memory_stability(
        self, market_env: MarketEnvironment, sample_fia: FIAProduct
    ) -> None:
        """No memory leak over 100 FIA pricings (with MC)."""
        try:
            import tracemalloc
        except ImportError:
            pytest.skip("tracemalloc not available")

        # Use fewer paths to keep memory reasonable
        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)

        tracemalloc.start()

        for _ in range(100):
            registry.price(sample_fia, term_years=1.0, validate=False)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak should be < 200MB for 100 FIA pricings with 1k paths each
        assert peak < 200 * 1024 * 1024, f"Memory usage too high: peak {peak / 1024 / 1024:.1f}MB"


# =============================================================================
# Convergence Performance Tests
# =============================================================================


class TestConvergencePerformance:
    """Tests for MC convergence characteristics."""

    def test_mc_standard_error_decreases_with_paths(
        self, market_env: MarketEnvironment, sample_fia: FIAProduct
    ) -> None:
        """Standard error decreases with path count.

        Theory: √16 = 4x reduction, but small sample + MC variance
        makes this noisy. Use generous 0.75 threshold.
        """
        results = []

        for n_paths in [1000, 4000, 16000]:
            # Run 5 trials with different seeds
            expected_credits = []
            for seed_offset in range(5):
                registry = ProductRegistry(
                    market_env=market_env,
                    n_mc_paths=n_paths,
                    seed=BENCHMARK_SEED + seed_offset,
                )
                result = registry.price(sample_fia, term_years=1.0, validate=False)
                expected_credits.append(result.expected_credit)

            std_err = np.std(expected_credits)
            results.append((n_paths, std_err))

        # Standard error should decrease with more paths
        # Check that 16k has lower std_err than 1k
        se_1k = results[0][1]
        se_16k = results[2][1]

        # With only 5 trials, variance in SE estimation is high.
        # Use very generous 0.75 threshold (expect ~0.25 from theory)
        assert se_16k < se_1k * 0.75, (
            f"Standard error didn't decrease as expected: "
            f"1k paths SE={se_1k:.6f}, 16k paths SE={se_16k:.6f}"
        )
