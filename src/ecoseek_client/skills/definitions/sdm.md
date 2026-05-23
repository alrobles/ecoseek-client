---
name: sdm
description: Species Distribution Modeling workflow
category: ecology
triggers: [SDM, species distribution, MaxEnt, niche modeling, habitat suitability]
---

# Species Distribution Modeling (SDM)

Standard SDM pipeline for ecological research.

## Inputs
- Species occurrence data (GBIF, iNaturalist, or user CSV)
- Environmental layers (WorldClim, Bio-ORACLE, CHELSA)
- Study region polygon (GeoJSON or bounding box)

## Pipeline
1. **Data preparation**: Download occurrences, clean duplicates, thin points
2. **Environmental layers**: Download bioclimatic variables, crop to region
3. **Model selection**: MaxEnt (presence-only), BIOMOD2 (ensemble), or INLA (Bayesian)
4. **Training**: 5-fold cross-validation, 70/30 split
5. **Evaluation**: AUC, TSS, omission rate, variable importance
6. **Projection**: Project to current climate, future scenarios
7. **Output**: GeoTIFF maps, HTML report, CSV metrics

## Tools available via EcoAgent
- `ecoagent.sdm.maxent` — MaxEnt SDM
- `ecoagent.sdm.biomod2` — BIOMOD2 ensemble
- `ecoagent.sdm.inla` — INLA Bayesian SDM
- `ecoagent.sdm.evaluate` — Model evaluation
- `ecoagent.sdm.project` — Climate projection

## Species-specific notes
- Jaguar (Panthera onca): Use mesoamerican corridor layers
- Monarch (Danaus plexippus): Include milkweed distribution
- Coral species: Use Bio-ORACLE marine layers

## Pitfalls
- Do not use default MaxEnt settings without tuning regularization
- Presence-only data needs background/pseudoabsence points
- Check for spatial autocorrelation in evaluation
