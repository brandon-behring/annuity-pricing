"""
Extreme scenario validation for FIA/RILA pricing.

[T1] Validates that FIA/RILA pricers handle edge cases correctly:
- Extreme volatility (5% to 80%)
- Negative interest rates (-2% to 10%)
- Near-expiry options (T < 30 days)
- Deep ITM/OTM positions

These tests verify numerical stability, not external validation.

See: docs/TOLERANCE_JUSTIFICATION.md for anti-pattern tolerances
"""

import numpy as np
import pytest

from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
)
from annuity_pricing.options.pricing.black_scholes import (
    OptionType,
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
)


class TestBSExtremeVolatility:
    """
    Validates Black-Scholes at extreme volatility levels.

    [T1] At all volatility levels:
    - Option prices must be positive
    - Call price bounded by [0, S]
    - Put price bounded by [0, K*e^(-rT)]
    - Greeks must be finite (no NaN/Inf)
    """

    @pytest.mark.validation
    @pytest.mark.parametrize("volatility", [0.05, 0.10, 0.20, 0.40, 0.60, 0.80])
    @pytest.mark.parametrize("option_type", ["call", "put"])
    def test_price_bounds_across_volatility(self, volatility, option_type):
        """[T1] Option price within no-arbitrage bounds at all vol levels."""
        spot = 100.0
        strike = 100.0
        rate = 0.05
        dividend = 0.02
        T = 1.0

        if option_type == "call":
            price = black_scholes_call(spot, strike, rate, dividend, volatility, T)
            upper_bound = spot  # C <= S
            lower_bound = max(spot * np.exp(-dividend * T) - strike * np.exp(-rate * T), 0)
        else:
            price = black_scholes_put(spot, strike, rate, dividend, volatility, T)
            upper_bound = strike * np.exp(-rate * T)  # P <= K*e^(-rT)
            lower_bound = max(strike * np.exp(-rate * T) - spot * np.exp(-dividend * T), 0)

        assert price >= -ANTI_PATTERN_TOLERANCE, f"Price negative: {price}"
        assert price <= upper_bound + ANTI_PATTERN_TOLERANCE, (
            f"Price {price} exceeds upper bound {upper_bound}"
        )
        assert price >= lower_bound - ANTI_PATTERN_TOLERANCE, (
            f"Price {price} below lower bound {lower_bound}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("volatility", [0.05, 0.20, 0.40, 0.80])
    def test_greeks_finite_across_volatility(self, volatility):
        """[T1] All Greeks are finite (no NaN/Inf) at all vol levels."""
        spot = 100.0
        strike = 100.0
        rate = 0.05
        dividend = 0.02
        T = 1.0

        result = black_scholes_greeks(spot, strike, rate, dividend, volatility, T, OptionType.CALL)

        assert np.isfinite(result.delta), f"Delta not finite: {result.delta}"
        assert np.isfinite(result.gamma), f"Gamma not finite: {result.gamma}"
        assert np.isfinite(result.vega), f"Vega not finite: {result.vega}"
        assert np.isfinite(result.theta), f"Theta not finite: {result.theta}"
        assert np.isfinite(result.rho), f"Rho not finite: {result.rho}"


class TestBSNegativeRates:
    """
    Validates Black-Scholes under negative interest rate scenarios.

    [T1] Negative rates are economically valid (ECB, BOJ).
    """

    @pytest.mark.validation
    @pytest.mark.parametrize("rate", [-0.02, -0.01, 0.0, 0.02, 0.05, 0.10])
    def test_price_bounds_negative_rates(self, rate):
        """[T1] Option prices valid under negative rates."""
        spot = 100.0
        strike = 100.0
        dividend = 0.02
        volatility = 0.20
        T = 1.0

        call_price = black_scholes_call(spot, strike, rate, dividend, volatility, T)
        put_price = black_scholes_put(spot, strike, rate, dividend, volatility, T)

        # Both prices should be positive
        assert call_price > -ANTI_PATTERN_TOLERANCE, f"Call negative: {call_price}"
        assert put_price > -ANTI_PATTERN_TOLERANCE, f"Put negative: {put_price}"

        # Put-call parity should hold
        expected_diff = spot * np.exp(-dividend * T) - strike * np.exp(-rate * T)
        actual_diff = call_price - put_price
        parity_error = abs(actual_diff - expected_diff)
        assert parity_error < 1e-8, f"Put-call parity violated at r={rate}: error={parity_error}"


class TestBSNearExpiry:
    """
    Validates Black-Scholes near expiry (T < 30 days).

    [T1] Near-expiry options should converge to intrinsic value.
    """

    @pytest.mark.validation
    @pytest.mark.parametrize("days_to_expiry", [1, 7, 14, 30])
    def test_near_expiry_convergence(self, days_to_expiry):
        """[T1] Near-expiry option converges to intrinsic value."""
        spot = 100.0
        strike = 95.0  # ITM call
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        T = days_to_expiry / 365.0

        call_price = black_scholes_call(spot, strike, rate, dividend, volatility, T)
        intrinsic = max(spot - strike, 0)

        # As T → 0, call price → intrinsic (modulo discount)
        # Allow 20% deviation for short-term options
        if days_to_expiry <= 7:
            assert call_price >= intrinsic * 0.95, (
                f"Near-expiry call {call_price} below 95% intrinsic {intrinsic}"
            )
        else:
            assert call_price >= intrinsic * 0.80, (
                f"Call {call_price} below 80% intrinsic {intrinsic}"
            )

    @pytest.mark.validation
    @pytest.mark.parametrize("days_to_expiry", [1, 7, 14])
    def test_greeks_finite_near_expiry(self, days_to_expiry):
        """[T1] Greeks remain finite near expiry (no div-by-zero)."""
        spot = 100.0
        strike = 100.0
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        T = days_to_expiry / 365.0

        result = black_scholes_greeks(spot, strike, rate, dividend, volatility, T, OptionType.CALL)

        # All Greeks should be finite
        assert np.isfinite(result.price), f"Price not finite: {result.price}"
        assert np.isfinite(result.delta), f"Delta not finite: {result.delta}"
        # Gamma/theta may be large near expiry but should be finite
        assert np.isfinite(result.gamma), f"Gamma not finite: {result.gamma}"
        assert np.isfinite(result.theta), f"Theta not finite: {result.theta}"


class TestBSDeepMoneyness:
    """
    Validates Black-Scholes at deep ITM/OTM levels.

    [T1] Deep ITM/OTM options should have sensible prices.
    """

    @pytest.mark.validation
    @pytest.mark.parametrize("moneyness", [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.5])
    def test_deep_moneyness_bounds(self, moneyness):
        """[T1] Deep ITM/OTM prices within bounds."""
        spot = 100.0
        strike = spot * moneyness
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        T = 1.0

        call_price = black_scholes_call(spot, strike, rate, dividend, volatility, T)
        put_price = black_scholes_put(spot, strike, rate, dividend, volatility, T)

        # Call bounds
        call_upper = spot
        call_lower = max(spot * np.exp(-dividend * T) - strike * np.exp(-rate * T), 0)
        assert call_price <= call_upper + ANTI_PATTERN_TOLERANCE
        assert call_price >= call_lower - ANTI_PATTERN_TOLERANCE

        # Put bounds
        put_upper = strike * np.exp(-rate * T)
        put_lower = max(strike * np.exp(-rate * T) - spot * np.exp(-dividend * T), 0)
        assert put_price <= put_upper + ANTI_PATTERN_TOLERANCE
        assert put_price >= put_lower - ANTI_PATTERN_TOLERANCE


class TestFIAPricerExtremeScenarios:
    """
    Validates FIA pricer under extreme market conditions.

    [T1] FIA pricer should:
    - Return finite values
    - Enforce floor = 0 guarantee
    - Have embedded_option_value <= spot
    """

    @pytest.fixture
    def market_params(self):
        """Create market params fixture factory."""
        from annuity_pricing.products.fia import MarketParams

        def _create(vol=0.20, rate=0.05):
            return MarketParams(
                spot=100.0,
                risk_free_rate=rate,
                dividend_yield=0.02,
                volatility=vol,
            )

        return _create

    @pytest.fixture
    def sample_product(self):
        """Create sample FIA product."""
        from annuity_pricing.data.schemas import FIAProduct

        return FIAProduct(
            company_name="Test Company",
            product_name="Test FIA",
            product_group="FIA",
            status="current",
            cap_rate=0.10,
            indexing_method="Annual Point to Point",
            index_used="S&P 500",
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("volatility", [0.10, 0.30, 0.50, 0.70])
    def test_fia_extreme_vol(self, market_params, sample_product, volatility):
        """[T1] FIA pricer stable at extreme volatilities."""
        from annuity_pricing.products.fia import FIAPricer

        market = market_params(vol=volatility)
        pricer = FIAPricer(market_params=market, n_mc_paths=5000, seed=42)

        result = pricer.price(sample_product, term_years=1, premium=100.0)

        # Result should be valid
        assert np.isfinite(result.embedded_option_value)
        assert result.embedded_option_value >= 0
        assert result.embedded_option_value <= 100.0  # <= premium

        # Expected credit should be bounded by cap
        assert result.expected_credit >= 0
        assert result.expected_credit <= sample_product.cap_rate + 0.01

    @pytest.mark.validation
    @pytest.mark.parametrize("rate", [-0.01, 0.0, 0.03, 0.08])
    def test_fia_various_rates(self, market_params, sample_product, rate):
        """[T1] FIA pricer stable across rate environments."""
        from annuity_pricing.products.fia import FIAPricer

        market = market_params(rate=rate)
        pricer = FIAPricer(market_params=market, n_mc_paths=5000, seed=42)

        result = pricer.price(sample_product, term_years=1, premium=100.0)

        assert np.isfinite(result.embedded_option_value)
        assert result.embedded_option_value >= 0


class TestRILAPricerExtremeScenarios:
    """
    Validates RILA pricer under extreme market conditions.

    [T1] RILA pricer should:
    - Return finite values
    - Have protection_value >= 0
    - Have max_loss bounded by product definition
    """

    @pytest.fixture
    def market_params(self):
        """Create market params fixture factory."""
        from annuity_pricing.products.rila import MarketParams

        def _create(vol=0.20, rate=0.05):
            return MarketParams(
                spot=100.0,
                risk_free_rate=rate,
                dividend_yield=0.02,
                volatility=vol,
            )

        return _create

    @pytest.fixture
    def buffer_product(self):
        """Create sample RILA buffer product."""
        from annuity_pricing.data.schemas import RILAProduct

        return RILAProduct(
            company_name="Test Company",
            product_name="Test RILA",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Up To 10%",  # Required to indicate buffer type
            index_used="S&P 500",
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("volatility", [0.10, 0.30, 0.50, 0.70])
    def test_rila_extreme_vol(self, market_params, buffer_product, volatility):
        """[T1] RILA pricer stable at extreme volatilities."""
        from annuity_pricing.products.rila import RILAPricer

        market = market_params(vol=volatility)
        pricer = RILAPricer(market_params=market, n_mc_paths=5000, seed=42)

        result = pricer.price(buffer_product, term_years=1, premium=100.0)

        # Result should be valid
        assert np.isfinite(result.protection_value)
        assert result.protection_value >= 0

        # Max loss should be bounded (buffer absorbs first 10%)
        assert result.max_loss <= 1.0  # 100% max
        assert result.max_loss >= buffer_product.buffer_rate  # At least buffer exposure

    @pytest.mark.validation
    @pytest.mark.parametrize("rate", [-0.01, 0.0, 0.03, 0.08])
    def test_rila_various_rates(self, market_params, buffer_product, rate):
        """[T1] RILA pricer stable across rate environments."""
        from annuity_pricing.products.rila import RILAPricer

        market = market_params(rate=rate)
        pricer = RILAPricer(market_params=market, n_mc_paths=5000, seed=42)

        result = pricer.price(buffer_product, term_years=1, premium=100.0)

        assert np.isfinite(result.protection_value)
        assert result.protection_value >= 0
