"""
Frozen configuration settings for actuarial pricing.

All configuration is immutable (frozen dataclasses) to ensure reproducibility.
See: CONSTITUTION.md for methodology specifications.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


# =============================================================================
# Data Configuration
# =============================================================================

@dataclass(frozen=True)
class DataConfig:
    """
    Immutable data configuration. [T1: Best Practice]

    Attributes
    ----------
    wink_path : Path
        Path to WINK parquet file
    wink_checksum : str
        SHA-256 checksum for data integrity verification
    """

    wink_path: Path = Path(__file__).parent.parent.parent.parent / "data" / "raw" / "wink.parquet"
    wink_checksum: str = "5b1ae9e712544c55099b4e7a91dd725955e310d36cfaa9d6665f46459a40cc9a"

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
    fred_series: Tuple[str, ...] = (
        "DTB3",    # 3-month T-bill
        "DGS1",    # 1-year Treasury
        "DGS2",    # 2-year Treasury
        "DGS5",    # 5-year Treasury
        "DGS10",   # 10-year Treasury
        "DGS30",   # 30-year Treasury
        "SOFR",    # Secured Overnight Financing Rate
        "VIXCLS",  # VIX (implied vol proxy)
    )

    # Index tickers for Yahoo Finance [T2]
    index_tickers: Tuple[str, ...] = (
        "^GSPC",   # S&P 500
        "^RUT",    # Russell 2000
        "^NDX",    # NASDAQ-100
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
    """

    # Monte Carlo parameters [T3: Assumptions]
    mc_paths: int = 100_000  # Convergence to ~0.1%
    mc_seed: int = 42  # Reproducibility
    trading_days_per_year: int = 252  # [T1]

    # Convergence tolerance [T1]
    bs_mc_tolerance: float = 0.01  # 1% relative error for vanilla

    # No-arbitrage bounds tolerance [T1]
    arbitrage_tolerance: float = 1e-6

    # Put-call parity tolerance [T1]
    put_call_parity_tolerance: float = 0.01


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
    common_buffer_rates: Tuple[float, ...] = (0.10, 0.15, 0.20)

    # Common floor levels [T2: From WINK]
    common_floor_rates: Tuple[float, ...] = (0.10, 0.15, 0.20)


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
