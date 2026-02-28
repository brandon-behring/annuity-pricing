"""
Frozen configuration settings for actuarial pricing.

All configuration is immutable (frozen dataclasses) to ensure reproducibility.
See: METHODOLOGY.md for methodology specifications.
See: docs/TOLERANCE_JUSTIFICATION.md for tolerance derivations.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Import centralized tolerances
from annuity_pricing.config.tolerances import (
    ANTI_PATTERN_TOLERANCE,
    BS_MC_CONVERGENCE_TOLERANCE,
    PUT_CALL_PARITY_TOLERANCE,
)

# =============================================================================
# Data Configuration
# =============================================================================


def _resolve_wink_path() -> Path:
    """
    Resolve WINK data file path with environment variable override.

    Priority:
    1. WINK_PATH environment variable (if set)
    2. Default: wink.parquet in project root

    Returns
    -------
    Path
        Resolved path to WINK parquet file
    """
    env_path = os.environ.get("WINK_PATH")
    if env_path:
        return Path(env_path)
    # Default to project root (where scripts/Makefile expect it)
    return Path(__file__).parent.parent.parent.parent / "wink.parquet"


@dataclass(frozen=True)
class DataConfig:
    """
    Immutable data configuration. [T1: Best Practice]

    Attributes
    ----------
    wink_path : Path
        Path to WINK parquet file. Override with WINK_PATH environment variable.
    wink_checksum : str
        SHA-256 checksum for data integrity verification
    """

    wink_path: Path = None  # type: ignore[assignment]  # Set in __post_init__
    wink_checksum: str = "5b1ae9e712544c55099b4e7a91dd725955e310d36cfaa9d6665f46459a40cc9a"

    def __post_init__(self) -> None:
        """Initialize wink_path using resolver function."""
        # Frozen dataclass workaround: use object.__setattr__
        if self.wink_path is None:
            object.__setattr__(self, "wink_path", _resolve_wink_path())

    # Data quality thresholds [T2: From gap reports]
    cap_rate_max: float = 10.0  # Clip capRate to ≤ 10.0 (1000%)
    performance_triggered_max: float = 1.0  # Clip to ≤ 1.0 (100%)
    spread_rate_max: float = 1.0  # Clip to ≤ 1.0 (100%)
    guarantee_duration_min: int = 0  # Filter guaranteeDuration >= 0


# =============================================================================
# Market Data Configuration
# =============================================================================


@dataclass(frozen=True)
class MarketDataConfig:
    """
    Immutable market data configuration.

    Attributes
    ----------
    fred_series : Tuple[str, ...]
        FRED series IDs for Treasury curves and VIX
    index_tickers : Tuple[str, ...]
        Yahoo Finance tickers for equity indices
    """

    # FRED series for rates [T1]
    fred_series: tuple[str, ...] = (
        "DTB3",  # 3-month T-bill
        "DGS1",  # 1-year Treasury
        "DGS2",  # 2-year Treasury
        "DGS5",  # 5-year Treasury
        "DGS10",  # 10-year Treasury
        "DGS30",  # 30-year Treasury
        "SOFR",  # Secured Overnight Financing Rate
        "VIXCLS",  # VIX (implied vol proxy)
    )

    # Index tickers for Yahoo Finance [T2]
    index_tickers: tuple[str, ...] = (
        "^GSPC",  # S&P 500
        "^RUT",  # Russell 2000
        "^NDX",  # NASDAQ-100
        "^STOXX50E",  # Euro Stoxx 50
    )

    # Stooq backup URLs (fallback if Yahoo fails)
    stooq_base_url: str = "https://stooq.com/q/d/l/"


# =============================================================================
# Option Pricing Configuration
# =============================================================================


@dataclass(frozen=True)
class OptionConfig:
    """
    Immutable option pricing configuration. [T1: Academic standard]

    Attributes
    ----------
    mc_paths : int
        Number of Monte Carlo paths
    mc_seed : int
        Random seed for reproducibility
    trading_days_per_year : int
        Number of trading days in a year

    Note
    ----
    Tolerances are now centralized in config/tolerances.py.
    See docs/TOLERANCE_JUSTIFICATION.md for derivations.
    """

    # Monte Carlo parameters [T3: Assumptions]
    mc_paths: int = 100_000  # Convergence to ~0.1%
    mc_seed: int = 42  # Reproducibility
    trading_days_per_year: int = 252  # [T1]

    # Tolerances from centralized module (see docs/TOLERANCE_JUSTIFICATION.md)
    # These are kept here for backward compatibility but should be accessed
    # directly from tolerances.py in new code.
    bs_mc_tolerance: float = BS_MC_CONVERGENCE_TOLERANCE  # Was 0.01, now from tolerances
    arbitrage_tolerance: float = ANTI_PATTERN_TOLERANCE  # Was 1e-6, now 1e-10
    put_call_parity_tolerance: float = PUT_CALL_PARITY_TOLERANCE  # Was 0.01, now 1e-8


# =============================================================================
# MYGA Configuration
# =============================================================================


@dataclass(frozen=True)
class MYGAConfig:
    """
    Immutable MYGA pricing configuration.

    Attributes
    ----------
    mgsv_base_rate : float
        NAIC statutory minimum factor (87.5%) [T1]
    mgsv_rate_default : float
        Default MGSV interest rate [T1]
    """

    mgsv_base_rate: float = 0.875  # 87.5% [T1: NAIC law]
    mgsv_rate_default: float = 0.01  # 1% default [T3]


# =============================================================================
# FIA/RILA Configuration
# =============================================================================


@dataclass(frozen=True)
class IndexedAnnuityConfig:
    """
    Immutable FIA/RILA pricing configuration.

    Attributes
    ----------
    option_budget_default : float
        Default option budget as % of assets [T3: Assumption]
    """

    # Option budget assumption [T3]
    option_budget_default: float = 0.03  # 3% of assets annually

    # Common buffer levels [T2: From WINK]
    common_buffer_rates: tuple[float, ...] = (0.10, 0.15, 0.20)

    # Common floor levels [T2: From WINK]
    common_floor_rates: tuple[float, ...] = (0.10, 0.15, 0.20)


# =============================================================================
# Validation Configuration
# =============================================================================


@dataclass(frozen=True)
class ValidationConfig:
    """
    Immutable validation configuration.

    Attributes
    ----------
    halt_on_arbitrage : bool
        Whether to HALT on arbitrage violations
    """

    halt_on_arbitrage: bool = True  # [T1]
    halt_on_parity_violation: bool = True  # [T1]
    halt_on_negative_fia_payoff: bool = True  # [T1]

    # Implied vol bounds [T2]
    implied_vol_min: float = 0.0
    implied_vol_max: float = 2.0  # 200% annual vol


# =============================================================================
# Master Configuration
# =============================================================================


@dataclass(frozen=True)
class Settings:
    """
    Master frozen configuration combining all sub-configs.

    Usage
    -----
    >>> from annuity_pricing.config.settings import SETTINGS
    >>> SETTINGS.data.wink_path
    """

    data: DataConfig = DataConfig()
    market: MarketDataConfig = MarketDataConfig()
    option: OptionConfig = OptionConfig()
    myga: MYGAConfig = MYGAConfig()
    indexed: IndexedAnnuityConfig = IndexedAnnuityConfig()
    validation: ValidationConfig = ValidationConfig()


# Singleton instance - import this
SETTINGS = Settings()
