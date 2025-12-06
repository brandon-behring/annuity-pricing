.PHONY: help env-paper figures paper reproduce clean-paper clean lint format test

# Default target
help:
	@echo "annuity-pricing paper reproduction targets:"
	@echo ""
	@echo "  make env-paper      Install LaTeX and Python dependencies for paper"
	@echo "  make figures        Generate all figures (PDFs + CSVs)"
	@echo "  make paper          Compile LaTeX document to PDF"
	@echo "  make reproduce      Full pipeline: tests → figures → paper"
	@echo "  make clean-paper    Clean LaTeX build artifacts"
	@echo "  make clean          Clean all build artifacts"
	@echo ""
	@echo "Development targets:"
	@echo "  make lint           Run linters (ruff, mypy)"
	@echo "  make format         Format code (black)"
	@echo "  make test           Run unit tests"

# ============================================================================
# Paper Targets
# ============================================================================

env-paper:
	@echo "Installing LaTeX and paper dependencies..."
	pip install -e ".[viz,validation]" --quiet
	pip install latexmk nbconvert papermill --quiet
	@echo "✓ Environment ready for paper generation"

figures:
	@echo "Generating figures with deterministic seeds..."
	python -m scripts.figures.plot_rila_fia_payoffs
	python -m scripts.figures.plot_mc_convergence
	python -m scripts.figures.plot_bs_parity
	python -m scripts.figures.plot_glwb_fee_surface
	python -m scripts.figures.plot_vm21_cte_sensitivity
	@echo "✓ All figures generated"

paper: figures
	@echo "Compiling LaTeX document..."
	cd paper && latexmk -pdf -shell-escape main.tex
	@echo "✓ Paper compiled: paper/main.pdf"

reproduce: clean
	@echo "Running full reproduction pipeline..."
	@echo ""
	@echo "Step 1: Running unit tests..."
	pytest tests/ -v --tb=short
	@echo ""
	@echo "Step 2: Generating figures..."
	$(MAKE) figures
	@echo ""
	@echo "Step 3: Compiling paper..."
	$(MAKE) paper
	@echo ""
	@echo "Step 4: Saving dependency manifest..."
	mkdir -p paper/artifacts
	pip freeze > paper/artifacts/requirements-paper.txt
	@echo ""
	@echo "✓ REPRODUCTION COMPLETE"
	@echo "  Output: paper/main.pdf"
	@echo "  Artifacts: paper/artifacts/"
	@echo "  Figures: paper/figures/"
	@echo "  Requirements: paper/artifacts/requirements-paper.txt"

clean-paper:
	@echo "Cleaning LaTeX build artifacts..."
	cd paper && latexmk -C
	rm -f paper/main.pdf
	@echo "✓ LaTeX artifacts cleaned"

# ============================================================================
# Development Targets
# ============================================================================

lint:
	@echo "Running linters..."
	ruff check src/ tests/ scripts/
	mypy src/
	@echo "✓ Linting complete"

format:
	@echo "Formatting code..."
	black src/ tests/ scripts/
	@echo "✓ Formatting complete"

test:
	@echo "Running unit tests..."
	pytest tests/ -v --cov=src --cov-report=html
	@echo "✓ Tests complete (coverage report: htmlcov/index.html)"

# ============================================================================
# Clean Targets
# ============================================================================

clean: clean-paper
	@echo "Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Build artifacts cleaned"

.PHONY: help env-paper figures paper reproduce clean-paper clean lint format test
