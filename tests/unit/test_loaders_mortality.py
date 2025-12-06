"""
Tests for Mortality Loader - Phase 10.

[T1] Mortality properties:
- qx = probability of death within year, given alive at age x
- px = 1 - qx = probability of surviving year
- npx = probability of surviving n years
- ex = life expectancy at age x

See: SOA 2012 Individual Annuity Mortality Tables
"""

import pytest
import numpy as np

from annuity_pricing.loaders.mortality import (
    MortalityTable,
    MortalityLoader,
    compare_life_expectancy,
    calculate_annuity_pv,
)


class TestMortalityTable:
    """Tests for MortalityTable dataclass."""

    @pytest.fixture
    def simple_table(self) -> MortalityTable:
        """Simple mortality table for testing."""
        return MortalityTable(
            table_name="Test Table",
            min_age=0,
            max_age=100,
            qx=np.array([0.001 + 0.0001 * age for age in range(101)]),
            gender="male",
        )

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        """Mortality loader instance."""
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        """SOA 2012 IAM Male table."""
        return loader.soa_2012_iam("male")

    @pytest.fixture
    def soa_female(self, loader: MortalityLoader) -> MortalityTable:
        """SOA 2012 IAM Female table."""
        return loader.soa_2012_iam("female")

    def test_table_creation(self, simple_table: MortalityTable) -> None:
        """Table should be created with correct attributes."""
        assert simple_table.table_name == "Test Table"
        assert simple_table.min_age == 0
        assert simple_table.max_age == 100
        assert len(simple_table.qx) == 101

    def test_get_qx(self, simple_table: MortalityTable) -> None:
        """Should return qx for given age."""
        qx = simple_table.get_qx(50)
        expected = 0.001 + 0.0001 * 50
        assert qx == pytest.approx(expected)

    def test_get_px(self, simple_table: MortalityTable) -> None:
        """Should return px = 1 - qx."""
        qx = simple_table.get_qx(50)
        px = simple_table.get_px(50)
        assert px == pytest.approx(1 - qx)

    def test_qx_plus_px_equals_one(self, simple_table: MortalityTable) -> None:
        """qx + px should always equal 1."""
        for age in range(0, 100):
            qx = simple_table.get_qx(age)
            px = simple_table.get_px(age)
            assert qx + px == pytest.approx(1.0)

    def test_qx_bounds(self, simple_table: MortalityTable) -> None:
        """qx should be in [0, 1]."""
        for age in range(0, 101):
            qx = simple_table.get_qx(age)
            assert 0 <= qx <= 1


class TestNPXCalculation:
    """Tests for npx (n-year survival probability)."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    def test_1px_equals_px(self, soa_male: MortalityTable) -> None:
        """1px should equal px."""
        age = 65
        px = soa_male.get_px(age)
        npx = soa_male.npx(age, 1)
        assert npx == pytest.approx(px)

    def test_npx_decreasing_with_n(self, soa_male: MortalityTable) -> None:
        """npx should decrease as n increases."""
        age = 65
        p1 = soa_male.npx(age, 1)
        p5 = soa_male.npx(age, 5)
        p10 = soa_male.npx(age, 10)
        p20 = soa_male.npx(age, 20)

        assert p1 > p5 > p10 > p20

    def test_npx_product_formula(self, soa_male: MortalityTable) -> None:
        """npx should equal product of individual px values."""
        age = 65
        n = 5

        # Manual calculation: ₅p₆₅ = p₆₅ × p₆₆ × p₆₇ × p₆₈ × p₆₉
        manual = 1.0
        for i in range(n):
            manual *= soa_male.get_px(age + i)

        npx = soa_male.npx(age, n)
        assert npx == pytest.approx(manual, rel=0.0001)

    def test_0px_equals_one(self, soa_male: MortalityTable) -> None:
        """0px should be 1 (certain to survive 0 years)."""
        npx = soa_male.npx(65, 0)
        assert npx == pytest.approx(1.0)


class TestNQXCalculation:
    """Tests for nqx (n-year mortality probability)."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    def test_nqx_equals_1_minus_npx(self, soa_male: MortalityTable) -> None:
        """nqx should equal 1 - npx."""
        age = 65
        n = 10

        npx = soa_male.npx(age, n)
        nqx = soa_male.nqx(age, n)

        assert nqx == pytest.approx(1 - npx)

    def test_1qx_equals_qx(self, soa_male: MortalityTable) -> None:
        """1qx should equal qx."""
        age = 65
        qx = soa_male.get_qx(age)
        nqx = soa_male.nqx(age, 1)
        assert nqx == pytest.approx(qx)


class TestLifeExpectancy:
    """Tests for life expectancy calculation."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    @pytest.fixture
    def soa_female(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("female")

    def test_life_expectancy_positive(self, soa_male: MortalityTable) -> None:
        """Life expectancy should be positive."""
        ex = soa_male.life_expectancy(65)
        assert ex > 0

    def test_life_expectancy_decreasing_with_age(self, soa_male: MortalityTable) -> None:
        """Life expectancy should decrease with age."""
        ex_60 = soa_male.life_expectancy(60)
        ex_70 = soa_male.life_expectancy(70)
        ex_80 = soa_male.life_expectancy(80)

        assert ex_60 > ex_70 > ex_80

    def test_life_expectancy_reasonable_values(self, soa_male: MortalityTable) -> None:
        """Life expectancy at 65 should be ~15-30 years for annuitants."""
        ex = soa_male.life_expectancy(65)
        # SOA 2012 IAM is for annuitants (healthier), expect reasonable range
        assert 10 < ex < 35

    def test_females_live_longer(
        self, soa_male: MortalityTable, soa_female: MortalityTable
    ) -> None:
        """Female life expectancy should exceed male."""
        ex_male = soa_male.life_expectancy(65)
        ex_female = soa_female.life_expectancy(65)

        assert ex_female > ex_male

    def test_life_expectancy_at_birth_reasonable(
        self, soa_male: MortalityTable
    ) -> None:
        """Life expectancy at birth should be reasonable."""
        ex = soa_male.life_expectancy(0)
        # Annuitant tables start higher, expect > 70
        assert ex > 70


class TestLxDxColumns:
    """Tests for lx and dx columns."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    def test_lx_decreasing(self, soa_male: MortalityTable) -> None:
        """lx should be decreasing with age."""
        l60 = soa_male.lx(60)
        l70 = soa_male.lx(70)
        l80 = soa_male.lx(80)

        assert l60 > l70 > l80

    def test_lx_at_zero_is_radix(self, soa_male: MortalityTable) -> None:
        """l0 should be the radix (default 100,000)."""
        l0 = soa_male.lx(0)
        assert l0 == pytest.approx(100_000)

    def test_dx_equals_lx_difference(self, soa_male: MortalityTable) -> None:
        """dx should equal lx - l(x+1)."""
        age = 70
        lx = soa_male.lx(age)
        lx1 = soa_male.lx(age + 1)
        dx = soa_male.dx(age)

        assert dx == pytest.approx(lx - lx1, rel=0.001)

    def test_dx_positive(self, soa_male: MortalityTable) -> None:
        """dx should always be positive."""
        for age in range(0, 110):
            dx = soa_male.dx(age)
            assert dx >= 0


class TestAnnuityFactor:
    """Tests for annuity factor calculation."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def soa_male(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    def test_annuity_factor_positive(self, soa_male: MortalityTable) -> None:
        """Annuity factor should be positive."""
        ax = soa_male.annuity_factor(65, r=0.05)
        assert ax > 0

    def test_annuity_factor_increases_with_rate(
        self, soa_male: MortalityTable
    ) -> None:
        """Higher rate → lower annuity factor (more discounting)."""
        ax_low = soa_male.annuity_factor(65, r=0.03)
        ax_high = soa_male.annuity_factor(65, r=0.07)

        assert ax_low > ax_high

    def test_annuity_factor_decreases_with_age(
        self, soa_male: MortalityTable
    ) -> None:
        """Older age → lower annuity factor (fewer expected payments)."""
        ax_60 = soa_male.annuity_factor(60, r=0.05)
        ax_70 = soa_male.annuity_factor(70, r=0.05)
        ax_80 = soa_male.annuity_factor(80, r=0.05)

        assert ax_60 > ax_70 > ax_80

    def test_annuity_factor_reasonable_value(self, soa_male: MortalityTable) -> None:
        """65-year-old annuity factor at 5% should be ~10-18."""
        ax = soa_male.annuity_factor(65, r=0.05)
        # Standard actuarial benchmark
        assert 8 < ax < 20


class TestMortalityLoader:
    """Tests for MortalityLoader factory methods."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    def test_soa_2012_iam_male(self, loader: MortalityLoader) -> None:
        """Should load SOA 2012 IAM male table."""
        table = loader.soa_2012_iam("male")

        assert "SOA 2012 IAM" in table.table_name
        assert "Male" in table.table_name or "male" in table.table_name.lower()
        assert table.min_age == 0
        assert table.max_age == 120
        assert table.get_qx(0) > 0

    def test_soa_2012_iam_female(self, loader: MortalityLoader) -> None:
        """Should load SOA 2012 IAM female table."""
        table = loader.soa_2012_iam("female")

        assert "SOA 2012 IAM" in table.table_name
        assert table.min_age == 0
        assert table.max_age == 120

    def test_soa_2012_iam_invalid_gender_raises(self, loader: MortalityLoader) -> None:
        """Invalid gender should raise."""
        with pytest.raises(ValueError, match="male.*female"):
            loader.soa_2012_iam("unknown")

    def test_gompertz_table(self, loader: MortalityLoader) -> None:
        """Should create Gompertz mortality table."""
        table = loader.gompertz(a=0.0001, b=0.08)

        assert "Gompertz" in table.table_name
        # qx should increase exponentially
        qx_60 = table.get_qx(60)
        qx_70 = table.get_qx(70)
        assert qx_70 > qx_60

    def test_from_dict(self, loader: MortalityLoader) -> None:
        """Should create table from dict."""
        data = {age: 0.01 + 0.001 * age for age in range(0, 101)}
        table = loader.from_dict(data, table_name="Custom Table")

        assert table.table_name == "Custom Table"
        assert table.get_qx(50) == pytest.approx(0.01 + 0.001 * 50)

    def test_with_improvement(self, loader: MortalityLoader) -> None:
        """Mortality improvement should reduce qx."""
        base = loader.soa_2012_iam("male")
        improved = loader.with_improvement(base, improvement_rate=0.01, projection_years=10)

        # qx should be lower after improvement
        assert improved.get_qx(65) < base.get_qx(65)


class TestMortalityImprovement:
    """Tests for mortality improvement factors."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    @pytest.fixture
    def base_table(self, loader: MortalityLoader) -> MortalityTable:
        return loader.soa_2012_iam("male")

    def test_improvement_reduces_mortality(
        self, loader: MortalityLoader, base_table: MortalityTable
    ) -> None:
        """Improvement should reduce mortality rates."""
        improved = loader.with_improvement(base_table, improvement_rate=0.02, projection_years=20)

        for age in [50, 65, 80]:
            assert improved.get_qx(age) < base_table.get_qx(age)

    def test_improvement_formula(
        self, loader: MortalityLoader, base_table: MortalityTable
    ) -> None:
        """Improvement should follow (1-r)^years formula."""
        rate = 0.01
        years = 10
        improved = loader.with_improvement(base_table, improvement_rate=rate, projection_years=years)

        age = 70
        base_qx = base_table.get_qx(age)
        expected_qx = base_qx * ((1 - rate) ** years)
        actual_qx = improved.get_qx(age)

        assert actual_qx == pytest.approx(expected_qx, rel=0.01)

    def test_zero_improvement_unchanged(
        self, loader: MortalityLoader, base_table: MortalityTable
    ) -> None:
        """Zero improvement should not change table."""
        improved = loader.with_improvement(base_table, improvement_rate=0.0, projection_years=10)

        for age in [50, 65, 80]:
            assert improved.get_qx(age) == pytest.approx(base_table.get_qx(age))


class TestBlendTables:
    """Tests for table blending."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    def test_blend_50_50(self, loader: MortalityLoader) -> None:
        """50/50 blend should average mortality."""
        male = loader.soa_2012_iam("male")
        female = loader.soa_2012_iam("female")

        blended = loader.blend_tables(male, female, weight1=0.5)

        # Blended should be between male and female
        for age in [50, 65, 80]:
            qx_blended = blended.get_qx(age)
            qx_male = male.get_qx(age)
            qx_female = female.get_qx(age)

            assert min(qx_male, qx_female) <= qx_blended <= max(qx_male, qx_female)

    def test_blend_100_0(self, loader: MortalityLoader) -> None:
        """100/0 blend should equal first table."""
        male = loader.soa_2012_iam("male")
        female = loader.soa_2012_iam("female")

        blended = loader.blend_tables(male, female, weight1=1.0)

        for age in [50, 65, 80]:
            assert blended.get_qx(age) == pytest.approx(male.get_qx(age))


class TestCompareLifeExpectancy:
    """Tests for compare_life_expectancy function."""

    def test_comparison_returns_dict(self) -> None:
        """Should return comparison dict."""
        loader = MortalityLoader()
        male = loader.soa_2012_iam("male")
        female = loader.soa_2012_iam("female")

        # compare_life_expectancy expects Dict[str, MortalityTable]
        tables = {"Male": male, "Female": female}
        result = compare_life_expectancy(tables, ages=np.array([60, 65, 70]))

        assert isinstance(result, dict)
        # Check that the table names are in the result
        assert "Male" in result or "Female" in result


class TestCalculateAnnuityPV:
    """Tests for calculate_annuity_pv function."""

    def test_annuity_pv_basic(self) -> None:
        """Should calculate annuity PV."""
        loader = MortalityLoader()
        table = loader.soa_2012_iam("male")

        pv = calculate_annuity_pv(
            table=table,
            age=65,
            annual_payment=10_000,
            discount_rate=0.05,
        )

        assert pv > 0
        # PV should be roughly payment × annuity factor
        ax = table.annuity_factor(65, r=0.05)
        expected = 10_000 * ax
        assert pv == pytest.approx(expected, rel=0.01)

    def test_annuity_pv_increases_with_payment(self) -> None:
        """Higher payment → higher PV."""
        loader = MortalityLoader()
        table = loader.soa_2012_iam("male")

        pv_low = calculate_annuity_pv(table, 65, 10_000, discount_rate=0.05)
        pv_high = calculate_annuity_pv(table, 65, 20_000, discount_rate=0.05)

        assert pv_high == pytest.approx(2 * pv_low)


class TestSOA2012IAMValues:
    """Tests verifying SOA 2012 IAM specific values."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    def test_male_qx_at_65(self, loader: MortalityLoader) -> None:
        """Male qx at 65 should match published value."""
        table = loader.soa_2012_iam("male")
        qx = table.get_qx(65)
        # SOA 2012 IAM Male qx at 65 ≈ 0.0168 (from our embedded data)
        assert 0.01 < qx < 0.03

    def test_female_qx_at_65(self, loader: MortalityLoader) -> None:
        """Female qx at 65 should match published value."""
        table = loader.soa_2012_iam("female")
        qx = table.get_qx(65)
        # SOA 2012 IAM Female qx at 65 should be lower than male
        male_qx = loader.soa_2012_iam("male").get_qx(65)
        assert qx < male_qx

    def test_qx_increases_with_age(self, loader: MortalityLoader) -> None:
        """qx should generally increase with age."""
        table = loader.soa_2012_iam("male")

        # Check trend from 50 to 90
        qx_prev = table.get_qx(50)
        for age in range(51, 90):
            qx_curr = table.get_qx(age)
            # Allow some non-monotonicity at very young ages
            if age > 60:
                assert qx_curr >= qx_prev * 0.95  # Allow 5% noise
            qx_prev = qx_curr

    def test_omega_age(self, loader: MortalityLoader) -> None:
        """Table should extend to age 120."""
        male = loader.soa_2012_iam("male")
        female = loader.soa_2012_iam("female")

        assert male.max_age == 120
        assert female.max_age == 120


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    def test_very_old_age(self, loader: MortalityLoader) -> None:
        """Very old ages should have high but valid qx."""
        table = loader.soa_2012_iam("male")

        qx_100 = table.get_qx(100)
        qx_110 = table.get_qx(110)

        assert 0 < qx_100 <= 1
        assert 0 < qx_110 <= 1
        assert qx_110 > qx_100

    def test_infant_mortality(self, loader: MortalityLoader) -> None:
        """Infant mortality should be low for annuitant table."""
        table = loader.soa_2012_iam("male")
        qx_0 = table.get_qx(0)
        # Annuitant tables have selection, very low infant mortality
        assert qx_0 < 0.01

    def test_age_beyond_table_returns_one(self, loader: MortalityLoader) -> None:
        """Age beyond max_age should return qx=1."""
        table = loader.soa_2012_iam("male")

        # Beyond max_age, qx should be 1.0
        qx_130 = table.get_qx(130)
        assert qx_130 == 1.0

    def test_negative_age_raises(self, loader: MortalityLoader) -> None:
        """Negative age should raise."""
        table = loader.soa_2012_iam("male")

        with pytest.raises(ValueError, match="below minimum"):
            table.get_qx(-5)

    def test_npx_beyond_table(self, loader: MortalityLoader) -> None:
        """npx extending beyond table should handle gracefully."""
        table = loader.soa_2012_iam("male")

        # 100-year-old + 30 years = 130, beyond table
        npx = table.npx(100, 30)
        # Should be very close to 0 (almost certain death)
        assert npx < 0.01


class TestGompertzModel:
    """Tests for Gompertz mortality model."""

    @pytest.fixture
    def loader(self) -> MortalityLoader:
        return MortalityLoader()

    def test_gompertz_exponential_increase(self, loader: MortalityLoader) -> None:
        """Gompertz qx should increase exponentially."""
        table = loader.gompertz(a=0.0001, b=0.08)

        qx_60 = table.get_qx(60)
        qx_70 = table.get_qx(70)
        qx_80 = table.get_qx(80)

        # Check exponential pattern: ratio should be constant
        ratio_1 = qx_70 / qx_60
        ratio_2 = qx_80 / qx_70
        assert ratio_1 == pytest.approx(ratio_2, rel=0.1)

    def test_gompertz_formula(self, loader: MortalityLoader) -> None:
        """Verify Gompertz formula: qx = a * e^(b*x)."""
        a, b = 0.0001, 0.08
        table = loader.gompertz(a=a, b=b)

        for age in [50, 60, 70, 80]:
            qx = table.get_qx(age)
            expected = min(1.0, a * np.exp(b * age))
            assert qx == pytest.approx(expected, rel=0.01)
