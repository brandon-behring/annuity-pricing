"""
GLWB (Guaranteed Lifetime Withdrawal Benefit) pricer.

GLWB provides guaranteed income for life, continuing even if the account
value is exhausted. This module wraps the path simulation engine for
pricing GLWB guarantees.

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md
"""

from dataclasses import dataclass
from datetime import date
from typing import NoReturn

from annuity_pricing.data.schemas import GLWBProduct
from annuity_pricing.glwb.gwb_tracker import GWBConfig, RollupType
from annuity_pricing.glwb.path_sim import GLWBPathSimulator
from annuity_pricing.glwb.path_sim import GLWBPricingResult as SimResult
from annuity_pricing.products.base import BasePricer, PricingResult


@dataclass(frozen=True)
class GLWBPricingResult(PricingResult):
    """
    Extended pricing result for GLWB products.

    Attributes
    ----------
    guarantee_cost : float
        Cost of guarantee as % of premium
    prob_ruin : float
        Probability account value exhausted before death
    mean_ruin_year : float
        Average year of ruin (if ruin occurs)
    prob_lapse : float
        Probability of lapse before death/ruin
    mean_lapse_year : float
        Average year of lapse (if lapse occurs)
    n_paths : int
        Number of paths simulated
    """

    guarantee_cost: float = 0.0
    prob_ruin: float = 0.0
    mean_ruin_year: float = 0.0
    prob_lapse: float = 0.0
    mean_lapse_year: float = 0.0
    n_paths: int = 0


class GLWBPricer(BasePricer):
    """
    Pricer for Guaranteed Lifetime Withdrawal Benefits.

    GLWB pricing requires path-dependent Monte Carlo simulation because
    the payoff depends on the entire path of account values, not just
    terminal value.

    [T1] GLWB value = E[PV(insurer payments when AV exhausted)]

    Parameters
    ----------
    risk_free_rate : float
        Risk-free rate for discounting
    volatility : float
        Index volatility for GBM simulation
    n_paths : int, default 10000
        Number of Monte Carlo paths
    seed : int, optional
        Random seed for reproducibility

    Examples
    --------
    >>> from annuity_pricing.data.schemas import GLWBProduct
    >>> product = GLWBProduct(
    ...     company_name="Example Life",
    ...     product_name="GLWB 5%",
    ...     product_group="GLWB",
    ...     status="current",
    ...     withdrawal_rate=0.05,
    ...     rollup_rate=0.06,
    ... )
    >>> pricer = GLWBPricer(risk_free_rate=0.04, volatility=0.15)
    >>> result = pricer.price(product, premium=100_000, age=65)
    >>> result.guarantee_cost  # Cost as % of premium
    """

    def __init__(
        self,
        risk_free_rate: float = 0.04,
        volatility: float = 0.15,
        n_paths: int = 10000,
        seed: int | None = None,
    ):
        """
        Initialize GLWB pricer.

        Parameters
        ----------
        risk_free_rate : float
            Risk-free rate for discounting and drift
        volatility : float
            Index volatility (annualized)
        n_paths : int
            Number of MC paths (more = more accurate but slower)
        seed : int, optional
            Random seed for reproducibility
        """
        if risk_free_rate < 0:
            raise ValueError(f"risk_free_rate must be >= 0, got {risk_free_rate}")
        if volatility <= 0:
            raise ValueError(f"volatility must be > 0, got {volatility}")
        if n_paths < 100:
            raise ValueError(f"n_paths must be >= 100, got {n_paths}")

        self.risk_free_rate = risk_free_rate
        self.volatility = volatility
        self.n_paths = n_paths
        self.seed = seed

    def price(  # type: ignore[override]  # Subclass has specific params
        self,
        product: GLWBProduct,
        as_of_date: date | None = None,
        premium: float = 100_000.0,
        age: int = 65,
        max_age: int = 100,
        gender: str = "male",
    ) -> GLWBPricingResult:
        """
        Price GLWB guarantee.

        Parameters
        ----------
        product : GLWBProduct
            GLWB product to price
        as_of_date : date, optional
            Valuation date (default: today)
        premium : float
            Initial premium amount
        age : int
            Starting age of annuitant
        max_age : int
            Maximum simulation age
        gender : str
            'male' or 'female' for mortality table

        Returns
        -------
        GLWBPricingResult
            Pricing result with guarantee cost and risk metrics
        """
        self.validate_product(product, ["withdrawal_rate", "rollup_rate"])

        if age < 40 or age > 90:
            raise ValueError(f"age must be 40-90, got {age}")

        # Convert GLWBProduct to GWBConfig
        rollup_type = (
            RollupType.COMPOUND
            if product.rollup_type == "compound"
            else RollupType.SIMPLE
        )

        gwb_config = GWBConfig(
            rollup_type=rollup_type,
            rollup_rate=product.rollup_rate,
            rollup_cap_years=product.rollup_cap_years,
            ratchet_enabled=product.step_up_frequency > 0,
            ratchet_frequency=product.step_up_frequency,
            withdrawal_rate=product.withdrawal_rate,
            fee_rate=product.fee_rate,
        )

        # Create simulator and price
        simulator = GLWBPathSimulator(
            gwb_config=gwb_config,
            n_paths=self.n_paths,
            seed=self.seed,
        )

        sim_result: SimResult = simulator.price(
            premium=premium,
            age=age,
            r=self.risk_free_rate,
            sigma=self.volatility,
            max_age=max_age,
            gender=gender,
            deferral_years=product.deferral_years,
        )

        return GLWBPricingResult(
            present_value=sim_result.price,
            duration=None,  # Duration not meaningful for path-dependent products
            convexity=None,
            details={
                "mean_payoff": sim_result.mean_payoff,
                "std_payoff": sim_result.std_payoff,
                "standard_error": sim_result.standard_error,
                "premium": premium,
                "age": age,
                "withdrawal_rate": product.withdrawal_rate,
                "rollup_rate": product.rollup_rate,
            },
            as_of_date=as_of_date or date.today(),
            guarantee_cost=sim_result.guarantee_cost,
            prob_ruin=sim_result.prob_ruin,
            mean_ruin_year=sim_result.mean_ruin_year,
            prob_lapse=sim_result.prob_lapse,
            mean_lapse_year=sim_result.mean_lapse_year,
            n_paths=sim_result.n_paths,
        )

    def competitive_position(
        self,
        product: GLWBProduct,
        market_data: "pd.DataFrame",  # type: ignore[name-defined]  # noqa: F821
        **kwargs: object,
    ) -> NoReturn:
        """
        Competitive positioning not implemented for GLWB.

        GLWB products are highly customized and not directly comparable
        on a single metric like MYGA rates.
        """
        raise NotImplementedError(
            "Competitive positioning not implemented for GLWB products. "
            "Use price() to compare guarantee costs across products."
        )
