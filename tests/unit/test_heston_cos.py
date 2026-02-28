"""
Unit tests for Heston COS method implementation.

Tests cover:
- COSParams validation
- Characteristic function properties
- Cumulant calculations
- Truncation range
- Price bounds and sanity checks
- Error handling
"""

import numpy as np
import pytest

from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.heston import HestonParams
from annuity_pricing.options.pricing.heston_cos import (
    COSParams,
    chi_psi_coefficients,
    cos_truncation_range,
    heston_characteristic_function_cos,
    heston_cumulants,
    heston_price_call_cos,
    heston_price_cos,
    heston_price_put_cos,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def standard_heston_params():
    """Standard Heston parameters satisfying Feller condition."""
    return HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)


@pytest.fixture
def high_vol_heston_params():
    """High vol-of-vol parameters (Feller violated)."""
    return HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.6, rho=-0.7)


# =============================================================================
# COSParams Tests
# =============================================================================


class TestCOSParams:
    """Test COSParams dataclass validation."""

    def test_default_values(self):
        """Default values should be N=256, L=10.0."""
        params = COSParams()
        assert params.N == 256
        assert params.L == 10.0

    def test_custom_values(self):
        """Custom values should be accepted."""
        params = COSParams(N=512, L=15.0)
        assert params.N == 512
        assert params.L == 15.0

    def test_n_too_small(self):
        """N < 16 should raise error."""
        with pytest.raises(ValueError, match="N must be >= 16"):
            COSParams(N=8)

    def test_l_zero(self):
        """L <= 0 should raise error."""
        with pytest.raises(ValueError, match="L must be > 0"):
            COSParams(L=0.0)

    def test_l_negative(self):
        """Negative L should raise error."""
        with pytest.raises(ValueError, match="L must be > 0"):
            COSParams(L=-5.0)


# =============================================================================
# Characteristic Function Tests
# =============================================================================


class TestCharacteristicFunction:
    """Test Heston characteristic function properties."""

    def test_phi_at_zero_is_one(self, standard_heston_params):
        """phi(0) = 1 (fundamental property)."""
        phi = heston_characteristic_function_cos(0.0, 0.0, 1.0, 0.05, 0.02, standard_heston_params)
        assert abs(phi - 1.0) < 1e-10

    def test_phi_magnitude_bounded(self, standard_heston_params):
        """|phi(u)| <= 1 for real u (probability density property)."""
        for u in [0.1, 1.0, 5.0, 10.0, 50.0]:
            phi = heston_characteristic_function_cos(
                u, 0.0, 1.0, 0.05, 0.02, standard_heston_params
            )
            assert abs(phi) <= 1.0 + 1e-10, f"|phi({u})| = {abs(phi)} > 1"

    def test_phi_conjugate_symmetry(self, standard_heston_params):
        """phi(-u) = conj(phi(u)) for real u."""
        for u in [1.0, 5.0, 10.0]:
            phi_pos = heston_characteristic_function_cos(
                u, 0.0, 1.0, 0.05, 0.02, standard_heston_params
            )
            phi_neg = heston_characteristic_function_cos(
                -u, 0.0, 1.0, 0.05, 0.02, standard_heston_params
            )
            assert abs(phi_neg - np.conj(phi_pos)) < 1e-10

    def test_phi_decays_with_u(self, standard_heston_params):
        """|phi(u)| should decay as u increases."""
        phi_values = []
        for u in [1, 5, 10, 20, 50]:
            phi = heston_characteristic_function_cos(
                u, 0.0, 1.0, 0.05, 0.02, standard_heston_params
            )
            phi_values.append(abs(phi))

        # Not strictly monotonic, but should generally decrease
        assert phi_values[0] > phi_values[-1], "phi should decay with large u"


# =============================================================================
# Cumulant Tests
# =============================================================================


class TestCumulants:
    """Test Heston cumulant calculations."""

    def test_c2_positive(self, standard_heston_params):
        """Second cumulant (variance) must be positive."""
        c1, c2, c4, w = heston_cumulants(1.0, 0.05, 0.02, standard_heston_params)
        assert c2 > 0, f"c2 = {c2} should be positive"

    def test_cumulants_scale_with_time(self, standard_heston_params):
        """Variance should roughly scale with time."""
        c1_short, c2_short, _, _ = heston_cumulants(0.5, 0.05, 0.02, standard_heston_params)
        c1_long, c2_long, _, _ = heston_cumulants(2.0, 0.05, 0.02, standard_heston_params)

        # c2 should increase with time (not necessarily linearly)
        assert c2_long > c2_short


# =============================================================================
# Truncation Range Tests
# =============================================================================


class TestTruncationRange:
    """Test truncation range calculation."""

    def test_range_centered_on_c1(self):
        """Range should be roughly centered on c1."""
        c1, c2 = 0.03, 0.04
        a, b = cos_truncation_range(c1, c2, L=10.0)

        mid = (a + b) / 2
        assert abs(mid - c1) < 1e-10, f"Range not centered: mid={mid}, c1={c1}"

    def test_range_width_depends_on_variance(self):
        """Higher variance should give wider range."""
        c1 = 0.03
        a_low, b_low = cos_truncation_range(c1, 0.01, L=10.0)
        a_high, b_high = cos_truncation_range(c1, 0.09, L=10.0)

        width_low = b_low - a_low
        width_high = b_high - a_high

        assert width_high > width_low

    def test_range_width_depends_on_L(self):
        """Higher L should give wider range."""
        c1, c2 = 0.03, 0.04
        a_10, b_10 = cos_truncation_range(c1, c2, L=10.0)
        a_15, b_15 = cos_truncation_range(c1, c2, L=15.0)

        assert (b_15 - a_15) > (b_10 - a_10)


# =============================================================================
# Chi-Psi Coefficient Tests
# =============================================================================


class TestChiPsiCoefficients:
    """Test chi and psi payoff coefficients."""

    def test_psi_k0_is_range(self):
        """psi_0 = d - c (integral of constant)."""
        k = np.array([0, 1, 2, 3])
        chi, psi = chi_psi_coefficients(-1.0, 1.0, -0.5, 0.5, k)
        assert abs(psi[0] - 1.0) < 1e-10  # d - c = 0.5 - (-0.5) = 1.0

    def test_coefficients_finite(self):
        """All coefficients should be finite."""
        k = np.arange(256)
        chi, psi = chi_psi_coefficients(-2.0, 2.0, 0.0, 2.0, k)

        assert np.all(np.isfinite(chi)), "chi has non-finite values"
        assert np.all(np.isfinite(psi)), "psi has non-finite values"


# =============================================================================
# Pricing Tests
# =============================================================================


class TestHestonCOSPricing:
    """Test Heston COS pricing function."""

    def test_call_positive(self, standard_heston_params):
        """Call price should be positive."""
        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL)
        assert price > 0

    def test_put_positive(self, standard_heston_params):
        """Put price should be positive."""
        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.PUT)
        assert price > 0

    def test_call_bounded_by_spot(self, standard_heston_params):
        """Call price <= spot (no arbitrage)."""
        spot = 100.0
        price = heston_price_cos(
            spot, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL
        )
        assert price <= spot

    def test_put_bounded_by_strike(self, standard_heston_params):
        """Put price <= K * e^(-rT) (no arbitrage)."""
        strike = 100.0
        rate = 0.05
        time = 1.0
        price = heston_price_cos(
            100, strike, rate, 0.02, time, standard_heston_params, OptionType.PUT
        )
        assert price <= strike * np.exp(-rate * time)

    def test_call_increases_with_spot(self, standard_heston_params):
        """Call price should increase with spot."""
        price_low = heston_price_cos(
            90, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL
        )
        price_high = heston_price_cos(
            110, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL
        )
        assert price_high > price_low

    def test_call_decreases_with_strike(self, standard_heston_params):
        """Call price should decrease with strike."""
        price_low_k = heston_price_cos(
            100, 90, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL
        )
        price_high_k = heston_price_cos(
            100, 110, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL
        )
        assert price_low_k > price_high_k

    def test_put_call_parity(self, standard_heston_params):
        """Put-call parity: C - P = S*e^(-qT) - K*e^(-rT)."""
        spot, strike = 100.0, 100.0
        rate, dividend, time = 0.05, 0.02, 1.0

        call = heston_price_cos(
            spot, strike, rate, dividend, time, standard_heston_params, OptionType.CALL
        )
        put = heston_price_cos(
            spot, strike, rate, dividend, time, standard_heston_params, OptionType.PUT
        )

        forward = spot * np.exp(-dividend * time)
        df_strike = strike * np.exp(-rate * time)
        parity_diff = call - put - (forward - df_strike)

        assert abs(parity_diff) < 1e-6, f"Put-call parity error: {parity_diff}"

    def test_convenience_functions(self, standard_heston_params):
        """Convenience functions should match main function."""
        args = (100, 100, 0.05, 0.02, 1.0, standard_heston_params)

        call_main = heston_price_cos(*args, option_type=OptionType.CALL)
        call_conv = heston_price_call_cos(*args)
        assert abs(call_main - call_conv) < 1e-10

        put_main = heston_price_cos(*args, option_type=OptionType.PUT)
        put_conv = heston_price_put_cos(*args)
        assert abs(put_main - put_conv) < 1e-10


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_negative_spot_raises(self, standard_heston_params):
        """Negative spot should raise ValueError."""
        with pytest.raises(ValueError, match="spot must be > 0"):
            heston_price_cos(-100, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL)

    def test_zero_spot_raises(self, standard_heston_params):
        """Zero spot should raise ValueError."""
        with pytest.raises(ValueError, match="spot must be > 0"):
            heston_price_cos(0, 100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL)

    def test_negative_strike_raises(self, standard_heston_params):
        """Negative strike should raise ValueError."""
        with pytest.raises(ValueError, match="strike must be > 0"):
            heston_price_cos(100, -100, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL)

    def test_negative_time_raises(self, standard_heston_params):
        """Negative time should raise ValueError."""
        with pytest.raises(ValueError, match="time must be > 0"):
            heston_price_cos(100, 100, 0.05, 0.02, -1.0, standard_heston_params, OptionType.CALL)

    def test_feller_violated_still_works(self, high_vol_heston_params):
        """Should still price correctly when Feller is violated."""
        assert not high_vol_heston_params.satisfies_feller()

        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, high_vol_heston_params, OptionType.CALL)
        assert price > 0
        assert np.isfinite(price)


# =============================================================================
# Numerical Stability Tests
# =============================================================================


class TestNumericalStability:
    """Test numerical stability under extreme parameters."""

    def test_very_low_variance(self):
        """Low v0 should still give reasonable prices."""
        params = HestonParams(v0=0.001, kappa=2.0, theta=0.001, sigma=0.1, rho=-0.5)
        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, params, OptionType.CALL)
        assert price > 0
        assert np.isfinite(price)

    def test_high_mean_reversion(self):
        """High kappa should be stable."""
        params = HestonParams(v0=0.04, kappa=10.0, theta=0.04, sigma=0.3, rho=-0.7)
        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, params, OptionType.CALL)
        assert price > 0
        assert np.isfinite(price)

    def test_extreme_correlation(self):
        """rho near -1 should be stable."""
        params = HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.95)
        price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, params, OptionType.CALL)
        assert price > 0
        assert np.isfinite(price)

    def test_deep_itm_call(self, standard_heston_params):
        """Deep ITM call should be close to intrinsic."""
        spot, strike = 150.0, 100.0
        rate, div, time = 0.05, 0.02, 1.0

        price = heston_price_cos(
            spot, strike, rate, div, time, standard_heston_params, OptionType.CALL
        )
        intrinsic = spot * np.exp(-div * time) - strike * np.exp(-rate * time)

        # Price should be >= intrinsic (no early exercise for European)
        assert price >= intrinsic - 0.01

    def test_deep_otm_call(self, standard_heston_params):
        """Deep OTM call should be small but positive."""
        price = heston_price_cos(100, 200, 0.05, 0.02, 1.0, standard_heston_params, OptionType.CALL)
        assert 0 < price < 1.0  # Should be very small
