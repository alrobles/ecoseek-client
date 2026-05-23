---
name: climate
description: Climate change scenario analysis and projections
category: ecology
triggers: [climate, CMIP6, projection, future scenario, SSP, ensemble]
---

# Climate Change Scenario Analysis

Future climate projections and impacts on species distributions.

## Inputs
- Current distribution or niche model
- Climate model outputs (CMIP6)
- Emission scenarios (SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5)
- Time horizons (2030, 2050, 2070, 2090)

## Pipeline
1. **Model selection**: Choose GCMs (at least 5 for ensemble)
2. **Downscaling**: If needed, downscale to study resolution
3. **Projection**: Project SDM to future climates
4. **Ensemble**: Average across GCMs per scenario
5. **Uncertainty**: Coefficient of variation across GCMs
6. **Range shift**: Calculate centroid shift, area change
7. **Refugia**: Identify climatically stable areas

## Tools available via EcoAgent
- `ecoagent.climate.download` — Download CMIP6 data
- `ecoagent.climate.project` — Project SDMs to future
- `ecoagent.climate.ensemble` — Multi-GCM ensemble
- `ecoagent.climate.refugia` — Climate refugia detection
- `ecoagent.climate.velocity` — Climate velocity metrics

## Pitfalls
- GCMs disagree — always use multi-model ensembles
- Novel climates outside training range — check MESS maps
- Dispersal assumptions dominate range shift predictions
- Resolution mismatch between climate data and species data
