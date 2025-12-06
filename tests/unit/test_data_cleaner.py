"""
Tests for WINK data cleaning functionality.

Tests cover:
- Outlier clipping (cap_rate, performance_triggered_rate, spread_rate)
- Invalid duration filtering
- Null value coercion
- Cleaning summary generation
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from annuity_pricing.config.settings import SETTINGS
from annuity_pricing.data.cleaner import (
    clean_wink_data,
    clip_cap_rate,
    clip_performance_triggered_rate,
    clip_spread_rate,
    coerce_mva_nulls,
    filter_valid_guarantee_duration,
    get_cleaning_summary,
)


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PARQUET = FIXTURES_DIR / "wink_sample.parquet"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load sample WINK fixture."""
    return pd.read_parquet(SAMPLE_PARQUET)


@pytest.fixture
def df_with_outliers() -> pd.DataFrame:
    """Create DataFrame with known outliers for testing."""
    return pd.DataFrame(
        {
            "companyName": ["A", "B", "C", "D", "E"],
            "capRate": [0.05, 0.10, 9999.99, 15.0, 0.08],  # Outliers at idx 2, 3
            "performanceTriggeredRate": [0.5, 999.0, 0.8, 0.3, 0.7],  # Outlier at idx 1
            "spreadRate": [0.02, 0.03, 99.0, 0.01, 0.05],  # Outlier at idx 2
            "guaranteeDuration": [5, 7, -1, 10, 3],  # Invalid at idx 2
            "mva": ["Yes", "None", "No", "None", "Yes"],  # 'None' strings at idx 1, 3
            "status": ["current"] * 5,
        }
    )


# =============================================================================
# Clip Cap Rate Tests
# =============================================================================

class TestClipCapRate:
    """Tests for clip_cap_rate function."""

    def test_clips_high_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should clip capRate values above threshold."""
        result = clip_cap_rate(df_with_outliers)

        assert result["capRate"].max() <= SETTINGS.data.cap_rate_max
        assert result.loc[2, "capRate"] == SETTINGS.data.cap_rate_max
        assert result.loc[3, "capRate"] == SETTINGS.data.cap_rate_max

    def test_preserves_valid_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should not modify valid values."""
        result = clip_cap_rate(df_with_outliers)

        assert result.loc[0, "capRate"] == 0.05
        assert result.loc[1, "capRate"] == 0.10
        assert result.loc[4, "capRate"] == 0.08

    def test_does_not_modify_original_by_default(
        self, df_with_outliers: pd.DataFrame
    ) -> None:
        """Should return copy, not modify original."""
        original_value = df_with_outliers.loc[2, "capRate"]
        clip_cap_rate(df_with_outliers)

        assert df_with_outliers.loc[2, "capRate"] == original_value

    def test_modifies_inplace_when_requested(
        self, df_with_outliers: pd.DataFrame
    ) -> None:
        """Should modify in place when inplace=True."""
        clip_cap_rate(df_with_outliers, inplace=True)

        assert df_with_outliers.loc[2, "capRate"] == SETTINGS.data.cap_rate_max

    def test_handles_missing_column(self) -> None:
        """Should handle DataFrame without capRate column."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = clip_cap_rate(df)

        assert "other_col" in result.columns
        assert len(result) == 3


# =============================================================================
# Clip Performance Triggered Rate Tests
# =============================================================================

class TestClipPerformanceTriggeredRate:
    """Tests for clip_performance_triggered_rate function."""

    def test_clips_high_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should clip performanceTriggeredRate values above threshold."""
        result = clip_performance_triggered_rate(df_with_outliers)

        assert result["performanceTriggeredRate"].max() <= SETTINGS.data.performance_triggered_max
        assert result.loc[1, "performanceTriggeredRate"] == SETTINGS.data.performance_triggered_max

    def test_preserves_valid_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should not modify valid values."""
        result = clip_performance_triggered_rate(df_with_outliers)

        assert result.loc[0, "performanceTriggeredRate"] == 0.5
        assert result.loc[2, "performanceTriggeredRate"] == 0.8


# =============================================================================
# Clip Spread Rate Tests
# =============================================================================

class TestClipSpreadRate:
    """Tests for clip_spread_rate function."""

    def test_clips_high_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should clip spreadRate values above threshold."""
        result = clip_spread_rate(df_with_outliers)

        assert result["spreadRate"].max() <= SETTINGS.data.spread_rate_max
        assert result.loc[2, "spreadRate"] == SETTINGS.data.spread_rate_max

    def test_preserves_valid_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should not modify valid values."""
        result = clip_spread_rate(df_with_outliers)

        assert result.loc[0, "spreadRate"] == 0.02
        assert result.loc[1, "spreadRate"] == 0.03


# =============================================================================
# Filter Valid Guarantee Duration Tests
# =============================================================================

class TestFilterValidGuaranteeDuration:
    """Tests for filter_valid_guarantee_duration function."""

    def test_filters_negative_durations(self, df_with_outliers: pd.DataFrame) -> None:
        """Should filter out rows with negative guaranteeDuration."""
        result = filter_valid_guarantee_duration(df_with_outliers)

        assert len(result) == 4  # Original 5 minus 1 invalid
        assert (result["guaranteeDuration"] >= 0).all()

    def test_preserves_valid_rows(self, df_with_outliers: pd.DataFrame) -> None:
        """Should keep rows with valid durations."""
        result = filter_valid_guarantee_duration(df_with_outliers)

        assert 5 in result["guaranteeDuration"].values
        assert 7 in result["guaranteeDuration"].values
        assert 10 in result["guaranteeDuration"].values
        assert 3 in result["guaranteeDuration"].values

    def test_handles_missing_column(self) -> None:
        """Should handle DataFrame without guaranteeDuration column."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = filter_valid_guarantee_duration(df)

        assert len(result) == 3


# =============================================================================
# Coerce MVA Nulls Tests
# =============================================================================

class TestCoerceMvaNulls:
    """Tests for coerce_mva_nulls function."""

    def test_converts_none_strings_to_null(
        self, df_with_outliers: pd.DataFrame
    ) -> None:
        """Should convert 'None' strings to actual null values."""
        result = coerce_mva_nulls(df_with_outliers)

        assert pd.isna(result.loc[1, "mva"])
        assert pd.isna(result.loc[3, "mva"])

    def test_preserves_valid_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should not modify other values."""
        result = coerce_mva_nulls(df_with_outliers)

        assert result.loc[0, "mva"] == "Yes"
        assert result.loc[2, "mva"] == "No"
        assert result.loc[4, "mva"] == "Yes"

    def test_handles_missing_column(self) -> None:
        """Should handle DataFrame without mva column."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        result = coerce_mva_nulls(df)

        assert len(result) == 3


# =============================================================================
# Clean WINK Data Tests
# =============================================================================

class TestCleanWinkData:
    """Tests for clean_wink_data function."""

    def test_applies_all_cleaning_steps(self, df_with_outliers: pd.DataFrame) -> None:
        """Should apply all cleaning steps by default."""
        result = clean_wink_data(df_with_outliers)

        # Clipping applied
        assert result["capRate"].max() <= SETTINGS.data.cap_rate_max
        assert result["spreadRate"].max() <= SETTINGS.data.spread_rate_max

        # Filtering applied (row with duration=-1 removed)
        assert len(result) == 4

        # Null coercion applied
        null_count = result["mva"].isna().sum()
        assert null_count >= 1  # At least one 'None' converted

    def test_can_skip_clipping(self, df_with_outliers: pd.DataFrame) -> None:
        """Should skip clipping when clip_outliers=False."""
        result = clean_wink_data(df_with_outliers, clip_outliers=False)

        # Outliers still present
        assert result["capRate"].max() > SETTINGS.data.cap_rate_max

    def test_can_skip_duration_filter(self, df_with_outliers: pd.DataFrame) -> None:
        """Should skip duration filter when filter_duration=False."""
        result = clean_wink_data(df_with_outliers, filter_duration=False)

        # All rows preserved
        assert len(result) == 5

    def test_can_skip_null_coercion(self, df_with_outliers: pd.DataFrame) -> None:
        """Should skip null coercion when coerce_nulls=False."""
        result = clean_wink_data(df_with_outliers, coerce_nulls=False)

        # 'None' strings still present
        assert "None" in result["mva"].values

    def test_works_on_real_fixture(self, sample_df: pd.DataFrame) -> None:
        """Should clean real WINK sample fixture without errors."""
        result = clean_wink_data(sample_df)

        assert len(result) > 0
        assert len(result) <= len(sample_df)


# =============================================================================
# Cleaning Summary Tests
# =============================================================================

class TestGetCleaningSummary:
    """Tests for get_cleaning_summary function."""

    def test_calculates_row_counts(self, df_with_outliers: pd.DataFrame) -> None:
        """Should calculate before/after row counts."""
        df_clean = clean_wink_data(df_with_outliers)
        summary = get_cleaning_summary(df_with_outliers, df_clean)

        assert summary["rows_before"] == 5
        assert summary["rows_after"] == 4
        assert summary["rows_removed"] == 1
        assert summary["removal_pct"] == 20.0

    def test_counts_clipped_values(self, df_with_outliers: pd.DataFrame) -> None:
        """Should count values that would be clipped."""
        df_clean = clean_wink_data(df_with_outliers)
        summary = get_cleaning_summary(df_with_outliers, df_clean)

        assert summary["cap_rate_clipped"] == 2  # idx 2 and 3
        assert summary["perf_triggered_clipped"] == 1  # idx 1
        assert summary["spread_rate_clipped"] == 1  # idx 2

    def test_counts_filtered_durations(self, df_with_outliers: pd.DataFrame) -> None:
        """Should count invalid duration values."""
        df_clean = clean_wink_data(df_with_outliers)
        summary = get_cleaning_summary(df_with_outliers, df_clean)

        assert summary["invalid_duration_filtered"] == 1  # idx 2

    def test_handles_real_fixture(self, sample_df: pd.DataFrame) -> None:
        """Should generate summary for real fixture."""
        df_clean = clean_wink_data(sample_df)
        summary = get_cleaning_summary(sample_df, df_clean)

        assert "rows_before" in summary
        assert "rows_after" in summary
        assert summary["rows_before"] == 100
