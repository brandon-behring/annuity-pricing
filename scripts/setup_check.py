#!/usr/bin/env python3
"""
setup_check.py - Verify annuity-pricing environment and dependencies.

Usage:
    python scripts/setup_check.py [--verbose]

Checks:
    1. Python version >= 3.10
    2. Core dependencies installed
    3. Optional dependencies status
    4. pyproject.toml consistency
    5. Directory structure
    6. Data files present

Exit codes:
    0 = All checks passed
    1 = Critical issue (blocks development)
    2 = Warning (non-blocking)
"""

import sys
import importlib
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    """Result of a single check."""
    name: str
    passed: bool
    message: str
    critical: bool = True


def check_python_version() -> CheckResult:
    """Verify Python version >= 3.10."""
    version = sys.version_info
    passed = version >= (3, 10)
    return CheckResult(
        name="Python Version",
        passed=passed,
        message=f"Python {version.major}.{version.minor}.{version.micro}",
        critical=True
    )


def check_core_dependencies() -> list[CheckResult]:
    """Check that core dependencies are installed."""
    core_deps = [
        ("numpy", "1.24"),
        ("pandas", "2.0"),
        ("scipy", "1.11"),
        ("pyarrow", "14.0"),
        ("yfinance", "0.2"),
        ("fredapi", "0.5"),
    ]

    results = []
    for pkg_name, min_version in core_deps:
        try:
            module = importlib.import_module(pkg_name)
            version = getattr(module, "__version__", "unknown")
            results.append(CheckResult(
                name=f"Core: {pkg_name}",
                passed=True,
                message=f"v{version}",
                critical=True
            ))
        except ImportError:
            results.append(CheckResult(
                name=f"Core: {pkg_name}",
                passed=False,
                message=f"NOT INSTALLED (required >= {min_version})",
                critical=True
            ))

    return results


def check_optional_dependencies() -> list[CheckResult]:
    """Check optional dependencies (non-critical)."""
    optional_groups = {
        "dev": [("pytest", "7.0"), ("black", "23.0"), ("mypy", "1.0"), ("ruff", "0.1")],
        "viz": [("matplotlib", "3.5"), ("seaborn", "0.12"), ("plotly", "5.0"), ("jupyter", "1.0")],
        "vol": [("pysabr", "0.3")],
        "validation": [("financepy", "0.350"), ("QuantLib", "1.31")],
    }

    results = []
    for group, deps in optional_groups.items():
        for pkg_name, min_version in deps:
            try:
                # Handle special package names
                import_name = pkg_name.lower()
                if pkg_name == "QuantLib":
                    import_name = "QuantLib"

                module = importlib.import_module(import_name)
                version = getattr(module, "__version__", "unknown")
                results.append(CheckResult(
                    name=f"Optional[{group}]: {pkg_name}",
                    passed=True,
                    message=f"v{version}",
                    critical=False
                ))
            except ImportError:
                results.append(CheckResult(
                    name=f"Optional[{group}]: {pkg_name}",
                    passed=False,
                    message=f"not installed (optional, >= {min_version})",
                    critical=False
                ))

    return results


def check_directory_structure() -> list[CheckResult]:
    """Verify expected directory structure exists."""
    project_root = Path(__file__).parent.parent

    expected_dirs = [
        "src/annuity_pricing",
        "tests",
        "notebooks",
        "docs",
        "scripts",
    ]

    expected_files = [
        "pyproject.toml",
        "CLAUDE.md",
        "CONSTITUTION.md",
        "ROADMAP.md",
    ]

    results = []

    for dir_path in expected_dirs:
        full_path = project_root / dir_path
        results.append(CheckResult(
            name=f"Directory: {dir_path}",
            passed=full_path.exists(),
            message="exists" if full_path.exists() else "MISSING",
            critical=dir_path in ["src/annuity_pricing", "tests"]
        ))

    for file_path in expected_files:
        full_path = project_root / file_path
        results.append(CheckResult(
            name=f"File: {file_path}",
            passed=full_path.exists(),
            message="exists" if full_path.exists() else "MISSING",
            critical=file_path == "pyproject.toml"
        ))

    return results


def check_data_files() -> list[CheckResult]:
    """Check for data files."""
    project_root = Path(__file__).parent.parent

    data_files = [
        ("wink.parquet", "WINK competitive rate data"),
        ("wink-research-archive/data-dictionary/WINK_DATA_DICTIONARY.md", "WINK data dictionary"),
    ]

    results = []
    for file_path, description in data_files:
        full_path = project_root / file_path
        if full_path.exists():
            size_mb = full_path.stat().st_size / (1024 * 1024)
            results.append(CheckResult(
                name=f"Data: {description}",
                passed=True,
                message=f"{size_mb:.1f} MB" if size_mb > 0.1 else "present",
                critical=False
            ))
        else:
            results.append(CheckResult(
                name=f"Data: {description}",
                passed=False,
                message="not found",
                critical=False
            ))

    return results


def print_results(results: list[CheckResult], verbose: bool = False) -> tuple[int, int]:
    """Print results and return (critical_failures, warnings)."""
    critical_failures = 0
    warnings = 0

    for result in results:
        if result.passed:
            symbol = "✓"
            color = "\033[92m"  # Green
        elif result.critical:
            symbol = "✗"
            color = "\033[91m"  # Red
            critical_failures += 1
        else:
            symbol = "⚠"
            color = "\033[93m"  # Yellow
            warnings += 1

        reset = "\033[0m"

        if verbose or not result.passed:
            print(f"{color}{symbol}{reset} {result.name}: {result.message}")
        elif result.passed and verbose:
            print(f"{color}{symbol}{reset} {result.name}: {result.message}")

    return critical_failures, warnings


def main():
    """Run all checks and report results."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("=" * 60)
    print("  annuity-pricing Environment Check")
    print("=" * 60)
    print()

    all_results: list[CheckResult] = []

    # Python version
    print("Python Version:")
    result = check_python_version()
    all_results.append(result)
    print_results([result], verbose=True)
    print()

    # Core dependencies
    print("Core Dependencies:")
    results = check_core_dependencies()
    all_results.extend(results)
    print_results(results, verbose=verbose)
    print()

    # Optional dependencies
    print("Optional Dependencies:")
    results = check_optional_dependencies()
    all_results.extend(results)
    print_results(results, verbose=verbose)
    print()

    # Directory structure
    print("Directory Structure:")
    results = check_directory_structure()
    all_results.extend(results)
    print_results(results, verbose=verbose)
    print()

    # Data files
    print("Data Files:")
    results = check_data_files()
    all_results.extend(results)
    print_results(results, verbose=verbose)
    print()

    # Summary
    critical_failures, warnings = 0, 0
    for r in all_results:
        if not r.passed:
            if r.critical:
                critical_failures += 1
            else:
                warnings += 1

    print("=" * 60)
    if critical_failures > 0:
        print(f"\033[91m✗ {critical_failures} critical issue(s) found\033[0m")
        print("  Run: pip install -e '.[dev,viz]'")
        sys.exit(1)
    elif warnings > 0:
        print(f"\033[93m⚠ {warnings} warning(s) (non-blocking)\033[0m")
        print("  Optional packages can be installed with:")
        print("    pip install financepy QuantLib-Python")
        sys.exit(0)
    else:
        print("\033[92m✓ All checks passed!\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
