"""
Unit tests for competitive spreads module.

Tests SpreadAnalyzer: calculate_spread(), get_spread_distribution(), etc.
See: METHODOLOGY.md Section 5
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from annuity_pricing.competitive.spreads import (
    SpreadAnalyzer,
    SpreadDistribution,
    SpreadResult,
    build_treasury_curve,
)


class TestSpreadResult:
    """Test SpreadResult dataclass."""

    def test_creates_result(self) -> None:
        """Should create spread result."""
        result = SpreadResult(
            product_rate=0.045,
            treasury_rate=0.04,
            spread_bps=50.0,
            spread_pct=12.5,
            duration=5,
            as_of_date=date.today(),
        )

        assert result.product_rate == 0.045
        assert result.spread_bps == 50.0


class TestSpreadDistribution:
    """Test SpreadDistribution dataclass."""

    def test_creates_distribution(self) -> None:
        """Should create spread distribution."""
        dist = SpreadDistribution(
            min_bps=50.0,
            max_bps=200.0,
            mean_bps=125.0,
            median_bps=120.0,
            std_bps=30.0,
            q1_bps=100.0,
            q3_bps=150.0,
            count=100,
        )

        assert dist.mean_bps == 125.0
        assert dist.count == 100


class TestSpreadAnalyzerInit:
    """Test SpreadAnalyzer initialization."""

    def test_default_columns(self) -> None:
        """Should use default column names."""
        analyzer = SpreadAnalyzer()

        assert analyzer.rate_column == "fixedRate"
        assert analyzer.duration_column == "guaranteeDuration"


class TestCalculateSpread:
    """Test SpreadAnalyzer.calculate_spread() method."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    def test_returns_spread_result(self, analyzer: SpreadAnalyzer) -> None:
        """Should return SpreadResult."""
        result = analyzer.calculate_spread(
            product_rate=0.045,
            treasury_rate=0.04,
            duration=5,
        )

        assert isinstance(result, SpreadResult)
        assert result.duration == 5

    def test_spread_calculation_bps(self, analyzer: SpreadAnalyzer) -> None:
        """
        [T1] Spread (bps) = (product_rate - treasury_rate) × 10000

        4.5% - 4.0% = 0.5% = 50 bps
        """
        result = analyzer.calculate_spread(
            product_rate=0.045,
            treasury_rate=0.04,
            duration=5,
        )

        assert abs(result.spread_bps - 50.0) < 1e-6

    def test_spread_calculation_pct(self, analyzer: SpreadAnalyzer) -> None:
        """
        [T1] Spread (%) = (spread / treasury_rate) × 100

        0.5% / 4.0% = 12.5%
        """
        result = analyzer.calculate_spread(
            product_rate=0.045,
            treasury_rate=0.04,
            duration=5,
        )

        assert abs(result.spread_pct - 12.5) < 1e-6

    def test_negative_spread(self, analyzer: SpreadAnalyzer) -> None:
        """Spread can be negative."""
        result = analyzer.calculate_spread(
            product_rate=0.035,  # Below Treasury
            treasury_rate=0.04,
            duration=5,
        )

        assert result.spread_bps < 0

    def test_validates_treasury_rate(self, analyzer: SpreadAnalyzer) -> None:
        """Should raise for non-positive Treasury rate."""
        with pytest.raises(ValueError, match="CRITICAL"):
            analyzer.calculate_spread(
                product_rate=0.045,
                treasury_rate=0,  # Invalid
                duration=5,
            )


class TestCalculateMarketSpreads:
    """Test SpreadAnalyzer.calculate_market_spreads() method."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.045, 0.048, 0.050, 0.046],
            "guaranteeDuration": [5, 5, 7, 3],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
        })

    @pytest.fixture
    def treasury_curve(self) -> dict[int, float]:
        return {3: 0.035, 5: 0.04, 7: 0.042, 10: 0.045}

    def test_adds_spread_column(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should add spread_bps column."""
        result = analyzer.calculate_market_spreads(
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        assert "spread_bps" in result.columns
        assert len(result) > 0

    def test_calculates_correct_spreads(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should calculate correct spreads for each duration."""
        result = analyzer.calculate_market_spreads(
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        # First product: 4.5% - 4.0% (5Y) = 50 bps
        five_year = result[result["guaranteeDuration"] == 5].iloc[0]
        assert abs(five_year["spread_bps"] - 50.0) < 1e-6


class TestGetSpreadDistribution:
    """Test SpreadAnalyzer.get_spread_distribution() method."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        np.random.seed(42)
        return pd.DataFrame({
            "fixedRate": np.random.uniform(0.04, 0.055, 100),
            "guaranteeDuration": [5] * 100,
            "productGroup": ["MYGA"] * 100,
            "status": ["current"] * 100,
        })

    @pytest.fixture
    def treasury_curve(self) -> dict[int, float]:
        return {5: 0.04}

    def test_returns_distribution(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should return SpreadDistribution."""
        result = analyzer.get_spread_distribution(
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        assert isinstance(result, SpreadDistribution)
        assert result.count == 100

    def test_distribution_statistics(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should calculate valid distribution statistics."""
        result = analyzer.get_spread_distribution(
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        # All spreads positive since rates > treasury
        assert result.min_bps >= 0
        assert result.max_bps > result.min_bps
        assert result.q1_bps <= result.median_bps <= result.q3_bps


class TestAnalyzeSpreadPosition:
    """Test SpreadAnalyzer.analyze_spread_position() method."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.045, 0.048, 0.050, 0.052, 0.055],
            "guaranteeDuration": [5] * 5,
            "productGroup": ["MYGA"] * 5,
            "status": ["current"] * 5,
        })

    @pytest.fixture
    def treasury_curve(self) -> dict[int, float]:
        return {5: 0.04}

    def test_returns_position_analysis(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should return position analysis dict."""
        result = analyzer.analyze_spread_position(
            spread_bps=100.0,  # 1% spread
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        assert isinstance(result, dict)
        assert "percentile" in result
        assert "rank" in result


class TestSpreadByDuration:
    """Test SpreadAnalyzer.spread_by_duration() method."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.045, 0.048, 0.050, 0.052],
            "guaranteeDuration": [3, 5, 5, 7],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
        })

    @pytest.fixture
    def treasury_curve(self) -> dict[int, float]:
        return {3: 0.035, 5: 0.04, 7: 0.042}

    def test_returns_summary_by_duration(
        self, analyzer: SpreadAnalyzer, market_data: pd.DataFrame, treasury_curve: dict
    ) -> None:
        """Should return summary grouped by duration."""
        result = analyzer.spread_by_duration(
            market_data=market_data,
            treasury_curve=treasury_curve,
        )

        assert isinstance(result, pd.DataFrame)
        assert "guaranteeDuration" in result.columns
        assert "mean_spread_bps" in result.columns


class TestBuildTreasuryCurve:
    """Test build_treasury_curve helper function."""

    def test_builds_curve_from_fred_series(self) -> None:
        """Should build curve from FRED series names."""
        rates = {
            "DGS1": 0.035,
            "DGS5": 0.04,
            "DGS10": 0.045,
        }

        curve = build_treasury_curve(rates)

        assert curve[1] == 0.035
        assert curve[5] == 0.04
        assert curve[10] == 0.045

    def test_ignores_unknown_series(self) -> None:
        """Should ignore unknown series names."""
        rates = {
            "DGS5": 0.04,
            "UNKNOWN": 0.05,
        }

        curve = build_treasury_curve(rates)

        assert 5 in curve
        assert len(curve) == 1


class TestTreasuryInterpolation:
    """Test Treasury rate interpolation."""

    @pytest.fixture
    def analyzer(self) -> SpreadAnalyzer:
        return SpreadAnalyzer()

    def test_exact_match(self, analyzer: SpreadAnalyzer) -> None:
        """Should return exact rate for matching duration."""
        curve = {3: 0.035, 5: 0.04, 7: 0.042}
        rate = analyzer._interpolate_treasury(5, curve)

        assert rate == 0.04

    def test_interpolation(self, analyzer: SpreadAnalyzer) -> None:
        """Should interpolate for non-matching durations."""
        curve = {3: 0.030, 7: 0.040}  # 10 bps per year
        rate = analyzer._interpolate_treasury(5, curve)

        # Linear: 3.0% + (5-3)/(7-3) * (4.0% - 3.0%) = 3.5%
        assert abs(rate - 0.035) < 1e-6

    def test_extrapolation_below(self, analyzer: SpreadAnalyzer) -> None:
        """Should use minimum rate for durations below curve."""
        curve = {3: 0.035, 5: 0.04}
        rate = analyzer._interpolate_treasury(1, curve)

        assert rate == 0.035  # Use minimum

    def test_extrapolation_above(self, analyzer: SpreadAnalyzer) -> None:
        """Should use maximum rate for durations above curve."""
        curve = {3: 0.035, 5: 0.04}
        rate = analyzer._interpolate_treasury(10, curve)

        assert rate == 0.04  # Use maximum
