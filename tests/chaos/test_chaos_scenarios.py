"""
Chaos testing for annuity pricing system.

Tests error handling, extreme market conditions, data corruption detection,
and concurrent pricing safety.

Following CLAUDE.md principle: NEVER FAIL SILENTLY
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
import pytest

from annuity_pricing.data.schemas import FIAProduct, MYGAProduct, RILAProduct
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
    create_default_registry,
)

# =============================================================================
# Constants
# =============================================================================

BENCHMARK_SEED = 42


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def market_env() -> MarketEnvironment:
    """Standard market environment."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        spot=100.0,
        dividend_yield=0.02,
        volatility=0.20,
        option_budget_pct=0.03,
    )


@pytest.fixture
def sample_myga() -> MYGAProduct:
    """Sample MYGA product."""
    return MYGAProduct(
        company_name="Chaos Test Life",
        product_name="Chaos MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def sample_fia() -> FIAProduct:
    """Sample FIA product."""
    return FIAProduct(
        company_name="Chaos Test Life",
        product_name="Chaos FIA",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
        term_years=1,
    )


@pytest.fixture
def sample_rila() -> RILAProduct:
    """Sample RILA product."""
    return RILAProduct(
        company_name="Chaos Test Life",
        product_name="Chaos RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",  # Required field
        cap_rate=0.15,
        term_years=6,
    )


# =============================================================================
# Missing/Invalid Data Tests
# =============================================================================


class TestMissingDataRaises:
    """[T1] Tests that missing data raises explicit errors (never fails silently)."""

    def test_myga_missing_rate_raises(self) -> None:
        """MYGA without fixed_rate raises TypeError at construction time.

        Schema validation correctly catches None values at construction.
        """
        with pytest.raises((TypeError, ValueError)):
            MYGAProduct(
                company_name="Test",
                product_name="Test",
                product_group="MYGA",
                status="current",
                fixed_rate=None,  # type: ignore
                guarantee_duration=5,
            )

    def test_myga_missing_duration_raises(self) -> None:
        """MYGA without guarantee_duration raises TypeError at construction time.

        Schema validation correctly catches None values at construction.
        """
        with pytest.raises((TypeError, ValueError)):
            MYGAProduct(
                company_name="Test",
                product_name="Test",
                product_group="MYGA",
                status="current",
                fixed_rate=0.04,
                guarantee_duration=None,  # type: ignore
            )

    def test_fia_missing_crediting_raises(self) -> None:
        """FIA without any crediting method raises ValueError."""
        product = FIAProduct(
            company_name="Test",
            product_name="Test",
            product_group="FIA",
            status="current",
            cap_rate=None,
            participation_rate=None,
            spread_rate=None,
        )

        registry = create_default_registry()
        with pytest.raises(ValueError, match="crediting method"):
            registry.price(product, term_years=1.0)

    def test_fia_missing_term_raises(self) -> None:
        """FIA without term_years raises ValueError."""
        product = FIAProduct(
            company_name="Test",
            product_name="Test",
            product_group="FIA",
            status="current",
            cap_rate=0.10,
            term_years=None,
        )

        registry = create_default_registry()
        # Don't pass term_years, and product.term_years is None
        with pytest.raises(ValueError, match="term_years"):
            registry.price(product)

    def test_rila_missing_modifier_raises(self) -> None:
        """RILA without buffer_modifier raises ValueError at construction.

        buffer_modifier is required to determine protection type (buffer vs floor).
        """
        with pytest.raises(ValueError, match="buffer_modifier"):
            RILAProduct(
                company_name="Test",
                product_name="Test",
                product_group="RILA",
                status="current",
                buffer_rate=0.10,
                buffer_modifier=None,  # Missing required field
                cap_rate=0.15,
            )


# =============================================================================
# Invalid Value Tests
# =============================================================================


class TestInvalidValuesRaise:
    """Tests that invalid values raise explicit errors."""

    def test_negative_spot_raises(self) -> None:
        """Negative spot price raises ValueError."""
        with pytest.raises(ValueError, match="spot"):
            MarketEnvironment(
                risk_free_rate=0.05,
                spot=-100.0,
                dividend_yield=0.02,
                volatility=0.20,
            )

    def test_negative_volatility_raises(self) -> None:
        """Negative volatility raises ValueError."""
        with pytest.raises(ValueError, match="volatility"):
            MarketEnvironment(
                risk_free_rate=0.05,
                spot=100.0,
                dividend_yield=0.02,
                volatility=-0.20,
            )

    def test_extreme_rate_raises(self) -> None:
        """Extreme interest rates raise ValueError."""
        # Rate > 50% should raise
        with pytest.raises(ValueError, match="risk_free_rate"):
            MarketEnvironment(
                risk_free_rate=0.60,
                spot=100.0,
                dividend_yield=0.02,
                volatility=0.20,
            )

    def test_extreme_negative_rate_raises(self) -> None:
        """Extremely negative rate raises ValueError."""
        # Rate < -10% should raise
        with pytest.raises(ValueError, match="risk_free_rate"):
            MarketEnvironment(
                risk_free_rate=-0.15,
                spot=100.0,
                dividend_yield=0.02,
                volatility=0.20,
            )

    def test_negative_option_budget_raises(self) -> None:
        """Negative option budget raises ValueError."""
        with pytest.raises(ValueError, match="option_budget"):
            MarketEnvironment(
                risk_free_rate=0.05,
                spot=100.0,
                dividend_yield=0.02,
                volatility=0.20,
                option_budget_pct=-0.01,
            )


# =============================================================================
# Extreme Market Conditions Tests
# =============================================================================


class TestExtremeMarketConditions:
    """Tests system handles extreme market conditions gracefully."""

    def test_crisis_like_conditions(self, sample_fia: FIAProduct) -> None:
        """System handles 2008-style crisis parameters."""
        crisis_env = MarketEnvironment(
            risk_free_rate=0.001,  # Near-zero rates
            spot=50.0,  # 50% market drop
            dividend_yield=0.04,  # Higher yields (flight to dividends)
            volatility=0.80,  # VIX > 80
            option_budget_pct=0.03,
        )

        registry = ProductRegistry(market_env=crisis_env, n_mc_paths=1000, seed=BENCHMARK_SEED)

        # Should complete without error
        result = registry.price(sample_fia, term_years=1.0, validate=False)

        # PV should still be positive
        assert result.present_value > 0
        assert np.isfinite(result.present_value)
        assert np.isfinite(result.embedded_option_value)

    def test_high_rate_environment(self, sample_myga: MYGAProduct) -> None:
        """System handles high interest rate environment."""
        high_rate_env = MarketEnvironment(
            risk_free_rate=0.15,  # 15% rates (early 1980s style)
            spot=100.0,
            dividend_yield=0.05,
            volatility=0.25,
        )

        registry = ProductRegistry(market_env=high_rate_env, seed=BENCHMARK_SEED)
        result = registry.price(sample_myga)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)
        assert np.isfinite(result.duration)

    def test_negative_rate_environment(self, sample_myga: MYGAProduct) -> None:
        """System handles negative rate environment (ECB/SNB style)."""
        negative_env = MarketEnvironment(
            risk_free_rate=-0.005,  # -0.5% (negative rates)
            spot=100.0,
            dividend_yield=0.02,
            volatility=0.15,
        )

        registry = ProductRegistry(market_env=negative_env, seed=BENCHMARK_SEED)
        result = registry.price(sample_myga)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)

    def test_zero_volatility(self, sample_fia: FIAProduct) -> None:
        """System handles zero volatility (deterministic world)."""
        zero_vol_env = MarketEnvironment(
            risk_free_rate=0.05,
            spot=100.0,
            dividend_yield=0.02,
            volatility=0.0001,  # Near-zero vol (exactly 0 may cause numerical issues)
        )

        registry = ProductRegistry(market_env=zero_vol_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(sample_fia, term_years=1.0, validate=False)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)

    def test_high_volatility(self, sample_rila: RILAProduct) -> None:
        """System handles very high volatility."""
        high_vol_env = MarketEnvironment(
            risk_free_rate=0.05,
            spot=100.0,
            dividend_yield=0.02,
            volatility=1.50,  # 150% annualized vol
        )

        registry = ProductRegistry(market_env=high_vol_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(sample_rila, term_years=6.0, validate=False)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)


# =============================================================================
# Product Edge Cases
# =============================================================================


class TestProductEdgeCases:
    """Tests edge cases in product specifications."""

    def test_very_short_term(self, market_env: MarketEnvironment) -> None:
        """System handles very short term products."""
        fia = FIAProduct(
            company_name="Test",
            product_name="Short Term FIA",
            product_group="FIA",
            status="current",
            cap_rate=0.10,
            term_years=0.25,  # 3 months
        )

        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(fia, validate=False)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)

    def test_very_long_term(self, market_env: MarketEnvironment) -> None:
        """System handles very long term products."""
        myga = MYGAProduct(
            company_name="Test",
            product_name="Long Term MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.05,
            guarantee_duration=30,  # 30-year MYGA
        )

        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)
        result = registry.price(myga)

        assert result.present_value > 0
        assert np.isfinite(result.present_value)
        assert result.duration == 30

    def test_very_low_cap_rate(self, market_env: MarketEnvironment) -> None:
        """System handles very low cap rate."""
        fia = FIAProduct(
            company_name="Test",
            product_name="Low Cap FIA",
            product_group="FIA",
            status="current",
            cap_rate=0.01,  # 1% cap
            term_years=1,
        )

        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(fia, validate=False)

        assert result.present_value > 0
        # Expected credit should be capped
        assert result.expected_credit <= 0.01 + 0.001  # Small tolerance for MC noise

    def test_high_buffer_rate(self, market_env: MarketEnvironment) -> None:
        """System handles high buffer rate."""
        rila = RILAProduct(
            company_name="Test",
            product_name="High Buffer RILA",
            product_group="RILA",
            status="current",
            buffer_rate=0.30,  # 30% buffer
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.20,
            term_years=6,
        )

        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(rila, term_years=6.0, validate=False)

        assert result.present_value > 0
        assert result.protection_value > 0


# =============================================================================
# Concurrent Pricing Tests
# =============================================================================


class TestConcurrentPricing:
    """Tests thread safety of pricing operations."""

    def test_concurrent_myga_pricing(self, market_env: MarketEnvironment) -> None:
        """Thread-safe MYGA pricing with concurrent.futures."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)

        products = [
            MYGAProduct(
                company_name=f"Concurrent Test {i}",
                product_name=f"MYGA {i}",
                product_group="MYGA",
                status="current",
                fixed_rate=0.04 + i * 0.001,
                guarantee_duration=5,
            )
            for i in range(20)
        ]

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(registry.price, p): p for p in products}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        # All should complete without errors
        assert len(errors) == 0, f"Concurrent pricing errors: {errors}"
        assert len(results) == 20

        # All PVs should be positive and finite
        for result in results:
            assert result.present_value > 0
            assert np.isfinite(result.present_value)

    def test_concurrent_mixed_products(self, market_env: MarketEnvironment) -> None:
        """Thread-safe pricing of mixed product types."""
        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)

        # Create products with unique names
        products: list[tuple[Any, dict]] = []
        for i in range(5):
            products.append(
                (
                    MYGAProduct(
                        company_name="Test",
                        product_name=f"MYGA {i}",
                        product_group="MYGA",
                        status="current",
                        fixed_rate=0.04,
                        guarantee_duration=5,
                    ),
                    {},
                )
            )
            products.append(
                (
                    FIAProduct(
                        company_name="Test",
                        product_name=f"FIA {i}",
                        product_group="FIA",
                        status="current",
                        cap_rate=0.10,
                        term_years=1,
                    ),
                    {"validate": False},
                )
            )

        results = []
        errors = []

        def price_with_kwargs(args: tuple) -> Any:
            product, kwargs = args
            return registry.price(product, **kwargs)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(price_with_kwargs, p): p for p in products}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        # All should complete
        assert len(errors) == 0, f"Concurrent pricing errors: {errors}"
        assert len(results) == 10


# =============================================================================
# Large Portfolio Tests
# =============================================================================


class TestLargePortfolio:
    """Tests for handling large portfolios."""

    def test_large_myga_portfolio(self, market_env: MarketEnvironment) -> None:
        """1000-product MYGA portfolio doesn't OOM."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)

        products = [
            MYGAProduct(
                company_name=f"Test Life {i}",
                product_name=f"MYGA {i}",
                product_group="MYGA",
                status="current",
                fixed_rate=0.04 + (i % 100) * 0.0001,
                guarantee_duration=5 + (i % 5),
            )
            for i in range(1000)
        ]

        results = registry.price_multiple(products)

        assert len(results) == 1000
        # Check no errors
        if "error" in results.columns:
            errors = results[results["error"].notna()]
            assert len(errors) == 0, f"Portfolio pricing errors: {errors['error'].tolist()}"


# =============================================================================
# Numerical Stability Tests
# =============================================================================


class TestNumericalStability:
    """Tests for numerical stability in edge cases."""

    def test_no_nan_in_results(self, market_env: MarketEnvironment, sample_fia: FIAProduct) -> None:
        """No NaN values in pricing results."""
        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(sample_fia, term_years=1.0, validate=False)

        assert not np.isnan(result.present_value)
        assert not np.isnan(result.embedded_option_value)
        assert not np.isnan(result.expected_credit)
        assert not np.isnan(result.duration)

    def test_no_inf_in_results(self, market_env: MarketEnvironment, sample_fia: FIAProduct) -> None:
        """No Inf values in pricing results."""
        registry = ProductRegistry(market_env=market_env, n_mc_paths=1000, seed=BENCHMARK_SEED)
        result = registry.price(sample_fia, term_years=1.0, validate=False)

        assert not np.isinf(result.present_value)
        assert not np.isinf(result.embedded_option_value)
        assert not np.isinf(result.expected_credit)
        assert not np.isinf(result.duration)

    def test_consistent_across_runs(
        self, market_env: MarketEnvironment, sample_myga: MYGAProduct
    ) -> None:
        """MYGA pricing is consistent across multiple runs."""
        registry = ProductRegistry(market_env=market_env, seed=BENCHMARK_SEED)

        results = [registry.price(sample_myga).present_value for _ in range(10)]

        # All results should be identical (MYGA is deterministic)
        assert all(r == results[0] for r in results)
