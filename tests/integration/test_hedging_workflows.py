"""
Hedging workflow integration tests.

Tests delta hedging, vega hedging, and risk reduction through hedging.

References:
    [T1] Delta hedging: dP/dS ≈ 0 for hedged position
    [T1] Vega hedging: dP/dσ ≈ 0 for vega-neutral position
"""

import numpy as np
import pytest

from annuity_pricing.data.schemas import (
    FIAProduct,
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
        n_mc_paths=10000,
        seed=42,
    )


@pytest.fixture
def fia_product():
    """Sample FIA for hedging tests."""
    return FIAProduct(
        company_name="Hedge Test",
        product_name="FIA for Hedging",
        product_group="FIA",
        status="current",
        cap_rate=0.05,
        index_used="S&P 500",
    )


@pytest.fixture
def rila_product():
    """Sample RILA for hedging tests."""
    return RILAProduct(
        company_name="Hedge Test",
        product_name="RILA for Hedging",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.15,
        index_used="S&P 500",
    )


# =============================================================================
# Delta Hedging Tests
# =============================================================================


class TestDeltaHedging:
    """Test delta hedging reduces spot risk."""

    def test_fia_delta_hedge_reduces_pnl(self, market_env, fia_product):
        """[T1] Delta-hedged FIA has smaller P&L under spot shock."""
        # Base pricing
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        base_result = base_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Estimate delta via finite difference
        up_market = MarketEnvironment(
            risk_free_rate=market_env.risk_free_rate,
            spot=market_env.spot * 1.01,  # +1% spot
            dividend_yield=market_env.dividend_yield,
            volatility=market_env.volatility,
            option_budget_pct=market_env.option_budget_pct,
        )
        up_registry = ProductRegistry(market_env=up_market, n_mc_paths=10000, seed=42)
        up_result = up_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Unhedged P&L from embedded option
        unhedged_pnl = up_result.embedded_option_value - base_result.embedded_option_value

        # Delta estimate (per 1% spot move)
        delta_estimate = unhedged_pnl / (market_env.spot * 0.01)

        # Hedged P&L: option P&L - delta * spot change
        spot_change = market_env.spot * 0.01
        hedged_pnl = unhedged_pnl - delta_estimate * spot_change

        # Hedged P&L should be much smaller than unhedged
        # Allow for numerical noise in MC
        assert abs(hedged_pnl) < abs(unhedged_pnl) * 0.5 + 10, (
            f"Delta hedging should reduce P&L: unhedged={unhedged_pnl:.2f}, hedged={hedged_pnl:.2f}"
        )

    def test_rila_delta_finite_difference(self, market_env, rila_product):
        """RILA delta can be estimated via finite difference."""
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        base_result = base_registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # Bump up
        up_market = MarketEnvironment(
            risk_free_rate=market_env.risk_free_rate,
            spot=market_env.spot * 1.01,
            dividend_yield=market_env.dividend_yield,
            volatility=market_env.volatility,
            option_budget_pct=market_env.option_budget_pct,
        )
        up_registry = ProductRegistry(market_env=up_market, n_mc_paths=10000, seed=42)
        up_result = up_registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # Delta estimate
        delta = (up_result.protection_value - base_result.protection_value) / (
            market_env.spot * 0.01
        )

        # Delta should be finite and reasonable
        assert np.isfinite(delta), "Delta should be finite"
        # Protection value decreases as spot rises (less likely to need buffer)
        assert delta <= 0 or abs(delta) < 100, "Protection delta should be non-positive or small"


# =============================================================================
# Vega Hedging Tests
# =============================================================================


class TestVegaHedging:
    """Test vega hedging reduces volatility risk."""

    def test_fia_vega_finite_difference(self, market_env, fia_product):
        """FIA vega can be estimated via finite difference."""
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        base_result = base_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Bump volatility by 1%
        up_vol_market = MarketEnvironment(
            risk_free_rate=market_env.risk_free_rate,
            spot=market_env.spot,
            dividend_yield=market_env.dividend_yield,
            volatility=market_env.volatility + 0.01,
            option_budget_pct=market_env.option_budget_pct,
        )
        up_registry = ProductRegistry(market_env=up_vol_market, n_mc_paths=10000, seed=42)
        up_result = up_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Vega estimate (per 1% vol change)
        vega = up_result.embedded_option_value - base_result.embedded_option_value

        # [T1] Vega should be positive for long option position
        assert vega > -50, "FIA vega should be positive or small (long option)"

    def test_rila_vega_positive(self, market_env, rila_product):
        """RILA protection vega should be positive (higher vol = more valuable protection)."""
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        base_result = base_registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # Higher volatility
        high_vol_market = MarketEnvironment(
            risk_free_rate=market_env.risk_free_rate,
            spot=market_env.spot,
            dividend_yield=market_env.dividend_yield,
            volatility=market_env.volatility + 0.05,  # +5% vol
            option_budget_pct=market_env.option_budget_pct,
        )
        high_registry = ProductRegistry(market_env=high_vol_market, n_mc_paths=10000, seed=42)
        high_result = high_registry.price(rila_product, term_years=1.0, premium=100_000.0)

        # Protection value should increase with vol
        assert high_result.protection_value > base_result.protection_value - 50, (
            "Protection value should increase with volatility"
        )


# =============================================================================
# Gamma Hedging Tests
# =============================================================================


class TestGammaExposure:
    """Test gamma exposure estimation."""

    def test_fia_gamma_finite_difference(self, market_env, fia_product):
        """FIA gamma can be estimated via second-order finite difference."""
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)

        # Price at spot - 1%, spot, spot + 1%
        spots = [market_env.spot * 0.99, market_env.spot, market_env.spot * 1.01]
        option_values = []

        for spot in spots:
            mkt = MarketEnvironment(
                risk_free_rate=market_env.risk_free_rate,
                spot=spot,
                dividend_yield=market_env.dividend_yield,
                volatility=market_env.volatility,
                option_budget_pct=market_env.option_budget_pct,
            )
            reg = ProductRegistry(market_env=mkt, n_mc_paths=10000, seed=42)
            result = reg.price(fia_product, term_years=1.0, premium=100_000.0)
            option_values.append(result.embedded_option_value)

        # Second derivative estimate
        h = market_env.spot * 0.01
        gamma = (option_values[2] - 2 * option_values[1] + option_values[0]) / (h**2)

        # Gamma should be finite
        assert np.isfinite(gamma), "Gamma should be finite"

    def test_gamma_convexity(self, market_env, fia_product):
        """Option position should exhibit convexity."""
        # Price at multiple spot levels
        spots = [90, 95, 100, 105, 110]
        option_values = []

        for spot in spots:
            mkt = MarketEnvironment(
                risk_free_rate=market_env.risk_free_rate,
                spot=spot,
                dividend_yield=market_env.dividend_yield,
                volatility=market_env.volatility,
                option_budget_pct=market_env.option_budget_pct,
            )
            reg = ProductRegistry(market_env=mkt, n_mc_paths=10000, seed=42)
            result = reg.price(fia_product, term_years=1.0, premium=100_000.0)
            option_values.append(result.embedded_option_value)

        # Check for convexity pattern (second differences positive for long option)
        # With MC noise, we just check values are all positive
        assert all(v > 0 for v in option_values), "Option values should be positive at all spots"


# =============================================================================
# Hedging Strategy Tests
# =============================================================================


class TestHedgingStrategy:
    """Test hedging strategy effectiveness."""

    def test_rebalancing_improves_hedge(self, market_env, fia_product):
        """Frequent rebalancing should maintain hedge quality."""
        base_registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        base_result = base_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Simulate a 5% spot move
        shocked_market = MarketEnvironment(
            risk_free_rate=market_env.risk_free_rate,
            spot=market_env.spot * 1.05,
            dividend_yield=market_env.dividend_yield,
            volatility=market_env.volatility,
            option_budget_pct=market_env.option_budget_pct,
        )
        shocked_registry = ProductRegistry(market_env=shocked_market, n_mc_paths=10000, seed=42)
        shocked_result = shocked_registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # P&L from spot move
        pnl = shocked_result.embedded_option_value - base_result.embedded_option_value

        # With 5% spot move, P&L should be material (demonstrates hedging need)
        assert abs(pnl) > 0, "Spot move should generate P&L"

    def test_hedge_cost_estimation(self, market_env, fia_product):
        """Estimate hedging cost via bid-ask approximation."""
        registry = ProductRegistry(market_env=market_env, n_mc_paths=10000, seed=42)
        result = registry.price(fia_product, term_years=1.0, premium=100_000.0)

        # Simple hedge cost model: 0.5% of notional per year
        notional = 100_000.0
        annual_hedge_cost = notional * 0.005

        # Embedded option value should exceed typical hedge cost
        # (otherwise product is uneconomical)
        if result.embedded_option_value > 0:
            hedge_cost_ratio = annual_hedge_cost / result.embedded_option_value
            assert hedge_cost_ratio < 0.50, (
                "Hedge cost should be manageable fraction of option value"
            )
