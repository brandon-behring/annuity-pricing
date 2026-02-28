"""
Heston model validation against QuantLib.

Validates the Heston MC implementation by comparing pricing against
QuantLib's AnalyticHestonEngine (semi-analytical Fourier inversion).

[T1] QuantLib's AnalyticHestonEngine is highly accurate (closed-form).
Monte Carlo should converge to within 5% with 50k paths.

References
----------
[T1] Heston, S. L. (1993). A closed-form solution for options with stochastic
     volatility. Review of Financial Studies, 6(2), 327-343.
[T1] QuantLib documentation: https://quantlib-python-docs.readthedocs.io/
"""

import numpy as np
import pytest

# Check if QuantLib is available
try:
    import QuantLib as ql

    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False


def quantlib_heston_price(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time: float,
    v0: float,
    kappa: float,
    theta: float,
    sigma: float,
    rho: float,
    option_type: str = "call",
) -> float:
    """
    Price European option using QuantLib's AnalyticHestonEngine.

    [T1] This is the reference implementation for validation.
    Uses Fourier transform method with high accuracy.

    Parameters
    ----------
    spot, strike, rate, dividend, time : float
        Standard option parameters
    v0, kappa, theta, sigma, rho : float
        Heston model parameters
    option_type : str
        "call" or "put"

    Returns
    -------
    float
        Option price from QuantLib
    """
    # Set up QuantLib date framework
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today

    # Day count and calendar
    day_count = ql.Actual365Fixed()
    calendar = ql.NullCalendar()

    # Maturity date
    maturity = today + ql.Period(int(time * 365), ql.Days)

    # Spot price handle
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))

    # Risk-free rate term structure
    rate_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, rate, day_count))

    # Dividend yield term structure
    dividend_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, dividend, day_count))

    # Heston process
    heston_process = ql.HestonProcess(
        rate_ts,
        dividend_ts,
        spot_handle,
        v0,
        kappa,
        theta,
        sigma,
        rho,
    )

    # Heston model
    heston_model = ql.HestonModel(heston_process)

    # Analytic engine (Fourier inversion - highly accurate)
    engine = ql.AnalyticHestonEngine(heston_model)

    # Option setup
    if option_type.lower() == "call":
        payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
    else:
        payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike)

    exercise = ql.EuropeanExercise(maturity)
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(engine)

    return option.NPV()


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not installed")
class TestHestonMCvsQuantLib:
    """
    Validate Heston MC implementation against QuantLib.

    [T1] QuantLib's AnalyticHestonEngine is the reference.
    MC should converge to within 5% (Monte Carlo noise).
    """

    # Standard test parameters (satisfies Feller condition)
    SPOT = 100.0
    RATE = 0.05
    DIVIDEND = 0.02
    TIME = 1.0

    # Heston parameters (Feller: 2*2*0.04 = 0.16 >= 0.09 = 0.3^2 ✓)
    V0 = 0.04
    KAPPA = 2.0
    THETA = 0.04
    SIGMA = 0.3
    RHO = -0.7

    # MC parameters
    MC_PATHS = 50000
    MC_STEPS = 252
    MC_SEED = 42

    # Tolerance for MC vs analytical
    TOLERANCE = 0.05  # 5%

    def test_call_atm(self):
        """ATM call option validation."""
        strike = self.SPOT

        # QuantLib reference price
        ql_price = quantlib_heston_price(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            self.V0,
            self.KAPPA,
            self.THETA,
            self.SIGMA,
            self.RHO,
            option_type="call",
        )

        # Skip if compact repo not available
        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0,
            kappa=self.KAPPA,
            theta=self.THETA,
            sigma=self.SIGMA,
            rho=self.RHO,
        )

        mc_price = heston_price_call_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        rel_error = abs(mc_price - ql_price) / ql_price

        assert rel_error < self.TOLERANCE, (
            f"ATM call: MC={mc_price:.4f}, QL={ql_price:.4f}, "
            f"error={rel_error * 100:.2f}% (tolerance={self.TOLERANCE * 100}%)"
        )

        print(f"ATM Call: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%")

    def test_call_itm(self):
        """ITM call option validation (K < S)."""
        strike = 90.0

        ql_price = quantlib_heston_price(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            self.V0,
            self.KAPPA,
            self.THETA,
            self.SIGMA,
            self.RHO,
            option_type="call",
        )

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        mc_price = heston_price_call_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        rel_error = abs(mc_price - ql_price) / ql_price

        assert rel_error < self.TOLERANCE, (
            f"ITM call: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%"
        )

        print(f"ITM Call: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%")

    def test_call_otm(self):
        """OTM call option validation (K > S)."""
        strike = 110.0

        ql_price = quantlib_heston_price(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            self.V0,
            self.KAPPA,
            self.THETA,
            self.SIGMA,
            self.RHO,
            option_type="call",
        )

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        mc_price = heston_price_call_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        rel_error = abs(mc_price - ql_price) / ql_price

        assert rel_error < self.TOLERANCE, (
            f"OTM call: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%"
        )

        print(f"OTM Call: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%")

    def test_put_atm(self):
        """ATM put option validation."""
        strike = self.SPOT

        ql_price = quantlib_heston_price(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            self.V0,
            self.KAPPA,
            self.THETA,
            self.SIGMA,
            self.RHO,
            option_type="put",
        )

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_put_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        mc_price = heston_price_put_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        rel_error = abs(mc_price - ql_price) / ql_price

        assert rel_error < self.TOLERANCE, (
            f"ATM put: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%"
        )

        print(f"ATM Put: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%")

    def test_put_call_parity(self):
        """
        Verify put-call parity holds for Heston MC.

        [T1] C - P = S*exp(-q*T) - K*exp(-r*T)
        """
        strike = self.SPOT

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
                heston_price_put_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        # Use same seed for both to reduce MC noise
        call_price = heston_price_call_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )
        put_price = heston_price_put_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        # Put-call parity [T1]
        forward = self.SPOT * np.exp((self.RATE - self.DIVIDEND) * self.TIME)
        discount = np.exp(-self.RATE * self.TIME)
        parity_diff = call_price - put_price - (forward - strike) * discount

        # Parity should hold within MC noise (~1-2% of price)
        max_error = 0.02 * max(call_price, put_price)

        assert abs(parity_diff) < max_error, (
            f"Put-call parity violated: C-P={call_price - put_price:.4f}, "
            f"(F-K)*DF={(forward - strike) * discount:.4f}, "
            f"diff={parity_diff:.4f}"
        )

        print(f"Put-call parity: diff={parity_diff:.4f} (max allowed={max_error:.4f})")

    def test_multiple_strikes(self):
        """
        Validate across multiple strikes.

        Tests strike range from 80 to 120 (deep ITM to deep OTM).
        """
        strikes = [80, 90, 95, 100, 105, 110, 120]

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        results = []
        for strike in strikes:
            ql_price = quantlib_heston_price(
                self.SPOT,
                strike,
                self.RATE,
                self.DIVIDEND,
                self.TIME,
                self.V0,
                self.KAPPA,
                self.THETA,
                self.SIGMA,
                self.RHO,
                option_type="call",
            )

            mc_price = heston_price_call_mc(
                self.SPOT,
                strike,
                self.RATE,
                self.DIVIDEND,
                self.TIME,
                params,
                paths=self.MC_PATHS,
                steps=self.MC_STEPS,
                seed=self.MC_SEED,
            )

            rel_error = abs(mc_price - ql_price) / ql_price if ql_price > 0.01 else 0
            results.append((strike, mc_price, ql_price, rel_error))

        # Print summary
        print("\nStrike Validation Summary:")
        print("-" * 60)
        print(f"{'Strike':>8} {'MC Price':>12} {'QL Price':>12} {'Error %':>10}")
        print("-" * 60)
        for strike, mc, ql, err in results:
            status = "✓" if err < self.TOLERANCE else "✗"
            print(f"{strike:>8} {mc:>12.4f} {ql:>12.4f} {err * 100:>9.2f}% {status}")

        # All should pass
        max_error = max(r[3] for r in results)
        assert max_error < self.TOLERANCE, (
            f"Max error {max_error * 100:.2f}% exceeds tolerance {self.TOLERANCE * 100}%"
        )

    def test_high_vol_of_vol(self):
        """
        Test with high volatility of volatility (more challenging).

        [T1] High sigma tests robustness of variance discretization.
        """
        # Higher sigma, but still satisfies Feller: 2*3*0.09 = 0.54 >= 0.36 = 0.6^2 ✓
        v0 = 0.09
        kappa = 3.0
        theta = 0.09
        sigma = 0.6
        rho = -0.8

        strike = self.SPOT

        ql_price = quantlib_heston_price(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            v0,
            kappa,
            theta,
            sigma,
            rho,
            option_type="call",
        )

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call_mc,
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(v0=v0, kappa=kappa, theta=theta, sigma=sigma, rho=rho)

        mc_price = heston_price_call_mc(
            self.SPOT,
            strike,
            self.RATE,
            self.DIVIDEND,
            self.TIME,
            params,
            paths=self.MC_PATHS,
            steps=self.MC_STEPS,
            seed=self.MC_SEED,
        )

        rel_error = abs(mc_price - ql_price) / ql_price

        # Slightly higher tolerance for high vol-of-vol
        assert rel_error < self.TOLERANCE * 1.5, (
            f"High vov: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%"
        )

        print(f"High VoV: MC={mc_price:.4f}, QL={ql_price:.4f}, error={rel_error * 100:.2f}%")


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not installed")
class TestHestonFFTvsQuantLib:
    """
    Test Heston FFT implementation against QuantLib.

    Note: FFT is documented to have 20-50% bias. This test documents
    the actual bias level for future debugging.
    """

    SPOT = 100.0
    RATE = 0.05
    DIVIDEND = 0.02
    TIME = 1.0

    V0 = 0.04
    KAPPA = 2.0
    THETA = 0.04
    SIGMA = 0.3
    RHO = -0.7

    def test_fft_bias_documentation(self):
        """
        Document FFT bias level (not a pass/fail test).

        This test records the FFT vs QuantLib difference for reference.
        FFT is known to be biased; this tracks the magnitude.
        """
        strikes = [90, 100, 110]

        try:
            from annuity_pricing.options.pricing.heston import (
                HestonParams,
                heston_price_call,  # FFT version
            )
        except ImportError:
            pytest.skip("Heston module not available")

        params = HestonParams(
            v0=self.V0, kappa=self.KAPPA, theta=self.THETA, sigma=self.SIGMA, rho=self.RHO
        )

        print("\nFFT Bias Documentation:")
        print("-" * 60)
        print(f"{'Strike':>8} {'FFT Price':>12} {'QL Price':>12} {'Bias %':>10}")
        print("-" * 60)

        biases = []
        for strike in strikes:
            ql_price = quantlib_heston_price(
                self.SPOT,
                strike,
                self.RATE,
                self.DIVIDEND,
                self.TIME,
                self.V0,
                self.KAPPA,
                self.THETA,
                self.SIGMA,
                self.RHO,
                option_type="call",
            )

            fft_price = heston_price_call(
                self.SPOT, strike, self.RATE, self.DIVIDEND, self.TIME, params
            )

            bias = (fft_price - ql_price) / ql_price * 100
            biases.append(bias)
            print(f"{strike:>8} {fft_price:>12.4f} {ql_price:>12.4f} {bias:>+9.1f}%")

        avg_bias = np.mean(biases)
        print(f"\nAverage FFT bias: {avg_bias:+.1f}%")
        print("Note: FFT bias is documented in code. Use MC for production.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
