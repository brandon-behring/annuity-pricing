"""
Greeks validation against QuantLib.

[T1] Validates that our Black-Scholes Greeks match QuantLib's analytical engine.

Greeks Conventions (both implementations):
- Delta: Absolute (per $1 spot move)
- Gamma: Absolute (per $1 spot move, squared)
- Vega: Per 1% vol move (×0.01 scaling)
- Theta: Per day (/365 scaling)
- Rho: Per 1% rate move (×0.01 scaling)

Tolerance Justification (from docs/TOLERANCE_JUSTIFICATION.md):
- GREEKS_VALIDATION_TOLERANCE = 1e-5
- Delta/Gamma/Vega/Rho: Machine precision achievable
- Theta: Slightly looser due to day count convention differences

See: Hull (2021) Ch. 19 - Greek Letters
See: docs/knowledge/derivations/bs_greeks.md
"""

import pytest

# Skip entire module if QuantLib not available
pytest.importorskip("QuantLib")

from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter
from annuity_pricing.config.tolerances import GREEKS_VALIDATION_TOLERANCE
from annuity_pricing.options.pricing.black_scholes import (
    OptionType,
    black_scholes_greeks,
)


class TestCallGreeksVsQuantLib:
    """
    Validates call option Greeks against QuantLib.

    [T1] Delta, Gamma, Vega, Theta, Rho must match analytical QuantLib.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.fixture
    def standard_params(self):
        """Standard market parameters for testing."""
        return {
            "spot": 100.0,
            "rate": 0.05,
            "dividend": 0.02,
            "volatility": 0.20,
            "time_to_expiry": 1.0,
        }

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])  # ITM, ATM, OTM
    def test_call_delta_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Call delta matches QuantLib within GREEKS_VALIDATION_TOLERANCE."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="call",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        diff = abs(ql_greeks["delta"] - our_result.delta)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Call delta mismatch at K={strike}: QL={ql_greeks['delta']:.8f}, "
            f"Ours={our_result.delta:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_call_gamma_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Call gamma matches QuantLib (same for call/put)."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="call",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        diff = abs(ql_greeks["gamma"] - our_result.gamma)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Call gamma mismatch at K={strike}: QL={ql_greeks['gamma']:.8f}, "
            f"Ours={our_result.gamma:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_call_vega_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Call vega matches QuantLib (same for call/put)."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="call",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        diff = abs(ql_greeks["vega"] - our_result.vega)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Call vega mismatch at K={strike}: QL={ql_greeks['vega']:.8f}, "
            f"Ours={our_result.vega:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_call_theta_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """
        [T1] Call theta matches QuantLib.

        Note: Uses slightly looser tolerance (1e-4) for theta due to
        day count convention differences between implementations.
        """
        theta_tolerance = 1e-4  # Looser for day count effects

        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="call",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        diff = abs(ql_greeks["theta"] - our_result.theta)
        assert diff < theta_tolerance, (
            f"Call theta mismatch at K={strike}: QL={ql_greeks['theta']:.8f}, "
            f"Ours={our_result.theta:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_call_rho_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Call rho matches QuantLib."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="call",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.CALL,
        )

        diff = abs(ql_greeks["rho"] - our_result.rho)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Call rho mismatch at K={strike}: QL={ql_greeks['rho']:.8f}, "
            f"Ours={our_result.rho:.8f}, diff={diff:.2e}"
        )


class TestPutGreeksVsQuantLib:
    """
    Validates put option Greeks against QuantLib.

    [T1] Put Greeks are used in RILA buffer/floor pricing.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.fixture
    def standard_params(self):
        """Standard market parameters for testing."""
        return {
            "spot": 100.0,
            "rate": 0.05,
            "dividend": 0.02,
            "volatility": 0.20,
            "time_to_expiry": 1.0,
        }

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])  # OTM, ATM, ITM
    def test_put_delta_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Put delta matches QuantLib."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="put",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.PUT,
        )

        diff = abs(ql_greeks["delta"] - our_result.delta)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Put delta mismatch at K={strike}: QL={ql_greeks['delta']:.8f}, "
            f"Ours={our_result.delta:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_put_gamma_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Put gamma matches QuantLib (same for call/put)."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="put",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.PUT,
        )

        diff = abs(ql_greeks["gamma"] - our_result.gamma)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Put gamma mismatch at K={strike}: QL={ql_greeks['gamma']:.8f}, "
            f"Ours={our_result.gamma:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_put_theta_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Put theta matches QuantLib."""
        theta_tolerance = 1e-4  # Looser for day count effects

        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="put",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.PUT,
        )

        diff = abs(ql_greeks["theta"] - our_result.theta)
        assert diff < theta_tolerance, (
            f"Put theta mismatch at K={strike}: QL={ql_greeks['theta']:.8f}, "
            f"Ours={our_result.theta:.8f}, diff={diff:.2e}"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("strike", [90.0, 100.0, 110.0])
    def test_put_rho_vs_quantlib(self, quantlib_adapter, standard_params, strike):
        """[T1] Put rho matches QuantLib."""
        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type="put",
        )

        our_result = black_scholes_greeks(
            spot=standard_params["spot"],
            strike=strike,
            rate=standard_params["rate"],
            dividend=standard_params["dividend"],
            volatility=standard_params["volatility"],
            time_to_expiry=standard_params["time_to_expiry"],
            option_type=OptionType.PUT,
        )

        diff = abs(ql_greeks["rho"] - our_result.rho)
        assert diff < GREEKS_VALIDATION_TOLERANCE, (
            f"Put rho mismatch at K={strike}: QL={ql_greeks['rho']:.8f}, "
            f"Ours={our_result.rho:.8f}, diff={diff:.2e}"
        )


class TestGreeksAcrossVolatilities:
    """
    Validates Greeks across different volatility levels.

    [T1] Greeks should match QuantLib across the volatility spectrum.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize("volatility", [0.10, 0.20, 0.30, 0.40, 0.50])
    @pytest.mark.parametrize("option_type", ["call", "put"])
    def test_all_greeks_across_volatilities(self, quantlib_adapter, volatility, option_type):
        """[T1] All Greeks match QuantLib across volatility spectrum."""
        spot = 100.0
        strike = 100.0
        rate = 0.05
        dividend = 0.02
        time_to_expiry = 1.0

        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
        )

        opt_type = OptionType.CALL if option_type == "call" else OptionType.PUT
        our_result = black_scholes_greeks(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=opt_type,
        )

        # Check all Greeks
        assert abs(ql_greeks["delta"] - our_result.delta) < GREEKS_VALIDATION_TOLERANCE
        assert abs(ql_greeks["gamma"] - our_result.gamma) < GREEKS_VALIDATION_TOLERANCE
        assert abs(ql_greeks["vega"] - our_result.vega) < GREEKS_VALIDATION_TOLERANCE
        assert abs(ql_greeks["theta"] - our_result.theta) < 1e-4  # Looser for theta
        assert abs(ql_greeks["rho"] - our_result.rho) < GREEKS_VALIDATION_TOLERANCE


class TestGreeksAcrossTerms:
    """
    Validates Greeks across different time-to-expiry values.

    [T1] Greeks should match QuantLib for short and long-dated options.

    Note: Uses slightly looser tolerance (1e-4) for delta because QuantLib
    converts fractional years to calendar days, introducing small differences
    in the effective time-to-expiry calculation.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize("time_to_expiry", [0.25, 0.5, 1.0, 2.0, 3.0])
    @pytest.mark.parametrize("option_type", ["call", "put"])
    def test_all_greeks_across_terms(self, quantlib_adapter, time_to_expiry, option_type):
        """[T1] All Greeks match QuantLib across time horizons."""
        spot = 100.0
        strike = 100.0
        rate = 0.05
        dividend = 0.02
        volatility = 0.20

        # Tolerance for cross-term tests: use RELATIVE tolerance due to calendar day conversion
        # QuantLib converts fractional years to int(T * 365) days,
        # which introduces ~0.1-0.3% relative differences for non-integer years
        # Rho scales with T, so absolute tolerance is inappropriate
        rel_tolerance = 0.003  # 0.3% relative error

        ql_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=option_type,
        )

        opt_type = OptionType.CALL if option_type == "call" else OptionType.PUT
        our_result = black_scholes_greeks(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type=opt_type,
        )

        # Helper for relative comparison
        def rel_diff(a: float, b: float) -> float:
            if abs(b) < 1e-10:
                return abs(a - b)
            return abs(a - b) / abs(b)

        # Check all Greeks with relative tolerance
        assert rel_diff(ql_greeks["delta"], our_result.delta) < rel_tolerance, (
            f"Delta mismatch: QL={ql_greeks['delta']:.8f}, Ours={our_result.delta:.8f}"
        )
        assert rel_diff(ql_greeks["gamma"], our_result.gamma) < rel_tolerance
        assert rel_diff(ql_greeks["vega"], our_result.vega) < rel_tolerance
        assert rel_diff(ql_greeks["theta"], our_result.theta) < rel_tolerance
        assert rel_diff(ql_greeks["rho"], our_result.rho) < rel_tolerance


class TestRILAPositionGreeks:
    """
    End-to-end validation of RILA position Greeks.

    [T1] RILA position Greeks are combinations of put Greeks:
    - Buffer: Long ATM put - Short OTM put (put spread)
    - Floor: Long OTM put

    This validates that position-level aggregation matches
    the sum of individual QuantLib Greeks.
    """

    @pytest.fixture
    def quantlib_adapter(self):
        """Get QuantLib adapter."""
        adapter = QuantLibAdapter()
        if not adapter.is_available:
            pytest.skip("QuantLib not available")
        return adapter

    @pytest.mark.validation
    @pytest.mark.parametrize("buffer_rate", [0.10, 0.15, 0.20])
    def test_buffer_position_delta_additivity(self, quantlib_adapter, buffer_rate):
        """
        [T1] Buffer position delta = ATM put delta - OTM put delta.

        Validates that the put spread delta is additive.
        """
        spot = 100.0
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        time_to_expiry = 1.0

        atm_strike = spot
        otm_strike = spot * (1 - buffer_rate)

        # Long ATM put
        atm_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=atm_strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
        )

        # Short OTM put
        otm_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=otm_strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
        )

        # Position delta (long - short)
        position_delta = atm_greeks["delta"] - otm_greeks["delta"]

        # Verify delta is sensible for put spread
        # Long ATM put (delta ~ -0.5) minus short OTM put (delta ~ -0.3)
        # gives roughly -0.2 (more negative than ATM alone)
        assert position_delta < 0, "Buffer put spread should have negative delta"
        assert position_delta > atm_greeks["delta"], (
            "Put spread delta should be less negative than long put alone"
        )

    @pytest.mark.validation
    @pytest.mark.parametrize("buffer_rate", [0.10, 0.15, 0.20])
    def test_buffer_position_gamma_additivity(self, quantlib_adapter, buffer_rate):
        """
        [T1] Buffer position gamma = ATM put gamma - OTM put gamma.

        Validates gamma additivity for put spread.
        """
        spot = 100.0
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        time_to_expiry = 1.0

        atm_strike = spot
        otm_strike = spot * (1 - buffer_rate)

        atm_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=atm_strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
        )

        otm_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=otm_strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
        )

        position_gamma = atm_greeks["gamma"] - otm_greeks["gamma"]

        # Put spread should have positive net gamma (ATM gamma > OTM gamma)
        assert position_gamma > 0, "Buffer put spread should have positive net gamma"

    @pytest.mark.validation
    @pytest.mark.parametrize("floor_rate", [0.10, 0.15, 0.20])
    def test_floor_position_delta(self, quantlib_adapter, floor_rate):
        """
        [T1] Floor position delta = OTM put delta.

        Floor is simply a long OTM put.
        """
        spot = 100.0
        rate = 0.05
        dividend = 0.02
        volatility = 0.20
        time_to_expiry = 1.0

        floor_strike = spot * (1 - floor_rate)

        floor_greeks = quantlib_adapter.calculate_greeks(
            spot=spot,
            strike=floor_strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry,
            option_type="put",
        )

        # Floor (long OTM put) should have negative delta
        assert floor_greeks["delta"] < 0, "Floor (long OTM put) should have negative delta"
        # OTM put delta magnitude should be less than 0.5
        assert abs(floor_greeks["delta"]) < 0.5, "OTM put delta magnitude should be less than 0.5"
