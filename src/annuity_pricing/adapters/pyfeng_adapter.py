"""
Pyfeng adapter for Monte Carlo validation.

Validates our Monte Carlo implementation against pyfeng.

Golden Values (MC convergence to BS)
------------------------------------
| Test          | Paths | Expected BS | MC Tolerance |
|---------------|-------|-------------|--------------|
| ATM call 1Y   | 100k  | 10.45       | 0.10 (1%)    |
| ITM call 1Y   | 100k  | 13.70       | 0.15         |
"""

from dataclasses import dataclass

from annuity_pricing.config.tolerances import CROSS_LIBRARY_TOLERANCE

from .base import BaseAdapter, ValidationResult

# Try to import pyfeng
try:
    import pyfeng as pf

    PYFENG_AVAILABLE = True
except ImportError:
    PYFENG_AVAILABLE = False


@dataclass(frozen=True)
class MCConvergenceCase:
    """A Monte Carlo convergence test case."""

    name: str
    spot: float
    strike: float
    rate: float
    dividend: float
    volatility: float
    time_to_expiry: float
    n_paths: int
    expected_bs: float
    tolerance: float


# MC convergence test cases
MC_CONVERGENCE_CASES: list[MCConvergenceCase] = [
    MCConvergenceCase(
        name="ATM call 1Y",
        spot=100.0,
        strike=100.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
        n_paths=100000,
        expected_bs=9.93,
        tolerance=0.15,  # 1.5% tolerance for MC
    ),
    MCConvergenceCase(
        name="ITM call 1Y",
        spot=100.0,
        strike=90.0,
        rate=0.05,
        dividend=0.02,
        volatility=0.20,
        time_to_expiry=1.0,
        n_paths=100000,
        expected_bs=15.24,
        tolerance=0.20,
    ),
]


class PyfengAdapter(BaseAdapter):
    """
    Adapter for validating Monte Carlo against pyfeng.

    Examples
    --------
    >>> adapter = PyfengAdapter()
    >>> if adapter.is_available:
    ...     price = adapter.price_mc_call(100, 100, 0.05, 0.02, 0.20, 1.0)
    """

    @property
    def name(self) -> str:
        return "pyfeng"

    @property
    def is_available(self) -> bool:
        return PYFENG_AVAILABLE

    @property
    def _install_hint(self) -> str:
        return "pip install pyfeng"

    def price_bs_call(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """
        Price European call using pyfeng Black-Scholes.

        Uses pyfeng's Bsm (Black-Scholes-Merton) model.
        """
        self.require_available()

        # pyfeng uses different parameter names
        # intr = interest rate, divr = dividend rate
        model = pf.Bsm(sigma=volatility, intr=rate, divr=dividend)
        price = model.price(strike=strike, spot=spot, texp=time_to_expiry)

        return float(price)

    def price_bs_put(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """Price European put using pyfeng Black-Scholes."""
        self.require_available()

        model = pf.Bsm(sigma=volatility, intr=rate, divr=dividend)
        price = model.price(strike=strike, spot=spot, texp=time_to_expiry, cp=-1)

        return float(price)

    def price_mc_call(
        self,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
        n_paths: int = 100000,
        seed: int | None = None,
    ) -> float:
        """
        Price European call using pyfeng Monte Carlo.

        Parameters
        ----------
        n_paths : int
            Number of simulation paths
        seed : int, optional
            Random seed for reproducibility
        """
        self.require_available()

        # pyfeng's Monte Carlo model
        model = pf.BsmMc(sigma=volatility, intr=rate, divr=dividend)
        model.set_num_params(n_path=n_paths)
        if seed is not None:
            model.rng_seed = seed

        price = model.price(strike=strike, spot=spot, texp=time_to_expiry)

        return float(price)

    def validate_mc_convergence(
        self,
        our_mc_price: float,
        our_bs_price: float,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
        tolerance: float = 0.10,
    ) -> ValidationResult:
        """
        Validate that our MC converges to BS.

        Compares our MC price against our BS price
        (both should converge to the same value).
        """
        return self.validate(
            our_mc_price,
            our_bs_price,
            tolerance,
            test_case=f"MC→BS S={spot} K={strike}",
        )

    def validate_against_pyfeng_bs(
        self,
        our_price: float,
        spot: float,
        strike: float,
        rate: float,
        dividend: float,
        volatility: float,
        time_to_expiry: float,
        tolerance: float = CROSS_LIBRARY_TOLERANCE,
    ) -> ValidationResult:
        """Validate our BS implementation against pyfeng's BS."""
        external_price = self.price_bs_call(
            spot, strike, rate, dividend, volatility, time_to_expiry
        )
        return self.validate(
            our_price,
            external_price,
            tolerance,
            test_case=f"BS vs pyfeng S={spot} K={strike}",
        )

    def run_convergence_tests(self) -> list[ValidationResult]:
        """
        Run all MC convergence test cases.

        Validates that our MC converges to our BS for various scenarios.
        """
        from annuity_pricing.options.pricing.black_scholes import (
            black_scholes_call,
        )
        from annuity_pricing.options.simulation.monte_carlo import (
            monte_carlo_price,
        )

        results = []
        for case in MC_CONVERGENCE_CASES:
            bs_price = black_scholes_call(
                case.spot,
                case.strike,
                case.rate,
                case.dividend,
                case.volatility,
                case.time_to_expiry,
            )

            mc_price = monte_carlo_price(
                spot=case.spot,
                strike=case.strike,
                rate=case.rate,
                dividend=case.dividend,
                volatility=case.volatility,
                time_to_expiry=case.time_to_expiry,
                n_paths=case.n_paths,
                option_type="call",
            )

            result = self.validate_mc_convergence(
                mc_price,
                bs_price,
                case.spot,
                case.strike,
                case.rate,
                case.dividend,
                case.volatility,
                case.time_to_expiry,
                tolerance=case.tolerance,
            )

            # Update test case name
            result = ValidationResult(
                our_value=result.our_value,
                external_value=result.external_value,
                difference=result.difference,
                passed=result.passed,
                tolerance=result.tolerance,
                validator_name="MC→BS",
                test_case=case.name,
            )
            results.append(result)

        return results
