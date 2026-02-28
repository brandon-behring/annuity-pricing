"""
Unit tests for rate recommender.

Tests rate_setting/recommender.py
See: METHODOLOGY.md Section 5
"""

import numpy as np
import pandas as pd
import pytest

from annuity_pricing.rate_setting.recommender import (
    MarginAnalysis,
    RateRecommendation,
    RateRecommender,
)


class TestRateRecommendation:
    """Test RateRecommendation dataclass."""

    def test_creates_recommendation(self) -> None:
        """Should create recommendation with required fields."""
        rec = RateRecommendation(
            recommended_rate=0.045,
            target_percentile=75.0,
        )

        assert rec.recommended_rate == 0.045
        assert rec.target_percentile == 75.0

    def test_immutable(self) -> None:
        """Recommendation should be immutable (frozen)."""
        rec = RateRecommendation(
            recommended_rate=0.045,
            target_percentile=75.0,
        )

        with pytest.raises(AttributeError):
            rec.recommended_rate = 0.05  # type: ignore

    def test_validates_non_negative_rate(self) -> None:
        """Should raise ValueError for negative rate."""
        with pytest.raises(ValueError, match="CRITICAL"):
            RateRecommendation(
                recommended_rate=-0.01,
                target_percentile=75.0,
            )

    def test_validates_percentile_range(self) -> None:
        """Should raise ValueError for invalid percentile."""
        with pytest.raises(ValueError, match="CRITICAL"):
            RateRecommendation(
                recommended_rate=0.045,
                target_percentile=150.0,
            )

        with pytest.raises(ValueError, match="CRITICAL"):
            RateRecommendation(
                recommended_rate=0.045,
                target_percentile=-10.0,
            )


class TestMarginAnalysis:
    """Test MarginAnalysis dataclass."""

    def test_creates_analysis(self) -> None:
        """Should create margin analysis."""
        analysis = MarginAnalysis(
            gross_spread=150.0,
            option_cost=0.0,
            expense_load=50.0,
            net_margin=100.0,
        )

        assert analysis.gross_spread == 150.0
        assert analysis.option_cost == 0.0
        assert analysis.expense_load == 50.0
        assert analysis.net_margin == 100.0


class TestRateRecommenderInit:
    """Test RateRecommender initialization."""

    def test_default_initialization(self) -> None:
        """Should create recommender with defaults."""
        recommender = RateRecommender()

        assert recommender.default_expense_load == 0.0050  # 50 bps
        assert recommender.duration_tolerance == 1

    def test_custom_initialization(self) -> None:
        """Should allow custom parameters."""
        recommender = RateRecommender(
            default_expense_load=0.0075,
            duration_tolerance=2,
        )

        assert recommender.default_expense_load == 0.0075
        assert recommender.duration_tolerance == 2


class TestRecommendRate:
    """Test RateRecommender.recommend_rate() method."""

    @pytest.fixture
    def recommender(self) -> RateRecommender:
        return RateRecommender()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        """Create sample market data with known distribution."""
        return pd.DataFrame(
            {
                "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
                "guaranteeDuration": [5, 5, 5, 5, 5, 5],
                "productGroup": ["MYGA"] * 6,
                "status": ["current"] * 6,
            }
        )

    def test_returns_recommendation(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should return complete RateRecommendation."""
        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=75.0,
            market_data=market_data,
        )

        assert isinstance(result, RateRecommendation)
        assert result.recommended_rate > 0
        assert result.target_percentile == 75.0
        assert result.comparable_count == 6

    def test_percentile_calculation(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """
        [T2] Rate at percentile P = numpy percentile calculation.
        """
        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=75.0,
            market_data=market_data,
        )

        expected = np.percentile([0.040, 0.042, 0.044, 0.046, 0.048, 0.050], 75)
        assert abs(result.recommended_rate - expected) < 1e-6

    def test_spread_calculation_with_treasury(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should calculate spread over Treasury when provided."""
        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=50.0,
            market_data=market_data,
            treasury_rate=0.04,
        )

        assert result.spread_over_treasury is not None
        # Median rate is ~0.045, Treasury is 0.04, spread ≈ 50 bps
        assert result.spread_over_treasury > 0

    def test_margin_estimate(self, recommender: RateRecommender, market_data: pd.DataFrame) -> None:
        """Should estimate margin when Treasury provided."""
        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=50.0,
            market_data=market_data,
            treasury_rate=0.04,
        )

        assert result.margin_estimate is not None
        # Margin = spread - expenses
        # Default expense = 50 bps
        expected_margin = result.spread_over_treasury - 50.0
        assert abs(result.margin_estimate - expected_margin) < 1e-6

    def test_validates_percentile_range(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should raise ValueError for invalid percentile."""
        with pytest.raises(ValueError, match="CRITICAL"):
            recommender.recommend_rate(
                guarantee_duration=5,
                target_percentile=150.0,  # Invalid
                market_data=market_data,
            )

    def test_validates_positive_duration(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should raise ValueError for non-positive duration."""
        with pytest.raises(ValueError, match="CRITICAL"):
            recommender.recommend_rate(
                guarantee_duration=0,  # Invalid
                target_percentile=50.0,
                market_data=market_data,
            )

    def test_raises_on_no_comparables(self, recommender: RateRecommender) -> None:
        """Should raise ValueError when no comparables found."""
        empty_market = pd.DataFrame(
            {
                "fixedRate": [],
                "guaranteeDuration": [],
                "productGroup": [],
                "status": [],
            }
        )

        with pytest.raises(ValueError, match="CRITICAL"):
            recommender.recommend_rate(
                guarantee_duration=5,
                target_percentile=50.0,
                market_data=empty_market,
            )

    def test_duration_matching(self, recommender: RateRecommender) -> None:
        """Should filter to similar duration products."""
        market_data = pd.DataFrame(
            {
                "fixedRate": [0.040, 0.042, 0.044, 0.055, 0.060],
                "guaranteeDuration": [5, 5, 5, 3, 10],
                "productGroup": ["MYGA"] * 5,
                "status": ["current"] * 5,
            }
        )

        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=50.0,
            market_data=market_data,
        )

        # Should only use 3 products (duration 4-6)
        assert result.comparable_count == 3

    def test_confidence_levels(self, recommender: RateRecommender) -> None:
        """Should assess confidence based on sample size and percentile."""
        # Large sample, moderate percentile -> high confidence
        large_market = pd.DataFrame(
            {
                "fixedRate": np.linspace(0.03, 0.06, 100),
                "guaranteeDuration": [5] * 100,
                "productGroup": ["MYGA"] * 100,
                "status": ["current"] * 100,
            }
        )

        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=50.0,
            market_data=large_market,
            treasury_rate=0.035,
        )

        assert result.confidence == "high"

        # Small sample -> lower confidence
        small_market = pd.DataFrame(
            {
                "fixedRate": [0.040, 0.045, 0.050],
                "guaranteeDuration": [5, 5, 5],
                "productGroup": ["MYGA"] * 3,
                "status": ["current"] * 3,
            }
        )

        result = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=50.0,
            market_data=small_market,
        )

        # Small sample reduces confidence
        assert result.confidence in ["low", "medium"]


class TestRecommendForSpread:
    """Test RateRecommender.recommend_for_spread() method."""

    @pytest.fixture
    def recommender(self) -> RateRecommender:
        return RateRecommender()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
                "guaranteeDuration": [5, 5, 5, 5, 5, 5],
                "productGroup": ["MYGA"] * 6,
                "status": ["current"] * 6,
            }
        )

    def test_calculates_rate_from_spread(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """
        [T1] Rate = Treasury + spread/10000
        """
        result = recommender.recommend_for_spread(
            guarantee_duration=5,
            treasury_rate=0.04,
            target_spread_bps=100.0,  # 100 bps = 1%
            market_data=market_data,
        )

        expected_rate = 0.04 + 0.01  # 5%
        assert abs(result.recommended_rate - expected_rate) < 1e-6

    def test_determines_percentile(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should determine percentile for recommended rate."""
        result = recommender.recommend_for_spread(
            guarantee_duration=5,
            treasury_rate=0.04,
            target_spread_bps=50.0,  # 4.5% rate
            market_data=market_data,
        )

        # 4.5% is at ~50th percentile in our sample
        assert result.target_percentile > 0
        assert result.target_percentile < 100

    def test_validates_treasury_rate(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should raise ValueError for negative treasury rate."""
        with pytest.raises(ValueError, match="CRITICAL"):
            recommender.recommend_for_spread(
                guarantee_duration=5,
                treasury_rate=-0.01,  # Invalid
                target_spread_bps=100.0,
                market_data=market_data,
            )


class TestAnalyzeMargin:
    """Test RateRecommender.analyze_margin() method."""

    @pytest.fixture
    def recommender(self) -> RateRecommender:
        return RateRecommender()

    def test_calculates_margin_breakdown(self, recommender: RateRecommender) -> None:
        """Should calculate complete margin breakdown."""
        result = recommender.analyze_margin(
            rate=0.045,
            treasury_rate=0.04,
        )

        assert isinstance(result, MarginAnalysis)
        assert abs(result.gross_spread - 50.0) < 1e-6  # 0.5% = 50 bps
        assert result.option_cost == 0.0  # MYGA has no options
        assert result.expense_load == 50.0  # Default 50 bps
        assert abs(result.net_margin - 0.0) < 1e-6  # 50 - 0 - 50 = 0

    def test_custom_expense_load(self, recommender: RateRecommender) -> None:
        """Should use custom expense load if provided."""
        result = recommender.analyze_margin(
            rate=0.045,
            treasury_rate=0.04,
            expense_load=0.003,  # 30 bps
        )

        assert result.expense_load == 30.0
        assert abs(result.net_margin - 20.0) < 1e-6  # 50 - 0 - 30 = 20

    def test_negative_margin_possible(self, recommender: RateRecommender) -> None:
        """Margin can be negative if spread < expenses."""
        result = recommender.analyze_margin(
            rate=0.041,  # Only 10 bps over Treasury
            treasury_rate=0.04,
        )

        assert abs(result.gross_spread - 10.0) < 1e-6
        assert result.net_margin < 0  # 10 - 50 = -40


class TestSensitivityAnalysis:
    """Test RateRecommender.sensitivity_analysis() method."""

    @pytest.fixture
    def recommender(self) -> RateRecommender:
        return RateRecommender()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
                "guaranteeDuration": [5, 5, 5, 5, 5, 5],
                "productGroup": ["MYGA"] * 6,
                "status": ["current"] * 6,
            }
        )

    def test_returns_dataframe(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should return DataFrame with analysis results."""
        result = recommender.sensitivity_analysis(
            guarantee_duration=5,
            market_data=market_data,
            treasury_rate=0.04,
        )

        assert isinstance(result, pd.DataFrame)
        assert "percentile" in result.columns
        assert "rate" in result.columns
        assert "spread_bps" in result.columns
        assert "margin_bps" in result.columns

    def test_default_percentile_range(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should use default percentile range [25, 50, 75, 90]."""
        result = recommender.sensitivity_analysis(
            guarantee_duration=5,
            market_data=market_data,
            treasury_rate=0.04,
        )

        assert len(result) == 4
        assert set(result["percentile"]) == {25.0, 50.0, 75.0, 90.0}

    def test_custom_percentile_range(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """Should use custom percentile range if provided."""
        result = recommender.sensitivity_analysis(
            guarantee_duration=5,
            market_data=market_data,
            treasury_rate=0.04,
            percentile_range=[10.0, 50.0, 90.0],
        )

        assert len(result) == 3
        assert set(result["percentile"]) == {10.0, 50.0, 90.0}

    def test_rate_increases_with_percentile(
        self, recommender: RateRecommender, market_data: pd.DataFrame
    ) -> None:
        """
        [T1] Higher percentile targets require higher rates.
        """
        result = recommender.sensitivity_analysis(
            guarantee_duration=5,
            market_data=market_data,
            treasury_rate=0.04,
        )

        rates = result.sort_values("percentile")["rate"].tolist()

        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1], f"Rate should increase with percentile: {rates}"
