# Model Cards

Model cards provide standardized documentation for each major component,
including intended use, assumptions, validation status, and limitations.

## Available Model Cards

```{toctree}
:maxdepth: 1

myga
fia
rila
glwb
fia_pricer
rila_pricer
glwb_simulator
TEMPLATE
```

## What's in a Model Card?

Each model card includes:

| Section | Purpose |
|---------|---------|
| **Overview** | Version, module, knowledge tier |
| **Intended Use** | What it's for (and what it's not) |
| **Parameters** | Inputs with types and tiers |
| **Assumptions** | What the model assumes |
| **Validation** | How it's been tested |
| **Limitations** | Known constraints |
| **References** | Academic and data sources |

## Knowledge Tiers

All claims are tagged with validation levels:

- **[T1]** Academically validated (peer-reviewed)
- **[T2]** Empirically validated (WINK data, cross-library)
- **[T3]** Assumptions (require sensitivity analysis)

See {doc}`/glossary` for full tier definitions.
