"""
Monte Carlo option pricing engine.

Implements Monte Carlo simulation for option pricing:
- Vanilla European options (with analytical comparison)
- FIA crediting method payoffs
- RILA buffer/floor payoffs

[T1] MC converges to analytical price at rate 1/√N

See: METHODOLOGY.md Section 4
See: docs/knowledge/domain/option_pricing.md
See: Glasserman (2003) "Monte Carlo Methods in Financial Engineering"
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from annuity_pricing.options.payoffs.base import BasePayoff, IndexPath, OptionType
from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    generate_gbm_paths,
    generate_terminal_values,
)

if TYPE_CHECKING:
    from annuity_pricing.options.pricing.heston import HestonParams


@dataclass(frozen=True)
class MCResult:
    """
    Monte Carlo pricing result.

    Attributes
    ----------
    price : float
        Option price (discounted expected payoff)
    standard_error : float
        Standard error of the estimate
    confidence_interval : tuple[float, float]
        95% confidence interval
    n_paths : int
        Number of paths used
    payoffs : np.ndarray
        Individual path payoffs (undiscounted)
    discount_factor : float
        Discount factor used
    """

    price: float
    standard_error: float
    confidence_interval: tuple[float, float]
    n_paths: int
    payoffs: np.ndarray
    discount_factor: float

    @property
    def relative_error(self) -> float:
        """Relative standard error (SE / price)."""
        if abs(self.price) < 1e-10:
            return float("inf")
        return self.standard_error / abs(self.price)

    @property
    def ci_width(self) -> float:
        """Width of 95% confidence interval."""
        return self.confidence_interval[1] - self.confidence_interval[0]


class MonteCarloEngine:
    """
    Monte Carlo pricing engine.

    Parameters
    ----------
    n_paths : int, default 100000
        Number of simulation paths
    antithetic : bool, default True
        Use antithetic variates for variance reduction
    seed : int, optional
        Random seed for reproducibility

    Examples
    --------
    >>> engine = MonteCarloEngine(n_paths=100000, seed=42)
    >>> params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
    >>> result = engine.price_european_call(params, strike=100)
    >>> print(f"Price: {result.price:.4f} ± {result.standard_error:.4f}")
    """

    def __init__(
        self,
        n_paths: int = 100000,
        antithetic: bool = True,
        seed: int | None = None,
    ):
        if n_paths <= 0:
            raise ValueError(f"CRITICAL: n_paths must be > 0, got {n_paths}")

        self.n_paths = n_paths
        self.antithetic = antithetic
        self.seed = seed

        # Ensure even number for antithetic
        if antithetic and n_paths % 2 != 0:
            self.n_paths = n_paths + 1

    def price_european_call(
        self,
        params: GBMParams,
        strike: float,
    ) -> MCResult:
        """
        Price European call option.

        [T1] Call payoff: max(S(T) - K, 0)

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        strike : float
            Strike price

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        if strike <= 0:
            raise ValueError(f"CRITICAL: strike must be > 0, got {strike}")

        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        # Call payoff
        payoffs = np.maximum(terminal - strike, 0)

        return self._compute_result(params, payoffs)

    def price_european_put(
        self,
        params: GBMParams,
        strike: float,
    ) -> MCResult:
        """
        Price European put option.

        [T1] Put payoff: max(K - S(T), 0)

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        strike : float
            Strike price

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        if strike <= 0:
            raise ValueError(f"CRITICAL: strike must be > 0, got {strike}")

        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        # Put payoff
        payoffs = np.maximum(strike - terminal, 0)

        return self._compute_result(params, payoffs)

    def price_with_payoff(
        self,
        params: GBMParams,
        payoff: BasePayoff,
        n_steps: int = 252,
    ) -> MCResult:
        """
        Price option with custom payoff object.

        Uses vectorized calculation when available for >10x performance.
        Falls back to path-by-path calculation for path-dependent payoffs.

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        payoff : BasePayoff
            Payoff object (FIA or RILA)
        n_steps : int, default 252
            Number of time steps (252 = daily for 1 year)

        Returns
        -------
        MCResult
            Monte Carlo pricing result with credited returns
        """
        # Use vectorized path for point-to-point payoffs (>10x faster)
        if payoff.supports_vectorized():
            # Generate only terminal values for efficiency
            terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

            # Calculate returns
            index_returns = (terminal - params.spot) / params.spot

            # Vectorized payoff calculation
            credited_returns = payoff.calculate_vectorized(index_returns)

            # Convert to dollar payoffs
            payoffs = params.spot * credited_returns

            return self._compute_result(params, payoffs)

        # Fallback: full path simulation for path-dependent payoffs
        path_result = generate_gbm_paths(params, self.n_paths, n_steps, self.seed, self.antithetic)

        # Calculate payoffs for each path
        payoffs = np.zeros(self.n_paths)
        for i in range(self.n_paths):
            index_path = path_result.get_index_path(i)
            result = payoff.calculate_from_path(index_path)
            # Convert credited return to dollar payoff
            payoffs[i] = params.spot * result.credited_return

        return self._compute_result(params, payoffs)

    def price_with_payoff_heston(
        self,
        spot: float,
        rate: float,
        dividend: float,
        time_to_expiry: float,
        heston_params: "HestonParams",
        payoff: BasePayoff,
        n_steps: int = 252,
    ) -> MCResult:
        """
        Price option with custom payoff using Heston stochastic volatility paths.

        [T1] Generates paths using Andersen QE scheme for variance process.
        Uses vectorized calculation when available, falls back to path-by-path.

        Parameters
        ----------
        spot : float
            Initial spot price
        rate : float
            Risk-free rate (decimal)
        dividend : float
            Dividend yield (decimal)
        time_to_expiry : float
            Time to expiry in years
        heston_params : HestonParams
            Heston model parameters (v0, kappa, theta, sigma, rho)
        payoff : BasePayoff
            Payoff object (FIA or RILA)
        n_steps : int, default 252
            Number of time steps for path simulation

        Returns
        -------
        MCResult
            Monte Carlo pricing result with credited returns

        Examples
        --------
        >>> from annuity_pricing.options.pricing.heston import HestonParams
        >>> heston = HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)
        >>> engine = MonteCarloEngine(n_paths=50000, seed=42)
        >>> result = engine.price_with_payoff_heston(100, 0.05, 0.02, 1.0, heston, payoff)
        """
        from annuity_pricing.options.simulation.heston_paths import (
            generate_heston_paths,
            generate_heston_terminal_spots,
        )

        # Create a dummy GBMParams for _compute_result (uses rate, time_to_expiry)
        dummy_params = GBMParams(
            spot=spot,
            rate=rate,
            dividend=dividend,
            volatility=np.sqrt(heston_params.v0),  # Use sqrt(v0) as reference vol
            time_to_expiry=time_to_expiry,
        )

        # Use vectorized path for point-to-point payoffs
        if payoff.supports_vectorized():
            # Generate only terminal values for efficiency
            terminal = generate_heston_terminal_spots(
                spot=spot,
                time=time_to_expiry,
                steps=n_steps,
                paths=self.n_paths,
                rate=rate,
                dividend=dividend,
                params=heston_params,
                seed=self.seed,
            )

            # Calculate returns
            index_returns = (terminal - spot) / spot

            # Vectorized payoff calculation
            credited_returns = payoff.calculate_vectorized(index_returns)

            # Convert to dollar payoffs
            payoffs = spot * credited_returns

            return self._compute_result(dummy_params, payoffs)

        # Fallback: full path simulation for path-dependent payoffs
        path_result = generate_heston_paths(
            spot=spot,
            time=time_to_expiry,
            steps=n_steps,
            paths=self.n_paths,
            rate=rate,
            dividend=dividend,
            params=heston_params,
            seed=self.seed,
        )

        # Calculate payoffs for each path
        payoffs = np.zeros(self.n_paths)
        for i in range(self.n_paths):
            # Create IndexPath from Heston path
            index_path = IndexPath(
                times=tuple(path_result.times.tolist()),
                values=tuple(path_result.spot_paths[i, :].tolist()),
                initial_value=path_result.spot,
            )
            result = payoff.calculate_from_path(index_path)
            # Convert credited return to dollar payoff
            payoffs[i] = spot * result.credited_return

        return self._compute_result(dummy_params, payoffs)

    def price_with_terminal_payoff(
        self,
        params: GBMParams,
        payoff_func: Callable[[float, float], float],
    ) -> MCResult:
        """
        Price option with custom terminal payoff function.

        For path-independent payoffs that only depend on terminal value.

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        payoff_func : Callable[[float, float], float]
            Function(spot, terminal) -> payoff

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        payoffs = np.array([payoff_func(params.spot, t) for t in terminal])

        return self._compute_result(params, payoffs)

    def price_capped_call_return(
        self,
        params: GBMParams,
        cap_rate: float,
    ) -> MCResult:
        """
        Price capped call on return (FIA style).

        [T1] Payoff: spot × max(0, min(return, cap))

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        cap_rate : float
            Cap rate (decimal, e.g., 0.10 for 10%)

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        if cap_rate <= 0:
            raise ValueError(f"CRITICAL: cap_rate must be > 0, got {cap_rate}")

        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        # Return = (S(T) - S(0)) / S(0)
        returns = (terminal - params.spot) / params.spot

        # Capped call on return: max(0, min(return, cap))
        credited_returns = np.maximum(0, np.minimum(returns, cap_rate))

        # Convert to dollar payoff
        payoffs = params.spot * credited_returns

        return self._compute_result(params, payoffs)

    def price_buffer_protection(
        self,
        params: GBMParams,
        buffer_rate: float,
        cap_rate: float | None = None,
    ) -> MCResult:
        """
        Price buffer protection (RILA style).

        [T1] Buffer absorbs first X% of losses.

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        buffer_rate : float
            Buffer rate (decimal, e.g., 0.10 for 10%)
        cap_rate : float, optional
            Cap rate (decimal)

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        if buffer_rate <= 0:
            raise ValueError(f"CRITICAL: buffer_rate must be > 0, got {buffer_rate}")

        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        returns = (terminal - params.spot) / params.spot

        # Buffer payoff
        credited_returns = np.where(
            returns >= 0,
            returns,  # Positive: full upside
            np.maximum(returns + buffer_rate, 0),  # Negative: buffer absorbs first X%
        )

        # Apply cap if specified
        if cap_rate is not None:
            credited_returns = np.minimum(credited_returns, cap_rate)

        payoffs = params.spot * credited_returns

        return self._compute_result(params, payoffs)

    def price_floor_protection(
        self,
        params: GBMParams,
        floor_rate: float,
        cap_rate: float | None = None,
    ) -> MCResult:
        """
        Price floor protection (RILA style).

        [T1] Floor limits maximum loss to X%.

        Parameters
        ----------
        params : GBMParams
            GBM parameters
        floor_rate : float
            Floor rate (decimal, e.g., -0.10 for -10% max loss)
        cap_rate : float, optional
            Cap rate (decimal)

        Returns
        -------
        MCResult
            Monte Carlo pricing result
        """
        if floor_rate > 0:
            raise ValueError(f"CRITICAL: floor_rate should be <= 0, got {floor_rate}")

        terminal = generate_terminal_values(params, self.n_paths, self.seed, self.antithetic)

        returns = (terminal - params.spot) / params.spot

        # Floor payoff: max(return, floor)
        credited_returns = np.maximum(returns, floor_rate)

        # Apply cap if specified
        if cap_rate is not None:
            credited_returns = np.minimum(credited_returns, cap_rate)

        payoffs = params.spot * credited_returns

        return self._compute_result(params, payoffs)

    def _compute_result(self, params: GBMParams, payoffs: np.ndarray) -> MCResult:
        """
        Compute MC result from payoffs.

        Parameters
        ----------
        params : GBMParams
            GBM parameters (for discounting)
        payoffs : np.ndarray
            Undiscounted payoffs

        Returns
        -------
        MCResult
            Complete MC result with statistics
        """
        # Discount factor
        df = np.exp(-params.rate * params.time_to_expiry)

        # Discounted mean and standard error
        mean_payoff = payoffs.mean()
        std_payoff = payoffs.std(ddof=1)
        se = std_payoff / np.sqrt(len(payoffs))

        price = df * mean_payoff
        se_price = df * se

        # 95% confidence interval (z = 1.96)
        ci_lower = price - 1.96 * se_price
        ci_upper = price + 1.96 * se_price

        return MCResult(
            price=price,
            standard_error=se_price,
            confidence_interval=(ci_lower, ci_upper),
            n_paths=len(payoffs),
            payoffs=payoffs,
            discount_factor=df,
        )


def price_vanilla_mc(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
    option_type: OptionType,
    n_paths: int = 100000,
    seed: int | None = None,
) -> MCResult:
    """
    Convenience function to price vanilla option via MC.

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry in years
    option_type : OptionType
        CALL or PUT
    n_paths : int, default 100000
        Number of paths
    seed : int, optional
        Random seed

    Returns
    -------
    MCResult
        Monte Carlo pricing result
    """
    params = GBMParams(
        spot=spot,
        rate=rate,
        dividend=dividend,
        volatility=volatility,
        time_to_expiry=time_to_expiry,
    )

    engine = MonteCarloEngine(n_paths=n_paths, antithetic=True, seed=seed)

    if option_type == OptionType.CALL:
        return engine.price_european_call(params, strike)
    else:
        return engine.price_european_put(params, strike)


def convergence_analysis(
    params: GBMParams,
    strike: float,
    analytical_price: float,
    path_counts: list[int] | None = None,
    seed: int = 42,
) -> dict:
    """
    Analyze MC convergence to analytical price.

    [T1] MC error should converge at rate 1/√N.

    Parameters
    ----------
    params : GBMParams
        GBM parameters
    strike : float
        Strike price
    analytical_price : float
        Analytical (Black-Scholes) price
    path_counts : list[int]
        Number of paths to test
    seed : int
        Random seed

    Returns
    -------
    dict
        Convergence analysis results
    """
    if path_counts is None:
        path_counts = [1000, 5000, 10000, 50000, 100000, 500000]
    results = []

    for n in path_counts:
        engine = MonteCarloEngine(n_paths=n, antithetic=True, seed=seed)
        mc_result = engine.price_european_call(params, strike)

        error = abs(mc_result.price - analytical_price)
        rel_error = error / analytical_price if analytical_price > 0 else float("inf")

        results.append(
            {
                "n_paths": n,
                "mc_price": mc_result.price,
                "analytical_price": analytical_price,
                "absolute_error": error,
                "relative_error": rel_error,
                "standard_error": mc_result.standard_error,
                "within_ci": mc_result.confidence_interval[0]
                <= analytical_price
                <= mc_result.confidence_interval[1],
            }
        )

    return {
        "results": results,
        "convergence_rate": _estimate_convergence_rate(results),
    }


def _estimate_convergence_rate(results: list[dict]) -> float:
    """
    Estimate convergence rate from results.

    [T1] Theory predicts rate = -0.5 (error ~ 1/√N).

    Returns
    -------
    float
        Estimated convergence rate (should be ~-0.5)
    """
    import numpy as np

    # Log-log regression: log(error) = rate * log(N) + const
    log_n = np.log([r["n_paths"] for r in results])
    log_error = np.log([r["absolute_error"] + 1e-10 for r in results])

    # Simple linear regression
    n = len(log_n)
    slope = (n * np.sum(log_n * log_error) - np.sum(log_n) * np.sum(log_error)) / (
        n * np.sum(log_n**2) - np.sum(log_n) ** 2
    )

    return slope


def monte_carlo_price(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
    n_paths: int = 100000,
    option_type: str = "call",
    seed: int | None = None,
) -> float:
    """
    Convenience function to price vanilla option via Monte Carlo.

    This is a simple wrapper that returns just the price (not full MCResult).
    Useful for validation against external implementations.

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry in years
    n_paths : int, default 100000
        Number of simulation paths
    option_type : str, default "call"
        Option type: "call" or "put"
    seed : int, optional
        Random seed for reproducibility

    Returns
    -------
    float
        Option price

    Examples
    --------
    >>> price = monte_carlo_price(100, 100, 0.05, 0.02, 0.20, 1.0)
    >>> print(f"MC price: {price:.4f}")
    """
    opt_type = OptionType.CALL if option_type.lower() == "call" else OptionType.PUT

    result = price_vanilla_mc(
        spot=spot,
        strike=strike,
        rate=rate,
        dividend=dividend,
        volatility=volatility,
        time_to_expiry=time_to_expiry,
        option_type=opt_type,
        n_paths=n_paths,
        seed=seed,
    )

    return result.price
