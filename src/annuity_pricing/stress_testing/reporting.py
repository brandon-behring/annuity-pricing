"""
Stress Test Reporting - Phase I.4.

[T2] Generates Markdown executive summaries and JSON structured
output for stress test results.

Design Principles:
- **Dual Format**: Both Markdown (human-readable) and JSON (machine-readable)
- **Executive Summary**: Concise 1-2 paragraph summary for executives
- **Comprehensive**: Includes all scenarios, sensitivity, reverse stress
- **Integration**: Works with all stress testing modules

See: docs/stress_testing/STRESS_TESTING_GUIDE.md
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .metrics import SeverityLevel, StressMetrics, StressTestSummary
from .reverse import ReverseStressReport
from .sensitivity import TornadoData

# =============================================================================
# Report Configuration
# =============================================================================


@dataclass
class ReportConfig:
    """
    Configuration for report generation.

    Attributes
    ----------
    title : str
        Report title
    include_scenarios : bool
        Include individual scenario results
    include_sensitivity : bool
        Include sensitivity analysis section
    include_reverse_stress : bool
        Include reverse stress testing section
    include_executive_summary : bool
        Include executive summary
    max_scenarios_to_display : int
        Maximum scenarios to show in detail (0 = all)
    percentile_levels : tuple
        Percentile levels to include
    """

    title: str = "Stress Test Report"
    include_scenarios: bool = True
    include_sensitivity: bool = True
    include_reverse_stress: bool = True
    include_executive_summary: bool = True
    max_scenarios_to_display: int = 10
    percentile_levels: tuple = (5, 25, 50, 75, 95)


# =============================================================================
# Markdown Report Generation
# =============================================================================


class StressTestReporter:
    """
    Generates stress test reports in Markdown and JSON formats.

    Examples
    --------
    >>> from annuity_pricing.stress_testing import (
    ...     StressTestReporter, quick_stress_test
    ... )
    >>> result = quick_stress_test(base_reserve=100_000)
    >>> reporter = StressTestReporter()
    >>> markdown = reporter.to_markdown(result)
    >>> print(markdown)
    """

    def __init__(self, config: ReportConfig | None = None):
        """
        Initialize reporter.

        Parameters
        ----------
        config : Optional[ReportConfig]
            Report configuration. If None, uses defaults.
        """
        self.config = config or ReportConfig()

    def generate_executive_summary(
        self,
        summary: StressTestSummary,
        sensitivity: TornadoData | None = None,
        reverse_stress: ReverseStressReport | None = None,
    ) -> str:
        """
        Generate 1-2 paragraph executive summary.

        Parameters
        ----------
        summary : StressTestSummary
            Stress test summary
        sensitivity : Optional[TornadoData]
            Sensitivity analysis results
        reverse_stress : Optional[ReverseStressReport]
            Reverse stress results

        Returns
        -------
        str
            Executive summary paragraph(s)
        """
        lines = []

        # First paragraph: Overall results
        worst_pct = abs(summary.worst_reserve_delta_pct * 100)
        p95_pct = abs(summary.percentiles.get(95, 0) * 100)

        status = "passed" if summary.n_failed == 0 else "failed"
        critical_count = summary.severity_counts.get(SeverityLevel.CRITICAL, 0)

        lines.append(
            f"Stress testing of {summary.n_scenarios} scenarios {status} "
            f"with {summary.n_passed} passing and {summary.n_failed} failing validation gates. "
            f"The worst case ({summary.worst_scenario}) shows a reserve increase of {worst_pct:.1f}%, "
            f"with the 95th percentile at {p95_pct:.1f}%. "
        )

        if critical_count > 0:
            lines[-1] += f"{critical_count} scenarios classified as CRITICAL severity."
        else:
            lines[-1] += "No scenarios reached CRITICAL severity."

        # Second paragraph: Key insights
        insights = []

        if sensitivity:
            most_sensitive = sensitivity.most_sensitive_parameter
            if most_sensitive:
                width = sensitivity.results[0].sensitivity_width * 100
                insights.append(
                    f"{most_sensitive} is the most sensitive parameter "
                    f"(sensitivity width: {width:.1f}%)"
                )

        if reverse_stress:
            breached = reverse_stress.get_breached_results()
            if breached:
                insights.append(f"{len(breached)} reverse stress scenarios breach their thresholds")
            else:
                insights.append("no reverse stress thresholds were breached")

        if insights:
            lines.append("Key findings: " + ", ".join(insights) + ".")

        return " ".join(lines)

    def _format_scenario_table(
        self,
        metrics: list[StressMetrics],
        max_rows: int = 0,
    ) -> str:
        """Format scenarios as Markdown table."""
        lines = [
            "| Scenario | Stressed Reserve | Δ Reserve | Severity | Status |",
            "|----------|------------------|-----------|----------|--------|",
        ]

        # Sort by reserve delta descending (worst first)
        sorted_metrics = sorted(metrics, key=lambda m: m.reserve_delta_pct, reverse=True)

        if max_rows > 0:
            sorted_metrics = sorted_metrics[:max_rows]

        for m in sorted_metrics:
            status = "✓ PASS" if m.passed_gates else "✗ FAIL"
            lines.append(
                f"| {m.scenario_name} | "
                f"${m.stressed_reserve:,.0f} | "
                f"{m.reserve_delta_pct * 100:+.1f}% | "
                f"{m.severity.value.upper()} | "
                f"{status} |"
            )

        return "\n".join(lines)

    def _format_percentile_table(self, summary: StressTestSummary) -> str:
        """Format percentile distribution as Markdown table."""
        lines = [
            "| Percentile | Reserve Δ |",
            "|------------|-----------|",
        ]

        for p in self.config.percentile_levels:
            value = summary.percentiles.get(p, 0)
            lines.append(f"| {p}th | {value * 100:+.1f}% |")

        return "\n".join(lines)

    def _format_severity_breakdown(self, summary: StressTestSummary) -> str:
        """Format severity breakdown as Markdown table."""
        lines = [
            "| Severity | Count | % of Total |",
            "|----------|-------|------------|",
        ]

        for level in SeverityLevel:
            count = summary.severity_counts.get(level, 0)
            pct = (count / summary.n_scenarios * 100) if summary.n_scenarios > 0 else 0
            lines.append(f"| {level.value.upper()} | {count} | {pct:.0f}% |")

        return "\n".join(lines)

    def _format_worst_scenarios(
        self,
        metrics: list[StressMetrics],
        top_n: int = 5,
    ) -> str:
        """Format worst scenarios in detail."""
        lines = []

        sorted_metrics = sorted(metrics, key=lambda m: m.reserve_delta_pct, reverse=True)[:top_n]

        for i, m in enumerate(sorted_metrics, 1):
            lines.append(f"**{i}. {m.scenario_name}**")
            lines.append(f"- Base Reserve: ${m.base_reserve:,.0f}")
            lines.append(f"- Stressed Reserve: ${m.stressed_reserve:,.0f}")
            lines.append(f"- Delta: {m.reserve_delta_pct * 100:+.1f}% (${m.reserve_delta:+,.0f})")
            lines.append(f"- Severity: {m.severity.value.upper()}")
            if m.gate_failures:
                lines.append(f"- Failed Gates: {', '.join(m.gate_failures)}")
            lines.append("")

        return "\n".join(lines)

    def _format_sensitivity_section(self, tornado: TornadoData) -> str:
        """Format sensitivity analysis section."""
        lines = [
            "## Sensitivity Analysis",
            "",
            f"Base Scenario: {tornado.scenario_name}",
            f"Parameters Analyzed: {tornado.n_parameters}",
            "",
            "### Parameter Sensitivity (Sorted by Impact)",
            "",
            "| Parameter | Down Shock Δ | Up Shock Δ | Total Width |",
            "|-----------|--------------|------------|-------------|",
        ]

        for r in tornado.results:
            lines.append(
                f"| {r.display_name} | "
                f"{r.down_delta_pct * 100:+.1f}% | "
                f"{r.up_delta_pct * 100:+.1f}% | "
                f"{r.sensitivity_width * 100:.1f}% |"
            )

        if tornado.most_sensitive_parameter:
            lines.append("")
            most = tornado.results[0]
            lines.append(
                f"**Most Sensitive**: {most.display_name} "
                f"(width: {most.sensitivity_width * 100:.1f}%)"
            )

        return "\n".join(lines)

    def _format_reverse_stress_section(self, report: ReverseStressReport) -> str:
        """Format reverse stress testing section."""
        lines = [
            "## Reverse Stress Testing",
            "",
            f"Base Reserve: ${report.base_reserve:,.0f}",
            f"Target-Parameter Combinations: {len(report.results)}",
            "",
            "### Breaking Points",
            "",
            "| Target | Parameter | Breaking Point | Iterations | Status |",
            "|--------|-----------|----------------|------------|--------|",
        ]

        for (target_type, param), r in sorted(report.results.items()):
            if r.breached and r.breaking_point is not None:
                bp_str = f"{r.breaking_point:.4f}"
                iter_str = str(r.iterations)
                status = "✓ Found"
            else:
                bp_str = "N/A"
                iter_str = "-"
                status = "Not in range"

            lines.append(f"| {target_type} | {param} | {bp_str} | {iter_str} | {status} |")

        breached = report.get_breached_results()
        lines.append("")
        lines.append(f"**Thresholds Breached**: {len(breached)} / {len(report.results)}")

        return "\n".join(lines)

    def _format_validation_failures(self, metrics: list[StressMetrics]) -> str:
        """Format validation gate failures."""
        failed = [m for m in metrics if not m.passed_gates]

        if not failed:
            return "No validation gate failures."

        lines = [
            "## Validation Gate Failures",
            "",
            f"{len(failed)} scenarios failed at least one validation gate:",
            "",
        ]

        for m in failed:
            lines.append(f"- **{m.scenario_name}**: {', '.join(m.gate_failures)}")

        return "\n".join(lines)

    def to_markdown(
        self,
        result: "StressTestResult",
        sensitivity: TornadoData | None = None,
        reverse_stress: ReverseStressReport | None = None,
        title: str | None = None,
    ) -> str:
        """
        Generate complete Markdown report.

        Parameters
        ----------
        result : StressTestResult
            Stress test results
        sensitivity : Optional[TornadoData]
            Sensitivity analysis results
        reverse_stress : Optional[ReverseStressReport]
            Reverse stress results
        title : Optional[str]
            Override report title

        Returns
        -------
        str
            Complete Markdown report
        """
        report_title = title or self.config.title
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sections = [
            f"# {report_title}",
            "",
            f"**Generated**: {timestamp}",
            f"**Calculator**: {result.calculator_type}",
            f"**Execution Time**: {result.execution_time_sec:.2f}s",
            f"**Base Reserve**: ${result.summary.base_reserve:,.0f}",
            "",
        ]

        # Executive Summary
        if self.config.include_executive_summary:
            sections.append("## Executive Summary")
            sections.append("")
            sections.append(
                self.generate_executive_summary(result.summary, sensitivity, reverse_stress)
            )
            sections.append("")

        # Scenario Results
        if self.config.include_scenarios:
            sections.append("## Scenario Results")
            sections.append("")
            sections.append(
                self._format_scenario_table(
                    result.metrics,
                    max_rows=self.config.max_scenarios_to_display,
                )
            )
            sections.append("")

            if len(result.metrics) > self.config.max_scenarios_to_display > 0:
                remaining = len(result.metrics) - self.config.max_scenarios_to_display
                sections.append(f"*...and {remaining} more scenarios*")
                sections.append("")

        # Percentile Distribution
        sections.append("## Percentile Distribution")
        sections.append("")
        sections.append(self._format_percentile_table(result.summary))
        sections.append("")

        # Severity Breakdown
        sections.append("## Severity Breakdown")
        sections.append("")
        sections.append(self._format_severity_breakdown(result.summary))
        sections.append("")

        # Top 5 Worst Scenarios
        sections.append("## Top 5 Worst Scenarios")
        sections.append("")
        sections.append(self._format_worst_scenarios(result.metrics, top_n=5))

        # Sensitivity Analysis
        if self.config.include_sensitivity and sensitivity:
            sections.append(self._format_sensitivity_section(sensitivity))
            sections.append("")

        # Reverse Stress Testing
        if self.config.include_reverse_stress and reverse_stress:
            sections.append(self._format_reverse_stress_section(reverse_stress))
            sections.append("")

        # Validation Failures
        sections.append(self._format_validation_failures(result.metrics))

        return "\n".join(sections)

    def _metrics_to_dict(self, m: StressMetrics) -> dict[str, Any]:
        """Convert StressMetrics to JSON-serializable dict."""
        return {
            "scenario_name": m.scenario_name,
            "base_reserve": m.base_reserve,
            "stressed_reserve": m.stressed_reserve,
            "reserve_delta": m.reserve_delta,
            "reserve_delta_pct": m.reserve_delta_pct,
            "severity": m.severity.value,
            "passed_gates": m.passed_gates,
            "gate_failures": list(m.gate_failures),
            "additional_metrics": dict(m.additional_metrics),
        }

    def _summary_to_dict(self, s: StressTestSummary) -> dict[str, Any]:
        """Convert StressTestSummary to JSON-serializable dict."""
        return {
            "n_scenarios": s.n_scenarios,
            "n_passed": s.n_passed,
            "n_failed": s.n_failed,
            "worst_scenario": s.worst_scenario,
            "worst_reserve_delta_pct": s.worst_reserve_delta_pct,
            "best_scenario": s.best_scenario,
            "best_reserve_delta_pct": s.best_reserve_delta_pct,
            "percentiles": {str(k): v for k, v in s.percentiles.items()},
            "severity_counts": {k.value: v for k, v in s.severity_counts.items()},
            "base_reserve": s.base_reserve,
        }

    def _sensitivity_to_dict(self, t: TornadoData) -> dict[str, Any]:
        """Convert TornadoData to JSON-serializable dict."""
        results = []
        for r in t.results:
            results.append(
                {
                    "parameter": r.parameter,
                    "display_name": r.display_name,
                    "base_value": r.base_value,
                    "base_reserve": r.base_reserve,
                    "down_value": r.down_value,
                    "down_reserve": r.down_reserve,
                    "up_value": r.up_value,
                    "up_reserve": r.up_reserve,
                    "down_delta_pct": r.down_delta_pct,
                    "up_delta_pct": r.up_delta_pct,
                    "sensitivity_width": r.sensitivity_width,
                }
            )

        return {
            "scenario_name": t.scenario_name,
            "base_reserve": t.base_reserve,
            "n_parameters": t.n_parameters,
            "most_sensitive": t.most_sensitive_parameter,
            "least_sensitive": t.least_sensitive_parameter,
            "results": results,
        }

    def _reverse_stress_to_dict(self, r: ReverseStressReport) -> dict[str, Any]:
        """Convert ReverseStressReport to JSON-serializable dict."""
        results = []
        for (target_type, param), res in r.results.items():
            results.append(
                {
                    "target_type": target_type,
                    "parameter": param,
                    "threshold": res.target.threshold,
                    "breach_condition": res.target.breach_condition.value,
                    "breaking_point": res.breaking_point,
                    "iterations": res.iterations,
                    "converged": res.converged,
                    "breached": res.breached,
                    "base_value": res.base_value,
                    "search_range": list(res.search_range),
                    "final_metric_value": res.final_metric_value,
                }
            )

        return {
            "base_reserve": r.base_reserve,
            "targets_tested": r.targets_tested,
            "parameters_tested": r.parameters_tested,
            "results": results,
        }

    def to_json(
        self,
        result: "StressTestResult",
        sensitivity: TornadoData | None = None,
        reverse_stress: ReverseStressReport | None = None,
        indent: int = 2,
    ) -> str:
        """
        Generate JSON report.

        Parameters
        ----------
        result : StressTestResult
            Stress test results
        sensitivity : Optional[TornadoData]
            Sensitivity analysis results
        reverse_stress : Optional[ReverseStressReport]
            Reverse stress results
        indent : int
            JSON indentation (0 for compact)

        Returns
        -------
        str
            JSON string
        """
        timestamp = datetime.now().isoformat()

        report = {
            "metadata": {
                "timestamp": timestamp,
                "calculator_type": result.calculator_type,
                "execution_time_sec": result.execution_time_sec,
                "report_version": "1.0",
            },
            "summary": self._summary_to_dict(result.summary),
            "scenarios": [self._metrics_to_dict(m) for m in result.metrics],
        }

        if sensitivity:
            report["sensitivity"] = self._sensitivity_to_dict(sensitivity)

        if reverse_stress:
            report["reverse_stress"] = self._reverse_stress_to_dict(reverse_stress)

        if self.config.include_executive_summary:
            report["executive_summary"] = self.generate_executive_summary(
                result.summary, sensitivity, reverse_stress
            )

        return json.dumps(report, indent=indent if indent > 0 else None)

    def to_dict(
        self,
        result: "StressTestResult",
        sensitivity: TornadoData | None = None,
        reverse_stress: ReverseStressReport | None = None,
    ) -> dict[str, Any]:
        """
        Generate report as Python dict.

        Parameters
        ----------
        result : StressTestResult
            Stress test results
        sensitivity : Optional[TornadoData]
            Sensitivity analysis results
        reverse_stress : Optional[ReverseStressReport]
            Reverse stress results

        Returns
        -------
        Dict[str, Any]
            Report as dictionary
        """
        return json.loads(self.to_json(result, sensitivity, reverse_stress))

    def save_report(
        self,
        result: "StressTestResult",
        filepath: str,
        format: str = "markdown",
        sensitivity: TornadoData | None = None,
        reverse_stress: ReverseStressReport | None = None,
    ) -> None:
        """
        Save report to file.

        Parameters
        ----------
        result : StressTestResult
            Stress test results
        filepath : str
            Output file path
        format : str
            Output format ("markdown" or "json")
        sensitivity : Optional[TornadoData]
            Sensitivity analysis results
        reverse_stress : Optional[ReverseStressReport]
            Reverse stress results

        Raises
        ------
        ValueError
            If format is not supported
        """
        if format.lower() in ("markdown", "md"):
            content = self.to_markdown(result, sensitivity, reverse_stress)
        elif format.lower() == "json":
            content = self.to_json(result, sensitivity, reverse_stress)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'markdown' or 'json'.")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_stress_report(
    result: "StressTestResult",
    sensitivity: TornadoData | None = None,
    reverse_stress: ReverseStressReport | None = None,
    format: str = "markdown",
    title: str = "Stress Test Report",
) -> str:
    """
    Generate stress test report.

    Parameters
    ----------
    result : StressTestResult
        Stress test results
    sensitivity : Optional[TornadoData]
        Sensitivity analysis results
    reverse_stress : Optional[ReverseStressReport]
        Reverse stress results
    format : str
        Output format ("markdown" or "json")
    title : str
        Report title (markdown only)

    Returns
    -------
    str
        Generated report

    Examples
    --------
    >>> from annuity_pricing.stress_testing import quick_stress_test
    >>> result = quick_stress_test(base_reserve=100_000)
    >>> report = generate_stress_report(result, format="markdown")
    >>> print(report)
    """
    config = ReportConfig(title=title)
    reporter = StressTestReporter(config)

    if format.lower() in ("markdown", "md"):
        return reporter.to_markdown(result, sensitivity, reverse_stress, title=title)
    elif format.lower() == "json":
        return reporter.to_json(result, sensitivity, reverse_stress)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'markdown' or 'json'.")


def generate_quick_summary(
    result: "StressTestResult",
) -> str:
    """
    Generate one-paragraph summary.

    Parameters
    ----------
    result : StressTestResult
        Stress test results

    Returns
    -------
    str
        Brief summary paragraph

    Examples
    --------
    >>> from annuity_pricing.stress_testing import quick_stress_test
    >>> result = quick_stress_test(base_reserve=100_000)
    >>> print(generate_quick_summary(result))
    """
    reporter = StressTestReporter()
    return reporter.generate_executive_summary(result.summary)


# Import for type hints (avoiding circular import)
try:
    from .runner import StressTestResult
except ImportError:
    pass
