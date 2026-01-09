Glossary & Knowledge Tiers
==========================

Knowledge Tier System
---------------------

All claims in this documentation are tagged with knowledge tiers to indicate
their level of validation:

.. glossary::

   [T1] Academically Validated
      Claims backed by peer-reviewed literature or mathematical proof.
      These are foundational results that can be trusted without reservation.

      **Examples:**

      - Black-Scholes formula (Black & Scholes, 1973)
      - Put-Call Parity: :math:`C - P = S - Ke^{-rT}`
      - No-arbitrage bounds: option value ≤ underlying
      - Buffer = Long ATM put - Short OTM put

   [T2] Empirically Validated
      Claims validated against WINK market data or cross-validated with
      external libraries (financepy, QuantLib, pyfeng).

      **Examples:**

      - Median FIA cap rate = 5% (WINK Q4 2024)
      - BS implementation matches financepy within 1e-10
      - SOA 2018 lapse rates match published study

   [T3] Assumptions
      Working assumptions that require sensitivity analysis.
      Use with caution; validate in your specific context.

      **Examples:**

      - Option budget = 3% of premium (carrier-specific)
      - Base lapse rate = 5% (varies by product)
      - GLWB utilization = 80% at age 70

Domain Terms
------------

Product Types
^^^^^^^^^^^^^

.. glossary::

   MYGA
      Multi-Year Guaranteed Annuity. Fixed rate for a specified term.
      Simplest annuity product. PV = sum of guaranteed payments.

   FIA
      Fixed Indexed Annuity. Credited return linked to an index (e.g., S&P 500)
      with a 0% floor guarantee. [T1] FIA cannot lose money due to index performance.

   RILA
      Registered Index-Linked Annuity. Similar to FIA but with partial
      downside protection (buffer or floor) instead of 0% guarantee.
      Offers higher upside caps in exchange for some downside risk.

   GLWB
      Guaranteed Lifetime Withdrawal Benefit. Rider that provides income
      for life, continuing even if account value is exhausted.
      [T1] GLWB guarantees are backed by insurer reserves.

Protection Mechanics
^^^^^^^^^^^^^^^^^^^^

.. glossary::

   Buffer
      RILA protection where insurer absorbs the FIRST X% of losses.
      [T1] Implemented as: Long ATM put - Short OTM put (put spread).

      **Example:** 10% buffer, index returns -15% → client loses 5%

   Floor
      RILA protection where insurer covers losses BEYOND X%.
      [T1] Implemented as: Long OTM put.

      **Example:** -10% floor, index returns -15% → client loses 10%

   Cap
      Maximum credited return on FIA/RILA products.
      [T1] FIA payoff = min(index_return, cap)

      **Example:** 8% cap, index returns 15% → credited 8%

   Participation Rate
      Percentage of index return credited to policyholder.
      [T1] FIA payoff = index_return × participation_rate (subject to cap/floor)

      **Example:** 80% participation, index returns 10% → credited 8%

   Spread
      Amount deducted from index return before crediting.
      [T1] FIA payoff = max(0, index_return - spread)

      **Example:** 2% spread, index returns 7% → credited 5%

Options & Pricing
^^^^^^^^^^^^^^^^^

.. glossary::

   Black-Scholes
      [T1] Closed-form option pricing formula assuming log-normal returns
      and constant volatility. Foundation of all embedded option valuation.

   Put-Call Parity
      [T1] Fundamental identity: :math:`C - P = S - Ke^{-rT}`
      Used to verify BS implementation correctness.

   Greeks
      [T1] Option sensitivities: Delta (∂V/∂S), Gamma (∂²V/∂S²),
      Vega (∂V/∂σ), Theta (∂V/∂t), Rho (∂V/∂r).

   Monte Carlo
      Simulation-based pricing for path-dependent options.
      Convergence: error ∝ 1/√n where n = number of paths.

Regulatory
^^^^^^^^^^

.. glossary::

   VM-21
      NAIC Valuation Manual Chapter 21. Requirements for variable
      annuity reserves. Includes stochastic scenarios and CTE calculations.

   VM-22
      NAIC Valuation Manual Chapter 22. Requirements for fixed
      annuity reserves, including MYGA and FIA products.

   MGSV
      Minimum Guaranteed Surrender Value. NAIC-required floor
      on surrender values to protect policyholders.

   MVA
      Market Value Adjustment. Adjustment to surrender value
      based on interest rate changes since issue.

See Also
--------

- :doc:`/validation/cross_validation` - How T2 validation is performed
- :doc:`/api/products` - Product API reference
- :doc:`/guides/getting_started` - Quick start guide
