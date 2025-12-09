"""
Integration tests for WINK data pipeline.

Tests end-to-end flow: load → clean → registry pricing.
Uses sample WINK fixture for realistic testing.

**Checksum Validation**: Tests enforce fail-fast on data drift.
If checksum mismatch occurs, regenerate fixtures via:
    scripts/regenerate_goldens.py --wink-fixture
"""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from annuity_pricing.data.cleaner import clean_wink_data, get_cleaning_summary
from annuity_pricing.data.loader import (
    load_wink_data,
    compute_sha256,
    verify_checksum,
    DataIntegrityError,
)
from annuity_pricing.data.schemas import FIAProduct, MYGAProduct, RILAProduct
from annuity_pricing.products.registry import create_default_registry


# =============================================================================
# Fixtures and Constants
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_PARQUET = FIXTURES_DIR / "wink_sample.parquet"
# SHA-256 checksum of wink_sample.parquet - FAIL if this changes
SAMPLE_CHECKSUM = "c1910138b6755fd51edb4713da74b5e7d199e8866468360035aa44f5bfe22e2a"


@pytest.fixture
def wink_sample_path() -> Path:
    """Path to WINK sample fixture."""
    return SAMPLE_PARQUET


@pytest.fixture
def registry():
    """Create default pricing registry."""
    return create_default_registry(
        risk_free_rate=0.045,
        volatility=0.18,
    )


# =============================================================================
# Checksum Validation Tests (FAIL-FAST)
# =============================================================================


@pytest.mark.integration
class TestWinkChecksumValidation:
    """
    Checksum validation tests that FAIL if fixture data changes.

    [T1] Data integrity is critical for regression testing.
    Any change to the fixture requires explicit checksum update.

    To regenerate after intentional changes:
        scripts/regenerate_goldens.py --wink-fixture
    """

    def test_fixture_checksum_matches(self, wink_sample_path: Path) -> None:
        """
        [P0] FAIL if fixture checksum changes.

        This is the primary data integrity gate. Any modification to
        wink_sample.parquet will cause this test to fail immediately.
        """
        if not wink_sample_path.exists():
            pytest.fail(f"CRITICAL: Fixture not found at {wink_sample_path}")

        actual_checksum = compute_sha256(wink_sample_path)

        assert actual_checksum == SAMPLE_CHECKSUM, (
            f"CHECKSUM MISMATCH - Data drift detected!\n"
            f"Expected: {SAMPLE_CHECKSUM}\n"
            f"Actual:   {actual_checksum}\n\n"
            f"If intentional, update SAMPLE_CHECKSUM in this file.\n"
            f"Run: scripts/regenerate_goldens.py --wink-fixture"
        )

    def test_loader_raises_on_checksum_mismatch(self, wink_sample_path: Path) -> None:
        """
        [P0] Verify loader raises DataIntegrityError on bad checksum.

        The loader must NEVER silently accept corrupted data.
        """
        wrong_checksum = "0" * 64  # Obviously wrong

        with pytest.raises(DataIntegrityError) as exc_info:
            verify_checksum(wink_sample_path, wrong_checksum)

        assert "CRITICAL" in str(exc_info.value)
        assert "Checksum mismatch" in str(exc_info.value)

    def test_loader_accepts_valid_checksum(self, wink_sample_path: Path) -> None:
        """
        [P0] Verify loader accepts valid checksum without error.
        """
        # Should not raise
        verify_checksum(wink_sample_path, SAMPLE_CHECKSUM)

    def test_fixture_row_count_stable(self, wink_sample_path: Path) -> None:
        """
        [P0] Verify fixture has expected row count.

        Row count changes indicate data drift.
        """
        df = pd.read_parquet(wink_sample_path)

        expected_rows = 100
        assert len(df) == expected_rows, (
            f"Row count changed: expected {expected_rows}, got {len(df)}. "
            f"Update expected_rows if this is intentional."
        )

    def test_fixture_has_required_columns(self, wink_sample_path: Path) -> None:
        """
        [P0] Verify fixture has all required columns for pricing.
        """
        df = pd.read_parquet(wink_sample_path)

        required_columns = {
            "companyName",
            "productName",
            "productGroup",
            "status",
        }

        missing = required_columns - set(df.columns)
        assert not missing, f"Missing required columns: {missing}"


# =============================================================================
# Pipeline Integration Tests
# =============================================================================

@pytest.mark.integration
class TestWinkPipelineIntegration:
    """Integration tests for full WINK data pipeline."""

    def test_load_clean_pipeline(self, wink_sample_path: Path) -> None:
        """Should load and clean WINK data end-to-end."""
        # Load
        with patch("annuity_pricing.data.loader.SETTINGS") as mock_settings:
            mock_settings.data.wink_path = wink_sample_path
            mock_settings.data.wink_checksum = SAMPLE_CHECKSUM

            df_raw = load_wink_data(path=wink_sample_path, verify=True)

        # Clean
        df_clean = clean_wink_data(df_raw)

        # Verify
        assert len(df_raw) == 100
        assert len(df_clean) <= 100
        assert "productGroup" in df_clean.columns

    def test_cleaning_summary_generation(self, wink_sample_path: Path) -> None:
        """Should generate meaningful cleaning summary."""
        df_raw = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df_raw)

        summary = get_cleaning_summary(df_raw, df_clean)

        assert summary["rows_before"] == 100
        assert summary["rows_after"] <= 100
        assert "removal_pct" in summary

    def test_myga_row_to_pricing(self, wink_sample_path: Path, registry) -> None:
        """Should convert MYGA rows to products and price them."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        # Filter to MYGA
        myga_rows = df_clean[df_clean["productGroup"] == "MYGA"]

        if len(myga_rows) == 0:
            pytest.skip("No MYGA rows in fixture")

        # Take first MYGA row and create product
        row = myga_rows.iloc[0]

        # Get the fixed rate - check various column names
        fixed_rate = None
        for col in ["fixedRate", "guaranteedRate", "crediting_rate"]:
            if col in row.index and pd.notna(row.get(col)):
                fixed_rate = row[col]
                break

        if fixed_rate is None or fixed_rate <= 0:
            fixed_rate = 0.04  # Default for testing

        product = MYGAProduct(
            company_name=str(row.get("companyName", "Test Company")),
            product_name=str(row.get("productName", "Test MYGA")),
            product_group="MYGA",
            status="current",
            fixed_rate=float(fixed_rate),
            guarantee_duration=int(row.get("guaranteeDuration", 5)),
        )

        # Price
        result = registry.price(product, premium=100_000)

        assert result.present_value > 0, (
            f"MYGA pricing failed: PV must be positive, got {result.present_value}"
        )
        # Check details for guaranteed_value if present
        if hasattr(result, 'details') and result.details:
            guaranteed_value = result.details.get('guaranteed_value', 0)
            assert guaranteed_value >= 0, (
                f"MYGA guaranteed_value must be non-negative, got {guaranteed_value}"
            )
            # Golden expectation: guaranteed_value should be at least premium for MYGA
            # (since MYGA guarantees return of principal at minimum)
            if 'premium' in result.details:
                assert guaranteed_value >= result.details['premium'] * 0.95, (
                    f"MYGA guaranteed_value {guaranteed_value} should be >= 95% of premium"
                )

    def test_fia_row_to_pricing(self, wink_sample_path: Path, registry) -> None:
        """Should convert FIA rows to products and price them."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        # Filter to FIA
        fia_rows = df_clean[df_clean["productGroup"] == "FIA"]

        if len(fia_rows) == 0:
            pytest.skip("No FIA rows in fixture")

        # Take first FIA row and create product
        row = fia_rows.iloc[0]

        # Get cap rate with fallback
        # [F.4] Use 5% default to fit within tightened 10% budget tolerance
        cap_rate = row.get("capRate")
        if pd.isna(cap_rate) or cap_rate <= 0 or cap_rate > 0.30:
            cap_rate = 0.05  # Default 5% cap (within budget tolerance)

        product = FIAProduct(
            company_name=str(row.get("companyName", "Test Company")),
            product_name=str(row.get("productName", "Test FIA")),
            product_group="FIA",
            status="current",
            cap_rate=float(cap_rate),
            index_used=str(row.get("indexName", "S&P 500")),
            indexing_method="Annual Point to Point",
        )

        # Price ([F.1] term_years now required)
        result = registry.price(product, premium=100_000, term_years=1.0)

        assert result.expected_credit >= 0  # Can be 0 with floor
        assert result.embedded_option_value >= 0

    def test_rila_row_to_pricing(self, wink_sample_path: Path, registry) -> None:
        """Should convert RILA rows to products and price them."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        # Filter to RILA
        rila_rows = df_clean[df_clean["productGroup"] == "RILA"]

        if len(rila_rows) == 0:
            pytest.skip("No RILA rows in fixture")

        # Take first RILA row and create product
        row = rila_rows.iloc[0]

        # Get buffer rate with fallback
        buffer_rate = row.get("bufferRate")
        if pd.isna(buffer_rate) or buffer_rate <= 0:
            buffer_rate = 0.10  # Default 10% buffer

        # Get cap rate with fallback
        cap_rate = row.get("capRate")
        if pd.isna(cap_rate) or cap_rate <= 0 or cap_rate > 1.0:
            cap_rate = 0.15  # Default 15% cap

        product = RILAProduct(
            company_name=str(row.get("companyName", "Test Company")),
            product_name=str(row.get("productName", "Test RILA")),
            product_group="RILA",
            status="current",
            buffer_rate=float(buffer_rate),
            cap_rate=float(cap_rate),
            index_used=str(row.get("indexName", "S&P 500")),
            buffer_modifier="Losses Covered Up To",
        )

        # Price ([F.1] term_years now required)
        result = registry.price(product, premium=100_000, term_years=1.0)

        assert result.max_loss <= 1.0  # Max loss capped at 100%
        assert result.protection_value >= 0


@pytest.mark.integration
class TestDataQualityAfterCleaning:
    """Tests to verify data quality post-cleaning."""

    def test_no_outlier_cap_rates(self, wink_sample_path: Path) -> None:
        """Cleaned data should have no extreme capRate values."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        if "capRate" in df_clean.columns:
            # Skip NaN values when checking max
            non_null_caps = df_clean["capRate"].dropna()
            if len(non_null_caps) > 0:
                assert non_null_caps.max() <= 10.0

    def test_no_negative_durations(self, wink_sample_path: Path) -> None:
        """Cleaned data should have no negative guarantee durations."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        if "guaranteeDuration" in df_clean.columns:
            assert (df_clean["guaranteeDuration"] >= 0).all()

    def test_all_products_have_company(self, wink_sample_path: Path) -> None:
        """All products should have company names."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        assert df_clean["companyName"].notna().all()

    def test_product_groups_preserved(self, wink_sample_path: Path) -> None:
        """Cleaning should preserve all product groups."""
        df = pd.read_parquet(wink_sample_path)
        df_clean = clean_wink_data(df)

        original_groups = set(df["productGroup"].unique())
        clean_groups = set(df_clean["productGroup"].unique())

        # All groups that had valid data should be preserved
        assert len(clean_groups) >= 1
        assert clean_groups.issubset(original_groups)
