"""
Tests for stress test reporting module (Phase I.4).

Tests the StressTestReporter class and formatting functions.
"""

import json
import tempfile
from pathlib import Path

import pytest

from annuity_pricing.stress_testing.metrics import (
    create_stress_metrics,
    create_summary,
)
from annuity_pricing.stress_testing.reporting import (
    ReportConfig,
    StressTestReporter,
    generate_quick_summary,
    generate_stress_report,
)
from annuity_pricing.stress_testing.reverse import (
    RBC_BREACH_200,
    RESERVE_EXHAUSTION,
    ReverseStressReport,
    ReverseStressResult,
)
from annuity_pricing.stress_testing.runner import (
    StressTestConfig,
    StressTestResult,
)
from annuity_pricing.stress_testing.sensitivity import (
    SensitivityResult,
    TornadoData,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_metrics_list():
    """Create sample metrics list for testing."""
    return [
        create_stress_metrics(
            scenario_name="hist_2008_gfc",
            base_reserve=100_000,
            stressed_reserve=145_000,
            validation_gates={"reserve_positive": True, "reserve_within_limit": True},
        ),
        create_stress_metrics(
            scenario_name="hist_2020_covid",
            base_reserve=100_000,
            stressed_reserve=125_000,
            validation_gates={"reserve_positive": True, "reserve_within_limit": True},
        ),
        create_stress_metrics(
            scenario_name="orsa_moderate",
            base_reserve=100_000,
            stressed_reserve=108_000,
            validation_gates={"reserve_positive": True, "reserve_within_limit": True},
        ),
        create_stress_metrics(
            scenario_name="orsa_severely",
            base_reserve=100_000,
            stressed_reserve=120_000,
            validation_gates={"reserve_positive": True, "reserve_within_limit": True},
        ),
        create_stress_metrics(
            scenario_name="orsa_extremely",
            base_reserve=100_000,
            stressed_reserve=135_000,
            validation_gates={"reserve_positive": True, "reserve_within_limit": True},
        ),
    ]


@pytest.fixture
def sample_summary(sample_metrics_list):
    """Create sample summary for testing."""
    return create_summary(sample_metrics_list)


@pytest.fixture
def sample_result(sample_metrics_list, sample_summary):
    """Create sample StressTestResult for testing."""
    return StressTestResult(
        summary=sample_summary,
        metrics=sample_metrics_list,
        execution_time_sec=2.5,
        calculator_type="vm21",
        config=StressTestConfig(),
    )


@pytest.fixture
def sample_tornado():
    """Create sample TornadoData for testing."""
    results = [
        SensitivityResult(
            parameter="equity_shock",
            display_name="Equity Shock",
            base_value=-0.30,
            base_reserve=100_000,
            down_value=-0.60,
            down_reserve=148_000,
            up_value=-0.10,
            up_reserve=108_000,
            down_delta_pct=0.48,
            up_delta_pct=0.08,
            sensitivity_width=0.40,
        ),
        SensitivityResult(
            parameter="rate_shock",
            display_name="Rate Shock",
            base_value=-0.0100,
            base_reserve=100_000,
            down_value=-0.0200,
            down_reserve=120_000,
            up_value=0.0100,
            up_reserve=90_000,
            down_delta_pct=0.20,
            up_delta_pct=-0.10,
            sensitivity_width=0.30,
        ),
        SensitivityResult(
            parameter="vol_shock",
            display_name="Volatility Multiplier",
            base_value=2.0,
            base_reserve=100_000,
            down_value=1.0,
            down_reserve=95_000,
            up_value=4.0,
            up_reserve=115_000,
            down_delta_pct=-0.05,
            up_delta_pct=0.15,
            sensitivity_width=0.20,
        ),
    ]
    return TornadoData(
        results=results,
        base_reserve=100_000,
        scenario_name="ORSA Severely Adverse",
    )


@pytest.fixture
def sample_reverse_stress_report():
    """Create sample ReverseStressReport for testing."""
    target1 = RESERVE_EXHAUSTION
    target2 = RBC_BREACH_200

    results = {
        ("reserve_exhaustion", "equity_shock"): ReverseStressResult(
            target=target1,
            parameter_name="equity_shock",
            breaking_point=None,
            iterations=0,
            converged=True,
            breached=False,
            base_value=-0.30,
            search_range=(-1.0, 0.5),
            final_metric_value=None,
        ),
        ("reserve_exhaustion", "rate_shock"): ReverseStressResult(
            target=target1,
            parameter_name="rate_shock",
            breaking_point=None,
            iterations=0,
            converged=True,
            breached=False,
            base_value=-0.01,
            search_range=(-0.05, 0.05),
            final_metric_value=None,
        ),
        ("rbc_breach_200", "equity_shock"): ReverseStressResult(
            target=target2,
            parameter_name="equity_shock",
            breaking_point=-0.85,
            iterations=15,
            converged=True,
            breached=True,
            base_value=-0.30,
            search_range=(-1.0, 0.5),
            final_metric_value=1.95,
        ),
    }

    return ReverseStressReport(
        results=results,
        base_reserve=100_000,
    )


# =============================================================================
# ReportConfig Tests
# =============================================================================


class TestReportConfig:
    """Tests for ReportConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReportConfig()
        assert config.title == "Stress Test Report"
        assert config.include_scenarios is True
        assert config.include_sensitivity is True
        assert config.include_reverse_stress is True
        assert config.include_executive_summary is True
        assert config.max_scenarios_to_display == 10
        assert config.percentile_levels == (5, 25, 50, 75, 95)

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReportConfig(
            title="Custom Report",
            include_scenarios=False,
            max_scenarios_to_display=5,
        )
        assert config.title == "Custom Report"
        assert config.include_scenarios is False
        assert config.max_scenarios_to_display == 5


# =============================================================================
# StressTestReporter Tests
# =============================================================================


class TestStressTestReporter:
    """Tests for StressTestReporter class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        reporter = StressTestReporter()
        assert reporter.config is not None
        assert reporter.config.title == "Stress Test Report"

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = ReportConfig(title="My Report")
        reporter = StressTestReporter(config=config)
        assert reporter.config.title == "My Report"


class TestExecutiveSummary:
    """Tests for executive summary generation."""

    def test_basic_summary(self, sample_summary):
        """Test basic executive summary generation."""
        reporter = StressTestReporter()
        summary = reporter.generate_executive_summary(sample_summary)

        assert isinstance(summary, str)
        assert len(summary) > 50
        assert "5 scenarios" in summary
        assert "passed" in summary.lower() or "failed" in summary.lower()

    def test_summary_includes_worst_case(self, sample_summary):
        """Test that summary includes worst case scenario."""
        reporter = StressTestReporter()
        summary = reporter.generate_executive_summary(sample_summary)

        assert sample_summary.worst_scenario in summary or "45.0%" in summary

    def test_summary_with_sensitivity(self, sample_summary, sample_tornado):
        """Test summary includes sensitivity insights."""
        reporter = StressTestReporter()
        summary = reporter.generate_executive_summary(sample_summary, sensitivity=sample_tornado)

        assert "most sensitive" in summary.lower() or "equity" in summary.lower()

    def test_summary_with_reverse_stress(self, sample_summary, sample_reverse_stress_report):
        """Test summary includes reverse stress insights."""
        reporter = StressTestReporter()
        summary = reporter.generate_executive_summary(
            sample_summary, reverse_stress=sample_reverse_stress_report
        )

        assert "reverse stress" in summary.lower() or "breach" in summary.lower()


# =============================================================================
# Markdown Generation Tests
# =============================================================================


class TestMarkdownGeneration:
    """Tests for Markdown report generation."""

    def test_to_markdown_basic(self, sample_result):
        """Test basic Markdown generation."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert isinstance(markdown, str)
        assert "# Stress Test Report" in markdown
        assert "## Executive Summary" in markdown
        assert "## Scenario Results" in markdown

    def test_to_markdown_custom_title(self, sample_result):
        """Test Markdown with custom title."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result, title="My Custom Report")

        assert "# My Custom Report" in markdown

    def test_markdown_includes_metadata(self, sample_result):
        """Test Markdown includes metadata."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert "**Generated**:" in markdown
        assert "**Calculator**:" in markdown
        assert "vm21" in markdown
        assert "$100,000" in markdown

    def test_markdown_includes_scenario_table(self, sample_result):
        """Test Markdown includes scenario table."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert "| Scenario |" in markdown
        assert "hist_2008_gfc" in markdown

    def test_markdown_includes_percentile_table(self, sample_result):
        """Test Markdown includes percentile table."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert "## Percentile Distribution" in markdown
        assert "| Percentile |" in markdown
        assert "50th" in markdown

    def test_markdown_includes_severity_breakdown(self, sample_result):
        """Test Markdown includes severity breakdown."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert "## Severity Breakdown" in markdown
        assert "LOW" in markdown or "MEDIUM" in markdown

    def test_markdown_includes_worst_scenarios(self, sample_result):
        """Test Markdown includes worst scenarios section."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result)

        assert "## Top 5 Worst Scenarios" in markdown

    def test_markdown_with_sensitivity(self, sample_result, sample_tornado):
        """Test Markdown includes sensitivity section."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result, sensitivity=sample_tornado)

        assert "## Sensitivity Analysis" in markdown
        assert "Equity Shock" in markdown
        assert "Most Sensitive" in markdown

    def test_markdown_with_reverse_stress(self, sample_result, sample_reverse_stress_report):
        """Test Markdown includes reverse stress section."""
        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result, reverse_stress=sample_reverse_stress_report)

        assert "## Reverse Stress Testing" in markdown
        assert "Breaking Points" in markdown

    def test_markdown_scenario_limit(self, sample_result):
        """Test scenario display limit is respected."""
        config = ReportConfig(max_scenarios_to_display=2)
        reporter = StressTestReporter(config=config)
        markdown = reporter.to_markdown(sample_result)

        # Should show limited scenarios plus "and X more"
        assert "...and" in markdown or "more scenarios" in markdown

    def test_markdown_without_executive_summary(self, sample_result):
        """Test Markdown without executive summary."""
        config = ReportConfig(include_executive_summary=False)
        reporter = StressTestReporter(config=config)
        markdown = reporter.to_markdown(sample_result)

        assert "## Executive Summary" not in markdown


# =============================================================================
# JSON Generation Tests
# =============================================================================


class TestJSONGeneration:
    """Tests for JSON report generation."""

    def test_to_json_basic(self, sample_result):
        """Test basic JSON generation."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result)

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert "metadata" in data
        assert "summary" in data
        assert "scenarios" in data

    def test_json_metadata(self, sample_result):
        """Test JSON metadata structure."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result)
        data = json.loads(json_str)

        assert "timestamp" in data["metadata"]
        assert data["metadata"]["calculator_type"] == "vm21"
        assert data["metadata"]["execution_time_sec"] == 2.5
        assert data["metadata"]["report_version"] == "1.0"

    def test_json_summary(self, sample_result):
        """Test JSON summary structure."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result)
        data = json.loads(json_str)

        summary = data["summary"]
        assert summary["n_scenarios"] == 5
        assert summary["n_passed"] == 5
        assert summary["n_failed"] == 0
        assert summary["base_reserve"] == 100_000
        assert "percentiles" in summary
        assert "severity_counts" in summary

    def test_json_scenarios(self, sample_result):
        """Test JSON scenarios structure."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result)
        data = json.loads(json_str)

        scenarios = data["scenarios"]
        assert len(scenarios) == 5
        assert scenarios[0]["scenario_name"] == "hist_2008_gfc"
        assert scenarios[0]["base_reserve"] == 100_000
        assert scenarios[0]["passed_gates"] is True

    def test_json_with_sensitivity(self, sample_result, sample_tornado):
        """Test JSON includes sensitivity data."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result, sensitivity=sample_tornado)
        data = json.loads(json_str)

        assert "sensitivity" in data
        sens = data["sensitivity"]
        assert sens["n_parameters"] == 3
        assert len(sens["results"]) == 3
        assert sens["most_sensitive"] == "equity_shock"

    def test_json_with_reverse_stress(self, sample_result, sample_reverse_stress_report):
        """Test JSON includes reverse stress data."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result, reverse_stress=sample_reverse_stress_report)
        data = json.loads(json_str)

        assert "reverse_stress" in data
        rev = data["reverse_stress"]
        assert rev["base_reserve"] == 100_000
        assert len(rev["results"]) == 3

    def test_json_indent(self, sample_result):
        """Test JSON indentation."""
        reporter = StressTestReporter()

        # Indented JSON
        json_indented = reporter.to_json(sample_result, indent=2)
        assert "\n" in json_indented

        # Compact JSON
        json_compact = reporter.to_json(sample_result, indent=0)
        assert len(json_compact) < len(json_indented)

    def test_json_includes_executive_summary(self, sample_result):
        """Test JSON includes executive summary."""
        reporter = StressTestReporter()
        json_str = reporter.to_json(sample_result)
        data = json.loads(json_str)

        assert "executive_summary" in data
        assert len(data["executive_summary"]) > 50


class TestToDict:
    """Tests for to_dict method."""

    def test_to_dict_basic(self, sample_result):
        """Test to_dict returns valid dict."""
        reporter = StressTestReporter()
        data = reporter.to_dict(sample_result)

        assert isinstance(data, dict)
        assert "metadata" in data
        assert "summary" in data
        assert "scenarios" in data


# =============================================================================
# Save Report Tests
# =============================================================================


class TestSaveReport:
    """Tests for save_report method."""

    def test_save_markdown(self, sample_result):
        """Test saving Markdown report."""
        reporter = StressTestReporter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            filepath = f.name

        try:
            reporter.save_report(sample_result, filepath, format="markdown")
            content = Path(filepath).read_text()
            assert "# Stress Test Report" in content
        finally:
            Path(filepath).unlink()

    def test_save_json(self, sample_result):
        """Test saving JSON report."""
        reporter = StressTestReporter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            reporter.save_report(sample_result, filepath, format="json")
            content = Path(filepath).read_text()
            data = json.loads(content)
            assert "metadata" in data
        finally:
            Path(filepath).unlink()

    def test_save_invalid_format(self, sample_result):
        """Test saving with invalid format raises error."""
        reporter = StressTestReporter()

        with pytest.raises(ValueError, match="Unsupported format"):
            reporter.save_report(sample_result, "test.txt", format="xml")


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_stress_report_markdown(self, sample_result):
        """Test generate_stress_report with markdown format."""
        report = generate_stress_report(sample_result, format="markdown")
        assert "# Stress Test Report" in report

    def test_generate_stress_report_json(self, sample_result):
        """Test generate_stress_report with JSON format."""
        report = generate_stress_report(sample_result, format="json")
        data = json.loads(report)
        assert "metadata" in data

    def test_generate_stress_report_custom_title(self, sample_result):
        """Test generate_stress_report with custom title."""
        report = generate_stress_report(sample_result, format="markdown", title="Custom Title")
        assert "# Custom Title" in report

    def test_generate_stress_report_invalid_format(self, sample_result):
        """Test generate_stress_report with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            generate_stress_report(sample_result, format="xml")

    def test_generate_quick_summary(self, sample_result):
        """Test generate_quick_summary function."""
        summary = generate_quick_summary(sample_result)

        assert isinstance(summary, str)
        assert len(summary) > 50
        assert "5 scenarios" in summary


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_gate_failures(self):
        """Test reporting with no gate failures."""
        metrics = [
            create_stress_metrics(
                scenario_name="test",
                base_reserve=100_000,
                stressed_reserve=110_000,
                validation_gates={"gate1": True},
            )
        ]
        summary = create_summary(metrics)
        result = StressTestResult(
            summary=summary,
            metrics=metrics,
            execution_time_sec=1.0,
            calculator_type="vm21",
            config=StressTestConfig(),
        )

        reporter = StressTestReporter()
        markdown = reporter.to_markdown(result)

        assert "No validation gate failures" in markdown

    def test_with_gate_failures(self):
        """Test reporting with gate failures."""
        metrics = [
            create_stress_metrics(
                scenario_name="failing_test",
                base_reserve=100_000,
                stressed_reserve=200_000,
                validation_gates={"reserve_within_limit": False},
            )
        ]
        summary = create_summary(metrics)
        result = StressTestResult(
            summary=summary,
            metrics=metrics,
            execution_time_sec=1.0,
            calculator_type="vm21",
            config=StressTestConfig(),
        )

        reporter = StressTestReporter()
        markdown = reporter.to_markdown(result)

        assert "## Validation Gate Failures" in markdown
        assert "failing_test" in markdown
        assert "reserve_within_limit" in markdown

    def test_large_reserve_values(self):
        """Test formatting with large reserve values."""
        metrics = [
            create_stress_metrics(
                scenario_name="large_test",
                base_reserve=1_000_000_000,
                stressed_reserve=1_450_000_000,
                validation_gates={"gate1": True},
            )
        ]
        summary = create_summary(metrics)
        result = StressTestResult(
            summary=summary,
            metrics=metrics,
            execution_time_sec=1.0,
            calculator_type="vm21",
            config=StressTestConfig(),
        )

        reporter = StressTestReporter()
        markdown = reporter.to_markdown(result)

        # Should format with commas
        assert "1,000,000,000" in markdown

    def test_all_critical_severity(self):
        """Test reporting when all scenarios are critical."""
        metrics = [
            create_stress_metrics(
                scenario_name=f"critical_{i}",
                base_reserve=100_000,
                stressed_reserve=200_000,  # 100% increase = critical
                validation_gates={"gate1": True},
            )
            for i in range(3)
        ]
        summary = create_summary(metrics)
        result = StressTestResult(
            summary=summary,
            metrics=metrics,
            execution_time_sec=1.0,
            calculator_type="vm21",
            config=StressTestConfig(),
        )

        reporter = StressTestReporter()
        summary_text = reporter.generate_executive_summary(summary)

        assert "CRITICAL" in summary_text or "3 scenarios" in summary_text

    def test_reverse_stress_no_breaches(self):
        """Test reverse stress section when no breaches."""
        target = RESERVE_EXHAUSTION
        results = {
            ("reserve_exhaustion", "equity_shock"): ReverseStressResult(
                target=target,
                parameter_name="equity_shock",
                breaking_point=None,
                iterations=0,
                converged=True,
                breached=False,
                base_value=-0.30,
                search_range=(-1.0, 0.5),
                final_metric_value=None,
            )
        }
        report = ReverseStressReport(results=results, base_reserve=100_000)

        sample_metrics = [
            create_stress_metrics(
                scenario_name="test",
                base_reserve=100_000,
                stressed_reserve=110_000,
                validation_gates={"gate1": True},
            )
        ]
        sample_summary = create_summary(sample_metrics)
        sample_result = StressTestResult(
            summary=sample_summary,
            metrics=sample_metrics,
            execution_time_sec=1.0,
            calculator_type="vm21",
            config=StressTestConfig(),
        )

        reporter = StressTestReporter()
        markdown = reporter.to_markdown(sample_result, reverse_stress=report)

        assert "Thresholds Breached**: 0 /" in markdown
