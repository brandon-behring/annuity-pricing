"""
Golden file regression tests.

Verifies that pricing outputs match known-correct values from:
- Hull textbook examples (analytical solutions)
- SEC RILA rule examples (regulatory compliance)
- Portfolio baselines (historical snapshots)

These tests catch regressions where implementation changes
inadvertently alter outputs.

References:
    [T1] Hull (2021) Options, Futures, and Other Derivatives
    [T1] SEC RILA Final Rule 2024

See: scripts/regenerate_goldens.py for regeneration
"""

import json
from pathlib import Path

import pytest

from annuity_pricing.config.tolerances import (
    GOLDEN_RELATIVE_TOLERANCE,
    HULL_EXAMPLE_TOLERANCE,
)
from annuity_pricing.data.schemas import FIAProduct, MYGAProduct, RILAProduct
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.payoffs.fia import CappedCallPayoff
from annuity_pricing.options.payoffs.rila import BufferPayoff, FloorPayoff
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
)
from annuity_pricing.products.fia import FIAPricer
from annuity_pricing.products.fia import MarketParams as FIAMarketParams
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.rila import MarketParams as RILAMarketParams
from annuity_pricing.products.rila import RILAPricer

# =============================================================================
# Golden File Loading
# =============================================================================

GOLDEN_DIR = Path(__file__).parent / "outputs"


def load_golden(filename: str) -> dict:
    """Load a golden file."""
    filepath = GOLDEN_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Golden file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)


# =============================================================================
# Hull Textbook Examples
# =============================================================================


class TestHullExamples:
    """Verify pricing matches Hull textbook examples."""

    @pytest.fixture(scope="class")
    def hull_data(self) -> dict:
        return load_golden("hull_examples.json")

    def test_example_15_6_call(self, hull_data: dict) -> None:
        """Hull Example 15.6: European call option."""
        example = hull_data["example_15_6_call"]
        params = example["parameters"]

        call = black_scholes_call(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
        )

        expected = example["expected"]["call_price"]
        assert abs(call - expected) < HULL_EXAMPLE_TOLERANCE, (
            f"Hull 15.6 call: got {call:.4f}, expected {expected}"
        )

    def test_example_15_6_put(self, hull_data: dict) -> None:
        """Hull Example 15.6: European put option."""
        example = hull_data["example_15_6_put"]
        params = example["parameters"]

        put = black_scholes_put(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
        )

        expected = example["expected"]["put_price"]
        assert abs(put - expected) < HULL_EXAMPLE_TOLERANCE, (
            f"Hull 15.6 put: got {put:.4f}, expected {expected}"
        )

    def test_example_19_1_delta(self, hull_data: dict) -> None:
        """Hull Example 19.1: Delta calculation."""
        example = hull_data["example_19_1_delta"]
        params = example["parameters"]

        greeks = black_scholes_greeks(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        expected = example["expected"]["delta"]
        # Delta tolerance is tighter since it's in [0,1]
        assert abs(greeks.delta - expected) < 0.005, (
            f"Hull 19.1 delta: got {greeks.delta:.4f}, expected {expected}"
        )

    def test_example_19_4_gamma(self, hull_data: dict) -> None:
        """Hull Example 19.4: Gamma calculation."""
        example = hull_data["example_19_4_gamma"]
        params = example["parameters"]

        greeks = black_scholes_greeks(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        expected = example["expected"]["gamma"]
        # Gamma is small, use relative tolerance
        assert abs(greeks.gamma - expected) < 0.002, (
            f"Hull 19.4 gamma: got {greeks.gamma:.4f}, expected {expected}"
        )

    def test_example_19_6_vega(self, hull_data: dict) -> None:
        """Hull Example 19.6: Vega calculation."""
        example = hull_data["example_19_6_vega"]
        params = example["parameters"]

        greeks = black_scholes_greeks(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        expected = example["expected"]["vega_per_pct"]
        # Our vega is scaled to 1% move, Hull's is per 1% change
        # vega_per_pct = S * sqrt(T) * N'(d1) / 100
        # We need to compare correctly
        # Our vega is already scaled to 1% move
        actual_vega_pct = greeks.vega * 100  # Convert to same units as Hull

        assert abs(actual_vega_pct - expected) < 0.5, (
            f"Hull 19.6 vega: got {actual_vega_pct:.2f}, expected {expected}"
        )

    def test_atm_call_with_dividend(self, hull_data: dict) -> None:
        """ATM call with continuous dividend."""
        example = hull_data["atm_call_with_dividend"]
        params = example["parameters"]

        call = black_scholes_call(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
        )

        expected = example["expected"]["call_price"]
        assert abs(call - expected) < HULL_EXAMPLE_TOLERANCE, (
            f"ATM call with dividend: got {call:.4f}, expected {expected}"
        )

    def test_itm_call_with_dividend(self, hull_data: dict) -> None:
        """ITM call with continuous dividend."""
        example = hull_data["itm_call_with_dividend"]
        params = example["parameters"]

        call = black_scholes_call(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
        )

        expected = example["expected"]["call_price"]
        assert abs(call - expected) < HULL_EXAMPLE_TOLERANCE, (
            f"ITM call with dividend: got {call:.4f}, expected {expected}"
        )

    def test_otm_call_with_dividend(self, hull_data: dict) -> None:
        """OTM call with continuous dividend."""
        example = hull_data["otm_call_with_dividend"]
        params = example["parameters"]

        call = black_scholes_call(
            spot=params["spot"],
            strike=params["strike"],
            rate=params["rate"],
            dividend=params["dividend"],
            volatility=params["volatility"],
            time_to_expiry=params["time_to_expiry"],
        )

        expected = example["expected"]["call_price"]
        assert abs(call - expected) < HULL_EXAMPLE_TOLERANCE, (
            f"OTM call with dividend: got {call:.4f}, expected {expected}"
        )


# =============================================================================
# SEC RILA Examples
# =============================================================================


class TestSECRILAExamples:
    """Verify RILA payoffs match SEC rule examples."""

    @pytest.fixture(scope="class")
    def sec_data(self) -> dict:
        return load_golden("sec_rila_examples.json")

    def test_buffer_10_loss_5(self, sec_data: dict) -> None:
        """10% buffer absorbs 5% loss completely."""
        example = sec_data["buffer_10_loss_5"]
        params = example["parameters"]

        payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Buffer 10% loss 5%: got {result.credited_return}, expected {expected}"
        )

    def test_buffer_10_loss_15(self, sec_data: dict) -> None:
        """10% buffer absorbs first 10% of 15% loss."""
        example = sec_data["buffer_10_loss_15"]
        params = example["parameters"]

        payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Buffer 10% loss 15%: got {result.credited_return}, expected {expected}"
        )

    def test_buffer_10_loss_25(self, sec_data: dict) -> None:
        """10% buffer with 25% market loss."""
        example = sec_data["buffer_10_loss_25"]
        params = example["parameters"]

        payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Buffer 10% loss 25%: got {result.credited_return}, expected {expected}"
        )

    def test_buffer_10_gain_12(self, sec_data: dict) -> None:
        """10% buffer with 12% gain (full upside)."""
        example = sec_data["buffer_10_gain_12"]
        params = example["parameters"]

        payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Buffer gain: got {result.credited_return}, expected {expected}"
        )

    def test_floor_10_loss_5(self, sec_data: dict) -> None:
        """-10% floor with 5% loss (no protection needed)."""
        example = sec_data["floor_10_loss_5"]
        params = example["parameters"]

        payoff = FloorPayoff(floor_rate=params["floor_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Floor loss 5%: got {result.credited_return}, expected {expected}"
        )

    def test_floor_10_loss_15(self, sec_data: dict) -> None:
        """-10% floor limits 15% loss to 10%."""
        example = sec_data["floor_10_loss_15"]
        params = example["parameters"]

        payoff = FloorPayoff(floor_rate=params["floor_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Floor loss 15%: got {result.credited_return}, expected {expected}"
        )

    def test_floor_10_loss_25(self, sec_data: dict) -> None:
        """-10% floor with 25% market loss."""
        example = sec_data["floor_10_loss_25"]
        params = example["parameters"]

        payoff = FloorPayoff(floor_rate=params["floor_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"Floor loss 25%: got {result.credited_return}, expected {expected}"
        )

    def test_buffer_vs_floor_small_loss(self, sec_data: dict) -> None:
        """Buffer better for small losses."""
        example = sec_data["buffer_vs_floor_small_loss"]
        params = example["parameters"]

        buffer_payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        floor_payoff = FloorPayoff(floor_rate=params["floor_rate"])

        buffer_result = buffer_payoff.calculate(params["index_return"])
        floor_result = floor_payoff.calculate(params["index_return"])

        expected_buffer = example["expected"]["buffer_credited"]
        expected_floor = example["expected"]["floor_credited"]

        assert abs(buffer_result.credited_return - expected_buffer) < GOLDEN_RELATIVE_TOLERANCE
        assert abs(floor_result.credited_return - expected_floor) < GOLDEN_RELATIVE_TOLERANCE
        assert buffer_result.credited_return > floor_result.credited_return, (
            "Buffer should be better for small losses"
        )

    def test_buffer_vs_floor_large_loss(self, sec_data: dict) -> None:
        """Floor better for large losses."""
        example = sec_data["buffer_vs_floor_large_loss"]
        params = example["parameters"]

        buffer_payoff = BufferPayoff(buffer_rate=params["buffer_rate"])
        floor_payoff = FloorPayoff(floor_rate=params["floor_rate"])

        buffer_result = buffer_payoff.calculate(params["index_return"])
        floor_result = floor_payoff.calculate(params["index_return"])

        expected_buffer = example["expected"]["buffer_credited"]
        expected_floor = example["expected"]["floor_credited"]

        assert abs(buffer_result.credited_return - expected_buffer) < GOLDEN_RELATIVE_TOLERANCE
        assert abs(floor_result.credited_return - expected_floor) < GOLDEN_RELATIVE_TOLERANCE
        assert floor_result.credited_return > buffer_result.credited_return, (
            "Floor should be better for large losses"
        )

    def test_fia_cap_example(self, sec_data: dict) -> None:
        """FIA with 10% cap."""
        example = sec_data["fia_cap_example"]
        params = example["parameters"]

        payoff = CappedCallPayoff(cap_rate=params["cap_rate"], floor_rate=params["floor_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"FIA cap: got {result.credited_return}, expected {expected}"
        )
        assert result.cap_applied == example["expected"]["cap_applied"]

    def test_fia_floor_example(self, sec_data: dict) -> None:
        """FIA principal protection (0% floor)."""
        example = sec_data["fia_floor_example"]
        params = example["parameters"]

        payoff = CappedCallPayoff(cap_rate=params["cap_rate"], floor_rate=params["floor_rate"])
        result = payoff.calculate(params["index_return"])

        expected = example["expected"]["credited_return"]
        assert abs(result.credited_return - expected) < GOLDEN_RELATIVE_TOLERANCE, (
            f"FIA floor: got {result.credited_return}, expected {expected}"
        )
        assert result.floor_applied == example["expected"]["floor_applied"]


# =============================================================================
# WINK Products Golden Tests
# =============================================================================


# Tolerance tiers for WINK products
WINK_MYGA_TOLERANCE = 0.01  # Tight for deterministic MYGA pricing
WINK_FIA_TOLERANCE = 0.05  # 5% relative for FIA (MC variance)
WINK_RILA_TOLERANCE = 0.05  # 5% relative for RILA (MC variance)


class TestWINKGoldenProducts:
    """
    Regression tests against WINK competitive rate products.

    Verifies that pricing outputs match known-correct values from
    the curated WINK product golden file.

    [T2] Products selected from current WINK data to exercise:
    - MYGA: Duration variety (3yr, 5yr, 7yr, 10yr) plus edge cases
    - FIA: Crediting method variety (cap, participation, spread)
    - RILA: Buffer levels (10%, 15%, 20%) plus floor products

    See: scripts/regenerate_goldens.py --wink
    """

    @pytest.fixture(scope="class")
    def wink_data(self) -> dict:
        """Load WINK golden file."""
        return load_golden("wink_products.json")

    # -------------------------------------------------------------------------
    # MYGA Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "product_key",
        [
            "myga_3yr_median",
            "myga_5yr_median",
            "myga_7yr_median",
            "myga_10yr_median",
            "myga_edge_high_rate",
        ],
    )
    def test_myga_present_value(self, wink_data: dict, product_key: str) -> None:
        """[T2] MYGA present value matches golden expectation."""
        if product_key not in wink_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = wink_data[product_key]
        params = product_data["parameters"]

        # Create MYGA product
        product = MYGAProduct(
            company_name=params["company_name"],
            product_name=params["product_name"],
            product_group="MYGA",
            status="current",
            fixed_rate=params["fixed_rate"],
            guarantee_duration=params["guarantee_duration"],
        )

        # Price with standard discount rate (5%)
        pricer = MYGAPricer()
        result = pricer.price(product, principal=params["premium"], discount_rate=0.05)

        expected_pv = product_data["expected"]["present_value"]
        relative_error = abs(result.present_value - expected_pv) / expected_pv

        assert relative_error < WINK_MYGA_TOLERANCE, (
            f"MYGA {product_key} PV mismatch: got {result.present_value:.2f}, "
            f"expected {expected_pv:.2f}, error = {relative_error:.4%}"
        )

    @pytest.mark.parametrize(
        "product_key",
        [
            "myga_3yr_median",
            "myga_5yr_median",
            "myga_7yr_median",
            "myga_10yr_median",
        ],
    )
    def test_myga_annualized_return(self, wink_data: dict, product_key: str) -> None:
        """[T2] MYGA annualized return matches fixed rate."""
        if product_key not in wink_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = wink_data[product_key]
        params = product_data["parameters"]
        expected_return = product_data["expected"]["annualized_return"]

        # Fixed rate should equal annualized return
        assert abs(params["fixed_rate"] - expected_return) < 1e-6, (
            f"MYGA {product_key} return mismatch: rate={params['fixed_rate']}, "
            f"expected={expected_return}"
        )

    # -------------------------------------------------------------------------
    # FIA Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "product_key",
        [
            "fia_cap_median",
            "fia_high_participation",
            "fia_with_spread",
            "fia_edge_low_cap",
        ],
    )
    def test_fia_option_value(self, wink_data: dict, product_key: str) -> None:
        """[T2] FIA embedded option value matches golden expectation."""
        if product_key not in wink_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = wink_data[product_key]
        params = product_data["parameters"]
        market = params.get("market_params", {})

        # Create FIA product
        product = FIAProduct(
            company_name=params["company_name"],
            product_name=params["product_name"],
            product_group="FIA",
            status="current",
            cap_rate=params.get("cap_rate"),
            participation_rate=params.get("participation_rate", 1.0),
            spread_rate=params.get("spread_rate", 0.0),
        )

        # Create market params
        market_params = FIAMarketParams(
            spot=100.0,
            risk_free_rate=market.get("rate", 0.05),
            dividend_yield=market.get("dividend", 0.02),
            volatility=market.get("volatility", 0.20),
        )

        # Price using 10k paths for reproducibility
        pricer = FIAPricer(market_params=market_params, n_mc_paths=10_000, seed=42)
        term_years = params.get("term_years", 1.0)
        result = pricer.price(product, term_years=term_years)

        expected_option_pct = product_data["expected"]["option_value_pct"]
        # Option value as percentage of spot
        actual_option_pct = (result.embedded_option_value / 100.0) * 100  # Already in %

        relative_error = abs(actual_option_pct - expected_option_pct) / expected_option_pct

        assert relative_error < WINK_FIA_TOLERANCE, (
            f"FIA {product_key} option value mismatch: got {actual_option_pct:.2f}%, "
            f"expected {expected_option_pct:.2f}%, error = {relative_error:.4%}"
        )

    # -------------------------------------------------------------------------
    # RILA Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "product_key",
        [
            "rila_buffer_10",
            "rila_buffer_15",
            "rila_buffer_20",
            "rila_floor_10",
            "rila_edge_deep_buffer",
            "rila_edge_shallow_buffer",
        ],
    )
    def test_rila_buffer_cost(self, wink_data: dict, product_key: str) -> None:
        """[T2] RILA buffer/floor cost matches golden expectation."""
        if product_key not in wink_data:
            pytest.skip(f"Product {product_key} not in golden file")

        product_data = wink_data[product_key]

        # Skip products marked as requiring special handling
        if "skip_reason" in product_data.get("expected", {}):
            pytest.skip(product_data["expected"]["skip_reason"])

        params = product_data["parameters"]
        market = params.get("market_params", {})

        # Create RILA product
        product = RILAProduct(
            company_name=params["company_name"],
            product_name=params["product_name"],
            product_group="RILA",
            status="current",
            buffer_rate=params["buffer_rate"],
            buffer_modifier=params["buffer_modifier"],
            cap_rate=params.get("cap_rate"),
        )

        # Create market params
        market_params = RILAMarketParams(
            spot=100.0,
            risk_free_rate=market.get("rate", 0.05),
            dividend_yield=market.get("dividend", 0.02),
            volatility=market.get("volatility", 0.20),
        )

        # Price using 10k paths for reproducibility
        pricer = RILAPricer(market_params=market_params, n_mc_paths=10_000, seed=42)
        term_years = params.get("term_years", 1.0)
        result = pricer.price(product, term_years=term_years)

        # Get expected value (buffer_cost_pct or floor_cost_pct)
        if "buffer_cost_pct" in product_data["expected"]:
            expected_cost_pct = product_data["expected"]["buffer_cost_pct"]
        elif "floor_cost_pct" in product_data["expected"]:
            expected_cost_pct = product_data["expected"]["floor_cost_pct"]
        else:
            pytest.skip(f"No expected cost in golden for {product_key}")

        # Protection value as percentage
        actual_cost_pct = result.protection_value

        # Use absolute tolerance for small values
        if expected_cost_pct < 1.0:
            # For very small values, use absolute tolerance
            assert abs(actual_cost_pct - expected_cost_pct) < 0.5, (
                f"RILA {product_key} cost mismatch: got {actual_cost_pct:.2f}%, "
                f"expected {expected_cost_pct:.2f}%"
            )
        else:
            relative_error = abs(actual_cost_pct - expected_cost_pct) / expected_cost_pct
            assert relative_error < WINK_RILA_TOLERANCE, (
                f"RILA {product_key} cost mismatch: got {actual_cost_pct:.2f}%, "
                f"expected {expected_cost_pct:.2f}%, error = {relative_error:.4%}"
            )
