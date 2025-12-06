"""
Expense Modeling - Phase 7.

Models policy expenses for pricing and reserving:
- Per-policy fixed expenses (inflated annually)
- Percentage of AV expenses (M&E)
- Acquisition costs (one-time at issue)

Theory
------
[T1] Total expense = per_policy × inflation_factor + AV × pct_of_av

[T2] Inflation factor = (1 + inflation_rate)^years_from_issue

[T3] PV of expenses = sum over t of expense(t) × survival(t) × discount(t)

See: docs/knowledge/domain/expense_assumptions.md
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class ExpenseAssumptions:
    """
    Expense assumptions.

    Attributes
    ----------
    per_policy_annual : float
        Fixed annual per-policy expense (e.g., $100)
    pct_of_av_annual : float
        Annual percentage of AV (M&E) (e.g., 0.0150 for 1.50%)
    acquisition_pct : float
        One-time acquisition cost as % of premium
    inflation_rate : float
        Annual inflation rate for per-policy expenses
    """

    per_policy_annual: float = 100.0
    pct_of_av_annual: float = 0.0150  # 1.50% M&E
    acquisition_pct: float = 0.03  # 3% acquisition
    inflation_rate: float = 0.025  # 2.5% inflation


@dataclass(frozen=True)
class ExpenseResult:
    """
    Result of expense calculation.

    Attributes
    ----------
    total_expense : float
        Total expense for the period
    per_policy_component : float
        Fixed per-policy portion (inflated)
    av_component : float
        % of AV portion
    """

    total_expense: float
    per_policy_component: float
    av_component: float


class ExpenseModel:
    """
    Policy expense model.

    [T1] Combines per-policy fixed expenses with AV-based charges.

    Examples
    --------
    >>> model = ExpenseModel(ExpenseAssumptions())
    >>> result = model.calculate_period_expense(
    ...     av=100_000, period_years=1.0, years_from_issue=0
    ... )
    >>> result.total_expense
    1600.0  # $100 + 1.5% of $100k

    See: docs/knowledge/domain/expense_assumptions.md
    """

    def __init__(self, assumptions: ExpenseAssumptions):
        """
        Initialize expense model.

        Parameters
        ----------
        assumptions : ExpenseAssumptions
            Expense assumptions
        """
        self.assumptions = assumptions

    def calculate_period_expense(
        self,
        av: float,
        period_years: float = 1.0,
        years_from_issue: int = 0,
    ) -> ExpenseResult:
        """
        Calculate expense for a period.

        [T1] expense = per_policy × inflation × period + AV × pct × period

        Parameters
        ----------
        av : float
            Account value (for % of AV calculation)
        period_years : float
            Length of period in years
        years_from_issue : int
            Years since policy issue (for inflation)

        Returns
        -------
        ExpenseResult
            Calculated expenses with breakdown
        """
        if av < 0:
            raise ValueError(f"Account value cannot be negative, got {av}")
        if period_years <= 0:
            raise ValueError(f"Period must be positive, got {period_years}")

        a = self.assumptions

        # Per-policy component with inflation
        # [T2] Inflation factor = (1 + r)^t
        inflation_factor = (1 + a.inflation_rate) ** years_from_issue
        per_policy_expense = a.per_policy_annual * inflation_factor * period_years

        # AV component (M&E charge)
        av_expense = av * a.pct_of_av_annual * period_years

        total = per_policy_expense + av_expense

        return ExpenseResult(
            total_expense=total,
            per_policy_component=per_policy_expense,
            av_component=av_expense,
        )

    def calculate_acquisition_cost(self, premium: float) -> float:
        """
        Calculate one-time acquisition cost.

        [T1] Acquisition cost = premium × acquisition_pct

        Parameters
        ----------
        premium : float
            Premium amount

        Returns
        -------
        float
            Acquisition cost
        """
        if premium < 0:
            raise ValueError(f"Premium cannot be negative, got {premium}")

        return premium * self.assumptions.acquisition_pct

    def calculate_path_expenses(
        self,
        av_path: np.ndarray,
        dt: float = 1.0,
    ) -> np.ndarray:
        """
        Calculate expenses along a simulation path.

        Parameters
        ----------
        av_path : ndarray
            Path of account values (shape: [n_steps])
        dt : float
            Time step in years

        Returns
        -------
        ndarray
            Expenses at each time step (shape: [n_steps])
        """
        n_steps = len(av_path)
        expenses = np.zeros(n_steps)

        for t in range(n_steps):
            result = self.calculate_period_expense(
                av=av_path[t],
                period_years=dt,
                years_from_issue=int(t * dt),
            )
            expenses[t] = result.total_expense

        return expenses

    def calculate_pv_expenses(
        self,
        av_path: np.ndarray,
        survival_probs: np.ndarray,
        discount_rate: float,
        dt: float = 1.0,
        include_acquisition: bool = False,
        premium: Optional[float] = None,
    ) -> float:
        """
        Calculate present value of expenses along a path.

        [T3] PV = sum_t expense(t) × survival(t) × e^(-r × t × dt)

        Parameters
        ----------
        av_path : ndarray
            Path of account values (shape: [n_steps])
        survival_probs : ndarray
            Survival probabilities at each step (shape: [n_steps])
            Should be cumulative survival from t=0
        discount_rate : float
            Annual discount rate (e.g., 0.05 for 5%)
        dt : float
            Time step in years
        include_acquisition : bool
            Whether to add acquisition cost to PV
        premium : float, optional
            Premium amount (required if include_acquisition=True)

        Returns
        -------
        float
            Present value of expenses
        """
        if len(av_path) != len(survival_probs):
            raise ValueError(
                f"Path lengths must match: av={len(av_path)}, survival={len(survival_probs)}"
            )

        # Calculate period expenses
        expenses = self.calculate_path_expenses(av_path, dt)

        # Discount each period's expense
        n_steps = len(av_path)
        pv = 0.0

        for t in range(n_steps):
            discount_factor = np.exp(-discount_rate * t * dt)
            pv += expenses[t] * survival_probs[t] * discount_factor

        # Add acquisition cost if requested
        if include_acquisition:
            if premium is None:
                raise ValueError(
                    "Premium required when include_acquisition=True"
                )
            pv += self.calculate_acquisition_cost(premium)

        return pv

    def calculate_annual_expense_rate(
        self,
        av: float,
        years_from_issue: int = 0,
    ) -> float:
        """
        Calculate total expense as annualized rate of AV.

        Useful for comparing expense loads across products.

        Parameters
        ----------
        av : float
            Account value
        years_from_issue : int
            Years since policy issue

        Returns
        -------
        float
            Total annual expense rate (decimal)
            e.g., 0.0165 for 1.65% of AV

        Examples
        --------
        >>> model = ExpenseModel(ExpenseAssumptions())
        >>> model.calculate_annual_expense_rate(100_000)
        0.016  # 1.6% = (100 + 1500) / 100000
        """
        if av <= 0:
            raise ValueError(f"Account value must be positive, got {av}")

        result = self.calculate_period_expense(
            av=av,
            period_years=1.0,
            years_from_issue=years_from_issue,
        )

        return result.total_expense / av

    def expense_sensitivity(
        self,
        av: float,
        parameter: str,
        delta: float = 0.0001,
    ) -> float:
        """
        Calculate sensitivity of expenses to a parameter change.

        Parameters
        ----------
        av : float
            Account value
        parameter : str
            Parameter name: 'per_policy', 'pct_of_av', 'inflation'
        delta : float
            Relative change to parameter (default 0.01% = 1bp)

        Returns
        -------
        float
            Approximate derivative (change in expense per unit change in param)
        """
        from dataclasses import replace

        base_result = self.calculate_period_expense(av=av)

        # Create shocked assumptions
        a = self.assumptions
        if parameter == "per_policy":
            shocked = replace(a, per_policy_annual=a.per_policy_annual * (1 + delta))
        elif parameter == "pct_of_av":
            shocked = replace(a, pct_of_av_annual=a.pct_of_av_annual * (1 + delta))
        elif parameter == "inflation":
            shocked = replace(a, inflation_rate=a.inflation_rate + delta)
        else:
            raise ValueError(f"Unknown parameter: {parameter}")

        shocked_model = ExpenseModel(shocked)
        shocked_result = shocked_model.calculate_period_expense(av=av)

        # Calculate sensitivity
        expense_change = shocked_result.total_expense - base_result.total_expense

        if parameter == "inflation":
            # For inflation, sensitivity is per absolute change
            return expense_change / delta
        else:
            # For others, sensitivity is per relative change
            param_change = (
                a.per_policy_annual * delta if parameter == "per_policy"
                else a.pct_of_av_annual * delta
            )
            return expense_change / param_change if param_change != 0 else 0.0
