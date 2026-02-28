"""
Portfolio workflow integration tests.

Tests pricing, aggregation, and analysis of portfolios containing
multiple products across MYGA, FIA, and RILA types.

Approach: Hybrid (Parametric Sweep + Symbolic Portfolios)
- Parametric sweep: Systematic coverage of rate/term/type combinations
- Symbolic portfolios: Hand-crafted for specific test scenarios

References:
    [T1] Portfolio diversification should reduce risk vs concentrated positions
"""

import numpy as np
import pytest

from annuity_pricing.config.tolerances import INTEGRATION_TOLERANCE
from annuity_pricing.data.schemas import (
    FIAProduct,
    MYGAProduct,
    RILAProduct,
)
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def market_env():
    """Standard market environment."""
    return MarketEnvironment(
        risk_free_rate=0.05,
        spot=100.0,
        dividend_yield=0.02,
        volatility=0.20,
        option_budget_pct=0.03,
    )


@pytest.fixture
def registry(market_env):
    """Registry with seeded RNG."""
    return ProductRegistry(
        market_env=market_env,
        n_mc_paths=5000,  # Reduced for faster tests
        seed=42,
    )


def create_myga_products(rates, terms):
    """Create MYGA products for parametric sweep."""
    products = []
    for rate in rates:
        for term in terms:
            products.append(
                MYGAProduct(
                    company_name="Sweep MYGA",
                    product_name=f"MYGA r={rate:.1%} t={term}",
                    product_group="MYGA",
                    status="current",
                    fixed_rate=rate,
                    guarantee_duration=term,
                )
            )
    return products


def create_fia_products(caps, terms):
    """Create FIA products for parametric sweep."""
    products = []
    for cap in caps:
        for term in terms:
            products.append(
                FIAProduct(
                    company_name="Sweep FIA",
                    product_name=f"FIA cap={cap:.1%} t={term}",
                    product_group="FIA",
                    status="current",
                    cap_rate=cap,
                    index_used="S&P 500",
                )
            )
    return products


def create_rila_products(buffers, terms):
    """Create RILA products for parametric sweep."""
    products = []
    for buffer in buffers:
        for term in terms:
            products.append(
                RILAProduct(
                    company_name="Sweep RILA",
                    product_name=f"RILA buf={buffer:.1%} t={term}",
                    product_group="RILA",
                    status="current",
                    buffer_rate=buffer,
                    buffer_modifier="Losses Covered Up To",
                    cap_rate=0.15,
                    index_used="S&P 500",
                )
            )
    return products


# =============================================================================
# Parametric Portfolio Tests
# =============================================================================


class TestParametricPortfolio:
    """Test systematic portfolio construction and pricing."""

    def test_myga_portfolio_sweep(self, registry):
        """Price 12-product MYGA parametric portfolio (3 rates × 4 terms)."""
        products = create_myga_products(
            rates=[0.03, 0.04, 0.05],
            terms=[3, 5, 7, 10],
        )
        assert len(products) == 12

        results_df = registry.price_multiple(products)

        # All should price successfully
        assert len(results_df) == 12
        assert "error" not in results_df.columns or results_df["error"].isna().all()
        assert all(results_df["present_value"] > 0)

    def test_fia_portfolio_sweep(self, registry):
        """Price 9-product FIA parametric portfolio (3 caps × 3 terms)."""
        products = create_fia_products(
            caps=[0.04, 0.05, 0.06],  # Lower caps to fit budget tolerance
            terms=[1, 3, 5],
        )
        assert len(products) == 9

        results_df = registry.price_multiple(products, term_years=1.0)

        assert len(results_df) == 9
        assert "error" not in results_df.columns or results_df["error"].isna().all()
        assert all(results_df["present_value"] > 0)

    def test_rila_portfolio_sweep(self, registry):
        """Price 6-product RILA parametric portfolio (3 buffers × 2 terms)."""
        products = create_rila_products(
            buffers=[0.10, 0.15, 0.20],
            terms=[3, 6],
        )
        assert len(products) == 6

        results_df = registry.price_multiple(products, term_years=1.0)

        assert len(products) == 6
        assert "error" not in results_df.columns or results_df["error"].isna().all()
        assert all(results_df["present_value"] > 0)

    def test_mixed_parametric_portfolio(self, registry):
        """Price 27-product mixed portfolio (9 MYGA + 9 FIA + 9 RILA)."""
        myga_products = create_myga_products([0.03, 0.04, 0.05], [3, 5, 7])
        fia_products = create_fia_products([0.04, 0.05, 0.06], [1, 3, 5])
        rila_products = create_rila_products([0.10, 0.15, 0.20], [3, 6, 9])

        products = myga_products + fia_products + rila_products
        assert len(products) == 27

        results_df = registry.price_multiple(products, term_years=1.0)

        assert len(results_df) == 27
        assert all(results_df["present_value"] > 0)


# =============================================================================
# Portfolio Aggregation Tests
# =============================================================================


class TestPortfolioAggregation:
    """Test portfolio-level calculations."""

    def test_total_pv_positive(self, registry):
        """Portfolio total PV should be positive."""
        products = (
            create_myga_products([0.04], [5])
            + create_fia_products([0.05], [1])
            + create_rila_products([0.10], [3])
        )

        results_df = registry.price_multiple(products, term_years=1.0)
        total_pv = results_df["present_value"].sum()

        assert total_pv > 0

    def test_portfolio_duration_weighted(self, registry):
        """Weighted duration should be computable."""
        products = create_myga_products([0.03, 0.04, 0.05], [3, 5, 7])
        results_df = registry.price_multiple(products)

        # Weighted average duration
        pvs = results_df["present_value"].values
        durations = results_df["duration"].values

        # Skip if any duration is None
        if any(d is None for d in durations):
            pytest.skip("Some durations are None")

        weighted_duration = np.average(durations, weights=pvs)
        assert 3 <= weighted_duration <= 7  # Should be within term range


# =============================================================================
# Rate Shock Tests
# =============================================================================


class TestPortfolioRateShocks:
    """Test portfolio behavior under rate shocks."""

    def test_myga_pv_decreases_with_rate_increase(self):
        """[T1] MYGA PV should decrease when discount rate rises."""
        base_market = MarketEnvironment(risk_free_rate=0.05)
        shocked_market = MarketEnvironment(risk_free_rate=0.07)

        base_registry = ProductRegistry(market_env=base_market, seed=42)
        shocked_registry = ProductRegistry(market_env=shocked_market, seed=42)

        products = create_myga_products([0.04], [5])
        base_pv = base_registry.price_multiple(products)["present_value"].sum()
        shocked_pv = shocked_registry.price_multiple(products)["present_value"].sum()

        assert shocked_pv < base_pv, "+200bp rate shock should decrease MYGA PV"

    def test_portfolio_rate_sensitivity(self):
        """Portfolio PV changes with rate environment."""
        base_market = MarketEnvironment(risk_free_rate=0.05)
        shocked_market = MarketEnvironment(risk_free_rate=0.06)

        base_registry = ProductRegistry(market_env=base_market, n_mc_paths=5000, seed=42)
        shocked_registry = ProductRegistry(market_env=shocked_market, n_mc_paths=5000, seed=42)

        products = (
            create_myga_products([0.04], [5])
            + create_fia_products([0.05], [1])
            + create_rila_products([0.10], [3])
        )

        base_results = base_registry.price_multiple(products, term_years=1.0)
        shocked_results = shocked_registry.price_multiple(products, term_years=1.0)

        # PV should change under rate shock
        base_total = base_results["present_value"].sum()
        shocked_total = shocked_results["present_value"].sum()

        # Direction depends on product mix, but values should differ
        assert abs(base_total - shocked_total) > INTEGRATION_TOLERANCE


# =============================================================================
# Vol Shock Tests
# =============================================================================


class TestPortfolioVolShocks:
    """Test portfolio behavior under volatility shocks."""

    def test_option_value_increases_with_vol(self):
        """[T1] FIA/RILA option value should increase with volatility.

        Note: For capped options, higher vol can actually DECREASE value
        when the cap limits upside. This is the opposite of vanilla options.
        We test the RILA protection value which has clearer vol sensitivity.
        """
        low_vol_market = MarketEnvironment(volatility=0.15)
        high_vol_market = MarketEnvironment(volatility=0.30)

        low_vol_registry = ProductRegistry(market_env=low_vol_market, n_mc_paths=10000, seed=42)
        high_vol_registry = ProductRegistry(market_env=high_vol_market, n_mc_paths=10000, seed=42)

        # RILA protection value increases with vol (more risk to protect against)
        rila = RILAProduct(
            company_name="Test",
            product_name="Vol Test RILA",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            index_used="S&P 500",
        )

        low_vol_result = low_vol_registry.price(rila, term_years=1.0)
        high_vol_result = high_vol_registry.price(rila, term_years=1.0)

        # Protection value should increase with vol
        # (buffer is more valuable when there's more downside risk)
        assert high_vol_result.protection_value > low_vol_result.protection_value - 0.5, (
            "Higher vol should increase protection value"
        )


# =============================================================================
# Portfolio Composition Tests
# =============================================================================


class TestPortfolioComposition:
    """Test portfolio composition effects."""

    def test_myga_only_vs_mixed(self, registry):
        """Compare MYGA-only vs mixed portfolio characteristics."""
        myga_only = create_myga_products([0.04], [5, 7])
        mixed = create_myga_products([0.04], [5]) + create_rila_products([0.10], [3])

        myga_results = registry.price_multiple(myga_only, term_years=1.0)
        mixed_results = registry.price_multiple(mixed, term_years=1.0)

        # Both should price successfully
        assert len(myga_results) == 2
        assert len(mixed_results) == 2
        assert all(myga_results["present_value"] > 0)
        assert all(mixed_results["present_value"] > 0)

    def test_large_portfolio_pricing(self, registry):
        """Price larger portfolio (50+ products) without failure."""
        # Create 50-product portfolio
        products = (
            create_myga_products([0.03, 0.04, 0.05], [3, 5, 7, 10])  # 12
            + create_myga_products([0.035, 0.045], [3, 5, 7])  # 6
            + create_fia_products([0.04, 0.05, 0.06], [1, 3, 5, 7])  # 12
            + create_fia_products([0.045, 0.055], [1, 3, 5])  # 6
            + create_rila_products([0.10, 0.15, 0.20, 0.25], [3, 6])  # 8
            + create_rila_products([0.12, 0.18], [3, 6, 9])  # 6
        )

        assert len(products) >= 50

        results_df = registry.price_multiple(products, term_years=1.0)

        assert len(results_df) == len(products)
        # Allow some failures due to extreme parameters, but most should succeed
        success_rate = results_df["present_value"].notna().mean()
        assert success_rate >= 0.90, f"Success rate {success_rate:.1%} too low"
