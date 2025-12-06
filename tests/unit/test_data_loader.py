"""
Tests for WINK data loader functionality.

Tests cover:
- Valid parquet loading
- Checksum verification (correct + incorrect)
- Product filtering
- Error handling for missing files

Uses real WINK sample fixture for realistic testing.
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from annuity_pricing.data.loader import (
    DataIntegrityError,
    DataLoadError,
    compute_sha256,
    load_wink_by_product,
    load_wink_data,
    verify_checksum,
)


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PARQUET = FIXTURES_DIR / "wink_sample.parquet"
SAMPLE_CHECKSUM = "c1910138b6755fd51edb4713da74b5e7d199e8866468360035aa44f5bfe22e2a"


@pytest.fixture
def sample_wink_path() -> Path:
    """Path to sample WINK parquet fixture."""
    return SAMPLE_PARQUET


@pytest.fixture
def sample_wink_df() -> pd.DataFrame:
    """Pre-loaded sample WINK DataFrame."""
    return pd.read_parquet(SAMPLE_PARQUET)


# =============================================================================
# Checksum Tests
# =============================================================================

class TestComputeSha256:
    """Tests for compute_sha256 function."""

    def test_computes_correct_checksum(self, sample_wink_path: Path) -> None:
        """Should compute correct SHA-256 hash for fixture file."""
        result = compute_sha256(sample_wink_path)
        assert result == SAMPLE_CHECKSUM

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for non-existent file."""
        missing_file = tmp_path / "does_not_exist.parquet"

        with pytest.raises(FileNotFoundError) as exc_info:
            compute_sha256(missing_file)

        assert "CRITICAL" in str(exc_info.value)
        assert "does_not_exist.parquet" in str(exc_info.value)


class TestVerifyChecksum:
    """Tests for verify_checksum function."""

    def test_passes_on_correct_checksum(self, sample_wink_path: Path) -> None:
        """Should pass silently when checksum matches."""
        # Should not raise
        verify_checksum(sample_wink_path, SAMPLE_CHECKSUM)

    def test_raises_on_incorrect_checksum(self, sample_wink_path: Path) -> None:
        """Should raise DataIntegrityError when checksum doesn't match."""
        wrong_checksum = "0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises(DataIntegrityError) as exc_info:
            verify_checksum(sample_wink_path, wrong_checksum)

        error_msg = str(exc_info.value)
        assert "CRITICAL" in error_msg
        assert "Checksum mismatch" in error_msg
        assert SAMPLE_CHECKSUM in error_msg  # Shows actual checksum


# =============================================================================
# Load WINK Data Tests
# =============================================================================

class TestLoadWinkData:
    """Tests for load_wink_data function."""

    def test_loads_fixture_without_verification(self, sample_wink_path: Path) -> None:
        """Should load fixture data when verification is skipped."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df = load_wink_data(path=sample_wink_path, verify=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 100  # Our fixture has 100 rows
        assert "productGroup" in df.columns
        assert "companyName" in df.columns

    def test_loads_with_verification(self, sample_wink_path: Path) -> None:
        """Should load and verify fixture data."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df = load_wink_data(path=sample_wink_path, verify=True)

        assert len(df) == 100

    def test_loads_specific_columns(self, sample_wink_path: Path) -> None:
        """Should load only specified columns."""
        columns = ["companyName", "productGroup", "status"]

        df = load_wink_data(path=sample_wink_path, verify=False, columns=columns)

        assert list(df.columns) == columns
        assert len(df) == 100

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Should raise DataLoadError for missing file."""
        missing_file = tmp_path / "missing.parquet"

        with pytest.raises((FileNotFoundError, DataLoadError)):
            load_wink_data(path=missing_file, verify=False)

    def test_raises_on_checksum_mismatch(self, sample_wink_path: Path) -> None:
        """Should raise DataIntegrityError on checksum mismatch."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = "wrong_checksum_value"

            with pytest.raises(DataIntegrityError):
                load_wink_data(path=sample_wink_path, verify=True)


# =============================================================================
# Load WINK By Product Tests
# =============================================================================

class TestLoadWinkByProduct:
    """Tests for load_wink_by_product function."""

    def test_filters_myga_products(self, sample_wink_path: Path) -> None:
        """Should filter to only MYGA products."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df = load_wink_by_product("MYGA", verify=True)

        assert len(df) > 0
        assert (df["productGroup"] == "MYGA").all()
        assert (df["status"] == "current").all()

    def test_filters_fia_products(self, sample_wink_path: Path) -> None:
        """Should filter to only FIA products."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df = load_wink_by_product("FIA", verify=True)

        assert len(df) > 0
        assert (df["productGroup"] == "FIA").all()

    def test_filters_rila_products(self, sample_wink_path: Path) -> None:
        """Should filter to only RILA products."""
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = sample_wink_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df = load_wink_by_product("RILA", verify=True)

        assert len(df) > 0
        assert (df["productGroup"] == "RILA").all()

    def test_raises_on_invalid_product_group(self) -> None:
        """Should raise ValueError for invalid product group."""
        with pytest.raises(ValueError) as exc_info:
            load_wink_by_product("INVALID")

        error_msg = str(exc_info.value)
        assert "CRITICAL" in error_msg
        assert "INVALID" in error_msg

    def test_raises_on_invalid_status(self) -> None:
        """Should raise ValueError for invalid status."""
        with pytest.raises(ValueError) as exc_info:
            load_wink_by_product("MYGA", status="invalid_status")

        error_msg = str(exc_info.value)
        assert "CRITICAL" in error_msg
        assert "invalid_status" in error_msg


# =============================================================================
# Data Quality Tests
# =============================================================================

class TestWinkDataQuality:
    """Tests to verify WINK sample fixture has expected structure."""

    def test_fixture_has_expected_columns(self, sample_wink_df: pd.DataFrame) -> None:
        """Fixture should have key WINK columns."""
        required_columns = [
            "companyName",
            "productGroup",
            "productName",
            "status",
            "guaranteeDuration",
        ]
        for col in required_columns:
            assert col in sample_wink_df.columns, f"Missing column: {col}"

    def test_fixture_has_all_product_groups(self, sample_wink_df: pd.DataFrame) -> None:
        """Fixture should contain MYGA, FIA, and RILA products."""
        product_groups = set(sample_wink_df["productGroup"].unique())

        assert "MYGA" in product_groups
        assert "FIA" in product_groups
        assert "RILA" in product_groups

    def test_fixture_row_count(self, sample_wink_df: pd.DataFrame) -> None:
        """Fixture should have expected number of rows."""
        assert len(sample_wink_df) == 100

    def test_fixture_has_current_status(self, sample_wink_df: pd.DataFrame) -> None:
        """All fixture rows should have 'current' status."""
        assert (sample_wink_df["status"] == "current").all()
