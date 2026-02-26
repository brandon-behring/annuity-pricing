"""
Unit tests for competitive positioning module.

Tests PositioningAnalyzer: analyze_position(), get_distribution_stats(), etc.
See: METHODOLOGY.md Section 5
"""

import numpy as np
import pandas as pd
import pytest

from annuity_pricing.competitive.positioning import (
    DistributionStats,
    PositioningAnalyzer,
    PositionResult,
)


class TestPositionResult:
    """Test PositionResult dataclass."""

    def test_creates_result(self) -> None:
        """Should create position result."""
        result = PositionResult(
            rate=0.045,
            percentile=75.0,
            rank=3,
            total_products=10,
            quartile=1,
            position_label="Top Quartile",
        )

        assert result.rate == 0.045
        assert result.percentile == 75.0
        assert result.rank == 3

    def test_validates_percentile(self) -> None:
        """Should raise for invalid percentile."""
        with pytest.raises(ValueError, match="CRITICAL"):
            PositionResult(
                rate=0.045,
                percentile=150.0,  # Invalid
                rank=1,
                total_products=10,
                quartile=1,
                position_label="Top",
            )

    def test_validates_quartile(self) -> None:
        """Should raise for invalid quartile."""
        with pytest.raises(ValueError, match="CRITICAL"):
            PositionResult(
                rate=0.045,
                percentile=75.0,
                rank=1,
                total_products=10,
                quartile=5,  # Invalid
                position_label="Top",
            )


class TestDistributionStats:
    """Test DistributionStats dataclass."""

    def test_creates_stats(self) -> None:
        """Should create distribution stats."""
        stats = DistributionStats(
            min=0.03,
            max=0.06,
            mean=0.045,
            median=0.044,
            std=0.005,
            q1=0.04,
            q3=0.05,
            count=100,
        )

        assert stats.min == 0.03
        assert stats.count == 100


class TestPositioningAnalyzerInit:
    """Test PositioningAnalyzer initialization."""

    def test_default_columns(self) -> None:
        """Should use default column names."""
        analyzer = PositioningAnalyzer()

        assert analyzer.rate_column == "fixedRate"
        assert analyzer.duration_column == "guaranteeDuration"

    def test_custom_columns(self) -> None:
        """Should accept custom column names."""
        analyzer = PositioningAnalyzer(
            rate_column="rate",
            duration_column="duration",
        )

        assert analyzer.rate_column == "rate"
        assert analyzer.duration_column == "duration"


class TestAnalyzePosition:
    """Test PositioningAnalyzer.analyze_position() method."""

    @pytest.fixture
    def analyzer(self) -> PositioningAnalyzer:
        return PositioningAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        """Create sample market data."""
        return pd.DataFrame({
            "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
            "companyName": ["A", "B", "C", "D", "E", "F"],
        })

    def test_returns_position_result(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return PositionResult."""
        result = analyzer.analyze_position(
            rate=0.045,
            market_data=market_data,
        )

        assert isinstance(result, PositionResult)
        assert result.rate == 0.045
        assert result.total_products == 6

    def test_percentile_calculation(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """
        [T2] Percentile = count(rate <= value) / total.

        For 0.045 in [0.040, 0.042, 0.044, 0.046, 0.048, 0.050]:
        3 rates <= 0.045 → percentile = 3/6 * 100 = 50%
        """
        result = analyzer.analyze_position(
            rate=0.045,
            market_data=market_data,
        )

        assert result.percentile == 50.0

    def test_rank_calculation(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """
        Rank = count(rate > value) + 1.

        For 0.045: 3 rates > 0.045, rank = 4.
        """
        result = analyzer.analyze_position(
            rate=0.045,
            market_data=market_data,
        )

        assert result.rank == 4

    def test_quartile_assignment(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should assign correct quartile."""
        # Top quartile (>= 75th percentile)
        result = analyzer.analyze_position(rate=0.049, market_data=market_data)
        assert result.quartile == 1

        # Bottom quartile (< 25th percentile)
        result = analyzer.analyze_position(rate=0.041, market_data=market_data)
        assert result.quartile == 4

    def test_product_group_filter(
        self, analyzer: PositioningAnalyzer
    ) -> None:
        """Should filter by product group."""
        market_data = pd.DataFrame({
            "fixedRate": [0.040, 0.050, 0.045, 0.055],
            "guaranteeDuration": [5, 5, 5, 5],
            "productGroup": ["MYGA", "MYGA", "FIA", "FIA"],
            "status": ["current"] * 4,
        })

        result = analyzer.analyze_position(
            rate=0.045,
            market_data=market_data,
            product_group="MYGA",
        )

        # Only MYGA products considered
        assert result.total_products == 2

    def test_duration_filter(
        self, analyzer: PositioningAnalyzer
    ) -> None:
        """Should filter by duration."""
        market_data = pd.DataFrame({
            "fixedRate": [0.040, 0.045, 0.050, 0.055],
            "guaranteeDuration": [3, 5, 5, 10],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
        })

        result = analyzer.analyze_position(
            rate=0.047,
            market_data=market_data,
            guarantee_duration=5,
            duration_tolerance=1,
        )

        # Only 5-year products (within tolerance)
        assert result.total_products == 2

    def test_exclude_company(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should exclude specified company."""
        result = analyzer.analyze_position(
            rate=0.045,
            market_data=market_data,
            exclude_company="A",
        )

        assert result.total_products == 5

    def test_raises_on_no_comparables(
        self, analyzer: PositioningAnalyzer
    ) -> None:
        """Should raise if no comparable products."""
        empty_data = pd.DataFrame({
            "fixedRate": [],
            "guaranteeDuration": [],
            "productGroup": [],
            "status": [],
        })

        with pytest.raises(ValueError, match="CRITICAL"):
            analyzer.analyze_position(
                rate=0.045,
                market_data=empty_data,
            )


class TestGetDistributionStats:
    """Test PositioningAnalyzer.get_distribution_stats() method."""

    @pytest.fixture
    def analyzer(self) -> PositioningAnalyzer:
        return PositioningAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
        })

    def test_returns_distribution_stats(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return DistributionStats."""
        stats = analyzer.get_distribution_stats(market_data)

        assert isinstance(stats, DistributionStats)
        assert stats.count == 6

    def test_calculates_statistics(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should calculate correct statistics."""
        stats = analyzer.get_distribution_stats(market_data)

        assert stats.min == 0.040
        assert stats.max == 0.050
        assert abs(stats.mean - 0.045) < 1e-6
        assert abs(stats.median - 0.045) < 1e-6


class TestGetPercentileThresholds:
    """Test PositioningAnalyzer.get_percentile_thresholds() method."""

    @pytest.fixture
    def analyzer(self) -> PositioningAnalyzer:
        return PositioningAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        np.random.seed(42)
        return pd.DataFrame({
            "fixedRate": np.linspace(0.03, 0.06, 100),
            "guaranteeDuration": [5] * 100,
            "productGroup": ["MYGA"] * 100,
            "status": ["current"] * 100,
        })

    def test_returns_thresholds(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return percentile thresholds."""
        thresholds = analyzer.get_percentile_thresholds(market_data)

        assert isinstance(thresholds, dict)
        assert 50.0 in thresholds
        assert 75.0 in thresholds

    def test_custom_percentiles(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should accept custom percentiles."""
        thresholds = analyzer.get_percentile_thresholds(
            market_data,
            percentiles=[10.0, 50.0, 90.0],
        )

        assert set(thresholds.keys()) == {10.0, 50.0, 90.0}


class TestCompareToPeers:
    """Test PositioningAnalyzer.compare_to_peers() method."""

    @pytest.fixture
    def analyzer(self) -> PositioningAnalyzer:
        return PositioningAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.048, 0.046, 0.044, 0.042, 0.040],
            "guaranteeDuration": [5] * 6,
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
            "companyName": ["A", "B", "C", "D", "E", "F"],
        })

    def test_returns_comparison_df(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return peer comparison DataFrame."""
        result = analyzer.compare_to_peers(
            rate=0.045,
            company="D",
            market_data=market_data,
        )

        assert isinstance(result, pd.DataFrame)
        assert "company" in result.columns
        assert "rate" in result.columns
        assert "rank" in result.columns

    def test_highlights_target_company(
        self, analyzer: PositioningAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should highlight target company."""
        result = analyzer.compare_to_peers(
            rate=0.044,
            company="D",
            market_data=market_data,
        )

        target_row = result[result["company"] == "D"]
        assert len(target_row) == 1
        assert target_row.iloc[0]["is_target"] == True  # noqa: E712 (numpy bool)
