"""
Tests for external validation adapters.

These tests skip if the external library is not installed.
Install with: pip install -e .[validation]
"""

import pytest
import numpy as np

from annuity_pricing.adapters import (
    FINANCEPY_AVAILABLE,
    PYFENG_AVAILABLE,
    QUANTLIB_AVAILABLE,
    ValidationResult,
)
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_pass(self):
        """Passed result should have correct attributes."""
        result = ValidationResult(
            our_value=10.0,
            external_value=10.01,
            difference=-0.01,
            passed=True,
            tolerance=0.05,
            validator_name="test",
        )
        assert result.passed
        assert result.pct_difference == pytest.approx(0.1, rel=0.01)

    def test_validation_result_fail(self):
        """Failed result should have correct attributes."""
        result = ValidationResult(
            our_value=10.0,
            external_value=11.0,
            difference=-1.0,
            passed=False,
            tolerance=0.05,
            validator_name="test",
        )
        assert not result.passed
        assert result.pct_difference == pytest.approx(9.09, rel=0.01)


@pytest.mark.skipif(not FINANCEPY_AVAILABLE, reason="financepy not installed")
class TestFinancepyAdapter:
    """Tests for Financepy Black-Scholes validation."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

        return FinancepyAdapter()

    def test_adapter_available(self, adapter):
        """Adapter should report availability."""
        assert adapter.is_available
        assert adapter.name == "financepy"

    def test_price_call(self, adapter):
        """Should price European call."""
        price = adapter.price_call(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert price > 0
        assert price < 100  # Reasonable bound

    def test_price_put(self, adapter):
        """Should price European put."""
        price = adapter.price_put(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert price > 0
        assert price < 100

    def test_hull_example_15_6(self, adapter):
        """Hull textbook Example 15.6."""
        # Parameters: S=42, K=40, r=0.10, σ=0.20, T=0.5, q=0
        our_price = black_scholes_call(42.0, 40.0, 0.10, 0.0, 0.20, 0.5)
        fp_price = adapter.price_call(42.0, 40.0, 0.10, 0.0, 0.20, 0.5)

        # Both should be close to 4.76
        assert abs(our_price - 4.76) < 0.02
        assert abs(fp_price - 4.76) < 0.02
        # Small difference due to date handling in financepy
        assert abs(our_price - fp_price) < 0.02

    def test_validate_call(self, adapter):
        """Should validate call prices."""
        our_price = black_scholes_call(100.0, 100.0, 0.05, 0.02, 0.20, 1.0)
        result = adapter.validate_call(
            our_price=our_price,
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            tolerance=0.05,
        )

        assert result.passed
        assert result.validator_name == "financepy"

    def test_calculate_greeks(self, adapter):
        """Should calculate Greeks."""
        greeks = adapter.calculate_greeks(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        assert "delta" in greeks
        assert "gamma" in greeks
        assert "vega" in greeks
        assert "theta" in greeks

        # ATM call delta should be ~0.5-0.7
        assert 0.4 < greeks["delta"] < 0.8

    def test_all_golden_cases(self, adapter):
        """All golden test cases should pass."""
        results = adapter.run_golden_tests()

        for result in results:
            assert result.passed, (
                f"{result.test_case} failed: "
                f"our={result.our_value:.4f} vs external={result.external_value:.4f}, "
                f"diff={result.difference:.4f}"
            )


@pytest.mark.skipif(not PYFENG_AVAILABLE, reason="pyfeng not installed")
class TestPyfengAdapter:
    """Tests for pyfeng Monte Carlo validation."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        from annuity_pricing.adapters.pyfeng_adapter import PyfengAdapter

        return PyfengAdapter()

    def test_adapter_available(self, adapter):
        """Adapter should report availability."""
        assert adapter.is_available
        assert adapter.name == "pyfeng"

    def test_price_bs_call(self, adapter):
        """Should price call with BS."""
        price = adapter.price_bs_call(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        assert price > 0
        assert price < 100

    def test_bs_matches_our_implementation(self, adapter):
        """Pyfeng BS should match our BS."""
        our_price = black_scholes_call(100.0, 100.0, 0.05, 0.02, 0.20, 1.0)
        pf_price = adapter.price_bs_call(100.0, 100.0, 0.05, 0.02, 0.20, 1.0)

        assert abs(our_price - pf_price) < 0.01

    def test_validate_against_pyfeng_bs(self, adapter):
        """Should validate against pyfeng BS."""
        our_price = black_scholes_call(100.0, 95.0, 0.05, 0.02, 0.20, 1.0)
        result = adapter.validate_against_pyfeng_bs(
            our_price=our_price,
            spot=100.0,
            strike=95.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        assert result.passed


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not installed")
class TestQuantLibAdapter:
    """Tests for QuantLib yield curve validation."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        return QuantLibAdapter()

    def test_adapter_available(self, adapter):
        """Adapter should report availability."""
        assert adapter.is_available
        assert adapter.name == "QuantLib"

    def test_build_flat_curve(self, adapter):
        """Should build flat curve."""
        curve = adapter.build_flat_curve(0.05)
        assert curve is not None

    def test_discount_factor_flat(self, adapter):
        """Should calculate discount factor."""
        df = adapter.discount_factor_flat(0.05, 1.0)

        # Should match e^(-0.05)
        expected = np.exp(-0.05)
        assert abs(df - expected) < 0.0001

    def test_zero_rate_flat(self, adapter):
        """Zero rate on flat curve should equal input rate."""
        rate = 0.05
        zero = adapter.zero_rate_flat(rate, 5.0)

        # Should be very close to input rate
        assert abs(zero - rate) < 0.0001

    def test_validate_discount_factor(self, adapter):
        """Should validate discount factors."""
        our_df = np.exp(-0.05 * 5.0)
        result = adapter.validate_discount_factor(
            our_df=our_df, rate=0.05, term_years=5.0, tolerance=0.0002
        )

        # Small difference due to day count convention (QuantLib uses calendar)
        assert result.passed

    def test_all_curve_tests(self, adapter):
        """All curve test cases should pass."""
        results = adapter.run_curve_tests()

        for result in results:
            assert result.passed, (
                f"{result.test_case} failed: "
                f"our={result.our_value:.6f} vs external={result.external_value:.6f}"
            )

    def test_price_european_call(self, adapter):
        """Should price European call with QuantLib."""
        ql_price = adapter.price_european_call(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
        )

        our_price = black_scholes_call(100.0, 100.0, 0.05, 0.02, 0.20, 1.0)

        # Should be very close
        assert abs(ql_price - our_price) < 0.05


class TestAdapterNotInstalled:
    """Tests for when adapters are not installed."""

    def test_financepy_import_error(self):
        """Should handle missing financepy gracefully."""
        from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

        adapter = FinancepyAdapter()
        if not adapter.is_available:
            with pytest.raises(ImportError, match="not installed"):
                adapter.require_available()

    def test_pyfeng_import_error(self):
        """Should handle missing pyfeng gracefully."""
        from annuity_pricing.adapters.pyfeng_adapter import PyfengAdapter

        adapter = PyfengAdapter()
        if not adapter.is_available:
            with pytest.raises(ImportError, match="not installed"):
                adapter.require_available()

    def test_quantlib_import_error(self):
        """Should handle missing QuantLib gracefully."""
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if not adapter.is_available:
            with pytest.raises(ImportError, match="not installed"):
                adapter.require_available()
