"""
Tests for regulatory module disclaimers.

Ensures all regulatory modules have proper [PROTOTYPE] disclaimers
to prevent accidental use for production regulatory filings.
"""


from annuity_pricing import regulatory
from annuity_pricing.regulatory import scenarios, vm21, vm22


class TestModuleDisclaimers:
    """Verify module-level disclaimers are present."""

    def test_init_has_prototype_disclaimer(self):
        """Main regulatory __init__ has PROTOTYPE disclaimer."""
        assert "[PROTOTYPE]" in regulatory.__doc__
        assert "EDUCATIONAL USE ONLY" in regulatory.__doc__

    def test_init_mentions_compliance_gap(self):
        """Main regulatory __init__ references compliance gap doc."""
        assert "AG43_COMPLIANCE_GAP.md" in regulatory.__doc__

    def test_vm21_has_prototype_disclaimer(self):
        """VM-21 module has PROTOTYPE disclaimer."""
        assert "[PROTOTYPE]" in vm21.__doc__
        assert "EDUCATIONAL USE ONLY" in vm21.__doc__

    def test_vm21_mentions_naic_scenarios(self):
        """VM-21 module mentions NAIC scenario requirements."""
        assert "NAIC" in vm21.__doc__
        assert "scenario" in vm21.__doc__.lower()

    def test_vm22_has_prototype_disclaimer(self):
        """VM-22 module has PROTOTYPE disclaimer."""
        assert "[PROTOTYPE]" in vm22.__doc__
        assert "EDUCATIONAL USE ONLY" in vm22.__doc__

    def test_vm22_mentions_goes_timeline(self):
        """VM-22 module mentions GOES transition timeline."""
        assert "GOES" in vm22.__doc__
        assert "2026" in vm22.__doc__

    def test_scenarios_has_prototype_disclaimer(self):
        """Scenarios module has PROTOTYPE disclaimer."""
        assert "[PROTOTYPE]" in scenarios.__doc__
        assert "NOT FOR NAIC REGULATORY FILING" in scenarios.__doc__

    def test_scenarios_mentions_vasicek_gbm(self):
        """Scenarios module mentions custom Vasicek + GBM."""
        assert "Vasicek" in scenarios.__doc__
        assert "GBM" in scenarios.__doc__


class TestClassDisclaimers:
    """Verify class-level disclaimers are present."""

    def test_vm21_calculator_has_disclaimer(self):
        """VM21Calculator class has PROTOTYPE disclaimer."""
        from annuity_pricing.regulatory.vm21 import VM21Calculator

        assert "[PROTOTYPE]" in VM21Calculator.__doc__
        assert "EDUCATIONAL USE ONLY" in VM21Calculator.__doc__

    def test_vm21_calculator_references_gap_doc(self):
        """VM21Calculator references compliance gap document."""
        from annuity_pricing.regulatory.vm21 import VM21Calculator

        assert "AG43_COMPLIANCE_GAP.md" in VM21Calculator.__doc__

    def test_vm22_calculator_has_disclaimer(self):
        """VM22Calculator class has PROTOTYPE disclaimer."""
        from annuity_pricing.regulatory.vm22 import VM22Calculator

        assert "[PROTOTYPE]" in VM22Calculator.__doc__
        assert "EDUCATIONAL USE ONLY" in VM22Calculator.__doc__

    def test_vm22_calculator_mentions_2029_deadline(self):
        """VM22Calculator mentions 2029 mandatory compliance."""
        from annuity_pricing.regulatory.vm22 import VM22Calculator

        assert "2029" in VM22Calculator.__doc__

    def test_scenario_generator_has_disclaimer(self):
        """ScenarioGenerator class has PROTOTYPE disclaimer."""
        from annuity_pricing.regulatory.scenarios import ScenarioGenerator

        assert "[PROTOTYPE]" in ScenarioGenerator.__doc__
        assert "NOT NAIC-COMPLIANT" in ScenarioGenerator.__doc__

    def test_scenario_generator_references_gap_doc(self):
        """ScenarioGenerator references compliance gap document."""
        from annuity_pricing.regulatory.scenarios import ScenarioGenerator

        assert "AG43_COMPLIANCE_GAP.md" in ScenarioGenerator.__doc__


class TestDisclaimerCompleteness:
    """Verify disclaimers contain required warnings."""

    def test_vm21_lists_missing_requirements(self):
        """VM-21 module lists missing compliance requirements."""
        doc = vm21.__doc__
        # Should mention key missing items
        assert "CDHS" in doc or "hedging" in doc.lower()
        assert "VM-31" in doc
        assert "FSA" in doc or "MAAA" in doc or "actuar" in doc.lower()

    def test_vm22_lists_missing_requirements(self):
        """VM-22 module lists missing compliance requirements."""
        doc = vm22.__doc__
        # Should mention key missing items
        assert "VM-31" in doc
        assert "VM-G" in doc
        assert "experience" in doc.lower() or "credibility" in doc.lower()

    def test_scenarios_explains_custom_models(self):
        """Scenarios module explains it uses custom models."""
        doc = scenarios.__doc__
        assert "Vasicek" in doc
        assert "GBM" in doc
        assert "NOT NAIC-prescribed" in doc or "NOT the NAIC-prescribed" in doc


class TestComplianceGapDocExists:
    """Verify compliance gap documentation exists."""

    def test_compliance_gap_doc_exists(self):
        """AG43_COMPLIANCE_GAP.md file exists."""
        import os

        gap_doc_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docs",
            "regulatory",
            "AG43_COMPLIANCE_GAP.md",
        )
        # Normalize path
        gap_doc_path = os.path.normpath(gap_doc_path)

        assert os.path.exists(gap_doc_path), f"Missing: {gap_doc_path}"

    def test_compliance_gap_doc_has_content(self):
        """AG43_COMPLIANCE_GAP.md has substantive content."""
        import os

        gap_doc_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docs",
            "regulatory",
            "AG43_COMPLIANCE_GAP.md",
        )
        gap_doc_path = os.path.normpath(gap_doc_path)

        with open(gap_doc_path, encoding="utf-8") as f:
            content = f.read()

        # Check for key sections
        assert "Executive Summary" in content
        assert "VM-21" in content
        assert "VM-22" in content
        assert "Scenario" in content
        assert "FSA" in content or "MAAA" in content  # Actuarial certification
        assert "GOES" in content  # Future scenario generator
        assert "2026" in content  # Key date
        assert "2029" in content  # VM-22 mandatory date


class TestRuntimeWarnings:
    """Test that runtime usage provides appropriate context."""

    def test_vm21_result_is_educational(self):
        """VM21Calculator produces results but is clearly educational."""
        from annuity_pricing.regulatory.vm21 import PolicyData, VM21Calculator

        calc = VM21Calculator(n_scenarios=10, seed=42)
        policy = PolicyData(av=100_000, gwb=110_000, age=70)

        # Should work for educational purposes
        result = calc.calculate_reserve(policy)
        assert result.reserve >= 0

        # But class is clearly marked as prototype
        assert "[PROTOTYPE]" in VM21Calculator.__doc__

    def test_vm22_result_is_educational(self):
        """VM22Calculator produces results but is clearly educational."""
        from annuity_pricing.regulatory.vm22 import FixedAnnuityPolicy, VM22Calculator

        calc = VM22Calculator(n_scenarios=10, seed=42)
        policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)

        # Should work for educational purposes
        result = calc.calculate_reserve(policy)
        assert result.reserve >= 0

        # But class is clearly marked as prototype
        assert "[PROTOTYPE]" in VM22Calculator.__doc__

    def test_scenario_generator_is_educational(self):
        """ScenarioGenerator produces scenarios but is clearly educational."""
        from annuity_pricing.regulatory.scenarios import ScenarioGenerator

        gen = ScenarioGenerator(n_scenarios=10, seed=42)

        # Should work for educational purposes
        scenarios = gen.generate_ag43_scenarios()
        assert scenarios.n_scenarios == 10

        # But class is clearly marked as prototype
        assert "[PROTOTYPE]" in ScenarioGenerator.__doc__
