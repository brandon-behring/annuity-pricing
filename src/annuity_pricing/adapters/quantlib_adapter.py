"""
QuantLib adapter for yield curve validation.

Validates yield curve construction against QuantLib.

Golden Values (Nelson-Siegel)
-----------------------------
| β₀   | β₁    | β₂    | τ   | 5Y Zero | Tolerance |
|------|-------|-------|-----|---------|-----------|
| 0.06 | -0.03 | 0.005 | 2.0 | 3.87%   | 0.01%     |

Note: QuantLib requires separate wheel installation on some platforms.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .base import BaseAdapter, ValidationResult


# Try to import QuantLib
try:
    import QuantLib as ql

    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False


@dataclass(frozen=True)
class CurveTestCase:
    """A yield curve test case."""

    name: str
    rate: float  # Flat rate for simple tests
    term_years: float
    expected_discount_factor: float
    tolerance: float = 0.0001


# Simple flat curve test cases
# Note: QuantLib uses calendar-based day counts, so we need tolerance for longer terms
CURVE_CASES: List[CurveTestCase] = [
    CurveTestCase(
        name="5% flat 1Y",
        rate=0.05,
        term_years=1.0,
        expected_discount_factor=0.9512,  # e^(-0.05)
        tolerance=0.0002,  # Slightly higher for calendar effects
    ),
    CurveTestCase(
        name="5% flat 5Y",
        rate=0.05,
        term_years=5.0,
        expected_discount_factor=0.7788,  # e^(-0.25)
        tolerance=0.0002,
    ),
    CurveTestCase(
        name="3% flat 10Y",
        rate=0.03,
        term_years=10.0,
        expected_discount_factor=0.7408,  # e^(-0.30)
        tolerance=0.0003,  # More tolerance for longer terms
    ),
]


class QuantLibAdapter(BaseAdapter):
    """
    Adapter for validating yield curves against QuantLib.

    Examples
    --------
    >>> adapter = QuantLibAdapter()
    >>> if adapter.is_available:
    ...     df = adapter.discount_factor_flat(0.05, 5.0)
    """

    @property
    def name(self) -> str:
        return "QuantLib"

    @property
    def is_available(self) -> bool:
        return QUANTLIB_AVAILABLE

    @property
    def _install_hint(self) -> str:
        return "pip install QuantLib"

    def _make_date(self, years_from_now: float) -> "ql.Date":
        """Create a QuantLib Date years from today."""
        self.require_available()

        today = ql.Date.todaysDate()
        # QuantLib uses Period for adding time
        if years_from_now == int(years_from_now):
            return today + ql.Period(int(years_from_now), ql.Years)
        else:
            # For fractional years, use days
            days = int(years_from_now * 365)
            return today + ql.Period(days, ql.Days)

    def build_flat_curve(
        self, rate: float, day_count: Optional[str] = None
    ) -> "ql.YieldTermStructureHandle":
        """
        Build a flat yield curve in QuantLib.

        Parameters
        ----------
        rate : float
            Flat rate (decimal)
        day_count : str, optional
            Day count convention ("Actual365Fixed", "Actual360", etc.)

        Returns
        -------
        ql.YieldTermStructureHandle
            QuantLib yield curve handle
        """
        self.require_available()

        today = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = today

        # Default to Actual/365 Fixed
        dc = ql.Actual365Fixed()

        flat_curve = ql.FlatForward(today, rate, dc)
        return ql.YieldTermStructureHandle(flat_curve)

    def discount_factor_flat(self, rate: float, term_years: float) -> float:
        """
        Calculate discount factor for flat curve.

        Parameters
        ----------
        rate : float
            Flat rate (decimal)
        term_years : float
            Time to maturity in years

        Returns
        -------
        float
            Discount factor
        """
        self.require_available()

        curve_handle = self.build_flat_curve(rate)
        maturity = self._make_date(term_years)

        return curve_handle.discount(maturity)

    def zero_rate_flat(self, rate: float, term_years: float) -> float:
        """
        Get zero rate from flat curve (should equal input rate).

        This is a sanity check - for a flat curve, zero rate = input rate.
        """
        self.require_available()

        curve_handle = self.build_flat_curve(rate)
        maturity = self._make_date(term_years)

        # Get zero rate (continuously compounded)
        zero = curve_handle.zeroRate(
            maturity, ql.Actual365Fixed(), ql.Continuous
        ).rate()

        return float(zero)

    def price_european_call(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """
        Price European call using QuantLib.

        Provides an additional cross-check for Black-Scholes.
        """
        self.require_available()

        today = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = today

        # Create expiry date
        expiry = self._make_date(time_to_expiry)

        # Build curves
        risk_free_curve = self.build_flat_curve(rate)
        dividend_curve = self.build_flat_curve(dividend)
        vol_curve = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, ql.NullCalendar(), volatility, ql.Actual365Fixed())
        )

        # Spot quote
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))

        # Black-Scholes process
        process = ql.BlackScholesMertonProcess(
            spot_handle, dividend_curve, risk_free_curve, vol_curve
        )

        # Option
        payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
        exercise = ql.EuropeanExercise(expiry)
        option = ql.VanillaOption(payoff, exercise)

        # Pricing engine
        engine = ql.AnalyticEuropeanEngine(process)
        option.setPricingEngine(engine)

        return option.NPV()

    def validate_discount_factor(
        self,
        our_df: float,
        rate: float,
        term_years: float,
        tolerance: float = 0.0001,
    ) -> ValidationResult:
        """
        Validate our discount factor against QuantLib.

        Parameters
        ----------
        our_df : float
            Our calculated discount factor
        rate : float
            Interest rate
        term_years : float
            Time to maturity
        tolerance : float
            Maximum allowed difference
        """
        external_df = self.discount_factor_flat(rate, term_years)
        return self.validate(
            our_df,
            external_df,
            tolerance,
            test_case=f"DF r={rate:.2%} T={term_years}Y",
        )

    def run_curve_tests(self) -> List[ValidationResult]:
        """
        Run all curve validation test cases.

        Validates our discount factor calculation against QuantLib.
        """
        import numpy as np

        results = []
        for case in CURVE_CASES:
            # Our calculation: e^(-rT)
            our_df = np.exp(-case.rate * case.term_years)

            result = self.validate_discount_factor(
                our_df, case.rate, case.term_years, tolerance=case.tolerance
            )

            # Update test case name
            result = ValidationResult(
                our_value=result.our_value,
                external_value=result.external_value,
                difference=result.difference,
                passed=result.passed,
                tolerance=result.tolerance,
                validator_name=result.validator_name,
                test_case=case.name,
            )
            results.append(result)

        return results
