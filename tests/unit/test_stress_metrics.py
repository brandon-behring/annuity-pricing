"""
Tests for Stress Test Metrics - Phase I.

[T2] Verifies metrics calculation, severity classification,
and summary aggregation.

See: docs/stress_testing/STRESS_TESTING_GUIDE.md
"""

import pytest

from annuity_pricing.stress_testing.metrics import (
    SeverityLevel,
    calculate_percentiles,
    calculate_reserve_delta,
    check_rbc_ratio,
    check_reserve_increase_limit,
    check_reserve_positive,
    check_solvency_ratio,
    classify_severity,
    create_stress_metrics,
    create_summary,
    format_metrics_row,
    format_summary,
)


class TestSeverityLevel:
    """Tests for SeverityLevel enum."""

    def test_low_value(self) -> None:
        """LOW should have value 'low'."""
        assert SeverityLevel.LOW.value == "low"

    def test_medium_value(self) -> None:
        """MEDIUM should have value 'medium'."""
        assert SeverityLevel.MEDIUM.value == "medium"

    def test_high_value(self) -> None:
        """HIGH should have value 'high'."""
        assert SeverityLevel.HIGH.value == "high"

    def test_critical_value(self) -> None:
        """CRITICAL should have value 'critical'."""
        assert SeverityLevel.CRITICAL.value == "critical"


class TestClassifySeverity:
    """Tests for classify_severity function."""

    def test_low_under_5_percent(self) -> None:
        """Reserve change < 5% should be LOW."""
        assert classify_severity(0.04) == SeverityLevel.LOW
        assert classify_severity(0.02) == SeverityLevel.LOW
        assert classify_severity(-0.03) == SeverityLevel.LOW

    def test_medium_5_to_15_percent(self) -> None:
        """Reserve change 5-15% should be MEDIUM."""
        assert classify_severity(0.05) == SeverityLevel.MEDIUM
        assert classify_severity(0.10) == SeverityLevel.MEDIUM
        assert classify_severity(0.14) == SeverityLevel.MEDIUM

    def test_high_15_to_30_percent(self) -> None:
        """Reserve change 15-30% should be HIGH."""
        assert classify_severity(0.15) == SeverityLevel.HIGH
        assert classify_severity(0.20) == SeverityLevel.HIGH
        assert classify_severity(0.29) == SeverityLevel.HIGH

    def test_critical_over_30_percent(self) -> None:
        """Reserve change >= 30% should be CRITICAL."""
        assert classify_severity(0.30) == SeverityLevel.CRITICAL
        assert classify_severity(0.50) == SeverityLevel.CRITICAL
        assert classify_severity(1.0) == SeverityLevel.CRITICAL

    def test_absolute_value_used(self) -> None:
        """Should use absolute value (negative changes also classified)."""
        assert classify_severity(-0.50) == SeverityLevel.CRITICAL
        assert classify_severity(-0.20) == SeverityLevel.HIGH


class TestCalculateReserveDelta:
    """Tests for calculate_reserve_delta function."""

    def test_positive_delta(self) -> None:
        """Should calculate positive delta correctly."""
        delta, pct = calculate_reserve_delta(100_000, 120_000)
        assert delta == 20_000
        assert pct == 0.20

    def test_negative_delta(self) -> None:
        """Should calculate negative delta correctly."""
        delta, pct = calculate_reserve_delta(100_000, 80_000)
        assert delta == -20_000
        assert pct == -0.20

    def test_zero_delta(self) -> None:
        """Should handle zero delta."""
        delta, pct = calculate_reserve_delta(100_000, 100_000)
        assert delta == 0
        assert pct == 0.0

    def test_large_percentage_change(self) -> None:
        """Should handle large percentage changes."""
        delta, pct = calculate_reserve_delta(100_000, 250_000)
        assert delta == 150_000
        assert pct == 1.50

    def test_zero_base_raises(self) -> None:
        """Should raise ValueError for zero base reserve."""
        with pytest.raises(ValueError, match="base_reserve must be > 0"):
            calculate_reserve_delta(0, 100_000)

    def test_negative_base_raises(self) -> None:
        """Should raise ValueError for negative base reserve."""
        with pytest.raises(ValueError, match="base_reserve must be > 0"):
            calculate_reserve_delta(-100_000, 100_000)


class TestCalculatePercentiles:
    """Tests for calculate_percentiles function."""

    def test_basic_percentiles(self) -> None:
        """Should calculate basic percentiles."""
        values = list(range(1, 101))  # 1 to 100
        percs = calculate_percentiles(values)
        assert 5 in percs
        assert 25 in percs
        assert 50 in percs
        assert 75 in percs
        assert 95 in percs

    def test_median_correct(self) -> None:
        """Median should be correct."""
        values = [10, 20, 30, 40, 50]
        percs = calculate_percentiles(values)
        assert percs[50] == 30.0

    def test_custom_percentiles(self) -> None:
        """Should accept custom percentile levels."""
        values = list(range(1, 101))
        percs = calculate_percentiles(values, percentiles=(10, 90))
        assert 10 in percs
        assert 90 in percs
        assert 50 not in percs

    def test_empty_list_raises(self) -> None:
        """Should raise ValueError for empty list."""
        with pytest.raises(ValueError, match="Cannot calculate percentiles of empty"):
            calculate_percentiles([])


class TestCreateStressMetrics:
    """Tests for create_stress_metrics function."""

    def test_creates_metrics(self) -> None:
        """Should create complete metrics."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
        )
        assert metrics.scenario_name == "test"
        assert metrics.base_reserve == 100_000
        assert metrics.stressed_reserve == 120_000
        assert metrics.reserve_delta == 20_000
        assert metrics.reserve_delta_pct == 0.20

    def test_severity_calculated(self) -> None:
        """Should calculate severity automatically."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
        )
        assert metrics.severity == SeverityLevel.HIGH

    def test_gates_all_pass(self) -> None:
        """Should pass when all gates pass."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
            validation_gates={"reserve_positive": True, "solvency": True},
        )
        assert metrics.passed_gates is True
        assert len(metrics.gate_failures) == 0

    def test_gates_with_failures(self) -> None:
        """Should record failed gates."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
            validation_gates={"reserve_positive": True, "solvency": False},
        )
        assert metrics.passed_gates is False
        assert "solvency" in metrics.gate_failures

    def test_additional_metrics(self) -> None:
        """Should include additional metrics."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
            additional_metrics={"cte70": 125_000, "var95": 130_000},
        )
        assert metrics.additional_metrics["cte70"] == 125_000


class TestStressMetrics:
    """Tests for StressMetrics dataclass."""

    def test_metrics_is_frozen(self) -> None:
        """Metrics should be immutable."""
        metrics = create_stress_metrics(
            scenario_name="test",
            base_reserve=100_000,
            stressed_reserve=120_000,
        )
        with pytest.raises(AttributeError):
            metrics.scenario_name = "modified"  # type: ignore


class TestCreateSummary:
    """Tests for create_summary function."""

    def test_creates_summary(self) -> None:
        """Should create summary from metrics list."""
        metrics_list = [
            create_stress_metrics("s1", 100_000, 110_000),
            create_stress_metrics("s2", 100_000, 120_000),
            create_stress_metrics("s3", 100_000, 130_000),
        ]
        summary = create_summary(metrics_list)
        assert summary.n_scenarios == 3
        assert summary.base_reserve == 100_000

    def test_worst_scenario_identified(self) -> None:
        """Should identify worst scenario."""
        metrics_list = [
            create_stress_metrics("mild", 100_000, 105_000),
            create_stress_metrics("severe", 100_000, 150_000),
            create_stress_metrics("moderate", 100_000, 120_000),
        ]
        summary = create_summary(metrics_list)
        assert summary.worst_scenario == "severe"
        assert summary.worst_reserve_delta_pct == 0.50

    def test_best_scenario_identified(self) -> None:
        """Should identify best (least severe) scenario."""
        metrics_list = [
            create_stress_metrics("mild", 100_000, 105_000),
            create_stress_metrics("severe", 100_000, 150_000),
            create_stress_metrics("moderate", 100_000, 120_000),
        ]
        summary = create_summary(metrics_list)
        assert summary.best_scenario == "mild"
        assert summary.best_reserve_delta_pct == 0.05

    def test_percentiles_calculated(self) -> None:
        """Should calculate percentiles."""
        metrics_list = [
            create_stress_metrics(f"s{i}", 100_000, 100_000 + i * 10_000) for i in range(10)
        ]
        summary = create_summary(metrics_list)
        assert 50 in summary.percentiles

    def test_severity_counts(self) -> None:
        """Should count by severity level."""
        metrics_list = [
            create_stress_metrics("low", 100_000, 103_000),  # 3% = LOW
            create_stress_metrics("medium", 100_000, 110_000),  # 10% = MEDIUM
            create_stress_metrics("high", 100_000, 125_000),  # 25% = HIGH
            create_stress_metrics("critical", 100_000, 150_000),  # 50% = CRITICAL
        ]
        summary = create_summary(metrics_list)
        assert summary.severity_counts[SeverityLevel.LOW] == 1
        assert summary.severity_counts[SeverityLevel.MEDIUM] == 1
        assert summary.severity_counts[SeverityLevel.HIGH] == 1
        assert summary.severity_counts[SeverityLevel.CRITICAL] == 1

    def test_passed_failed_counts(self) -> None:
        """Should count passed and failed gates."""
        metrics_list = [
            create_stress_metrics("pass1", 100_000, 110_000, {"gate": True}),
            create_stress_metrics("pass2", 100_000, 120_000, {"gate": True}),
            create_stress_metrics("fail1", 100_000, 130_000, {"gate": False}),
        ]
        summary = create_summary(metrics_list)
        assert summary.n_passed == 2
        assert summary.n_failed == 1

    def test_empty_list_raises(self) -> None:
        """Should raise ValueError for empty list."""
        with pytest.raises(ValueError, match="Cannot create summary from empty"):
            create_summary([])

    def test_inconsistent_base_reserves_raises(self) -> None:
        """Should raise ValueError for inconsistent base reserves."""
        metrics_list = [
            create_stress_metrics("s1", 100_000, 110_000),
            create_stress_metrics("s2", 200_000, 220_000),  # Different base
        ]
        with pytest.raises(ValueError, match="Inconsistent base reserves"):
            create_summary(metrics_list)


class TestValidationGates:
    """Tests for validation gate functions."""

    def test_check_reserve_positive(self) -> None:
        """Should check reserve is positive."""
        assert check_reserve_positive(100_000) is True
        assert check_reserve_positive(0.01) is True
        assert check_reserve_positive(0) is False
        assert check_reserve_positive(-100) is False

    def test_check_solvency_ratio(self) -> None:
        """Should check solvency ratio."""
        assert check_solvency_ratio(120_000, 100_000, 1.0) is True
        assert check_solvency_ratio(100_000, 100_000, 1.0) is True
        assert check_solvency_ratio(90_000, 100_000, 1.0) is False

    def test_check_solvency_zero_liabilities(self) -> None:
        """Should return True for zero liabilities."""
        assert check_solvency_ratio(100_000, 0, 1.0) is True

    def test_check_rbc_ratio(self) -> None:
        """Should check RBC ratio."""
        assert check_rbc_ratio(200_000, 100_000, 2.0) is True
        assert check_rbc_ratio(250_000, 100_000, 2.0) is True
        assert check_rbc_ratio(150_000, 100_000, 2.0) is False

    def test_check_reserve_increase_limit(self) -> None:
        """Should check reserve increase limit."""
        assert check_reserve_increase_limit(0.20, 0.50) is True
        assert check_reserve_increase_limit(0.50, 0.50) is True
        assert check_reserve_increase_limit(0.60, 0.50) is False


class TestFormatMetricsRow:
    """Tests for format_metrics_row function."""

    def test_format_basic_row(self) -> None:
        """Should format metrics as table row."""
        metrics = create_stress_metrics("test_scenario", 100_000, 120_000)
        row = format_metrics_row(metrics)
        assert "test_scenario" in row
        assert "+20.0%" in row
        assert "high" in row

    def test_format_passing_gate(self) -> None:
        """Should show PASS for passing metrics."""
        metrics = create_stress_metrics("test", 100_000, 110_000, {"gate": True})
        row = format_metrics_row(metrics)
        assert "PASS" in row

    def test_format_failing_gate(self) -> None:
        """Should show FAIL for failing metrics."""
        metrics = create_stress_metrics("test", 100_000, 110_000, {"gate": False})
        row = format_metrics_row(metrics)
        assert "FAIL" in row


class TestFormatSummary:
    """Tests for format_summary function."""

    def test_format_basic_summary(self) -> None:
        """Should format summary as multi-line string."""
        metrics_list = [
            create_stress_metrics("s1", 100_000, 110_000),
            create_stress_metrics("s2", 100_000, 120_000),
            create_stress_metrics("s3", 100_000, 130_000),
        ]
        summary = create_summary(metrics_list)
        formatted = format_summary(summary)

        assert "STRESS TEST SUMMARY" in formatted
        assert "Scenarios Tested: 3" in formatted
        assert "Base Reserve: $100,000" in formatted
        assert "Percentile Distribution" in formatted
        assert "Severity Distribution" in formatted

    def test_includes_worst_case(self) -> None:
        """Should include worst case info."""
        metrics_list = [
            create_stress_metrics("mild", 100_000, 105_000),
            create_stress_metrics("severe", 100_000, 150_000),
        ]
        summary = create_summary(metrics_list)
        formatted = format_summary(summary)
        assert "severe" in formatted
        assert "+50.0%" in formatted
