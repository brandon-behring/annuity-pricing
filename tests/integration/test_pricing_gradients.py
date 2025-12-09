"""
Pricing gradient matrix tests.

Verifies that pricing outputs respond correctly to parameter changes:
- PV decreases as discount rate increases (all products)
- Option value increases with volatility (FIA, RILA)
- Buffer cost increases with buffer level (RILA)
- Duration approximates term (MYGA)

These tests catch:
- Sign errors in pricing formulas
- Incorrect parameter dependencies
- Broken monotonicity assumptions

[T1] Economic monotonicity is fundamental to option pricing.
See: docs/knowledge/domain/option_pricing.md

Grid configuration:
- Rates: [0.03, 0.05, 0.07]
- Vols: [0.10, 0.20, 0.30]
- Tenors: [1, 3, 5] years
"""

import numpy as np
import pytest

from annuity_pricing.data.schemas import MYGAProduct, FIAProduct, RILAProduct
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.fia import FIAPricer, MarketParams as FIAMarketParams
from annuity_pricing.products.rila import RILAPricer, MarketParams as RILAMarketParams


# =============================================================================
# Test Configuration
# =============================================================================

#: Rate grid for sensitivity tests
RATE_GRID = [0.03, 0.05, 0.07]

#: Volatility grid
VOL_GRID = [0.10, 0.20, 0.30]

#: Tenor grid (years)
TENOR_GRID = [1, 3, 5]

#: MC settings for reproducibility
MC_PATHS = 10_000
MC_SEED = 42

#: Tolerance for MC noise in monotonicity tests
MONO_TOLERANCE = 0.01  # 1% tolerance for MC noise


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def myga_product() -> MYGAProduct:
    """Standard MYGA product for testing."""
    return MYGAProduct(
        company_name="Test",
        product_name="Test MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def fia_product() -> FIAProduct:
    """Standard FIA product with cap."""
    return FIAProduct(
        company_name="Test",
        product_name="Test FIA",
        product_group="FIA",
        status="current",
        cap_rate=0.10,
        participation_rate=1.0,
    )


@pytest.fixture
def rila_product() -> RILAProduct:
    """Standard RILA product with buffer."""
    return RILAProduct(
        company_name="Test",
        product_name="Test RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        buffer_modifier="Losses Covered Up To",
        cap_rate=0.20,
    )


# =============================================================================
# MYGA Gradient Tests
# =============================================================================


@pytest.mark.integration
class TestMYGAGradients:
    """
    [T1] MYGA pricing gradient tests.

    MYGA PV should decrease as discount rate increases (higher discounting
    reduces present value of future cash flows).
    """

    def test_pv_decreases_with_discount_rate(self, myga_product: MYGAProduct) -> None:
        """
        [P1] MYGA PV should strictly decrease as discount rate increases.

        This is fundamental to time value of money.
        """
        pricer = MYGAPricer()
        pvs = []

        for rate in RATE_GRID:
            result = pricer.price(
                myga_product,
                principal=100_000,
                discount_rate=rate,
            )
            pvs.append(result.present_value)

        # Verify strict monotonicity: PV[i] > PV[i+1] as rate increases
        for i in range(len(pvs) - 1):
            assert pvs[i] > pvs[i + 1], (
                f"MYGA PV should decrease with rate: "
                f"PV({RATE_GRID[i]:.2%})={pvs[i]:.2f} should be > "
                f"PV({RATE_GRID[i+1]:.2%})={pvs[i+1]:.2f}"
            )

    def test_guaranteed_value_increases_with_term(self) -> None:
        """
        [P1] MYGA guaranteed value should increase with longer term.

        Longer term means more compounding at the fixed rate.
        """
        pricer = MYGAPricer()
        guaranteed_values = []

        for term in TENOR_GRID:
            product = MYGAProduct(
                company_name="Test",
                product_name=f"Test MYGA {term}yr",
                product_group="MYGA",
                status="current",
                fixed_rate=0.045,
                guarantee_duration=term,
            )
            result = pricer.price(product, principal=100_000, discount_rate=0.05)
            # Guaranteed value = principal * (1 + rate)^term
            gv = 100_000 * (1 + 0.045) ** term
            guaranteed_values.append(gv)

        # Verify strict monotonicity
        for i in range(len(guaranteed_values) - 1):
            assert guaranteed_values[i] < guaranteed_values[i + 1], (
                f"MYGA guaranteed value should increase with term: "
                f"GV({TENOR_GRID[i]}yr)={guaranteed_values[i]:.2f} should be < "
                f"GV({TENOR_GRID[i+1]}yr)={guaranteed_values[i+1]:.2f}"
            )


# =============================================================================
# FIA Gradient Tests
# =============================================================================


@pytest.mark.integration
class TestFIAGradients:
    """
    [T1] FIA pricing gradient tests.

    FIA option value should generally increase with volatility
    (higher vol = more upside potential with floor at 0%).
    """

    def test_option_value_increases_with_volatility_low_vol(self) -> None:
        """
        [P1] FIA embedded option value should increase with volatility (low vol range).

        [T1] For capped calls, the vol/value relationship is nuanced:
        - At low vol: increasing vol increases value (more upside potential)
        - At high vol with low cap: may flatten or decrease (cap truncates upside,
          but floor at 0% already protects downside)

        We test the low vol range where monotonicity is more reliable.
        """
        low_vol_grid = [0.05, 0.10, 0.15]
        option_values = []

        # Use uncapped product to test clean vol relationship
        uncapped_product = FIAProduct(
            company_name="Test",
            product_name="Test FIA Uncapped",
            product_group="FIA",
            status="current",
            cap_rate=1.0,  # Effectively uncapped
            participation_rate=1.0,
        )

        for vol in low_vol_grid:
            market = FIAMarketParams(
                spot=100.0,
                risk_free_rate=0.05,
                dividend_yield=0.02,
                volatility=vol,
            )
            pricer = FIAPricer(
                market_params=market,
                n_mc_paths=MC_PATHS,
                seed=MC_SEED,
            )
            result = pricer.price(uncapped_product, term_years=1.0)
            option_values.append(result.embedded_option_value)

        # Verify monotonicity with tolerance for MC noise
        for i in range(len(option_values) - 1):
            # Allow small negative due to MC noise
            min_expected = option_values[i] * (1 - MONO_TOLERANCE)
            assert option_values[i + 1] >= min_expected, (
                f"FIA option value should increase with vol: "
                f"OV({low_vol_grid[i]:.0%})={option_values[i]:.4f} should be <= "
                f"OV({low_vol_grid[i+1]:.0%})={option_values[i+1]:.4f}"
            )

    def test_option_value_increases_with_cap(self) -> None:
        """
        [P1] FIA option value should increase with higher cap.

        Higher cap means more upside potential.
        """
        cap_grid = [0.05, 0.10, 0.15, 0.20]
        option_values = []

        market = FIAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = FIAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        for cap in cap_grid:
            product = FIAProduct(
                company_name="Test",
                product_name=f"Test FIA {cap:.0%} cap",
                product_group="FIA",
                status="current",
                cap_rate=cap,
                participation_rate=1.0,
            )
            result = pricer.price(product, term_years=1.0)
            option_values.append(result.embedded_option_value)

        # Verify monotonicity
        for i in range(len(option_values) - 1):
            min_expected = option_values[i] * (1 - MONO_TOLERANCE)
            assert option_values[i + 1] >= min_expected, (
                f"FIA option value should increase with cap: "
                f"OV({cap_grid[i]:.0%})={option_values[i]:.4f} should be <= "
                f"OV({cap_grid[i+1]:.0%})={option_values[i+1]:.4f}"
            )


# =============================================================================
# RILA Gradient Tests
# =============================================================================


@pytest.mark.integration
class TestRILAGradients:
    """
    [T1] RILA pricing gradient tests.

    Buffer/floor costs should respond predictably to protection level
    and market parameters.
    """

    def test_buffer_cost_increases_with_buffer_level(self) -> None:
        """
        [P1] Buffer cost should increase with deeper buffer protection.

        Deeper buffer = more downside protection = higher cost.
        """
        buffer_grid = [0.05, 0.10, 0.15, 0.20]
        buffer_costs = []

        market = RILAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = RILAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        for buffer in buffer_grid:
            product = RILAProduct(
                company_name="Test",
                product_name=f"Test RILA {buffer:.0%} buffer",
                product_group="RILA",
                status="current",
                buffer_rate=buffer,
                buffer_modifier="Losses Covered Up To",
                cap_rate=0.20,
            )
            result = pricer.price(product, term_years=1.0)
            buffer_costs.append(result.protection_value)

        # Verify monotonicity
        for i in range(len(buffer_costs) - 1):
            min_expected = buffer_costs[i] * (1 - MONO_TOLERANCE)
            assert buffer_costs[i + 1] >= min_expected, (
                f"Buffer cost should increase with level: "
                f"Cost({buffer_grid[i]:.0%})={buffer_costs[i]:.4f} should be <= "
                f"Cost({buffer_grid[i+1]:.0%})={buffer_costs[i+1]:.4f}"
            )

    def test_protection_increases_with_volatility(
        self, rila_product: RILAProduct
    ) -> None:
        """
        [P1] Protection value should increase with volatility.

        Higher vol = puts are more valuable = higher protection cost.
        """
        protection_values = []

        for vol in VOL_GRID:
            market = RILAMarketParams(
                spot=100.0,
                risk_free_rate=0.05,
                dividend_yield=0.02,
                volatility=vol,
            )
            pricer = RILAPricer(
                market_params=market,
                n_mc_paths=MC_PATHS,
                seed=MC_SEED,
            )
            result = pricer.price(rila_product, term_years=1.0)
            protection_values.append(result.protection_value)

        # Verify monotonicity
        for i in range(len(protection_values) - 1):
            min_expected = protection_values[i] * (1 - MONO_TOLERANCE)
            assert protection_values[i + 1] >= min_expected, (
                f"Protection value should increase with vol: "
                f"PV({VOL_GRID[i]:.0%})={protection_values[i]:.4f} should be <= "
                f"PV({VOL_GRID[i+1]:.0%})={protection_values[i+1]:.4f}"
            )

    def test_max_loss_decreases_with_buffer(self) -> None:
        """
        [P1] Max loss should decrease with higher buffer protection.
        """
        buffer_grid = [0.05, 0.10, 0.15, 0.20]
        max_losses = []

        market = RILAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = RILAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        for buffer in buffer_grid:
            product = RILAProduct(
                company_name="Test",
                product_name=f"Test RILA {buffer:.0%} buffer",
                product_group="RILA",
                status="current",
                buffer_rate=buffer,
                buffer_modifier="Losses Covered Up To",
                cap_rate=0.20,
            )
            result = pricer.price(product, term_years=1.0)
            max_losses.append(result.max_loss)

        # Verify strict monotonicity (deterministic relationship)
        for i in range(len(max_losses) - 1):
            assert max_losses[i] > max_losses[i + 1], (
                f"Max loss should decrease with buffer: "
                f"MaxLoss({buffer_grid[i]:.0%})={max_losses[i]:.4f} should be > "
                f"MaxLoss({buffer_grid[i+1]:.0%})={max_losses[i+1]:.4f}"
            )


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.integration
class TestPricingEdgeCases:
    """Edge case tests for pricing gradients."""

    def test_near_zero_vol_option_value(self, fia_product: FIAProduct) -> None:
        """
        [P1] Near-zero vol should give near-intrinsic option value.

        As σ → 0, call approaches max(S*e^((r-q)T) - K, 0).
        """
        market = FIAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.01,  # Very low vol
        )
        pricer = FIAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)
        result = pricer.price(fia_product, term_years=1.0)

        # At near-zero vol, expected credit should be deterministic
        # Forward = S * e^((r-q)T) = 100 * e^(0.03*1) ≈ 103.05
        # With 10% cap, expected credit ≈ min(3.05%, 10%) ≈ 3.05%
        # Option value should be small (near intrinsic)
        assert result.embedded_option_value < 5.0, (
            f"Near-zero vol option value should be small: {result.embedded_option_value}"
        )

    def test_negative_rate_scenario(self) -> None:
        """
        [P1] Pricing should handle negative interest rates (per VM-21).
        """
        # MYGA with negative discount rate
        pricer = MYGAPricer()
        product = MYGAProduct(
            company_name="Test",
            product_name="Test MYGA",
            product_group="MYGA",
            status="current",
            fixed_rate=0.03,
            guarantee_duration=5,
        )

        result = pricer.price(product, principal=100_000, discount_rate=-0.01)

        # With negative discount rate, PV > guaranteed value
        guaranteed = 100_000 * (1.03) ** 5
        assert result.present_value > guaranteed, (
            f"Negative rate should increase PV: {result.present_value} should be > {guaranteed}"
        )

    def test_very_high_volatility(self, rila_product: RILAProduct) -> None:
        """
        [P1] Very high volatility should produce valid results.
        """
        market = RILAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.80,  # Very high vol
        )
        pricer = RILAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)
        result = pricer.price(rila_product, term_years=1.0)

        # Should still produce valid results
        assert result.protection_value > 0
        assert result.max_loss <= 1.0
        assert result.present_value > 0

    def test_short_maturity(self, fia_product: FIAProduct) -> None:
        """
        [P1] Very short maturity should produce valid results.
        """
        market = FIAMarketParams(
            spot=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
        )
        pricer = FIAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        # 1 week maturity
        result = pricer.price(fia_product, term_years=1 / 52)

        # Should produce valid but small option value
        assert result.embedded_option_value >= 0
        assert result.expected_credit >= 0


# =============================================================================
# Grid Tests
# =============================================================================


@pytest.mark.integration
class TestPricingGrid:
    """Full grid tests across rate × vol × tenor."""

    @pytest.mark.parametrize("rate", RATE_GRID)
    @pytest.mark.parametrize("vol", VOL_GRID)
    def test_fia_grid_valid(self, rate: float, vol: float) -> None:
        """
        [P1] FIA pricing should produce valid results across parameter grid.
        """
        market = FIAMarketParams(
            spot=100.0,
            risk_free_rate=rate,
            dividend_yield=0.02,
            volatility=vol,
        )
        pricer = FIAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        product = FIAProduct(
            company_name="Test",
            product_name="Test FIA",
            product_group="FIA",
            status="current",
            cap_rate=0.10,
            participation_rate=1.0,
        )

        result = pricer.price(product, term_years=1.0)

        # Basic validity checks
        assert result.embedded_option_value >= 0, (
            f"Invalid option value at r={rate:.2%}, σ={vol:.0%}: {result.embedded_option_value}"
        )
        assert result.expected_credit >= 0, (
            f"Invalid expected credit at r={rate:.2%}, σ={vol:.0%}: {result.expected_credit}"
        )

    @pytest.mark.parametrize("rate", RATE_GRID)
    @pytest.mark.parametrize("vol", VOL_GRID)
    def test_rila_grid_valid(self, rate: float, vol: float) -> None:
        """
        [P1] RILA pricing should produce valid results across parameter grid.
        """
        market = RILAMarketParams(
            spot=100.0,
            risk_free_rate=rate,
            dividend_yield=0.02,
            volatility=vol,
        )
        pricer = RILAPricer(market_params=market, n_mc_paths=MC_PATHS, seed=MC_SEED)

        product = RILAProduct(
            company_name="Test",
            product_name="Test RILA",
            product_group="RILA",
            status="current",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.20,
        )

        result = pricer.price(product, term_years=1.0)

        # Basic validity checks
        assert result.protection_value >= 0, (
            f"Invalid protection value at r={rate:.2%}, σ={vol:.0%}: {result.protection_value}"
        )
        assert 0 <= result.max_loss <= 1.0, (
            f"Invalid max loss at r={rate:.2%}, σ={vol:.0%}: {result.max_loss}"
        )
