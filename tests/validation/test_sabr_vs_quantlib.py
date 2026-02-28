"""
SABR model validation against QuantLib.

Validates the SABR implied volatility implementation by comparing
against QuantLib's sabrVolatility function.

[T1] Both implementations use Hagan et al. (2002) approximation.
Since this is analytical (not Monte Carlo), error tolerance should be <1%.

References
----------
[T1] Hagan, P. S., Kumar, D., Lesniewski, A. S., & Woodward, D. E. (2002).
     Managing smile risk. Wilmott magazine, 1(September), 84-108.
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


def quantlib_sabr_implied_vol(
    forward: float,
    strike: float,
    time: float,
    alpha: float,
    beta: float,
    rho: float,
    nu: float,
) -> float:
    """
    Calculate SABR implied volatility using QuantLib.

    [T1] This is the reference implementation using Hagan (2002) approximation.

    Parameters
    ----------
    forward : float
        Forward price
    strike : float
        Strike price
    time : float
        Time to expiry in years
    alpha, beta, rho, nu : float
        SABR model parameters

    Returns
    -------
    float
        Black-Scholes implied volatility (decimal)
    """
    # QuantLib sabrVolatility(strike, forward, T, alpha, beta, nu, rho)
    # Note: QuantLib uses (nu, rho) order while we use (rho, nu)
    return ql.sabrVolatility(strike, forward, time, alpha, beta, nu, rho)


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not installed")
class TestSABRvsQuantLib:
    """
    Validate SABR implementation against QuantLib.

    [T1] Both use Hagan approximation (analytical).
    Tolerance: 1% (analytical formula, no MC noise).
    """

    # Standard test parameters
    FORWARD = 100.0
    TIME = 1.0

    # SABR parameters
    ALPHA = 0.2  # ~20% ATM vol
    BETA = 0.5  # Square-root backbone (typical for rates)
    RHO = -0.3  # Negative correlation (typical for equities)
    NU = 0.4  # Vol of vol

    # Analytical tolerance (should be very tight)
    TOLERANCE = 0.01  # 1%

    def test_atm(self):
        """ATM implied volatility validation."""
        strike = self.FORWARD

        # QuantLib reference
        ql_vol = quantlib_sabr_implied_vol(
            self.FORWARD, strike, self.TIME, self.ALPHA, self.BETA, self.RHO, self.NU
        )

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(
            alpha=self.ALPHA,
            beta=self.BETA,
            rho=self.RHO,
            nu=self.NU,
        )

        our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)

        rel_error = abs(our_vol - ql_vol) / ql_vol

        assert rel_error < self.TOLERANCE, (
            f"ATM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%"
        )

        print(f"ATM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

    def test_itm(self):
        """ITM implied volatility validation (K < F)."""
        strike = 90.0

        ql_vol = quantlib_sabr_implied_vol(
            self.FORWARD, strike, self.TIME, self.ALPHA, self.BETA, self.RHO, self.NU
        )

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=self.ALPHA, beta=self.BETA, rho=self.RHO, nu=self.NU)

        our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)

        rel_error = abs(our_vol - ql_vol) / ql_vol

        assert rel_error < self.TOLERANCE, (
            f"ITM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%"
        )

        print(f"ITM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

    def test_otm(self):
        """OTM implied volatility validation (K > F)."""
        strike = 110.0

        ql_vol = quantlib_sabr_implied_vol(
            self.FORWARD, strike, self.TIME, self.ALPHA, self.BETA, self.RHO, self.NU
        )

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=self.ALPHA, beta=self.BETA, rho=self.RHO, nu=self.NU)

        our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)

        rel_error = abs(our_vol - ql_vol) / ql_vol

        assert rel_error < self.TOLERANCE, (
            f"OTM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%"
        )

        print(f"OTM: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

    def test_multiple_strikes(self):
        """
        Validate across volatility smile.

        Tests strike range to capture smile/skew shape.
        """
        strikes = [70, 80, 90, 95, 100, 105, 110, 120, 130]

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=self.ALPHA, beta=self.BETA, rho=self.RHO, nu=self.NU)

        results = []
        for strike in strikes:
            ql_vol = quantlib_sabr_implied_vol(
                self.FORWARD, strike, self.TIME, self.ALPHA, self.BETA, self.RHO, self.NU
            )

            our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)

            rel_error = abs(our_vol - ql_vol) / ql_vol
            results.append((strike, our_vol, ql_vol, rel_error))

        # Print summary
        print("\nSABR Smile Validation:")
        print("-" * 70)
        print(f"{'Strike':>8} {'Our Vol':>12} {'QL Vol':>12} {'Error %':>10} {'Delta':>8}")
        print("-" * 70)
        for strike, our, ql, err in results:
            status = "✓" if err < self.TOLERANCE else "✗"
            # Approximate delta (rough)
            delta = 0.5 if strike == self.FORWARD else (0.8 if strike < self.FORWARD else 0.2)
            print(f"{strike:>8} {our:>12.6f} {ql:>12.6f} {err * 100:>9.4f}% {status}")

        # All should pass
        max_error = max(r[3] for r in results)
        assert max_error < self.TOLERANCE, (
            f"Max error {max_error * 100:.4f}% exceeds tolerance {self.TOLERANCE * 100}%"
        )

    def test_beta_lognormal(self):
        """
        Test with β=1 (lognormal backbone).

        [T1] β=1 is the Black-Scholes limit with stochastic vol.
        """
        beta = 1.0
        alpha = 0.2  # ~20% ATM vol
        rho = -0.3
        nu = 0.4

        strikes = [90, 100, 110]

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=alpha, beta=beta, rho=rho, nu=nu)

        print("\nβ=1 (Lognormal) Test:")
        print("-" * 60)
        for strike in strikes:
            ql_vol = quantlib_sabr_implied_vol(
                self.FORWARD, strike, self.TIME, alpha, beta, rho, nu
            )
            our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)
            rel_error = abs(our_vol - ql_vol) / ql_vol
            print(f"K={strike}: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

            assert rel_error < self.TOLERANCE, f"β=1, K={strike} failed"

    def test_beta_normal(self):
        """
        Test with β=0 (normal backbone).

        [T1] β=0 is the normal (Bachelier) model limit.
        Uses shifted SABR behavior.
        """
        beta = 0.0
        # For β=0, alpha has units of absolute vol (not relative)
        # Typical alpha ~ F * 0.01 for ~1% normal vol
        alpha = self.FORWARD * 0.002  # ~0.2% normal vol
        rho = -0.3
        nu = 0.3

        strikes = [95, 100, 105]

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=alpha, beta=beta, rho=rho, nu=nu)

        print("\nβ=0 (Normal) Test:")
        print("-" * 60)
        for strike in strikes:
            ql_vol = quantlib_sabr_implied_vol(
                self.FORWARD, strike, self.TIME, alpha, beta, rho, nu
            )
            our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)

            # For very small vols, use absolute tolerance
            if ql_vol < 0.01:
                error = abs(our_vol - ql_vol)
                passed = error < 0.001
            else:
                rel_error = abs(our_vol - ql_vol) / ql_vol
                passed = rel_error < self.TOLERANCE
                error = rel_error * 100

            print(f"K={strike}: our={our_vol:.6f}, QL={ql_vol:.6f}, error={error:.4f}%")
            assert passed, f"β=0, K={strike} failed"

    def test_short_expiry(self):
        """
        Test with short time to expiry.

        [T1] Hagan approximation is most accurate for short expiries.
        """
        time = 0.1  # ~1 month

        strikes = [95, 100, 105]

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=self.ALPHA, beta=self.BETA, rho=self.RHO, nu=self.NU)

        print("\nShort Expiry (T=0.1) Test:")
        print("-" * 60)
        for strike in strikes:
            ql_vol = quantlib_sabr_implied_vol(
                self.FORWARD, strike, time, self.ALPHA, self.BETA, self.RHO, self.NU
            )
            our_vol = sabr_implied_volatility(self.FORWARD, strike, time, params)
            rel_error = abs(our_vol - ql_vol) / ql_vol
            print(f"K={strike}: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

            assert rel_error < self.TOLERANCE, f"T=0.1, K={strike} failed"

    def test_high_vol_of_vol(self):
        """
        Test with high volatility of volatility.

        [T1] High ν tests robustness of approximation.
        """
        nu = 0.8  # High vol of vol

        strikes = [90, 100, 110]

        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_implied_volatility,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=self.ALPHA, beta=self.BETA, rho=self.RHO, nu=nu)

        print("\nHigh Vol-of-Vol (ν=0.8) Test:")
        print("-" * 60)
        for strike in strikes:
            ql_vol = quantlib_sabr_implied_vol(
                self.FORWARD, strike, self.TIME, self.ALPHA, self.BETA, self.RHO, nu
            )
            our_vol = sabr_implied_volatility(self.FORWARD, strike, self.TIME, params)
            rel_error = abs(our_vol - ql_vol) / ql_vol
            print(f"K={strike}: our={our_vol:.6f}, QL={ql_vol:.6f}, error={rel_error * 100:.4f}%")

            # Slightly higher tolerance for extreme parameters
            assert rel_error < self.TOLERANCE * 1.5, f"High ν, K={strike} failed"


@pytest.mark.skipif(not QUANTLIB_AVAILABLE, reason="QuantLib not installed")
class TestSABRPricing:
    """
    Test SABR option pricing (not just implied vol).

    Verifies that SABR vol → BS price gives sensible results.
    """

    FORWARD = 100.0
    TIME = 1.0
    RATE = 0.05

    def test_sabr_call_price(self):
        """Test SABR call pricing workflow."""
        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_price_call,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=0.2, beta=0.5, rho=-0.3, nu=0.4)

        # Spot (back out from forward)
        spot = self.FORWARD * np.exp(-self.RATE * self.TIME)

        strike = self.FORWARD
        price = sabr_price_call(spot, strike, self.RATE, 0.0, self.TIME, params)

        # Sanity checks
        assert price > 0, "Call price should be positive"
        assert price < spot, "Call price should be less than spot"

        print(f"\nSABR Call Price (ATM): {price:.4f}")

    def test_sabr_put_call_parity(self):
        """Verify put-call parity with SABR prices."""
        try:
            from annuity_pricing.options.pricing.sabr import (
                SABRParams,
                sabr_price_call,
                sabr_price_put,
            )
        except ImportError:
            pytest.skip("SABR module not available")

        params = SABRParams(alpha=0.2, beta=0.5, rho=-0.3, nu=0.4)

        spot = self.FORWARD * np.exp(-self.RATE * self.TIME)
        strike = self.FORWARD

        call = sabr_price_call(spot, strike, self.RATE, 0.0, self.TIME, params)
        put = sabr_price_put(spot, strike, self.RATE, 0.0, self.TIME, params)

        # Put-call parity [T1]
        # C - P = S - K*exp(-r*T)
        lhs = call - put
        rhs = spot - strike * np.exp(-self.RATE * self.TIME)

        diff = abs(lhs - rhs)
        assert diff < 0.01, f"Put-call parity violated: diff={diff:.6f}"

        print(f"Put-call parity: C-P={lhs:.4f}, S-K*DF={rhs:.4f}, diff={diff:.6f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
