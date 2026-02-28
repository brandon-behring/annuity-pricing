"""
Cross-library validation with oracle fallback.

Tests compare our Black-Scholes implementation against external oracles.
When external libraries (financepy, QuantLib) are unavailable, tests
fall back to stored golden values with a warning.

This ensures CI can validate cross-library consistency even without
optional dependencies installed.

[T1] Black-Scholes formula is deterministic - oracle values should match exactly.
"""

from typing import Any

import pytest

from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
)

# Cross-library tolerance - allow small differences between implementations
ORACLE_TOLERANCE = 0.01  # 1 cent on $10 option


class TestBSCallVsOracle:
    """Test BS call pricing against external oracles."""

    @pytest.mark.validation
    def test_atm_call_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] ATM call price should match oracle value.

        Uses live financepy if available, otherwise stored golden.
        """
        if oracle_bs_prices["live"]:
            # Live validation
            adapter = oracle_bs_prices["adapter"]
            our_price = black_scholes_call(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time_to_expiry=1.0,
            )
            oracle_price = adapter.price_call(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            # Stored oracle fallback
            data = oracle_bs_prices["data"]["bs_call_atm"]
            our_price = black_scholes_call(
                spot=data["params"]["spot"],
                strike=data["params"]["strike"],
                rate=data["params"]["rate"],
                dividend=data["params"]["dividend"],
                volatility=data["params"]["volatility"],
                time_to_expiry=data["params"]["time_to_expiry"],
            )
            oracle_price = data["financepy_value"]

        diff = abs(our_price - oracle_price)
        assert diff < ORACLE_TOLERANCE, (
            f"ATM call price mismatch: ours={our_price:.4f}, "
            f"oracle={oracle_price:.4f}, diff={diff:.4f}, "
            f"source={oracle_bs_prices['source']}"
        )

    @pytest.mark.validation
    def test_itm_call_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] ITM call price should match oracle value.
        """
        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            our_price = black_scholes_call(
                spot=110.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time_to_expiry=1.0,
            )
            oracle_price = adapter.price_call(
                spot=110.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            data = oracle_bs_prices["data"]["bs_call_itm"]
            our_price = black_scholes_call(
                spot=data["params"]["spot"],
                strike=data["params"]["strike"],
                rate=data["params"]["rate"],
                dividend=data["params"]["dividend"],
                volatility=data["params"]["volatility"],
                time_to_expiry=data["params"]["time_to_expiry"],
            )
            oracle_price = data["financepy_value"]

        diff = abs(our_price - oracle_price)
        assert diff < ORACLE_TOLERANCE, (
            f"ITM call price mismatch: ours={our_price:.4f}, "
            f"oracle={oracle_price:.4f}, diff={diff:.4f}"
        )

    @pytest.mark.validation
    def test_otm_call_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] OTM call price should match oracle value.
        """
        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            our_price = black_scholes_call(
                spot=90.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time_to_expiry=1.0,
            )
            oracle_price = adapter.price_call(
                spot=90.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            data = oracle_bs_prices["data"]["bs_call_otm"]
            our_price = black_scholes_call(
                spot=data["params"]["spot"],
                strike=data["params"]["strike"],
                rate=data["params"]["rate"],
                dividend=data["params"]["dividend"],
                volatility=data["params"]["volatility"],
                time_to_expiry=data["params"]["time_to_expiry"],
            )
            oracle_price = data["financepy_value"]

        diff = abs(our_price - oracle_price)
        assert diff < ORACLE_TOLERANCE, (
            f"OTM call price mismatch: ours={our_price:.4f}, "
            f"oracle={oracle_price:.4f}, diff={diff:.4f}"
        )


class TestBSPutVsOracle:
    """Test BS put pricing against external oracles."""

    @pytest.mark.validation
    def test_atm_put_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] ATM put price should match oracle value.
        """
        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            our_price = black_scholes_put(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time_to_expiry=1.0,
            )
            oracle_price = adapter.price_put(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            data = oracle_bs_prices["data"]["bs_put_atm"]
            our_price = black_scholes_put(
                spot=data["params"]["spot"],
                strike=data["params"]["strike"],
                rate=data["params"]["rate"],
                dividend=data["params"]["dividend"],
                volatility=data["params"]["volatility"],
                time_to_expiry=data["params"]["time_to_expiry"],
            )
            oracle_price = data["financepy_value"]

        diff = abs(our_price - oracle_price)
        assert diff < ORACLE_TOLERANCE, (
            f"ATM put price mismatch: ours={our_price:.4f}, "
            f"oracle={oracle_price:.4f}, diff={diff:.4f}"
        )


class TestBSGreeksVsOracle:
    """Test BS Greeks against external oracles."""

    @pytest.mark.validation
    def test_delta_call_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] Call delta should match oracle value.
        """
        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.CALL,
        )

        if oracle_bs_prices["live"]:
            # Live validation uses adapter method
            adapter = oracle_bs_prices["adapter"]
            oracle_delta = adapter.delta(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
                option_type="call",
            )
        else:
            data = oracle_bs_prices["data"]["bs_greeks_atm"]
            oracle_delta = data["delta_call"]

        diff = abs(greeks.delta - oracle_delta)
        assert diff < ORACLE_TOLERANCE, (
            f"Call delta mismatch: ours={greeks.delta:.4f}, "
            f"oracle={oracle_delta:.4f}, diff={diff:.4f}"
        )

    @pytest.mark.validation
    def test_gamma_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] Gamma should match oracle value.
        """
        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.CALL,
        )

        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            oracle_gamma = adapter.gamma(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            data = oracle_bs_prices["data"]["bs_greeks_atm"]
            oracle_gamma = data["gamma"]

        diff = abs(greeks.gamma - oracle_gamma)
        assert diff < 0.001, (
            f"Gamma mismatch: ours={greeks.gamma:.4f}, oracle={oracle_gamma:.4f}, diff={diff:.6f}"
        )

    @pytest.mark.validation
    def test_vega_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] Vega should match oracle value.
        """
        greeks = black_scholes_greeks(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.20,
            time_to_expiry=1.0,
            option_type=OptionType.CALL,
        )

        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            oracle_vega = adapter.vega(
                spot=100.0,
                strike=100.0,
                rate=0.05,
                dividend=0.02,
                volatility=0.20,
                time=1.0,
            )
        else:
            data = oracle_bs_prices["data"]["bs_greeks_atm"]
            oracle_vega = data["vega"]

        diff = abs(greeks.vega - oracle_vega)
        assert diff < 0.1, (  # Vega is larger, so allow more absolute tolerance
            f"Vega mismatch: ours={greeks.vega:.4f}, oracle={oracle_vega:.4f}, diff={diff:.4f}"
        )


class TestHullExampleVsOracle:
    """Test Hull textbook examples against oracles."""

    @pytest.mark.validation
    def test_hull_15_6_vs_oracle(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T1] Hull Example 15.6 should match both textbook and oracle.

        S=42, K=40, r=0.10, q=0, σ=0.20, T=0.5
        Expected: Call = 4.76 (textbook)
        """
        our_price = black_scholes_call(
            spot=42.0,
            strike=40.0,
            rate=0.10,
            dividend=0.0,
            volatility=0.20,
            time_to_expiry=0.5,
        )

        # Hull textbook value
        textbook_value = 4.76

        # Oracle value (stored or live)
        if oracle_bs_prices["live"]:
            adapter = oracle_bs_prices["adapter"]
            oracle_price = adapter.price_call(
                spot=42.0,
                strike=40.0,
                rate=0.10,
                dividend=0.0,
                volatility=0.20,
                time=0.5,
            )
        else:
            data = oracle_bs_prices["data"]["hull_15_6"]
            oracle_price = data["financepy_value"]

        # Check against textbook (looser tolerance for rounding)
        diff_textbook = abs(our_price - textbook_value)
        assert diff_textbook < 0.02, (
            f"Hull 15.6 vs textbook: ours={our_price:.4f}, "
            f"textbook={textbook_value:.2f}, diff={diff_textbook:.4f}"
        )

        # Check against oracle (tighter tolerance)
        diff_oracle = abs(our_price - oracle_price)
        assert diff_oracle < ORACLE_TOLERANCE, (
            f"Hull 15.6 vs oracle: ours={our_price:.4f}, "
            f"oracle={oracle_price:.4f}, diff={diff_oracle:.4f}"
        )


class TestOracleSourceReporting:
    """Test that oracle source is properly reported."""

    @pytest.mark.validation
    def test_oracle_source_available(self, oracle_bs_prices: dict[str, Any]) -> None:
        """
        [T2] Oracle fixture should report its source.
        """
        assert "source" in oracle_bs_prices
        assert oracle_bs_prices["source"] is not None

        # Log the source for debugging
        source = oracle_bs_prices["source"]
        is_live = oracle_bs_prices["live"]

        if is_live:
            assert "live" in source.lower(), f"Live source should contain 'live': {source}"
        else:
            assert "stored" in source.lower() or "json" in source.lower(), (
                f"Stored source should contain 'stored' or 'json': {source}"
            )
