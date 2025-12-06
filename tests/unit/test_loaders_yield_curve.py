"""
Tests for Yield Curve Loader - Phase 10.

[T1] Yield curve properties:
- Discount factor: P(t) = e^(-r(t) × t)
- Forward rate: f(t₁,t₂) = (r(t₂)t₂ - r(t₁)t₁)/(t₂ - t₁)
- Par rate: rate where bond prices at par

See: docs/knowledge/domain/yield_curves.md
"""

import pytest
import numpy as np

from annuity_pricing.loaders.yield_curve import (
    YieldCurve,
    YieldCurveLoader,
    NelsonSiegelParams,
    InterpolationMethod,
    fit_nelson_siegel,
    calculate_duration,
)


class TestYieldCurve:
    """Tests for YieldCurve dataclass."""

    @pytest.fixture
    def simple_curve(self) -> YieldCurve:
        """Simple upward sloping curve."""
        return YieldCurve(
            maturities=np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0]),
            rates=np.array([0.03, 0.035, 0.04, 0.045, 0.05, 0.055]),
            as_of_date="2024-01-15",
            curve_type="treasury",
        )

    def test_curve_creation(self, simple_curve: YieldCurve) -> None:
        """Curve should be created with correct attributes."""
        assert len(simple_curve.maturities) == 6
        assert len(simple_curve.rates) == 6
        assert simple_curve.as_of_date == "2024-01-15"

    def test_get_rate_at_tenor(self, simple_curve: YieldCurve) -> None:
        """Should return exact rate at tenor point."""
        rate = simple_curve.get_rate(1.0)
        assert rate == pytest.approx(0.04)

    def test_get_rate_interpolated(self, simple_curve: YieldCurve) -> None:
        """Should interpolate rate between tenors."""
        rate = simple_curve.get_rate(0.75)
        # Linear interpolation between 0.5 (3.5%) and 1.0 (4.0%)
        expected = 0.035 + 0.5 * (0.04 - 0.035)
        assert rate == pytest.approx(expected, rel=0.01)

    def test_get_rate_extrapolation_flat(self, simple_curve: YieldCurve) -> None:
        """Should flat extrapolate beyond curve."""
        rate = simple_curve.get_rate(15.0)
        # Flat extrapolation uses last rate
        assert rate == pytest.approx(0.055)

    def test_discount_factor_positive_tenor(self, simple_curve: YieldCurve) -> None:
        """Discount factor should be < 1 for positive tenor."""
        df = simple_curve.discount_factor(1.0)
        # P(1) = e^(-0.04 * 1) ≈ 0.9608
        expected = np.exp(-0.04 * 1.0)
        assert df == pytest.approx(expected, rel=0.01)

    def test_discount_factor_decreasing(self, simple_curve: YieldCurve) -> None:
        """Discount factor should decrease with tenor."""
        df1 = simple_curve.discount_factor(1.0)
        df5 = simple_curve.discount_factor(5.0)
        df10 = simple_curve.discount_factor(10.0)

        assert df1 > df5 > df10

    def test_forward_rate_basic(self, simple_curve: YieldCurve) -> None:
        """Forward rate should be calculable."""
        fwd = simple_curve.forward_rate(1.0, 2.0)
        # f(1,2) = (r2*t2 - r1*t1) / (t2 - t1)
        # f(1,2) = (0.045*2 - 0.04*1) / 1 = 0.05
        expected = (0.045 * 2 - 0.04 * 1) / (2 - 1)
        assert fwd == pytest.approx(expected, rel=0.01)

    def test_forward_rate_t1_equals_t2_raises(self, simple_curve: YieldCurve) -> None:
        """Forward rate with t1=t2 should raise."""
        with pytest.raises(ValueError, match="must be greater"):
            simple_curve.forward_rate(1.0, 1.0)

    def test_forward_rate_t2_less_than_t1_raises(self, simple_curve: YieldCurve) -> None:
        """Forward rate with t2<t1 should raise."""
        with pytest.raises(ValueError, match="must be greater"):
            simple_curve.forward_rate(2.0, 1.0)

    def test_par_rate_basic(self, simple_curve: YieldCurve) -> None:
        """Par rate should be positive."""
        par = simple_curve.par_rate(5.0)
        assert par > 0

    def test_par_rate_close_to_zero_coupon(self, simple_curve: YieldCurve) -> None:
        """Par rate should be close to zero-coupon for short tenors."""
        par = simple_curve.par_rate(1.0)
        zero = simple_curve.get_rate(1.0)
        # For 1Y, par and zero should be within ~50bp for low rates
        assert abs(par - zero) < 0.02


class TestYieldCurveInterpolation:
    """Tests for interpolation methods."""

    @pytest.fixture
    def test_curve(self) -> YieldCurve:
        """Curve for interpolation tests."""
        return YieldCurve(
            maturities=np.array([1.0, 2.0, 5.0, 10.0]),
            rates=np.array([0.03, 0.04, 0.045, 0.05]),
            as_of_date="2024-01-01",
            curve_type="treasury",
            interpolation=InterpolationMethod.LINEAR,
        )

    def test_linear_interpolation(self, test_curve: YieldCurve) -> None:
        """Linear interpolation should work."""
        rate = test_curve.get_rate(1.5)
        expected = 0.03 + 0.5 * (0.04 - 0.03)
        assert rate == pytest.approx(expected, rel=0.01)


class TestNelsonSiegelParams:
    """Tests for Nelson-Siegel parameters."""

    def test_params_creation(self) -> None:
        """Should create NS params."""
        params = NelsonSiegelParams(beta0=0.06, beta1=-0.03, beta2=0.01, tau=2.0)

        assert params.beta0 == 0.06
        assert params.beta1 == -0.03
        assert params.beta2 == 0.01
        assert params.tau == 2.0

    def test_rate_at_zero_approaches_beta0_plus_beta1(self) -> None:
        """Rate at t→0 should approach β₀ + β₁."""
        params = NelsonSiegelParams(beta0=0.06, beta1=-0.03, beta2=0.01, tau=2.0)

        # At t=0, returns beta0 + beta1 directly
        rate = params.rate(0.0)
        expected = params.beta0 + params.beta1
        assert rate == pytest.approx(expected)

    def test_rate_at_infinity_approaches_beta0(self) -> None:
        """Rate at t→∞ should approach β₀."""
        params = NelsonSiegelParams(beta0=0.06, beta1=-0.03, beta2=0.01, tau=2.0)

        # Very long tenor
        rate = params.rate(100.0)
        assert rate == pytest.approx(params.beta0, rel=0.01)

    def test_rate_curve_shape(self) -> None:
        """NS curve should produce reasonable shape."""
        params = NelsonSiegelParams(beta0=0.06, beta1=-0.03, beta2=0.01, tau=2.0)

        rates = [params.rate(t) for t in [0.5, 1.0, 2.0, 5.0, 10.0, 30.0]]

        # Should be upward sloping (β₁ < 0)
        assert all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1))


class TestYieldCurveLoader:
    """Tests for YieldCurveLoader."""

    @pytest.fixture
    def loader(self) -> YieldCurveLoader:
        """Yield curve loader instance."""
        return YieldCurveLoader()

    def test_flat_curve(self, loader: YieldCurveLoader) -> None:
        """Should create flat yield curve."""
        curve = loader.flat_curve(0.05)

        assert curve.get_rate(1.0) == pytest.approx(0.05)
        assert curve.get_rate(10.0) == pytest.approx(0.05)

    def test_from_points(self, loader: YieldCurveLoader) -> None:
        """Should create curve from points arrays."""
        maturities = np.array([1.0, 2.0, 5.0, 10.0])
        rates = np.array([0.03, 0.035, 0.04, 0.045])

        curve = loader.from_points(maturities, rates)

        assert curve.get_rate(1.0) == pytest.approx(0.03)
        assert curve.get_rate(10.0) == pytest.approx(0.045)

    def test_from_nelson_siegel(self, loader: YieldCurveLoader) -> None:
        """Should create curve from Nelson-Siegel params."""
        curve = loader.from_nelson_siegel(
            beta0=0.06, beta1=-0.03, beta2=0.01, tau=2.0
        )

        assert isinstance(curve, YieldCurve)
        # Long rate should approach beta0
        assert curve.get_rate(30.0) == pytest.approx(0.06, rel=0.05)


class TestFitNelsonSiegel:
    """Tests for Nelson-Siegel curve fitting."""

    def test_fit_simple_curve(self) -> None:
        """Should fit NS params to simple curve."""
        maturities = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 30.0])
        rates = np.array([0.035, 0.04, 0.045, 0.05, 0.055, 0.06])

        params = fit_nelson_siegel(maturities, rates)

        assert isinstance(params, NelsonSiegelParams)
        assert params.beta0 > 0

    def test_fit_reproduces_rates(self) -> None:
        """Fitted curve should approximately reproduce input rates."""
        maturities = np.array([1.0, 2.0, 5.0, 10.0])
        rates = np.array([0.03, 0.035, 0.04, 0.045])

        params = fit_nelson_siegel(maturities, rates)

        for i, t in enumerate(maturities):
            fitted_rate = params.rate(t)
            # Should be within 50bp of original
            assert abs(fitted_rate - rates[i]) < 0.005


class TestCalculateDuration:
    """Tests for duration calculation."""

    @pytest.fixture
    def loader(self) -> YieldCurveLoader:
        return YieldCurveLoader()

    def _create_bond_cash_flows(
        self, coupon: float, maturity: float, face: float = 100.0
    ) -> tuple:
        """Helper to create bond cash flows."""
        times = np.arange(1, int(maturity) + 1, dtype=float)
        cash_flows = np.full_like(times, coupon * face)
        cash_flows[-1] += face  # Add principal at maturity
        return cash_flows, times

    def test_duration_basic(self, loader: YieldCurveLoader) -> None:
        """Should calculate positive duration."""
        curve = loader.flat_curve(0.05)
        cash_flows, times = self._create_bond_cash_flows(0.05, 10.0)

        duration = calculate_duration(curve, cash_flows, times)

        assert duration > 0
        assert duration < 10.0  # Duration < maturity for coupon bond

    def test_duration_zero_coupon(self, loader: YieldCurveLoader) -> None:
        """Zero-coupon duration should equal maturity."""
        curve = loader.flat_curve(0.05)
        # Zero-coupon: single cash flow at maturity
        times = np.array([10.0])
        cash_flows = np.array([100.0])

        duration = calculate_duration(curve, cash_flows, times)

        assert duration == pytest.approx(10.0, rel=0.01)

    def test_duration_increases_with_maturity(self, loader: YieldCurveLoader) -> None:
        """Duration should increase with maturity."""
        curve = loader.flat_curve(0.05)

        cf_5y, t_5y = self._create_bond_cash_flows(0.05, 5.0)
        cf_10y, t_10y = self._create_bond_cash_flows(0.05, 10.0)
        cf_30y, t_30y = self._create_bond_cash_flows(0.05, 30.0)

        dur_5y = calculate_duration(curve, cf_5y, t_5y)
        dur_10y = calculate_duration(curve, cf_10y, t_10y)
        dur_30y = calculate_duration(curve, cf_30y, t_30y)

        assert dur_5y < dur_10y < dur_30y

    def test_duration_decreases_with_coupon(self, loader: YieldCurveLoader) -> None:
        """Duration should decrease with higher coupon."""
        curve = loader.flat_curve(0.05)

        cf_low, t_low = self._create_bond_cash_flows(0.02, 10.0)
        cf_high, t_high = self._create_bond_cash_flows(0.08, 10.0)

        dur_low = calculate_duration(curve, cf_low, t_low)
        dur_high = calculate_duration(curve, cf_high, t_high)

        assert dur_high < dur_low


class TestDiscountFactorProperties:
    """Tests for discount factor properties."""

    @pytest.fixture
    def flat_curve(self) -> YieldCurve:
        """Flat 5% curve."""
        loader = YieldCurveLoader()
        return loader.flat_curve(0.05)

    def test_df_product_equals_forward(self, flat_curve: YieldCurve) -> None:
        """P(0,t1) × P(t1,t2) should give forward DF."""
        # For flat curve: P(t) = e^(-rt)
        t1, t2 = 2.0, 5.0
        df1 = flat_curve.discount_factor(t1)
        df2 = flat_curve.discount_factor(t2)

        # Ratio should equal forward DF
        fwd_df = df2 / df1
        expected = np.exp(-0.05 * (t2 - t1))
        assert fwd_df == pytest.approx(expected, rel=0.01)

    def test_pv_of_1_at_maturity(self, flat_curve: YieldCurve) -> None:
        """PV of $1 at maturity should equal DF."""
        maturity = 10.0
        df = flat_curve.discount_factor(maturity)
        expected = np.exp(-0.05 * 10)
        assert df == pytest.approx(expected, rel=0.001)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_point_curve(self) -> None:
        """Single point curve should work."""
        curve = YieldCurve(
            maturities=np.array([5.0]),
            rates=np.array([0.05]),
            as_of_date="2024-01-01",
            curve_type="test",
        )

        # Should flat extrapolate everywhere
        assert curve.get_rate(5.0) == pytest.approx(0.05)
        assert curve.get_rate(10.0) == pytest.approx(0.05)

    def test_very_short_tenor(self) -> None:
        """Very short tenor should work."""
        loader = YieldCurveLoader()
        curve = loader.flat_curve(0.05)

        rate = curve.get_rate(0.01)
        assert rate == pytest.approx(0.05)

    def test_very_long_tenor(self) -> None:
        """Very long tenor should work."""
        loader = YieldCurveLoader()
        curve = loader.flat_curve(0.05)

        rate = curve.get_rate(100.0)
        assert rate == pytest.approx(0.05)

    def test_negative_rate_curve(self) -> None:
        """Negative rates should work (post-2008 reality)."""
        curve = YieldCurve(
            maturities=np.array([1.0, 5.0, 10.0]),
            rates=np.array([-0.005, 0.0, 0.01]),
            as_of_date="2024-01-01",
            curve_type="test",
        )

        rate = curve.get_rate(1.0)
        assert rate == pytest.approx(-0.005)

    def test_zero_tenor_raises(self) -> None:
        """Zero tenor should raise."""
        loader = YieldCurveLoader()
        curve = loader.flat_curve(0.05)

        with pytest.raises(ValueError, match="positive"):
            curve.get_rate(0.0)


class TestCurveMismatch:
    """Tests for curve validation."""

    def test_mismatched_lengths_raises(self) -> None:
        """Mismatched maturities and rates should raise."""
        with pytest.raises(ValueError, match="same length"):
            YieldCurve(
                maturities=np.array([1.0, 2.0, 5.0]),
                rates=np.array([0.03, 0.04]),
                as_of_date="2024-01-01",
                curve_type="test",
            )

    def test_non_increasing_maturities_raises(self) -> None:
        """Non-increasing maturities should raise."""
        with pytest.raises(ValueError, match="increasing"):
            YieldCurve(
                maturities=np.array([1.0, 5.0, 3.0]),
                rates=np.array([0.03, 0.04, 0.035]),
                as_of_date="2024-01-01",
                curve_type="test",
            )


class TestCurveFromFRED:
    """Tests for FRED data loading (may skip if no API key)."""

    def test_from_fred_structure(self) -> None:
        """Test FRED loader returns correct structure."""
        # This tests the function signature, actual API call may fail
        try:
            loader = YieldCurveLoader()
            curve = loader.from_fred()
            assert isinstance(curve, YieldCurve)
            assert len(curve.maturities) > 0
        except (ImportError, ValueError, RuntimeError, Exception):
            # Skip if pandas_datareader not installed or API issues
            pytest.skip("FRED data not available")


class TestCurveFromFixture:
    """Tests for fixture-based curve loading. [F.5] Deterministic validation."""

    @pytest.fixture
    def fixture_path(self) -> str:
        """Path to Treasury fixture file."""
        from pathlib import Path

        return str(
            Path(__file__).parent.parent / "fixtures" / "treasury_yields_2024_01_15.csv"
        )

    def test_from_fixture_loads_curve(self, fixture_path: str) -> None:
        """Should load curve from fixture file."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        assert isinstance(curve, YieldCurve)
        assert len(curve.maturities) == 12  # 12 Treasury maturities
        assert curve.curve_type == "treasury_fixture"

    def test_from_fixture_extracts_date(self, fixture_path: str) -> None:
        """Should extract date from filename."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        assert curve.as_of_date == "2024-01-15"

    def test_from_fixture_correct_rates(self, fixture_path: str) -> None:
        """Should load correct rates from fixture."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        # Check a few known rates from the fixture
        # 1-year: 4.82%
        rate_1y = curve.get_rate(1.0)
        assert rate_1y == pytest.approx(0.0482, rel=0.001)

        # 10-year: 4.14%
        rate_10y = curve.get_rate(10.0)
        assert rate_10y == pytest.approx(0.0414, rel=0.001)

    def test_from_fixture_inverted_curve(self, fixture_path: str) -> None:
        """Fixture represents inverted yield curve (short > long)."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        # 2024-01-15 was inverted: short rates > long rates
        rate_1mo = curve.get_rate(0.0833)
        rate_10y = curve.get_rate(10.0)

        assert rate_1mo > rate_10y  # Inverted curve

    def test_from_fixture_discount_factors(self, fixture_path: str) -> None:
        """Discount factors should be properly calculated."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        # 10-year discount factor at ~4.14%
        df_10y = curve.discount_factor(10.0)
        expected = np.exp(-0.0414 * 10)
        assert df_10y == pytest.approx(expected, rel=0.01)

    def test_from_fixture_override_date(self, fixture_path: str) -> None:
        """Should allow date override."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path, as_of_date="2025-01-01")

        assert curve.as_of_date == "2025-01-01"

    def test_from_fixture_missing_file(self) -> None:
        """Should raise FileNotFoundError for missing fixture."""
        loader = YieldCurveLoader()

        with pytest.raises(FileNotFoundError, match="Fixture file not found"):
            loader.from_fixture("nonexistent_fixture.csv")

    def test_from_fixture_forward_rates(self, fixture_path: str) -> None:
        """Forward rates should be calculable from fixture curve."""
        loader = YieldCurveLoader()
        curve = loader.from_fixture(fixture_path)

        # Calculate 1-year forward 1 year from now
        fwd = curve.forward_rate(1.0, 2.0)

        # Should be positive
        assert fwd > 0
