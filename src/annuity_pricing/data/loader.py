"""
WINK data loader with checksum verification.

NEVER fails silently - all errors are explicit. [T1: Defensive Programming]
See: CONSTITUTION.md Section 6.3
"""

import hashlib
from pathlib import Path
from typing import Optional

import pandas as pd

from annuity_pricing.config.settings import SETTINGS


class DataIntegrityError(Exception):
    """Raised when data checksum verification fails."""

    pass


class DataLoadError(Exception):
    """Raised when data loading fails."""

    pass


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
    path: Optional[Path] = None,
    verify: bool = True,
    columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Load WINK parquet data with optional checksum verification.

    Parameters
    ----------
    path : Path, optional
        Path to WINK parquet file. Defaults to SETTINGS.data.wink_path
    verify : bool, default True
        Whether to verify SHA-256 checksum before loading
    columns : list[str], optional
        Specific columns to load. None loads all columns.

    Returns
    -------
    pd.DataFrame
        WINK data with 62 columns, ~1M rows

    Raises
    ------
    DataIntegrityError
        If checksum verification fails
    DataLoadError
        If data loading fails
    ValueError
        If loaded data is empty

    Examples
    --------
    >>> df = load_wink_data()
    >>> len(df)
    1087253

    >>> df_myga = load_wink_data(columns=['companyName', 'productGroup', 'fixedRate'])
    """
    file_path = path or SETTINGS.data.wink_path

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

    df = load_wink_data(verify=verify)

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
