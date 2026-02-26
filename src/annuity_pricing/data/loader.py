"""
WINK data loader with checksum verification and SyntheticProvider.

NEVER fails silently - all errors are explicit. [T1: Defensive Programming]
See: METHODOLOGY.md Section 6.3

SyntheticProvider (Phase 0 of Julia port plan):
- Library default: ERROR if WINK path not configured (never fail silently)
- Test/docs default: SYNTHETIC via explicit use_synthetic=True or env var
- Set ANNUITY_USE_SYNTHETIC=1 for CI/testing
"""

import hashlib
import logging
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from annuity_pricing.config.settings import SETTINGS


def _use_synthetic_default() -> bool:
    """
    Check if synthetic data should be used by default.

    Returns True only if ANNUITY_USE_SYNTHETIC environment variable is set.
    Library code should NEVER silently fall back to synthetic.
    """
    return os.environ.get("ANNUITY_USE_SYNTHETIC", "").lower() in ("1", "true", "yes")


class DataIntegrityError(Exception):
    """Raised when data checksum verification fails."""

    pass


class DataLoadError(Exception):
    """Raised when data loading fails."""

    pass


class SyntheticDataWarning(UserWarning):
    """Warning issued when synthetic data is being used."""

    pass


# =============================================================================
# SyntheticProvider - Generates synthetic annuity data for testing
# =============================================================================


class SyntheticProvider:
    """
    Generate synthetic annuity product data for testing and CI.

    This provider creates realistic-looking but entirely synthetic data
    that can be used for testing, documentation, and CI pipelines without
    requiring access to licensed WINK data.

    ⚠️ SYNTHETIC DATA - NOT FOR PRODUCTION USE

    Usage
    -----
    >>> provider = SyntheticProvider(seed=42)
    >>> df = provider.generate_products(n_products=100)
    >>> df['productGroup'].value_counts()

    Environment Variable
    --------------------
    Set ANNUITY_USE_SYNTHETIC=1 to enable synthetic data in load_wink_data().
    """

    # Company names (synthetic)
    COMPANIES = [
        "Alpha Life Insurance",
        "Beta Annuity Corp",
        "Gamma Financial",
        "Delta Insurance Co",
        "Epsilon Life",
        "Zeta Retirement Services",
        "Eta Annuity Group",
        "Theta Life Insurance",
        "Iota Financial Services",
        "Kappa Retirement Corp",
    ]

    # Indices used for FIA/RILA
    INDICES = [
        "S&P 500",
        "Russell 2000",
        "NASDAQ-100",
        "MSCI EAFE",
        "DJIA",
    ]

    # Crediting methods
    CREDITING_METHODS = [
        "Annual Point to Point",
        "Monthly Average",
        "Monthly Point to Point",
        "Performance Triggered",
    ]

    def __init__(self, seed: int = 42):
        """
        Initialize SyntheticProvider with random seed for reproducibility.

        Parameters
        ----------
        seed : int
            Random seed for reproducible synthetic data generation
        """
        self.rng = np.random.default_rng(seed)
        self._synthetic_marker = True  # Flag for downstream consumers

    def generate_products(
        self,
        n_products: int = 100,
        product_groups: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Generate synthetic annuity product data.

        Parameters
        ----------
        n_products : int
            Number of products to generate
        product_groups : list[str], optional
            Product types to include. Default: ['MYGA', 'FIA', 'RILA']

        Returns
        -------
        pd.DataFrame
            Synthetic product data matching WINK schema
        """
        if product_groups is None:
            product_groups = ["MYGA", "FIA", "RILA"]

        records = []
        for i in range(n_products):
            product_group = self.rng.choice(product_groups)
            record = self._generate_product_record(i, product_group)
            records.append(record)

        df = pd.DataFrame(records)

        # Add metadata column to identify synthetic data
        df["_synthetic"] = True

        return df

    def _generate_product_record(self, idx: int, product_group: str) -> dict:
        """Generate a single product record based on product type."""
        base_record = {
            "companyName": self.rng.choice(self.COMPANIES),
            "productName": f"Synthetic {product_group} Product {idx}",
            "productGroup": product_group,
            "status": self.rng.choice(["current", "historic"], p=[0.8, 0.2]),
            "effectiveDate": date(
                2020 + self.rng.integers(0, 5),
                self.rng.integers(1, 13),
                self.rng.integers(1, 29),
            ),
            "surrChargeDuration": self.rng.integers(3, 11),
            "mva": self.rng.choice(["Y", "N"], p=[0.3, 0.7]),
        }

        if product_group == "MYGA":
            base_record.update(self._generate_myga_fields())
        elif product_group == "FIA":
            base_record.update(self._generate_fia_fields())
        elif product_group == "RILA":
            base_record.update(self._generate_rila_fields())

        return base_record

    def _generate_myga_fields(self) -> dict:
        """Generate MYGA-specific fields."""
        guarantee_duration = self.rng.integers(3, 11)
        return {
            "fixedRate": round(self.rng.uniform(0.03, 0.06), 4),
            "guaranteeDuration": guarantee_duration,
            "effectiveYield": round(self.rng.uniform(0.025, 0.055), 4),
            "premiumBand": self.rng.choice(["$10K-$100K", "$100K-$250K", "$250K+"]),
            # FIA/RILA fields as None
            "capRate": None,
            "participationRate": None,
            "spreadRate": None,
            "performanceTriggeredRate": None,
            "bufferRate": None,
            "bufferModifier": None,
            "indexUsed": None,
            "indexingMethod": None,
            "termYears": guarantee_duration,
        }

    def _generate_fia_fields(self) -> dict:
        """Generate FIA-specific fields."""
        crediting_method = self.rng.choice(self.CREDITING_METHODS)
        term_years = self.rng.integers(1, 7)

        fields = {
            "indexUsed": self.rng.choice(self.INDICES),
            "indexingMethod": crediting_method,
            "indexCreditingFrequency": "Annual",
            "termYears": term_years,
            # MYGA fields as None
            "fixedRate": None,
            "guaranteeDuration": None,
            "effectiveYield": None,
            "premiumBand": None,
            # RILA fields as None
            "bufferRate": None,
            "bufferModifier": None,
        }

        # Different crediting structures
        if crediting_method == "Performance Triggered":
            fields["capRate"] = None
            fields["participationRate"] = None
            fields["spreadRate"] = None
            fields["performanceTriggeredRate"] = round(self.rng.uniform(0.03, 0.08), 4)
        elif self.rng.random() < 0.5:
            # Cap-based
            fields["capRate"] = round(self.rng.uniform(0.05, 0.15), 4)
            fields["participationRate"] = 1.0
            fields["spreadRate"] = None
            fields["performanceTriggeredRate"] = None
        else:
            # Participation-based
            fields["capRate"] = None
            fields["participationRate"] = round(self.rng.uniform(0.20, 0.60), 2)
            fields["spreadRate"] = round(self.rng.uniform(0.0, 0.03), 4)
            fields["performanceTriggeredRate"] = None

        return fields

    def _generate_rila_fields(self) -> dict:
        """Generate RILA-specific fields."""
        # Buffer vs Floor (mutually exclusive in most products)
        is_buffer = self.rng.random() < 0.7

        fields = {
            "indexUsed": self.rng.choice(self.INDICES),
            "indexingMethod": "Annual Point to Point",
            "indexCreditingFrequency": "Annual",
            "termYears": self.rng.choice([1, 3, 6]),
            "capRate": round(self.rng.uniform(0.10, 0.25), 4),
            "participationRate": round(self.rng.uniform(0.80, 1.20), 2),
            "spreadRate": None,
            "performanceTriggeredRate": None,
            # MYGA fields as None
            "fixedRate": None,
            "guaranteeDuration": None,
            "effectiveYield": None,
            "premiumBand": None,
        }

        if is_buffer:
            fields["bufferRate"] = self.rng.choice([0.10, 0.15, 0.20])
            fields["bufferModifier"] = "Losses Covered Up To"  # Buffer
        else:
            fields["bufferRate"] = self.rng.choice([0.10, 0.15, 0.20])
            fields["bufferModifier"] = "Losses Covered After"  # Floor

        return fields

    def generate_rates(self, n_days: int = 252) -> pd.DataFrame:
        """
        Generate synthetic market rate data (Treasury curves, VIX).

        Parameters
        ----------
        n_days : int
            Number of trading days to generate

        Returns
        -------
        pd.DataFrame
            Synthetic rate data with columns: date, DTB3, DGS1, DGS5, DGS10, DGS30, VIX
        """
        dates = pd.date_range(end=date.today(), periods=n_days, freq="B")

        # Generate correlated rate curves
        base_rate = 0.04 + self.rng.normal(0, 0.005, n_days).cumsum() * 0.01

        data = {
            "date": dates,
            "DTB3": np.clip(base_rate - 0.01 + self.rng.normal(0, 0.001, n_days), 0.001, 0.10),
            "DGS1": np.clip(base_rate - 0.005 + self.rng.normal(0, 0.001, n_days), 0.001, 0.10),
            "DGS5": np.clip(base_rate + self.rng.normal(0, 0.001, n_days), 0.001, 0.12),
            "DGS10": np.clip(base_rate + 0.005 + self.rng.normal(0, 0.001, n_days), 0.001, 0.12),
            "DGS30": np.clip(base_rate + 0.01 + self.rng.normal(0, 0.001, n_days), 0.001, 0.15),
            "VIX": np.clip(18 + self.rng.normal(0, 3, n_days).cumsum() * 0.1, 10, 80),
            "_synthetic": True,
        }

        return pd.DataFrame(data)


# Global synthetic provider instance (lazy initialization)
_SYNTHETIC_PROVIDER: SyntheticProvider | None = None


def get_synthetic_provider(seed: int = 42) -> SyntheticProvider:
    """Get or create the global SyntheticProvider instance."""
    global _SYNTHETIC_PROVIDER
    if _SYNTHETIC_PROVIDER is None:
        _SYNTHETIC_PROVIDER = SyntheticProvider(seed=seed)
    return _SYNTHETIC_PROVIDER


# =============================================================================
# Checksum utilities
# =============================================================================


def compute_sha256(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Parameters
    ----------
    file_path : Path
        Path to file

    Returns
    -------
    str
        Hexadecimal SHA-256 hash

    Raises
    ------
    FileNotFoundError
        If file does not exist
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"CRITICAL: File not found: {file_path}. "
            f"Expected WINK data at this location."
        )

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def verify_checksum(file_path: Path, expected_checksum: str) -> None:
    """
    Verify file integrity via SHA-256 checksum.

    Parameters
    ----------
    file_path : Path
        Path to file
    expected_checksum : str
        Expected SHA-256 hash

    Raises
    ------
    DataIntegrityError
        If checksum does not match
    """
    actual_checksum = compute_sha256(file_path)

    if actual_checksum != expected_checksum:
        raise DataIntegrityError(
            f"CRITICAL: Checksum mismatch for {file_path}.\n"
            f"Expected: {expected_checksum}\n"
            f"Actual:   {actual_checksum}\n"
            f"Data may be corrupted or modified."
        )


def load_wink_data(
    path: Path | None = None,
    verify: bool = True,
    columns: list[str] | None = None,
    use_synthetic: bool | None = None,
    n_synthetic: int = 1000,
) -> pd.DataFrame:
    """
    Load WINK parquet data with optional checksum verification.

    Supports synthetic data for testing/CI via explicit opt-in.

    Parameters
    ----------
    path : Path, optional
        Path to WINK parquet file. Defaults to SETTINGS.data.wink_path
    verify : bool, default True
        Whether to verify SHA-256 checksum before loading
    columns : list[str], optional
        Specific columns to load. None loads all columns.
    use_synthetic : bool, optional
        If True, return synthetic data instead of WINK.
        If None (default), check ANNUITY_USE_SYNTHETIC env var.
        Library default is False (strict mode).
    n_synthetic : int, default 1000
        Number of synthetic products to generate if use_synthetic=True.

    Returns
    -------
    pd.DataFrame
        WINK data with 62 columns, ~1M rows (or synthetic equivalent)

    Raises
    ------
    DataIntegrityError
        If checksum verification fails
    DataLoadError
        If data loading fails
    ValueError
        If loaded data is empty
    FileNotFoundError
        If WINK file not found and synthetic not enabled

    Examples
    --------
    >>> df = load_wink_data()  # Requires WINK file or ANNUITY_USE_SYNTHETIC=1
    >>> len(df)
    1087253

    >>> df_synthetic = load_wink_data(use_synthetic=True)  # Explicit synthetic
    >>> "_synthetic" in df_synthetic.columns
    True

    >>> # For CI: export ANNUITY_USE_SYNTHETIC=1
    >>> df = load_wink_data()  # Will use synthetic if env var set
    """
    import warnings

    # Determine if synthetic should be used
    if use_synthetic is None:
        use_synthetic = _use_synthetic_default()

    # Synthetic data path
    if use_synthetic:
        warnings.warn(
            "Using SYNTHETIC data. Results are for testing only, not production use.",
            SyntheticDataWarning,
            stacklevel=2,
        )
        provider = get_synthetic_provider()
        df = provider.generate_products(n_products=n_synthetic)

        # Filter columns if requested
        if columns:
            available = [c for c in columns if c in df.columns]
            df = df[available + ["_synthetic"]]

        return df

    # Real WINK data path
    file_path = path or SETTINGS.data.wink_path

    # Check if file exists BEFORE checksum (clearer error)
    if not file_path.exists():
        raise FileNotFoundError(
            f"CRITICAL: WINK data file not found at {file_path}.\n"
            f"Options:\n"
            f"  1. Set WINK_PATH environment variable to your WINK parquet file\n"
            f"  2. Set ANNUITY_USE_SYNTHETIC=1 for testing with synthetic data\n"
            f"  3. Use load_wink_data(use_synthetic=True) explicitly"
        )

    # Verify checksum if requested
    if verify:
        verify_checksum(file_path, SETTINGS.data.wink_checksum)

    # Load data
    try:
        if columns:
            df = pd.read_parquet(file_path, columns=columns)
        else:
            df = pd.read_parquet(file_path)
    except Exception as e:
        raise DataLoadError(
            f"CRITICAL: Failed to load WINK data from {file_path}. "
            f"Error: {e}"
        ) from e

    # NEVER return empty data silently [T1]
    if df.empty:
        raise ValueError(
            f"CRITICAL: WINK data is empty after loading from {file_path}. "
            f"Expected ~1M rows."
        )

    return df


def load_wink_by_product(
    product_group: str,
    status: str = "current",
    verify: bool = True,
    use_synthetic: bool | None = None,
) -> pd.DataFrame:
    """
    Load WINK data filtered by product group and status.

    Parameters
    ----------
    product_group : str
        One of: 'MYGA', 'FIA', 'RILA', 'FA', 'IVA'
    status : str, default 'current'
        One of: 'current', 'historic', 'nlam', 'new'
    verify : bool, default True
        Whether to verify checksum
    use_synthetic : bool, optional
        If True, return synthetic data. See load_wink_data for details.

    Returns
    -------
    pd.DataFrame
        Filtered WINK data

    Raises
    ------
    ValueError
        If product_group is invalid or result is empty

    Examples
    --------
    >>> df_myga = load_wink_by_product('MYGA')
    >>> df_myga['productGroup'].unique()
    array(['MYGA'], dtype=object)
    """
    valid_products = {"MYGA", "FIA", "RILA", "FA", "IVA"}
    if product_group not in valid_products:
        raise ValueError(
            f"CRITICAL: Invalid product_group '{product_group}'. "
            f"Must be one of: {valid_products}"
        )

    valid_statuses = {"current", "historic", "nlam", "new", "market_status"}
    if status not in valid_statuses:
        raise ValueError(
            f"CRITICAL: Invalid status '{status}'. "
            f"Must be one of: {valid_statuses}"
        )

    df = load_wink_data(verify=verify, use_synthetic=use_synthetic)

    # Filter
    mask = (df["productGroup"] == product_group) & (df["status"] == status)
    result = df[mask].copy()

    # NEVER return empty data silently [T1]
    if result.empty:
        raise ValueError(
            f"CRITICAL: No data found for productGroup='{product_group}', "
            f"status='{status}'. Check filter criteria."
        )

    return result
