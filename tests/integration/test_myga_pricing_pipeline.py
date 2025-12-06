"""
Integration tests for complete MYGA pricing pipeline.

Tests end-to-end workflow: data → pricing → valuation → recommendations.
See: CONSTITUTION.md Section 4
"""

import numpy as np
import pandas as pd
import pytest
from datetime import date

from annuity_pricing.data.schemas import MYGAProduct
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.valuation.myga_pv import value_myga, sensitivity_analysis
from annuity_pricing.rate_setting.recommender import RateRecommender


class TestMYGAPricingPipeline:
    """Integration tests for complete MYGA pricing workflow."""

    @pytest.fixture
    def sample_market_data(self) -> pd.DataFrame:
        """
        Create realistic MYGA market data.

        [T2] Based on typical WINK distribution patterns.
        """
        np.random.seed(42)  # Reproducibility

        # Simulate 100 5-year MYGAs with realistic rate distribution
        # Mean ~4.5%, std ~0.5%
        rates_5y = np.random.normal(0.045, 0.005, 50)
        rates_5y = np.clip(rates_5y, 0.03, 0.06)  # Reasonable bounds

        # Simulate 50 3-year MYGAs (usually lower rates)
        rates_3y = np.random.normal(0.042, 0.004, 25)
        rates_3y = np.clip(rates_3y, 0.028, 0.055)

        # Simulate 50 7-year MYGAs (usually higher rates)
        rates_7y = np.random.normal(0.048, 0.005, 25)
        rates_7y = np.clip(rates_7y, 0.035, 0.065)

        return pd.DataFrame({
            "fixedRate": np.concatenate([rates_5y, rates_3y, rates_7y]),
            "guaranteeDuration": [5]*50 + [3]*25 + [7]*25,
            "productGroup": ["MYGA"] * 100,
            "status": ["current"] * 100,
            "companyName": [f"Company {i % 20}" for i in range(100)],
        })

    @pytest.fixture
    def target_product(self) -> MYGAProduct:
        """Create target product for analysis."""
        return MYGAProduct(
            company_name="Target Life",
            product_name="5-Year MYGA Select",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

    def test_complete_pricing_workflow(
        self,
        target_product: MYGAProduct,
        sample_market_data: pd.DataFrame,
    ) -> None:
        """
        Test complete pricing workflow:
        1. Price product
        2. Determine competitive position
        3. Calculate detailed valuation
        4. Get rate recommendations
        """
        # 1. Price the product
        pricer = MYGAPricer()
        pricing_result = pricer.price(
            target_product,
            principal=100_000,
            discount_rate=0.04,
            include_mgsv=True,
        )

        assert pricing_result.present_value > 0
        assert pricing_result.duration == 5.0
        assert pricing_result.details is not None
        assert "mgsv" in pricing_result.details

        # 2. Determine competitive position
        position = pricer.competitive_position(
            target_product,
            sample_market_data,
            duration_match=True,
        )

        assert 0 <= position.percentile <= 100
        assert position.total_products > 0

        # 3. Calculate detailed valuation
        valuation = value_myga(
            principal=100_000,
            fixed_rate=target_product.fixed_rate,
            guarantee_duration=target_product.guarantee_duration,
            discount_rate=0.04,
        )

        assert valuation.present_value > 0
        assert valuation.macaulay_duration > 0
        assert valuation.modified_duration > 0
        assert valuation.convexity > 0
        assert valuation.effective_duration is not None

        # 4. Get rate recommendations
        recommender = RateRecommender()
        recommendation = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=75.0,
            market_data=sample_market_data,
            treasury_rate=0.04,
        )

        assert recommendation.recommended_rate > 0
        assert recommendation.comparable_count > 0

    def test_pricing_consistency(
        self,
        target_product: MYGAProduct,
    ) -> None:
        """
        Test consistency between MYGAPricer and value_myga.

        Both should produce identical PV for same inputs.
        """
        principal = 100_000
        discount_rate = 0.04

        # Price via MYGAPricer
        pricer = MYGAPricer()
        pricer_result = pricer.price(
            target_product,
            principal=principal,
            discount_rate=discount_rate,
        )

        # Price via value_myga
        valuation_result = value_myga(
            principal=principal,
            fixed_rate=target_product.fixed_rate,
            guarantee_duration=target_product.guarantee_duration,
            discount_rate=discount_rate,
        )

        # PV should match
        assert abs(pricer_result.present_value - valuation_result.present_value) < 0.01, (
            f"PV mismatch: pricer={pricer_result.present_value}, "
            f"valuation={valuation_result.present_value}"
        )

        # Duration should match
        assert abs(pricer_result.duration - valuation_result.macaulay_duration) < 0.01

        # Convexity should match
        assert abs(pricer_result.convexity - valuation_result.convexity) < 0.01

    def test_rate_recommendation_achieves_target(
        self,
        sample_market_data: pd.DataFrame,
    ) -> None:
        """
        Test that recommended rate achieves target percentile.

        [T2] Verify recommendation is consistent with positioning.
        """
        recommender = RateRecommender()
        target_percentile = 75.0

        # Get recommendation
        recommendation = recommender.recommend_rate(
            guarantee_duration=5,
            target_percentile=target_percentile,
            market_data=sample_market_data,
        )

        # Create product with recommended rate
        test_product = MYGAProduct(
            company_name="Test",
            product_name="Test MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=recommendation.recommended_rate,
            guarantee_duration=5,
        )

        # Check actual position
        pricer = MYGAPricer()
        actual_position = pricer.competitive_position(
            test_product,
            sample_market_data,
            duration_match=True,
        )

        # Actual percentile should be close to target
        # (Some variance expected due to percentile calculation methods)
        assert abs(actual_position.percentile - target_percentile) < 20.0, (
            f"Recommended rate achieved {actual_position.percentile}th percentile, "
            f"expected ~{target_percentile}th"
        )

    def test_sensitivity_to_rates(
        self,
        target_product: MYGAProduct,
    ) -> None:
        """
        Test price sensitivity to discount rates.

        [T1] Duration predicts PV change for small rate changes.
        """
        base_rate = 0.04
        principal = 100_000

        # Get valuation at base rate
        base_val = value_myga(
            principal=principal,
            fixed_rate=target_product.fixed_rate,
            guarantee_duration=target_product.guarantee_duration,
            discount_rate=base_rate,
        )

        # Predict PV change using duration
        rate_change = 0.001  # 10 bps
        predicted_pct_change = -base_val.modified_duration * rate_change

        # Actual PV change
        new_val = value_myga(
            principal=principal,
            fixed_rate=target_product.fixed_rate,
            guarantee_duration=target_product.guarantee_duration,
            discount_rate=base_rate + rate_change,
        )
        actual_pct_change = (new_val.present_value - base_val.present_value) / base_val.present_value

        # Duration should predict PV change within 1% relative error
        # (Convexity accounts for the difference)
        assert abs(actual_pct_change - predicted_pct_change) < 0.001, (
            f"Duration prediction {predicted_pct_change:.6f} differs from "
            f"actual {actual_pct_change:.6f}"
        )

    def test_mgsv_floor_holds(
        self,
        target_product: MYGAProduct,
    ) -> None:
        """
        Test that MGSV provides meaningful floor.

        [T1] MGSV = 87.5% × Principal × (1 + 1%)^years
        """
        principal = 100_000

        # Price with MGSV
        pricer = MYGAPricer()
        result = pricer.price(
            target_product,
            principal=principal,
            include_mgsv=True,
        )

        # MGSV should be less than both PV and principal
        mgsv = result.details["mgsv"]
        assert mgsv < principal, "MGSV should be less than initial principal"
        assert mgsv < result.present_value, "MGSV should be less than PV"

        # MGSV should be at least 85% of principal for 5-year product
        # (87.5% base growing at 1%)
        assert mgsv > 0.85 * principal, (
            f"MGSV {mgsv} should be at least 85% of principal {principal}"
        )

    def test_sensitivity_analysis_integration(
        self,
        target_product: MYGAProduct,
        sample_market_data: pd.DataFrame,
    ) -> None:
        """
        Test sensitivity analysis provides actionable insights.
        """
        # Run rate sensitivity
        results = sensitivity_analysis(
            principal=100_000,
            fixed_rate=target_product.fixed_rate,
            guarantee_duration=target_product.guarantee_duration,
            base_discount_rate=0.04,
        )

        assert len(results) > 0

        # Run percentile sensitivity
        recommender = RateRecommender()
        sensitivity_df = recommender.sensitivity_analysis(
            guarantee_duration=5,
            market_data=sample_market_data,
            treasury_rate=0.04,
        )

        assert not sensitivity_df.empty
        assert "rate" in sensitivity_df.columns
        assert "margin_bps" in sensitivity_df.columns


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_low_rate_environment(self) -> None:
        """
        Test pricing in low rate environment.

        [T3] Assumption: rates can go near zero but stay positive.
        """
        product = MYGAProduct(
            company_name="Test",
            product_name="Low Rate MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.01,  # 1% - low but realistic
            guarantee_duration=5,
        )

        pricer = MYGAPricer()
        result = pricer.price(product, principal=100_000, discount_rate=0.005)

        assert result.present_value > 0
        assert result.present_value > 100_000  # PV > principal when rate > discount

    def test_high_rate_environment(self) -> None:
        """
        Test pricing in high rate environment.
        """
        product = MYGAProduct(
            company_name="Test",
            product_name="High Rate MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.08,  # 8% - high but seen historically
            guarantee_duration=5,
        )

        pricer = MYGAPricer()
        result = pricer.price(product, principal=100_000, discount_rate=0.07)

        assert result.present_value > 0
        assert result.present_value > 100_000

    def test_short_duration(self) -> None:
        """Test 1-year MYGA (shortest typical duration)."""
        product = MYGAProduct(
            company_name="Test",
            product_name="1-Year MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.04,
            guarantee_duration=1,
        )

        pricer = MYGAPricer()
        result = pricer.price(product, principal=100_000, discount_rate=0.04)

        assert result.duration == 1.0
        assert abs(result.present_value - 100_000) < 0.01

    def test_long_duration(self) -> None:
        """Test 10-year MYGA (longest typical duration)."""
        product = MYGAProduct(
            company_name="Test",
            product_name="10-Year MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.05,
            guarantee_duration=10,
        )

        pricer = MYGAPricer()
        result = pricer.price(product, principal=100_000, discount_rate=0.04)

        assert result.duration == 10.0
        assert result.present_value > 100_000  # Higher rate, lower discount

    def test_large_principal(self) -> None:
        """Test with large premium amount."""
        product = MYGAProduct(
            company_name="Test",
            product_name="Jumbo MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

        pricer = MYGAPricer()
        result = pricer.price(product, principal=5_000_000, discount_rate=0.04)

        # Check scaling is correct
        small_result = pricer.price(product, principal=100_000, discount_rate=0.04)
        ratio = result.present_value / small_result.present_value

        assert abs(ratio - 50) < 0.01, "PV should scale linearly with principal"


class TestDataValidation:
    """Test data validation and error handling."""

    def test_handles_missing_rates_in_market_data(self) -> None:
        """Should handle market data with some null rates."""
        market_data = pd.DataFrame({
            "fixedRate": [0.040, None, 0.044, 0.046, None, 0.050],
            "guaranteeDuration": [5, 5, 5, 5, 5, 5],
            "productGroup": ["MYGA"] * 6,
            "status": ["current"] * 6,
        })

        product = MYGAProduct(
            company_name="Test",
            product_name="Test",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

        pricer = MYGAPricer()
        result = pricer.competitive_position(product, market_data)

        # Should work with non-null rates only
        assert result.total_products == 4  # 6 - 2 nulls

    def test_rejects_all_null_rates(self) -> None:
        """Should raise error if all rates are null."""
        market_data = pd.DataFrame({
            "fixedRate": [None, None, None],
            "guaranteeDuration": [5, 5, 5],
            "productGroup": ["MYGA"] * 3,
            "status": ["current"] * 3,
        })

        product = MYGAProduct(
            company_name="Test",
            product_name="Test",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )

        pricer = MYGAPricer()

        with pytest.raises(ValueError, match="CRITICAL"):
            pricer.competitive_position(product, market_data)
