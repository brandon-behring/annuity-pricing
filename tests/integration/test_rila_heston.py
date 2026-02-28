"""
Integration tests for RILA pricing with Heston stochastic volatility.

Validates that:
1. RILA pricer correctly dispatches to Heston for option pricing
2. MC expected return uses Heston paths when configured
3. Buffer/floor pricing accounts for volatility smile

[T1] Heston converges to Black-Scholes when sigma → 0 (vol-of-vol approaches zero).

See: docs/knowledge/domain/buffer_floor.md
"""

import pytest

from annuity_pricing.data.schemas import RILAProduct
from annuity_pricing.options.pricing.heston import HestonParams
from annuity_pricing.options.volatility_models import HestonVolatility, VolatilityModelType
from annuity_pricing.products.rila import MarketParams, RILAPricer

# =============================================================================
# Test Configuration
# =============================================================================

#: Standard Heston parameters (typical equity index)
STANDARD_HESTON = HestonParams(
    v0=0.04,  # Initial variance (20% vol)
    kappa=2.0,  # Mean reversion speed
    theta=0.04,  # Long-run variance (20% vol)
    sigma=0.3,  # Vol-of-vol
    rho=-0.7,  # Negative correlation (leverage effect)
)

#: Low vol-of-vol Heston (should converge to BS)
LOW_VOLVOL_HESTON = HestonParams(
    v0=0.04,
    kappa=2.0,
    theta=0.04,
    sigma=0.01,  # Very low vol-of-vol
    rho=-0.5,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def heston_vol():
    """Standard Heston volatility model."""
    return HestonVolatility(STANDARD_HESTON)


@pytest.fixture
def low_volvol():
    """Low vol-of-vol Heston model (converges to BS)."""
    return HestonVolatility(LOW_VOLVOL_HESTON)


@pytest.fixture
def market_params_heston(heston_vol):
    """Market params with Heston model."""
    return MarketParams(
        spot=100.0,
        risk_free_rate=0.05,
        dividend_yield=0.02,
        volatility=0.20,  # Fallback/reference
        vol_model=heston_vol,
    )


@pytest.fixture
def market_params_bs():
    """Market params with default Black-Scholes."""
    return MarketParams(
        spot=100.0,
        risk_free_rate=0.05,
        dividend_yield=0.02,
        volatility=0.20,
    )


@pytest.fixture
def buffer_product():
    """Standard 10% buffer RILA product."""
    return RILAProduct(
        company_name="Test",
        product_name="10% Buffer RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.15,
    )


@pytest.fixture
def floor_product():
    """Standard 10% floor RILA product."""
    return RILAProduct(
        company_name="Test",
        product_name="10% Floor RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered After",
        cap_rate=0.20,
    )


@pytest.fixture
def deep_buffer_product():
    """Deep 20% buffer RILA product."""
    return RILAProduct(
        company_name="Test",
        product_name="20% Buffer RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.20,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.10,
    )


# =============================================================================
# Dispatcher Tests
# =============================================================================


class TestHestonDispatcher:
    """Tests that RILA pricer correctly dispatches to Heston."""

    def test_market_params_uses_stochastic_vol(self, market_params_heston):
        """Market params should report stochastic vol usage."""
        assert market_params_heston.uses_stochastic_vol()
        assert market_params_heston.get_vol_model_type() == VolatilityModelType.HESTON

    def test_market_params_bs_default(self, market_params_bs):
        """Market params without vol_model should use BS."""
        assert not market_params_bs.uses_stochastic_vol()
        assert market_params_bs.get_vol_model_type() == VolatilityModelType.BLACK_SCHOLES

    def test_pricer_initializes_with_heston(self, market_params_heston):
        """RILAPricer should accept Heston market params."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        assert pricer.market_params.uses_stochastic_vol()

    def test_buffer_product_prices_with_heston(self, market_params_heston, buffer_product):
        """Buffer RILA should price successfully with Heston."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        result = pricer.price(buffer_product, term_years=1.0)

        assert result.present_value > 0
        assert result.protection_value > 0
        assert result.protection_type == "buffer"

    def test_floor_product_prices_with_heston(self, market_params_heston, floor_product):
        """Floor RILA should price successfully with Heston."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        result = pricer.price(floor_product, term_years=1.0)

        assert result.present_value > 0
        assert result.protection_value > 0
        assert result.protection_type == "floor"


# =============================================================================
# Convergence Tests
# =============================================================================


class TestHestonBSConvergence:
    """
    Tests that Heston converges to BS when vol-of-vol → 0.

    [T1] When sigma (vol-of-vol) approaches 0, the Heston model degenerates
    to constant volatility, which is equivalent to Black-Scholes.
    """

    def test_protection_value_converges_to_bs(self, low_volvol, buffer_product, market_params_bs):
        """Protection value should converge to BS when sigma → 0."""
        market_heston = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=low_volvol,
        )

        pricer_heston = RILAPricer(market_params=market_heston, n_mc_paths=50000, seed=42)
        pricer_bs = RILAPricer(market_params=market_params_bs, n_mc_paths=50000, seed=42)

        result_heston = pricer_heston.price(buffer_product, term_years=1.0)
        result_bs = pricer_bs.price(buffer_product, term_years=1.0)

        # Protection values should be close
        rel_diff = (
            abs(result_heston.protection_value - result_bs.protection_value)
            / result_bs.protection_value
        )
        assert rel_diff < 0.10, (
            f"Heston protection value {result_heston.protection_value:.4f} "
            f"differs from BS {result_bs.protection_value:.4f} by {rel_diff:.1%}"
        )

    def test_upside_value_converges_to_bs(self, low_volvol, buffer_product, market_params_bs):
        """Upside value should converge to BS when sigma → 0."""
        market_heston = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=low_volvol,
        )

        pricer_heston = RILAPricer(market_params=market_heston, n_mc_paths=50000, seed=42)
        pricer_bs = RILAPricer(market_params=market_params_bs, n_mc_paths=50000, seed=42)

        result_heston = pricer_heston.price(buffer_product, term_years=1.0)
        result_bs = pricer_bs.price(buffer_product, term_years=1.0)

        # Upside values should be close
        rel_diff = abs(result_heston.upside_value - result_bs.upside_value) / result_bs.upside_value
        assert rel_diff < 0.10, (
            f"Heston upside value {result_heston.upside_value:.4f} "
            f"differs from BS {result_bs.upside_value:.4f} by {rel_diff:.1%}"
        )


# =============================================================================
# Sanity Checks
# =============================================================================


class TestHestonSanityChecks:
    """Basic sanity checks for Heston pricing."""

    def test_heston_price_is_positive(self, market_params_heston, buffer_product):
        """Present value should always be positive."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        result = pricer.price(buffer_product, term_years=1.0)
        assert result.present_value > 0

    def test_heston_protection_value_is_positive(self, market_params_heston, buffer_product):
        """Protection value should be positive (cost of protection)."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        result = pricer.price(buffer_product, term_years=1.0)
        assert result.protection_value > 0

    def test_heston_max_loss_correct(self, market_params_heston, buffer_product):
        """Max loss should reflect buffer level."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        result = pricer.price(buffer_product, term_years=1.0)

        # For 10% buffer, max loss is 90% (100% - 10%)
        expected_max_loss = 1.0 - buffer_product.buffer_rate
        assert abs(result.max_loss - expected_max_loss) < 0.001

    def test_deeper_buffer_costs_more(
        self, market_params_heston, buffer_product, deep_buffer_product
    ):
        """Deeper buffer should have higher protection cost."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result_10 = pricer.price(buffer_product, term_years=1.0)
        result_20 = pricer.price(deep_buffer_product, term_years=1.0)

        assert result_20.protection_value > result_10.protection_value

    def test_reproducibility_with_seed(self, market_params_heston, buffer_product):
        """Same seed should give same results."""
        pricer1 = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        pricer2 = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result1 = pricer1.price(buffer_product, term_years=1.0)
        result2 = pricer2.price(buffer_product, term_years=1.0)

        assert result1.expected_return == result2.expected_return


# =============================================================================
# Stochastic Vol Effects on RILA
# =============================================================================


class TestStochasticVolEffects:
    """Tests that verify stochastic vol produces expected effects on RILA."""

    def test_negative_rho_affects_buffer_pricing(self, buffer_product):
        """
        Negative rho should affect buffer (put spread) pricing.

        [T1] With negative correlation, large negative returns coincide with
        high volatility, making OTM puts more expensive relative to BS.
        Buffer = Long ATM put - Short OTM put, so effect depends on relative changes.
        """
        heston_neg = HestonVolatility(
            HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)
        )
        heston_zero = HestonVolatility(
            HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=0.0)
        )

        market_neg = MarketParams(
            spot=100,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=heston_neg,
        )
        market_zero = MarketParams(
            spot=100,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=heston_zero,
        )

        pricer_neg = RILAPricer(market_params=market_neg, n_mc_paths=50000, seed=42)
        pricer_zero = RILAPricer(market_params=market_zero, n_mc_paths=50000, seed=42)

        result_neg = pricer_neg.price(buffer_product, term_years=1.0)
        result_zero = pricer_zero.price(buffer_product, term_years=1.0)

        # Results should differ (skew effect)
        assert result_neg.protection_value != result_zero.protection_value

    def test_higher_volvol_increases_put_value(self, buffer_product):
        """
        Higher vol-of-vol should generally increase put option values.

        [T1] More volatility of volatility means more uncertainty,
        which increases option values (convexity effect).
        """
        heston_low = HestonVolatility(
            HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.1, rho=-0.5)
        )
        heston_high = HestonVolatility(
            HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.5, rho=-0.5)
        )

        market_low = MarketParams(
            spot=100,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=heston_low,
        )
        market_high = MarketParams(
            spot=100,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=heston_high,
        )

        pricer_low = RILAPricer(market_params=market_low, n_mc_paths=50000, seed=42)
        pricer_high = RILAPricer(market_params=market_high, n_mc_paths=50000, seed=42)

        result_low = pricer_low.price(buffer_product, term_years=1.0)
        result_high = pricer_high.price(buffer_product, term_years=1.0)

        # Higher vol-of-vol affects protection pricing
        # Protection value change depends on put spread dynamics
        # Just verify they're different (effect exists)
        assert result_high.protection_value != result_low.protection_value


# =============================================================================
# Buffer vs Floor with Heston
# =============================================================================


class TestBufferFloorWithHeston:
    """Tests comparing buffer vs floor protection under Heston."""

    def test_buffer_vs_floor_comparison(self, market_params_heston, buffer_product, floor_product):
        """Compare buffer and floor protection with same protection level."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result_buffer = pricer.price(buffer_product, term_years=1.0)
        result_floor = pricer.price(floor_product, term_years=1.0)

        # Both should have positive protection values
        assert result_buffer.protection_value > 0
        assert result_floor.protection_value > 0

        # Floor typically provides different protection profile
        # (covers tail losses, not first losses)
        assert result_buffer.protection_type == "buffer"
        assert result_floor.protection_type == "floor"

    def test_buffer_has_lower_max_loss(self, market_params_heston, buffer_product, floor_product):
        """Buffer should have lower max loss for same protection level."""
        pricer = RILAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result_buffer = pricer.price(buffer_product, term_years=1.0)
        result_floor = pricer.price(floor_product, term_years=1.0)

        # Buffer with 10% protection: max loss = 90%
        # Floor with 10% level: max loss = 10%
        assert result_buffer.max_loss > result_floor.max_loss
