"""
Unit tests for MYGA pricer.

Tests MYGAPricer: price(), competitive_position(), recommend_rate()
See: CONSTITUTION.md Section 4
"""

import pandas as pd
import pytest
from datetime import date

from annuity_pricing.data.schemas import MYGAProduct
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.base import PricingResult, CompetitivePosition


class TestMYGAPricerInit:
    """Test MYGAPricer initialization."""

    def test_creates_pricer(self) -> None:
        """Should create pricer instance."""
        pricer = MYGAPricer()
        assert pricer is not None


class TestMYGAPricerPrice:
    """Test MYGAPricer.price() method."""

    @pytest.fixture
    def pricer(self) -> MYGAPricer:
        return MYGAPricer()

    @pytest.fixture
    def sample_product(self) -> MYGAProduct:
        return MYGAProduct(
            company_name="Test Life",
            product_name="5-Year MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

    def test_basic_pricing(self, pricer: MYGAPricer, sample_product: MYGAProduct) -> None:
        """
        [T1] Basic MYGA pricing: FV = P(1+r)^n, PV = FV/(1+d)^n

        With rate = discount rate, PV = Principal.
        """
        result = pricer.price(sample_product, principal=100_000)

        assert isinstance(result, PricingResult)
        assert result.present_value > 0
        # When discount rate = fixed rate, PV should equal principal
        assert abs(result.present_value - 100_000) < 1e-6

    def test_pv_greater_when_discount_less(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T1] PV > Principal when discount rate < fixed rate.
        """
        result = pricer.price(
            sample_product,
            principal=100_000,
            discount_rate=0.04,  # Lower than 4.5% fixed rate
        )

        assert result.present_value > 100_000, (
            "PV should exceed principal when discount rate < fixed rate"
        )

    def test_pv_less_when_discount_greater(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T1] PV < Principal when discount rate > fixed rate.
        """
        result = pricer.price(
            sample_product,
            principal=100_000,
            discount_rate=0.05,  # Higher than 4.5% fixed rate
        )

        assert result.present_value < 100_000, (
            "PV should be less than principal when discount rate > fixed rate"
        )

    def test_duration_equals_term_for_zero_coupon(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T1] Macaulay duration = maturity for zero-coupon bond.

        MYGA with single maturity payment is effectively zero-coupon.
        """
        result = pricer.price(sample_product, principal=100_000)

        assert result.duration == 5.0, (
            "Duration should equal guarantee duration for single-payment MYGA"
        )

    def test_convexity_formula(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T1] Convexity = T(T+1)/(1+r)^2 for zero-coupon.
        """
        result = pricer.price(sample_product, principal=100_000)

        # Expected: 5 * 6 / (1.045)^2 = 30 / 1.092025 ≈ 27.47
        expected_convexity = 5 * 6 / (1.045) ** 2
        assert abs(result.convexity - expected_convexity) < 0.01, (
            f"Convexity should be {expected_convexity:.2f}, got {result.convexity:.2f}"
        )

    def test_details_include_mgsv(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """Should include MGSV floor in details."""
        result = pricer.price(sample_product, principal=100_000, include_mgsv=True)

        assert result.details is not None
        assert "mgsv" in result.details
        assert result.details["mgsv"] is not None
        assert result.details["mgsv"] > 0

    def test_mgsv_calculation(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T1] MGSV = 87.5% × Principal × (1 + 1%)^years
        """
        result = pricer.price(sample_product, principal=100_000, include_mgsv=True)

        # Expected: 0.875 * 100000 * (1.01)^5 ≈ 91,945.57
        expected_mgsv = 0.875 * 100_000 * (1.01) ** 5
        assert abs(result.details["mgsv"] - expected_mgsv) < 1.0, (
            f"MGSV should be {expected_mgsv:.2f}, got {result.details['mgsv']:.2f}"
        )

    def test_validates_required_fields(self, pricer: MYGAPricer) -> None:
        """Should raise ValueError for missing required fields."""
        invalid_product = MYGAProduct(
            company_name="Test",
            product_name="Test",
            product_group="MYGA",
            status="current",
            # Missing fixed_rate and guarantee_duration
        )

        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.price(invalid_product)

    def test_validates_positive_duration(self, pricer: MYGAPricer) -> None:
        """Should raise ValueError for non-positive duration."""
        invalid_product = MYGAProduct(
            company_name="Test",
            product_name="Test",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=0,  # Invalid
        )

        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.price(invalid_product)

    def test_returns_as_of_date(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """Should return provided as_of_date."""
        test_date = date(2025, 1, 15)
        result = pricer.price(sample_product, as_of_date=test_date)

        assert result.as_of_date == test_date


class TestMYGAPricerCompetitivePosition:
    """Test MYGAPricer.competitive_position() method."""

    @pytest.fixture
    def pricer(self) -> MYGAPricer:
        return MYGAPricer()

    @pytest.fixture
    def sample_product(self) -> MYGAProduct:
        return MYGAProduct(
            company_name="Test Life",
            product_name="5-Year MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        """Create sample market data with known distribution."""
        return pd.DataFrame({
            "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
        })

    def test_returns_competitive_position(
        self,
        pricer: MYGAPricer,
        sample_product: MYGAProduct,
        market_data: pd.DataFrame,
    ) -> None:
        """Should return CompetitivePosition result."""
        result = pricer.competitive_position(sample_product, market_data)

        assert isinstance(result, CompetitivePosition)
        assert result.rate == 0.045
        assert 0 <= result.percentile <= 100
        assert result.total_products == 6

    def test_percentile_calculation(
        self,
        pricer: MYGAPricer,
        sample_product: MYGAProduct,
        market_data: pd.DataFrame,
    ) -> None:
        """
        [T2] Percentile = count(rate <= product_rate) / total.

        For rate 0.045 in [0.040, 0.042, 0.044, 0.046, 0.048, 0.050]:
        - 3 rates <= 0.045 (0.040, 0.042, 0.044)
        - Percentile = 3/6 * 100 = 50%
        """
        result = pricer.competitive_position(sample_product, market_data)

        # 3 out of 6 rates are <= 0.045
        expected_percentile = (3 / 6) * 100
        assert result.percentile == expected_percentile, (
            f"Expected percentile {expected_percentile}, got {result.percentile}"
        )

    def test_rank_calculation(
        self,
        pricer: MYGAPricer,
        sample_product: MYGAProduct,
        market_data: pd.DataFrame,
    ) -> None:
        """
        Rank = count(rate > product_rate) + 1.

        For rate 0.045: 3 rates > 0.045, so rank = 4.
        """
        result = pricer.competitive_position(sample_product, market_data)

        # 3 rates > 0.045 (0.046, 0.048, 0.050), rank = 4
        assert result.rank == 4

    def test_duration_matching(
        self,
        pricer: MYGAPricer,
        sample_product: MYGAProduct,
    ) -> None:
        """Should filter to similar duration products."""
        # Market data with mixed durations
        market_data = pd.DataFrame({
            "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050, 0.055],
            "guaranteeDuration": [5, 5, 5, 5, 5, 3, 10],  # Last two different duration
            "productGroup": ["MYGA"] * 7,
            "status": ["current"] * 7,
        })

        result = pricer.competitive_position(sample_product, market_data, duration_match=True)

        # Should only use 5-year products (5 of them)
        assert result.total_products == 5

    def test_raises_on_empty_comparables(
        self,
        pricer: MYGAPricer,
        sample_product: MYGAProduct,
    ) -> None:
        """Should raise ValueError when no comparable products found."""
        empty_market = pd.DataFrame({
            "fixedRate": [],
            "guaranteeDuration": [],
            "productGroup": [],
            "status": [],
        })

        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.competitive_position(sample_product, empty_market)


class TestMYGAPricerRecommendRate:
    """Test MYGAPricer.recommend_rate() method."""

    @pytest.fixture
    def pricer(self) -> MYGAPricer:
        return MYGAPricer()

    @pytest.fixture
    def market_data(self) -> pd.DataFrame:
        """Create sample market data."""
        return pd.DataFrame({
            "fixedRate": [0.040, 0.042, 0.044, 0.046, 0.048, 0.050],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
        })

    def test_recommends_rate_for_percentile(
        self, pricer: MYGAPricer, market_data: pd.DataFrame
    ) -> None:
        """Should recommend rate to achieve target percentile."""
        rate = pricer.recommend_rate(
            target_percentile=75,
            market_data=market_data,
            guarantee_duration=5,
        )

        # 75th percentile of [0.040, 0.042, 0.044, 0.046, 0.048, 0.050]
        # Using numpy percentile logic
        import numpy as np
        expected = np.percentile([0.040, 0.042, 0.044, 0.046, 0.048, 0.050], 75)
        assert abs(rate - expected) < 1e-6

    def test_validates_percentile_range(
        self, pricer: MYGAPricer, market_data: pd.DataFrame
    ) -> None:
        """Should raise ValueError for invalid percentile."""
        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.recommend_rate(
                target_percentile=150,  # Invalid
                market_data=market_data,
                guarantee_duration=5,
            )

    def test_raises_on_no_comparables(
        self, pricer: MYGAPricer
    ) -> None:
        """Should raise ValueError when no comparables found."""
        empty_market = pd.DataFrame({
            "fixedRate": [],
            "guaranteeDuration": [],
            "productGroup": [],
            "status": [],
        })

        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.recommend_rate(
                target_percentile=50,
                market_data=empty_market,
                guarantee_duration=5,
            )


class TestMYGAPricerSpreadOverTreasury:
    """Test spread calculation."""

    @pytest.fixture
    def pricer(self) -> MYGAPricer:
        return MYGAPricer()

    @pytest.fixture
    def sample_product(self) -> MYGAProduct:
        return MYGAProduct(
            company_name="Test Life",
            product_name="5-Year MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

    def test_spread_calculation_bps(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """
        [T2] Spread = (product_rate - treasury_rate) × 10000 bps.
        """
        spread = pricer.calculate_spread_over_treasury(
            sample_product,
            treasury_rate=0.04,
        )

        # 4.5% - 4.0% = 0.5% = 50 bps
        assert abs(spread - 50.0) < 1e-6

    def test_negative_spread(
        self, pricer: MYGAPricer, sample_product: MYGAProduct
    ) -> None:
        """Spread can be negative if treasury exceeds product rate."""
        spread = pricer.calculate_spread_over_treasury(
            sample_product,
            treasury_rate=0.05,  # Higher than 4.5%
        )

        # 4.5% - 5.0% = -0.5% = -50 bps
        assert abs(spread - (-50.0)) < 1e-6
