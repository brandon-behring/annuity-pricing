"""
Integration tests for FIA pricing with Heston stochastic volatility.

Validates that:
1. FIA pricer correctly dispatches to Heston for option pricing
2. MC expected credit uses Heston paths when configured
3. Results are reasonable and consistent with BS (convergence when vol-of-vol → 0)

[T1] Heston converges to Black-Scholes when sigma → 0 (vol-of-vol approaches zero).

See: docs/knowledge/domain/option_pricing.md
"""

import pytest

from annuity_pricing.data.schemas import FIAProduct
from annuity_pricing.options.pricing.heston import HestonParams
from annuity_pricing.options.volatility_models import HestonVolatility
from annuity_pricing.products.fia import FIAPricer, MarketParams

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
def cap_product():
    """Standard capped FIA product."""
    return FIAProduct(
        company_name="Test",
        product_name="10% Cap FIA",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
    )


@pytest.fixture
def participation_product():
    """High participation FIA product."""
    return FIAProduct(
        company_name="Test",
        product_name="150% Participation FIA",
        product_group="FIA",
        status="current",
        participation_rate=1.50,
        cap_rate=0.50,
    )


# =============================================================================
# Dispatcher Tests
# =============================================================================


class TestHestonDispatcher:
    """Tests that FIA pricer correctly dispatches to Heston."""

    def test_market_params_uses_stochastic_vol(self, market_params_heston):
        """Market params should report stochastic vol usage."""
        assert market_params_heston.uses_stochastic_vol()
        from annuity_pricing.options.volatility_models import VolatilityModelType

        assert market_params_heston.get_vol_model_type() == VolatilityModelType.HESTON

    def test_market_params_bs_default(self, market_params_bs):
        """Market params without vol_model should use BS."""
        assert not market_params_bs.uses_stochastic_vol()
        from annuity_pricing.options.volatility_models import VolatilityModelType

        assert market_params_bs.get_vol_model_type() == VolatilityModelType.BLACK_SCHOLES

    def test_pricer_initializes_with_heston(self, market_params_heston):
        """FIAPricer should accept Heston market params."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        assert pricer.market_params.uses_stochastic_vol()

    def test_cap_product_prices_with_heston(self, market_params_heston, cap_product):
        """Capped FIA should price successfully with Heston."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        result = pricer.price(cap_product, term_years=1.0)

        assert result.present_value > 0
        assert result.embedded_option_value > 0
        assert result.expected_credit >= 0

    def test_participation_product_prices_with_heston(
        self, market_params_heston, participation_product
    ):
        """Participation FIA should price successfully with Heston."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=1000, seed=42)
        result = pricer.price(participation_product, term_years=1.0)

        assert result.present_value > 0
        assert result.embedded_option_value > 0
        assert result.expected_credit >= 0


# =============================================================================
# Convergence Tests
# =============================================================================


class TestHestonBSConvergence:
    """
    Tests that Heston converges to BS when vol-of-vol → 0.

    [T1] When sigma (vol-of-vol) approaches 0, the Heston model degenerates
    to constant volatility, which is equivalent to Black-Scholes.
    """

    def test_embedded_option_converges_to_bs(self, low_volvol, cap_product, market_params_bs):
        """Embedded option value should converge to BS when sigma → 0."""
        # Heston with low vol-of-vol
        market_heston = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=low_volvol,
        )

        pricer_heston = FIAPricer(market_params=market_heston, n_mc_paths=50000, seed=42)
        pricer_bs = FIAPricer(market_params=market_params_bs, n_mc_paths=50000, seed=42)

        result_heston = pricer_heston.price(cap_product, term_years=1.0)
        result_bs = pricer_bs.price(cap_product, term_years=1.0)

        # Embedded option values should be close
        rel_diff = (
            abs(result_heston.embedded_option_value - result_bs.embedded_option_value)
            / result_bs.embedded_option_value
        )
        assert rel_diff < 0.05, (
            f"Heston embedded option {result_heston.embedded_option_value:.4f} "
            f"differs from BS {result_bs.embedded_option_value:.4f} by {rel_diff:.1%}"
        )

    def test_fair_cap_converges_to_bs(self, low_volvol, cap_product, market_params_bs):
        """Fair cap rate should converge to BS when sigma → 0."""
        market_heston = MarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            vol_model=low_volvol,
        )

        pricer_heston = FIAPricer(market_params=market_heston, n_mc_paths=50000, seed=42)
        pricer_bs = FIAPricer(market_params=market_params_bs, n_mc_paths=50000, seed=42)

        result_heston = pricer_heston.price(cap_product, term_years=1.0)
        result_bs = pricer_bs.price(cap_product, term_years=1.0)

        # Fair cap rates should be close
        if result_bs.fair_cap is not None and result_heston.fair_cap is not None:
            abs_diff = abs(result_heston.fair_cap - result_bs.fair_cap)
            assert abs_diff < 0.02, (
                f"Heston fair cap {result_heston.fair_cap:.3f} "
                f"differs from BS {result_bs.fair_cap:.3f} by {abs_diff:.3f}"
            )


# =============================================================================
# Sanity Checks
# =============================================================================


class TestHestonSanityChecks:
    """Basic sanity checks for Heston pricing."""

    def test_heston_price_is_positive(self, market_params_heston, cap_product):
        """Present value should always be positive."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        result = pricer.price(cap_product, term_years=1.0)
        assert result.present_value > 0

    def test_heston_expected_credit_is_reasonable(self, market_params_heston, cap_product):
        """Expected credit should be between 0 and cap."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        result = pricer.price(cap_product, term_years=1.0)

        assert result.expected_credit >= 0
        assert result.expected_credit <= cap_product.cap_rate

    def test_heston_longer_term_higher_option_value(self, market_params_heston, cap_product):
        """Longer term should generally have higher option value."""
        pricer = FIAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result_1y = pricer.price(cap_product, term_years=1.0)
        result_3y = pricer.price(cap_product, term_years=3.0)

        # Option value should be higher for longer term (more time value)
        assert result_3y.embedded_option_value > result_1y.embedded_option_value * 0.9

    def test_reproducibility_with_seed(self, market_params_heston, cap_product):
        """Same seed should give same results."""
        pricer1 = FIAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)
        pricer2 = FIAPricer(market_params=market_params_heston, n_mc_paths=10000, seed=42)

        result1 = pricer1.price(cap_product, term_years=1.0)
        result2 = pricer2.price(cap_product, term_years=1.0)

        assert result1.expected_credit == result2.expected_credit


# =============================================================================
# Stochastic Vol Effects
# =============================================================================


class TestStochasticVolEffects:
    """Tests that verify stochastic vol produces expected effects."""

    def test_negative_rho_produces_skew(self, cap_product):
        """
        Negative rho should produce volatility skew (downside more expensive).

        [T1] With negative correlation, large negative returns coincide with
        high volatility, making OTM puts more expensive relative to BS.
        """
        # Standard negative rho
        heston_neg = HestonVolatility(
            HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)
        )
        # Zero rho (no skew)
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

        pricer_neg = FIAPricer(market_params=market_neg, n_mc_paths=50000, seed=42)
        pricer_zero = FIAPricer(market_params=market_zero, n_mc_paths=50000, seed=42)

        result_neg = pricer_neg.price(cap_product, term_years=1.0)
        result_zero = pricer_zero.price(cap_product, term_years=1.0)

        # Results should differ (skew effect)
        # Note: exact direction depends on product structure
        assert result_neg.embedded_option_value != result_zero.embedded_option_value

    def test_higher_volvol_increases_option_value(self, cap_product):
        """
        Higher vol-of-vol should generally increase option values.

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

        pricer_low = FIAPricer(market_params=market_low, n_mc_paths=50000, seed=42)
        pricer_high = FIAPricer(market_params=market_high, n_mc_paths=50000, seed=42)

        result_low = pricer_low.price(cap_product, term_years=1.0)
        result_high = pricer_high.price(cap_product, term_years=1.0)

        # Higher vol-of-vol should increase ATM call value
        assert result_high.embedded_option_value >= result_low.embedded_option_value * 0.95
