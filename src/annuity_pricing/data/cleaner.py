"""
WINK data cleaning functions.

Handles outliers and data quality issues identified in gap reports.
See: wink-research-archive/gap-reports/gap-report-round2.md
"""

import numpy as np
import pandas as pd

from annuity_pricing.config.settings import SETTINGS


def clip_cap_rate(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Clip capRate outliers to maximum value.

    [T2] WINK has capRate max=9999.99 which are data entry errors.
    Clip to ≤ 10.0 (1000%) per METHODOLOGY.md Section 6.1.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'capRate' column
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        DataFrame with clipped capRate
    """
    if not inplace:
        df = df.copy()

    if "capRate" in df.columns:
        df["capRate"] = df["capRate"].clip(upper=SETTINGS.data.cap_rate_max)

    return df


def clip_performance_triggered_rate(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Clip performanceTriggeredRate outliers to maximum value.

    [T2] WINK has performanceTriggeredRate max=999 which are errors.
    Clip to ≤ 1.0 (100%) per METHODOLOGY.md Section 6.1.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'performanceTriggeredRate' column
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        DataFrame with clipped performanceTriggeredRate
    """
    if not inplace:
        df = df.copy()

    if "performanceTriggeredRate" in df.columns:
        df["performanceTriggeredRate"] = df["performanceTriggeredRate"].clip(
            upper=SETTINGS.data.performance_triggered_max
        )

    return df


def clip_spread_rate(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Clip spreadRate outliers to maximum value.

    [T2] WINK has spreadRate max=99.0 which are errors.
    Clip to ≤ 1.0 (100%) per METHODOLOGY.md Section 6.1.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'spreadRate' column
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        DataFrame with clipped spreadRate
    """
    if not inplace:
        df = df.copy()

    if "spreadRate" in df.columns:
        df["spreadRate"] = df["spreadRate"].clip(upper=SETTINGS.data.spread_rate_max)

    return df


def filter_valid_guarantee_duration(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Filter out invalid guaranteeDuration values.

    [T2] WINK has guaranteeDuration=-1 which are invalid.
    Filter to ≥ 0 per METHODOLOGY.md Section 6.1.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'guaranteeDuration' column
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        DataFrame with valid guaranteeDuration only
    """
    if "guaranteeDuration" not in df.columns:
        return df if inplace else df.copy()

    mask = df["guaranteeDuration"] >= SETTINGS.data.guarantee_duration_min

    if inplace:
        # Can't truly modify in place with filtering, return filtered
        return df[mask]
    else:
        return df[mask].copy()


def coerce_mva_nulls(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Coerce 'None' strings in mva column to actual null values.

    [T2] WINK has 'mva' column with "None" strings that should be null.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'mva' column
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        DataFrame with proper null values in mva
    """
    if not inplace:
        df = df.copy()

    if "mva" in df.columns:
        df["mva"] = df["mva"].replace("None", np.nan)

    return df


def clean_wink_data(
    df: pd.DataFrame,
    clip_outliers: bool = True,
    filter_duration: bool = True,
    coerce_nulls: bool = True,
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Apply all WINK data cleaning steps.

    Parameters
    ----------
    df : pd.DataFrame
        Raw WINK DataFrame
    clip_outliers : bool, default True
        Whether to clip rate outliers
    filter_duration : bool, default True
        Whether to filter invalid guaranteeDuration
    coerce_nulls : bool, default True
        Whether to coerce 'None' strings to null
    inplace : bool, default False
        Whether to modify in place

    Returns
    -------
    pd.DataFrame
        Cleaned WINK DataFrame

    Examples
    --------
    >>> df_raw = load_wink_data()
    >>> df_clean = clean_wink_data(df_raw)
    >>> df_clean['capRate'].max() <= 10.0
    True
    """
    if not inplace:
        df = df.copy()

    # Clip outliers
    if clip_outliers:
        df = clip_cap_rate(df, inplace=True)
        df = clip_performance_triggered_rate(df, inplace=True)
        df = clip_spread_rate(df, inplace=True)

    # Filter invalid values
    if filter_duration:
        df = filter_valid_guarantee_duration(df, inplace=False)

    # Coerce nulls
    if coerce_nulls:
        df = coerce_mva_nulls(df, inplace=True)

    return df


def get_cleaning_summary(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> dict:
    """
    Generate summary of cleaning operations.

    Parameters
    ----------
    df_raw : pd.DataFrame
        Raw DataFrame before cleaning
    df_clean : pd.DataFrame
        DataFrame after cleaning

    Returns
    -------
    dict
        Summary statistics
    """
    summary = {
        "rows_before": len(df_raw),
        "rows_after": len(df_clean),
        "rows_removed": len(df_raw) - len(df_clean),
        "removal_pct": (len(df_raw) - len(df_clean)) / len(df_raw) * 100,
    }

    # Check specific columns
    if "capRate" in df_raw.columns:
        summary["cap_rate_clipped"] = (df_raw["capRate"] > SETTINGS.data.cap_rate_max).sum()

    if "performanceTriggeredRate" in df_raw.columns:
        summary["perf_triggered_clipped"] = (
            df_raw["performanceTriggeredRate"] > SETTINGS.data.performance_triggered_max
        ).sum()

    if "spreadRate" in df_raw.columns:
        summary["spread_rate_clipped"] = (
            df_raw["spreadRate"] > SETTINGS.data.spread_rate_max
        ).sum()

    if "guaranteeDuration" in df_raw.columns:
        summary["invalid_duration_filtered"] = (
            df_raw["guaranteeDuration"] < SETTINGS.data.guarantee_duration_min
        ).sum()

    return summary
