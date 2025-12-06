"""
Unit tests for competitive rankings module.

Tests RankingAnalyzer: rank_companies(), rank_products(), etc.
See: CONSTITUTION.md Section 5
"""

import numpy as np
import pandas as pd
import pytest

from annuity_pricing.competitive.rankings import (
    CompanyRanking,
    ProductRanking,
    RankingAnalyzer,
)


class TestCompanyRanking:
    """Test CompanyRanking dataclass."""

    def test_creates_ranking(self) -> None:
        """Should create company ranking."""
        ranking = CompanyRanking(
            company="Test Life",
            rank=1,
            best_rate=0.05,
            avg_rate=0.048,
            product_count=5,
            duration_coverage=(3, 5, 7),
        )

        assert ranking.company == "Test Life"
        assert ranking.rank == 1
        assert ranking.best_rate == 0.05


class TestProductRanking:
    """Test ProductRanking dataclass."""

    def test_creates_ranking(self) -> None:
        """Should create product ranking."""
        ranking = ProductRanking(
            company="Test Life",
            product="5-Year MYGA",
            rank=1,
            rate=0.05,
            duration=5,
        )

        assert ranking.product == "5-Year MYGA"
        assert ranking.rate == 0.05


class TestRankingAnalyzerInit:
    """Test RankingAnalyzer initialization."""

    def test_default_columns(self) -> None:
        """Should use default column names."""
        analyzer = RankingAnalyzer()

        assert analyzer.rate_column == "fixedRate"
        assert analyzer.company_column == "companyName"


class TestRankCompanies:
    """Test RankingAnalyzer.rank_companies() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.048, 0.045, 0.046, 0.044, 0.042],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
            "companyName": ["A", "A", "B", "B", "C", "C"],
            "productName": ["A1", "A2", "B1", "B2", "C1", "C2"],
        })

    def test_returns_company_rankings(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return list of CompanyRanking."""
        rankings = analyzer.rank_companies(market_data)

        assert isinstance(rankings, list)
        assert len(rankings) == 3
        assert all(isinstance(r, CompanyRanking) for r in rankings)

    def test_ranks_by_best_rate(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should rank companies by best rate (default)."""
        rankings = analyzer.rank_companies(market_data)

        # Company A has best rate (0.050)
        assert rankings[0].company == "A"
        assert rankings[0].rank == 1
        assert rankings[0].best_rate == 0.050

    def test_ranks_by_product_count(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should rank by product count when specified."""
        rankings = analyzer.rank_companies(market_data, rank_by="product_count")

        # All companies have 2 products, so order may vary
        assert all(r.product_count == 2 for r in rankings)

    def test_top_n_limit(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should limit to top N companies."""
        rankings = analyzer.rank_companies(market_data, top_n=2)

        assert len(rankings) == 2
        assert rankings[0].rank == 1
        assert rankings[1].rank == 2

    def test_product_group_filter(
        self, analyzer: RankingAnalyzer
    ) -> None:
        """Should filter by product group."""
        market_data = pd.DataFrame({
            "fixedRate": [0.050, 0.045, 0.048],
            "guaranteeDuration": [5, 5, 5],
            "productGroup": ["MYGA", "MYGA", "FIA"],
            "status": ["current"] * 3,
            "companyName": ["A", "B", "C"],
        })

        rankings = analyzer.rank_companies(market_data, product_group="MYGA")

        # Only 2 MYGA companies
        assert len(rankings) == 2

    def test_duration_filter(
        self, analyzer: RankingAnalyzer
    ) -> None:
        """Should filter by duration."""
        market_data = pd.DataFrame({
            "fixedRate": [0.050, 0.045, 0.048],
            "guaranteeDuration": [5, 3, 10],
            "productGroup": ["MYGA"] * 3,
            "status": ["current"] * 3,
            "companyName": ["A", "B", "C"],
        })

        rankings = analyzer.rank_companies(
            market_data,
            guarantee_duration=5,
            duration_tolerance=1,
        )

        # Only company A has 5-year product
        assert len(rankings) == 1
        assert rankings[0].company == "A"

    def test_raises_on_no_products(
        self, analyzer: RankingAnalyzer
    ) -> None:
        """Should raise if no products found."""
        empty_data = pd.DataFrame({
            "fixedRate": [],
            "guaranteeDuration": [],
            "productGroup": [],
            "status": [],
            "companyName": [],
        })

        with pytest.raises(ValueError, match="CRITICAL"):
            analyzer.rank_companies(empty_data)


class TestRankProducts:
    """Test RankingAnalyzer.rank_products() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.048, 0.045, 0.042],
            "guaranteeDuration": [5, 5, 5, 5],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
            "companyName": ["A", "B", "C", "D"],
            "productName": ["P1", "P2", "P3", "P4"],
        })

    def test_returns_product_rankings(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return list of ProductRanking."""
        rankings = analyzer.rank_products(market_data)

        assert isinstance(rankings, list)
        assert len(rankings) == 4
        assert all(isinstance(r, ProductRanking) for r in rankings)

    def test_ranks_by_rate(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should rank products by rate (highest first)."""
        rankings = analyzer.rank_products(market_data)

        assert rankings[0].rate == 0.050
        assert rankings[0].rank == 1
        assert rankings[-1].rate == 0.042
        assert rankings[-1].rank == 4

    def test_top_n_limit(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should limit to top N products."""
        rankings = analyzer.rank_products(market_data, top_n=2)

        assert len(rankings) == 2


class TestGetCompanyRank:
    """Test RankingAnalyzer.get_company_rank() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.045, 0.040],
            "guaranteeDuration": [5, 5, 5],
            "productGroup": ["MYGA"] * 3,
            "status": ["current"] * 3,
            "companyName": ["A", "B", "C"],
        })

    def test_finds_company(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should find and return company ranking."""
        ranking = analyzer.get_company_rank("B", market_data)

        assert ranking is not None
        assert ranking.company == "B"
        assert ranking.rank == 2

    def test_returns_none_for_unknown(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return None for unknown company."""
        ranking = analyzer.get_company_rank("Unknown", market_data)

        assert ranking is None

    def test_case_insensitive(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should match company name case-insensitively."""
        ranking = analyzer.get_company_rank("b", market_data)

        assert ranking is not None
        assert ranking.company == "B"


class TestMarketSummary:
    """Test RankingAnalyzer.market_summary() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.045, 0.040, 0.048],
            "guaranteeDuration": [5, 5, 3, 7],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
            "companyName": ["A", "B", "C", "A"],
        })

    def test_returns_summary(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return market summary dict."""
        summary = analyzer.market_summary(market_data)

        assert isinstance(summary, dict)
        assert "total_products" in summary
        assert "total_companies" in summary
        assert "rate_min" in summary
        assert "rate_max" in summary

    def test_correct_statistics(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should calculate correct statistics."""
        summary = analyzer.market_summary(market_data)

        assert summary["total_products"] == 4
        assert summary["total_companies"] == 3  # A, B, C
        assert summary["rate_min"] == 0.040
        assert summary["rate_max"] == 0.050


class TestRateLeadersByDuration:
    """Test RankingAnalyzer.rate_leaders_by_duration() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.048, 0.052, 0.049],
            "guaranteeDuration": [5, 5, 7, 7],
            "productGroup": ["MYGA"] * 4,
            "status": ["current"] * 4,
            "companyName": ["A", "B", "C", "D"],
            "productName": ["A5", "B5", "C7", "D7"],
        })

    def test_returns_leaders_df(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return DataFrame with leaders by duration."""
        leaders = analyzer.rate_leaders_by_duration(market_data)

        assert isinstance(leaders, pd.DataFrame)
        assert "duration" in leaders.columns
        assert "rank" in leaders.columns
        assert "rate" in leaders.columns

    def test_correct_leaders(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should identify correct leaders for each duration."""
        leaders = analyzer.rate_leaders_by_duration(market_data)

        # 5-year leader
        five_year = leaders[(leaders["duration"] == 5) & (leaders["rank"] == 1)]
        assert len(five_year) == 1
        assert five_year.iloc[0]["company"] == "A"

        # 7-year leader
        seven_year = leaders[(leaders["duration"] == 7) & (leaders["rank"] == 1)]
        assert len(seven_year) == 1
        assert seven_year.iloc[0]["company"] == "C"


class TestCompetitiveLandscape:
    """Test RankingAnalyzer.competitive_landscape() method."""

    @pytest.fixture
    def analyzer(self) -> RankingAnalyzer:
        return RankingAnalyzer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "fixedRate": [0.050, 0.048, 0.045, 0.042, 0.040],
            "guaranteeDuration": [5] * 5,
            "productGroup": ["MYGA"] * 5,
            "status": ["current"] * 5,
            "companyName": ["A", "B", "C", "D", "E"],
        })

    def test_returns_landscape_df(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should return landscape DataFrame."""
        landscape = analyzer.competitive_landscape(market_data)

        assert isinstance(landscape, pd.DataFrame)
        assert "companyName" in landscape.columns
        assert "best_rate" in landscape.columns
        assert "tier" in landscape.columns

    def test_assigns_tiers(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should assign competitive tiers."""
        landscape = analyzer.competitive_landscape(market_data)

        # Top company should be "Leader"
        top_company = landscape[landscape["rank"] == 1]
        assert top_company.iloc[0]["tier"] == "Leader"

    def test_calculates_percentiles(
        self, analyzer: RankingAnalyzer, market_data: pd.DataFrame
    ) -> None:
        """Should calculate rate percentiles."""
        landscape = analyzer.competitive_landscape(market_data)

        assert "rate_percentile" in landscape.columns
        # Top company should be 100th percentile
        top = landscape[landscape["rank"] == 1]
        assert top.iloc[0]["rate_percentile"] == 100.0
