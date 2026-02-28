"""
Yield Curve Loader - Phase 10.

Loads and constructs yield curves from market data:
- Treasury curves (FRED)
- Nelson-Siegel fitting
- Linear/log-linear interpolation

Theory
------
[T1] Nelson-Siegel: y(τ) = β₀ + β₁(1-e^(-τ/λ))/(τ/λ) + β₂((1-e^(-τ/λ))/(τ/λ) - e^(-τ/λ))
[T1] Discount factor: P(t) = e^(-r(t) × t)
[T1] Forward rate: f(t₁,t₂) = (r(t₂)t₂ - r(t₁)t₁)/(t₂ - t₁)

Validators: QuantLib, PyCurve
See: docs/CROSS_VALIDATION_MATRIX.md
"""

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class InterpolationMethod(Enum):
    """Interpolation method for yield curve."""

    LINEAR = "linear"
    LOG_LINEAR = "log_linear"
    CUBIC = "cubic"


@dataclass
class YieldCurve:
    """
    Yield curve representation.

    [T1] Zero-coupon yield curve with interpolation.

    Attributes
    ----------
    maturities : ndarray
        Maturities in years
    rates : ndarray
        Zero rates at each maturity (continuous compounding)
    as_of_date : str
        Curve date (YYYY-MM-DD)
    curve_type : str
        Curve construction method
    interpolation : InterpolationMethod
        Interpolation method for intermediate maturities
    """

    maturities: np.ndarray
    rates: np.ndarray
    as_of_date: str
    curve_type: str
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR

    def __post_init__(self) -> None:
        """Validate curve data."""
        if len(self.maturities) != len(self.rates):
            raise ValueError(
                f"Maturities ({len(self.maturities)}) and rates ({len(self.rates)}) "
                "must have same length"
            )
        if len(self.maturities) == 0:
            raise ValueError("Curve must have at least one point")
        if not np.all(np.diff(self.maturities) > 0):
            raise ValueError("Maturities must be strictly increasing")

    def get_rate(self, t: float) -> float:
        """
        Get interpolated zero rate at maturity t.

        [T1] Uses configured interpolation method.

        Parameters
        ----------
        t : float
            Maturity in years

        Returns
        -------
        float
            Zero rate at maturity t

        Examples
        --------
        >>> curve = YieldCurve(
        ...     maturities=np.array([1, 2, 5, 10]),
        ...     rates=np.array([0.03, 0.035, 0.04, 0.045]),
        ...     as_of_date="2024-01-01",
        ...     curve_type="treasury"
        ... )
        >>> curve.get_rate(3.0)  # Interpolated
        0.0375
        """
        if t <= 0:
            raise ValueError(f"Maturity must be positive, got {t}")

        # Extrapolation: flat at ends
        if t <= self.maturities[0]:
            return float(self.rates[0])
        if t >= self.maturities[-1]:
            return float(self.rates[-1])

        # Interpolation
        if self.interpolation == InterpolationMethod.LINEAR:
            return float(np.interp(t, self.maturities, self.rates))
        elif self.interpolation == InterpolationMethod.LOG_LINEAR:
            # Log-linear on discount factors
            log_df = -self.maturities * self.rates
            log_df_t = np.interp(t, self.maturities, log_df)
            return -log_df_t / t
        else:
            # Cubic (simplified: use numpy for now)
            return float(np.interp(t, self.maturities, self.rates))

    def discount_factor(self, t: float) -> float:
        """
        Calculate discount factor at maturity t.

        [T1] P(t) = e^(-r(t) × t)

        Parameters
        ----------
        t : float
            Maturity in years

        Returns
        -------
        float
            Discount factor

        Examples
        --------
        >>> curve = YieldCurve(
        ...     maturities=np.array([1, 5, 10]),
        ...     rates=np.array([0.04, 0.04, 0.04]),
        ...     as_of_date="2024-01-01",
        ...     curve_type="flat"
        ... )
        >>> curve.discount_factor(5.0)  # e^(-0.04 * 5)
        0.8187...
        """
        if t <= 0:
            return 1.0
        r = self.get_rate(t)
        return np.exp(-r * t)

    def forward_rate(self, t1: float, t2: float) -> float:
        """
        Calculate forward rate between t1 and t2.

        [T1] f(t₁,t₂) = (r(t₂)t₂ - r(t₁)t₁)/(t₂ - t₁)

        Parameters
        ----------
        t1 : float
            Start maturity
        t2 : float
            End maturity

        Returns
        -------
        float
            Forward rate

        Examples
        --------
        >>> curve = YieldCurve(
        ...     maturities=np.array([1, 2]),
        ...     rates=np.array([0.03, 0.04]),
        ...     as_of_date="2024-01-01",
        ...     curve_type="upward"
        ... )
        >>> curve.forward_rate(1.0, 2.0)  # 1-year forward 1 year from now
        0.05
        """
        if t2 <= t1:
            raise ValueError(f"t2 ({t2}) must be greater than t1 ({t1})")

        if t1 <= 0:
            # Spot rate to t2
            return self.get_rate(t2)

        r1 = self.get_rate(t1)
        r2 = self.get_rate(t2)

        return (r2 * t2 - r1 * t1) / (t2 - t1)

    def discount_factors(self, maturities: np.ndarray) -> np.ndarray:
        """
        Calculate discount factors for multiple maturities.

        Parameters
        ----------
        maturities : ndarray
            Array of maturities

        Returns
        -------
        ndarray
            Discount factors
        """
        return np.array([self.discount_factor(t) for t in maturities])

    def par_rate(self, maturity: float, frequency: int = 2) -> float:
        """
        Calculate par rate for given maturity.

        [T1] Par rate: coupon rate where bond prices at par.

        Parameters
        ----------
        maturity : float
            Bond maturity in years
        frequency : int
            Coupon frequency per year

        Returns
        -------
        float
            Par rate (annualized)
        """
        if maturity <= 0:
            raise ValueError(f"Maturity must be positive, got {maturity}")

        # Payment times
        n_payments = int(maturity * frequency)
        dt = 1.0 / frequency
        times = np.array([(i + 1) * dt for i in range(n_payments)])

        # Discount factors
        dfs = self.discount_factors(times)

        # Par rate: (1 - P(T)) / sum(P(ti)/frequency)
        pv_annuity = np.sum(dfs) / frequency
        final_df = dfs[-1]

        return (1 - final_df) / pv_annuity


@dataclass(frozen=True)
class NelsonSiegelParams:
    """
    Nelson-Siegel model parameters.

    [T1] y(τ) = β₀ + β₁(1-e^(-τ/λ))/(τ/λ) + β₂((1-e^(-τ/λ))/(τ/λ) - e^(-τ/λ))

    Attributes
    ----------
    beta0 : float
        Long-term level (asymptotic rate)
    beta1 : float
        Short-term component (slope)
    beta2 : float
        Medium-term component (curvature)
    tau : float
        Decay parameter (λ)
    """

    beta0: float
    beta1: float
    beta2: float
    tau: float

    def rate(self, t: float) -> float:
        """
        Calculate rate at maturity t using Nelson-Siegel.

        Parameters
        ----------
        t : float
            Maturity in years

        Returns
        -------
        float
            Zero rate
        """
        if t <= 0:
            return self.beta0 + self.beta1

        x = t / self.tau
        exp_term = np.exp(-x)
        term1 = (1 - exp_term) / x
        term2 = term1 - exp_term

        return self.beta0 + self.beta1 * term1 + self.beta2 * term2


class YieldCurveLoader:
    """
    Loads yield curves from various sources.

    Supports:
    - FRED Treasury curves (requires API key)
    - Nelson-Siegel construction
    - Custom curve points
    - Flat curves for testing

    Examples
    --------
    >>> loader = YieldCurveLoader()
    >>> curve = loader.from_nelson_siegel(beta0=0.04, beta1=-0.02, beta2=0.01, tau=2.0)
    >>> curve.get_rate(5.0)
    0.039...

    Validators: QuantLib, PyCurve
    See: docs/CROSS_VALIDATION_MATRIX.md
    """

    # Standard Treasury maturities (years)
    TREASURY_MATURITIES = np.array(
        [
            1 / 12,
            2 / 12,
            3 / 12,
            6 / 12,  # Bills
            1,
            2,
            3,
            5,
            7,
            10,
            20,
            30,  # Notes and bonds
        ]
    )

    # FRED series IDs for Treasury rates
    FRED_SERIES = {
        1 / 12: "DGS1MO",
        2 / 12: "DGS2MO",
        3 / 12: "DGS3MO",
        6 / 12: "DGS6MO",
        1: "DGS1",
        2: "DGS2",
        3: "DGS3",
        5: "DGS5",
        7: "DGS7",
        10: "DGS10",
        20: "DGS20",
        30: "DGS30",
    }

    def from_fred(
        self,
        as_of_date: str,
        api_key: str | None = None,
        maturities: np.ndarray | None = None,
    ) -> YieldCurve:
        """
        Load Treasury curve from FRED.

        Parameters
        ----------
        as_of_date : str
            Date in YYYY-MM-DD format
        api_key : str, optional
            FRED API key (or from FRED_API_KEY env var)
        maturities : ndarray, optional
            Specific maturities to load (default: all Treasury)

        Returns
        -------
        YieldCurve
            Treasury curve

        Examples
        --------
        >>> loader = YieldCurveLoader()
        >>> curve = loader.from_fred("2024-01-15")  # Requires FRED_API_KEY
        """
        import os

        api_key = api_key or os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError(
                "FRED API key required. Set FRED_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at fred.stlouisfed.org"
            )

        try:
            import pandas_datareader.data as web
        except ImportError as err:
            raise ImportError(
                "pandas-datareader required for FRED data. "
                "Install with: pip install pandas-datareader"
            ) from err

        maturities = maturities if maturities is not None else self.TREASURY_MATURITIES

        rates = []
        valid_maturities = []

        for mat in maturities:
            if mat not in self.FRED_SERIES:
                continue

            series_id = self.FRED_SERIES[mat]
            try:
                data = web.DataReader(series_id, "fred", as_of_date, as_of_date)
                if not data.empty and not np.isnan(data.iloc[0, 0]):
                    rate = data.iloc[0, 0] / 100  # Convert from percentage
                    rates.append(rate)
                    valid_maturities.append(mat)
            except Exception as e:
                # Log warning but continue - some maturities may be missing
                logger.warning(f"FRED fetch failed for {series_id} ({mat}Y): {e}")
                continue

        if len(rates) == 0:
            raise ValueError(f"No Treasury data available for {as_of_date}")

        return YieldCurve(
            maturities=np.array(valid_maturities),
            rates=np.array(rates),
            as_of_date=as_of_date,
            curve_type="treasury_fred",
        )

    def from_nelson_siegel(
        self,
        beta0: float,
        beta1: float,
        beta2: float,
        tau: float,
        as_of_date: str = "2024-01-01",
        maturities: np.ndarray | None = None,
    ) -> YieldCurve:
        """
        Construct Nelson-Siegel curve.

        [T1] y(τ) = β₀ + β₁(1-e^(-τ/λ))/(τ/λ) + β₂((1-e^(-τ/λ))/(τ/λ) - e^(-τ/λ))

        Parameters
        ----------
        beta0 : float
            Long-term level
        beta1 : float
            Short-term slope
        beta2 : float
            Curvature
        tau : float
            Decay parameter
        as_of_date : str
            Curve date
        maturities : ndarray, optional
            Maturities to evaluate (default: 0.25 to 30 years)

        Returns
        -------
        YieldCurve
            Nelson-Siegel curve

        Examples
        --------
        >>> loader = YieldCurveLoader()
        >>> curve = loader.from_nelson_siegel(0.04, -0.02, 0.01, 2.0)
        >>> curve.get_rate(10.0)
        0.039...
        """
        if tau <= 0:
            raise ValueError(f"Tau must be positive, got {tau}")

        params = NelsonSiegelParams(beta0=beta0, beta1=beta1, beta2=beta2, tau=tau)

        if maturities is None:
            maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30])

        rates = np.array([params.rate(t) for t in maturities])

        return YieldCurve(
            maturities=maturities,
            rates=rates,
            as_of_date=as_of_date,
            curve_type="nelson_siegel",
        )

    def from_points(
        self,
        maturities: np.ndarray,
        rates: np.ndarray,
        as_of_date: str = "2024-01-01",
        curve_type: str = "custom",
        interpolation: InterpolationMethod = InterpolationMethod.LINEAR,
    ) -> YieldCurve:
        """
        Create curve from explicit points.

        Parameters
        ----------
        maturities : ndarray
            Maturities in years
        rates : ndarray
            Zero rates (continuous compounding)
        as_of_date : str
            Curve date
        curve_type : str
            Description of curve
        interpolation : InterpolationMethod
            Interpolation method

        Returns
        -------
        YieldCurve
            Custom curve

        Examples
        --------
        >>> loader = YieldCurveLoader()
        >>> curve = loader.from_points(
        ...     maturities=np.array([1, 5, 10]),
        ...     rates=np.array([0.03, 0.04, 0.045])
        ... )
        """
        return YieldCurve(
            maturities=maturities,
            rates=rates,
            as_of_date=as_of_date,
            curve_type=curve_type,
            interpolation=interpolation,
        )

    def flat_curve(
        self,
        rate: float,
        as_of_date: str = "2024-01-01",
    ) -> YieldCurve:
        """
        Create flat yield curve.

        Parameters
        ----------
        rate : float
            Constant rate
        as_of_date : str
            Curve date

        Returns
        -------
        YieldCurve
            Flat curve

        Examples
        --------
        >>> loader = YieldCurveLoader()
        >>> curve = loader.flat_curve(0.04)
        >>> curve.get_rate(10.0)
        0.04
        """
        maturities = np.array([0.25, 1, 5, 10, 30])
        rates = np.full_like(maturities, rate)

        return YieldCurve(
            maturities=maturities,
            rates=rates,
            as_of_date=as_of_date,
            curve_type="flat",
        )

    def from_fixture(
        self,
        fixture_path: str,
        as_of_date: str | None = None,
    ) -> YieldCurve:
        """
        Load Treasury curve from CSV fixture file.

        [F.5] For deterministic testing without FRED API dependency.

        Parameters
        ----------
        fixture_path : str
            Path to CSV fixture file with columns: maturity, rate, series_id
        as_of_date : str, optional
            Override date (default: extracted from filename)

        Returns
        -------
        YieldCurve
            Treasury curve from fixture

        Examples
        --------
        >>> loader = YieldCurveLoader()
        >>> curve = loader.from_fixture("tests/fixtures/treasury_yields_2024_01_15.csv")
        """
        import csv
        from pathlib import Path

        path = Path(fixture_path)
        if not path.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

        maturities = []
        rates = []

        with open(path) as f:
            reader = csv.DictReader(filter(lambda row: not row.startswith("#"), f))
            for row in reader:
                maturities.append(float(row["maturity"]))
                rates.append(float(row["rate"]))

        if len(maturities) == 0:
            raise ValueError(f"No data in fixture file: {fixture_path}")

        # Extract date from filename if not provided
        if as_of_date is None:
            # Try to parse from filename like treasury_yields_2024_01_15.csv
            name = path.stem
            parts = name.split("_")
            if len(parts) >= 3:
                try:
                    year = parts[-3]
                    month = parts[-2]
                    day = parts[-1]
                    as_of_date = f"{year}-{month}-{day}"
                except (ValueError, IndexError):
                    as_of_date = "2024-01-01"
            else:
                as_of_date = "2024-01-01"

        return YieldCurve(
            maturities=np.array(maturities),
            rates=np.array(rates),
            as_of_date=as_of_date,
            curve_type="treasury_fixture",
        )

    def from_quantlib(
        self,
        as_of_date: str,
        market_quotes: list[tuple[float, float]],
    ) -> YieldCurve:
        """
        Build curve using QuantLib (if available).

        Parameters
        ----------
        as_of_date : str
            Curve date
        market_quotes : List[Tuple[float, float]]
            List of (maturity, rate) tuples

        Returns
        -------
        YieldCurve
            QuantLib-calibrated curve

        Notes
        -----
        Requires QuantLib: pip install QuantLib-Python
        """
        try:
            import QuantLib as ql
        except ImportError as err:
            raise ImportError(
                "QuantLib required for this method. Install with: pip install QuantLib-Python"
            ) from err

        # Parse date
        year, month, day = map(int, as_of_date.split("-"))
        eval_date = ql.Date(day, month, year)
        ql.Settings.instance().evaluationDate = eval_date

        # Build helpers
        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        day_count = ql.Actual365Fixed()

        helpers = []
        for maturity, rate in market_quotes:
            period = ql.Period(int(maturity * 12), ql.Months)
            helper = ql.DepositRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(rate)),
                period,
                2,  # Settlement days
                calendar,
                ql.ModifiedFollowing,
                False,
                day_count,
            )
            helpers.append(helper)

        # Build curve
        curve = ql.PiecewiseLogCubicDiscount(eval_date, helpers, day_count)
        curve.enableExtrapolation()

        # Extract points
        maturities = np.array([m for m, _ in market_quotes])
        rates = np.array([curve.zeroRate(m, ql.Continuous).rate() for m in maturities])

        return YieldCurve(
            maturities=maturities,
            rates=rates,
            as_of_date=as_of_date,
            curve_type="quantlib",
        )


def fit_nelson_siegel(
    maturities: np.ndarray,
    rates: np.ndarray,
    initial_guess: tuple[float, float, float, float] | None = None,
) -> NelsonSiegelParams:
    """
    Fit Nelson-Siegel parameters to market rates.

    [T1] Minimizes sum of squared errors between model and market rates.

    Parameters
    ----------
    maturities : ndarray
        Market maturities
    rates : ndarray
        Market rates
    initial_guess : tuple, optional
        Initial (beta0, beta1, beta2, tau)

    Returns
    -------
    NelsonSiegelParams
        Fitted parameters

    Examples
    --------
    >>> mats = np.array([1, 2, 5, 10, 30])
    >>> rates = np.array([0.03, 0.035, 0.04, 0.042, 0.045])
    >>> params = fit_nelson_siegel(mats, rates)
    >>> params.beta0
    0.045...
    """
    from scipy.optimize import minimize

    def objective(x: np.ndarray) -> float:
        beta0, beta1, beta2, tau = x
        if tau <= 0:
            return 1e10
        params = NelsonSiegelParams(beta0, beta1, beta2, tau)
        model_rates = np.array([params.rate(t) for t in maturities])
        return np.sum((model_rates - rates) ** 2)

    if initial_guess is None:
        # Smart initial guess
        beta0 = rates[-1]  # Long rate
        beta1 = rates[0] - rates[-1]  # Short - long
        beta2 = 0.0
        tau = 2.0
        initial_guess = (beta0, beta1, beta2, tau)

    result = minimize(
        objective,
        initial_guess,
        method="Nelder-Mead",
        options={"maxiter": 1000},
    )

    return NelsonSiegelParams(
        beta0=result.x[0],
        beta1=result.x[1],
        beta2=result.x[2],
        tau=abs(result.x[3]),
    )


def calculate_duration(
    curve: YieldCurve,
    cash_flows: np.ndarray,
    times: np.ndarray,
) -> float:
    """
    Calculate Macaulay duration.

    [T1] D = Σ(t × CF_t × P(t)) / Σ(CF_t × P(t))

    Parameters
    ----------
    curve : YieldCurve
        Discount curve
    cash_flows : ndarray
        Cash flow amounts
    times : ndarray
        Cash flow times

    Returns
    -------
    float
        Macaulay duration

    Examples
    --------
    >>> loader = YieldCurveLoader()
    >>> curve = loader.flat_curve(0.04)
    >>> cfs = np.array([5, 5, 5, 5, 105])  # 5% coupon bond
    >>> times = np.array([1, 2, 3, 4, 5])
    >>> calculate_duration(curve, cfs, times)
    4.45...
    """
    dfs = curve.discount_factors(times)
    pv_cfs = cash_flows * dfs
    total_pv = np.sum(pv_cfs)

    if total_pv <= 0:
        raise ValueError("Total PV must be positive")

    return np.sum(times * pv_cfs) / total_pv
