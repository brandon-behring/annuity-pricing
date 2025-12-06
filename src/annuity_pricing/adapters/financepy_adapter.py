"""
Financepy adapter for Black-Scholes validation.

Validates our Black-Scholes implementation against financepy.

Golden Values (Hull Ch. 15)
---------------------------
| Test      | S   | K   | r    | σ    | T   | Expected Call | Tolerance |
|-----------|-----|-----|------|------|-----|---------------|-----------|
| Hull 15.6 | 42  | 40  | 0.10 | 0.20 | 0.5 | 4.76          | 0.02      |
| ATM       | 100 | 100 | 0.05 | 0.20 | 1.0 | 10.45         | 0.05      |
| ITM       | 100 | 95  | 0.05 | 0.20 | 1.0 | 13.70         | 0.05      |
| OTM       | 100 | 105 | 0.05 | 0.20 | 1.0 | 7.97          | 0.05      |

Greeks Golden Values (ATM, S=K=100, r=5%, σ=20%, T=1):
| Greek | Expected | Tolerance |
|-------|----------|-----------|
| Delta | 0.637    | 0.01      |
| Gamma | 0.019    | 0.001     |
| Vega  | 37.5     | 0.5       |
| Theta | -6.4     | 0.5       |
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .base import BaseAdapter, ValidationResult


# Try to import financepy
try:
    from financepy.products.equity import EquityVanillaOption
    from financepy.utils.date import Date
    from financepy.utils.global_types import OptionTypes
    from financepy.market.curves.discount_curve_flat import DiscountCurveFlat
    from financepy.models.black_scholes import BlackScholes

    FINANCEPY_AVAILABLE = True
except ImportError:
    FINANCEPY_AVAILABLE = False


@dataclass(frozen=True)
class GoldenCase:
    """A golden test case with known expected value."""

    name: str
    spot: float
    strike: float
    rate: float
    dividend: float
    volatility: float
    time_to_expiry: float
    expected_call: float
    expected_put: Optional[float] = None
    tolerance: float = 0.05


# Hull textbook examples and common cases
GOLDEN_CASES: List[GoldenCase] = [
    GoldenCase(
        name="Hull 15.6",
        spot=42.0,
        strike=40.0,
        rate=0.10,
        dividend=0.0,
        volatility=0.20,
        time_to_expiry=0.5,
        expected_call=4.76,
        tolerance=0.02,
    ),
    GoldenCase(
        name="ATM",
        spot=100.0,
        strike=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
        expected_call=9.93,  # With dividend
        tolerance=0.05,
    ),
    GoldenCase(
        name="ITM",
        spot=100.0,
        strike=95.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
        expected_call=12.72,
        tolerance=0.05,
    ),
    GoldenCase(
        name="OTM",
        spot=100.0,
        strike=105.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
        expected_call=7.45,
        tolerance=0.05,
    ),
]


class FinancepyAdapter(BaseAdapter):
    """
    Adapter for validating Black-Scholes against financepy.

    Examples
    --------
    >>> adapter = FinancepyAdapter()
    >>> if adapter.is_available:
    ...     result = adapter.price_call(100, 100, 0.05, 0.02, 0.20, 1.0)
    """

    @property
    def name(self) -> str:
        return "financepy"

    @property
    def is_available(self) -> bool:
        return FINANCEPY_AVAILABLE

    @property
    def _install_hint(self) -> str:
        return "pip install financepy"

    def price_call(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """
        Price European call using financepy.

        Parameters match our black_scholes_call signature.
        """
        self.require_available()

        # financepy requires Date objects
        valuation_date = Date(1, 1, 2024)
        expiry_date = valuation_date.add_years(time_to_expiry)

        # Create discount curve
        discount_curve = DiscountCurveFlat(valuation_date, rate)
        dividend_curve = DiscountCurveFlat(valuation_date, dividend)

        # Create option
        option = EquityVanillaOption(
            expiry_date, strike, OptionTypes.EUROPEAN_CALL
        )

        # Create model
        model = BlackScholes(volatility)

        # Price
        value = option.value(
            valuation_date, spot, discount_curve, dividend_curve, model
        )

        return float(value)

    def price_put(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """Price European put using financepy."""
        self.require_available()

        valuation_date = Date(1, 1, 2024)
        expiry_date = valuation_date.add_years(time_to_expiry)

        discount_curve = DiscountCurveFlat(valuation_date, rate)
        dividend_curve = DiscountCurveFlat(valuation_date, dividend)

        option = EquityVanillaOption(
            expiry_date, strike, OptionTypes.EUROPEAN_PUT
        )
        model = BlackScholes(volatility)

        value = option.value(
            valuation_date, spot, discount_curve, dividend_curve, model
        )

        return float(value)

    def calculate_greeks(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> Dict[str, float]:
        """
        Calculate Greeks using financepy.

        Returns
        -------
        dict
            Dictionary with delta, gamma, vega, theta
        """
        self.require_available()

        valuation_date = Date(1, 1, 2024)
        expiry_date = valuation_date.add_years(time_to_expiry)

        discount_curve = DiscountCurveFlat(valuation_date, rate)
        dividend_curve = DiscountCurveFlat(valuation_date, dividend)

        option = EquityVanillaOption(
            expiry_date, strike, OptionTypes.EUROPEAN_CALL
        )
        model = BlackScholes(volatility)

        # financepy returns greeks as tuple
        delta = option.delta(
            valuation_date, spot, discount_curve, dividend_curve, model
        )
        gamma = option.gamma(
            valuation_date, spot, discount_curve, dividend_curve, model
        )
        vega = option.vega(
            valuation_date, spot, discount_curve, dividend_curve, model
        )
        theta = option.theta(
            valuation_date, spot, discount_curve, dividend_curve, model
        )

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta),
        }

    def validate_call(
        self,
        our_price: float,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
        tolerance: float = 0.01,
    ) -> ValidationResult:
        """
        Validate our call price against financepy.

        Parameters
        ----------
        our_price : float
            Price from our implementation
        spot, strike, rate, dividend, volatility, time_to_expiry : float
            Option parameters
        tolerance : float
            Maximum allowed difference

        Returns
        -------
        ValidationResult
            Comparison result
        """
        external_price = self.price_call(
            spot, strike, rate, dividend, volatility, time_to_expiry
        )
        return self.validate(
            our_price,
            external_price,
            tolerance,
            test_case=f"Call S={spot} K={strike}",
        )

    def validate_put(
        self,
        our_price: float,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
        tolerance: float = 0.01,
    ) -> ValidationResult:
        """Validate our put price against financepy."""
        external_price = self.price_put(
            spot, strike, rate, dividend, volatility, time_to_expiry
        )
        return self.validate(
            our_price,
            external_price,
            tolerance,
            test_case=f"Put S={spot} K={strike}",
        )

    def run_golden_tests(self) -> List[ValidationResult]:
        """
        Run all golden test cases.

        Returns
        -------
        List[ValidationResult]
            Results for each golden test case
        """
        from annuity_pricing.options.pricing.black_scholes import (
            black_scholes_call,
        )

        results = []
        for case in GOLDEN_CASES:
            our_price = black_scholes_call(
                case.spot,
                case.strike,
                case.rate,
                case.dividend,
                case.volatility,
                case.time_to_expiry,
            )
            result = self.validate_call(
                our_price,
                case.spot,
                case.strike,
                case.rate,
                case.dividend,
                case.volatility,
                case.time_to_expiry,
                tolerance=case.tolerance,
            )
            # Update test_case name
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
