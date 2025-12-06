#!/bin/bash
# R Actuarial Environment Helper Script
# Usage: ./r_actuarial.sh [command]
#
# Commands:
#   shell     - Start R interactive session
#   script    - Run an R script: ./r_actuarial.sh script myscript.R
#   jupyter   - Start Jupyter with R kernel
#   packages  - List installed actuarial packages
#   test      - Run validation test

MICROMAMBA=~/.local/bin/micromamba
ENV_NAME=r-actuarial

case "$1" in
    shell)
        $MICROMAMBA run -n $ENV_NAME R
        ;;
    script)
        if [ -z "$2" ]; then
            echo "Usage: $0 script <script.R>"
            exit 1
        fi
        $MICROMAMBA run -n $ENV_NAME Rscript "$2"
        ;;
    jupyter)
        $MICROMAMBA run -n $ENV_NAME jupyter lab
        ;;
    packages)
        $MICROMAMBA run -n $ENV_NAME Rscript -e '
        pkgs <- c("lifecontingencies", "StMoMo", "actuar", "demography",
                  "MortalityLaws", "MortalityTables", "AnnuityRIR",
                  "LifeInsuranceContracts", "markovchain")
        for(p in pkgs) {
            if(requireNamespace(p, quietly=TRUE)) {
                cat(sprintf("✓ %-25s v%s\n", p, packageVersion(p)))
            } else {
                cat(sprintf("✗ %-25s NOT INSTALLED\n", p))
            }
        }
        '
        ;;
    test)
        $MICROMAMBA run -n $ENV_NAME Rscript -e '
        library(lifecontingencies)
        data(soa08Act)
        ax <- axn(soa08Act, x=65, n=10, i=0.05)
        cat(sprintf("10-year annuity-due (age 65, 5%%): %.4f\n", ax))
        cat("✓ Validation passed\n")
        '
        ;;
    *)
        echo "R Actuarial Environment"
        echo "======================"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  shell     Start R interactive session"
        echo "  script    Run an R script"
        echo "  jupyter   Start Jupyter with R kernel"
        echo "  packages  List installed actuarial packages"
        echo "  test      Run validation test"
        echo ""
        echo "Example:"
        echo "  $0 shell                    # Start R"
        echo "  $0 script analysis.R        # Run script"
        echo ""
        echo "Direct micromamba usage:"
        echo "  ~/.local/bin/micromamba run -n r-actuarial R"
        echo "  ~/.local/bin/micromamba run -n r-actuarial Rscript script.R"
        ;;
esac
