---
name: niche
description: Ecological niche analysis and hypervolume modeling
category: ecology
triggers: [niche, hypervolume, niche overlap, environmental space, Hutchinson]
---

# Ecological Niche Analysis

Niche quantification using hypervolume and environmental space methods.

## Inputs
- Species occurrence records
- Environmental layers (bioclimatic, soil, topography)
- Optionally: trait data for mechanistic niche

## Pipeline
1. **Environmental extraction**: Extract env values at occurrence points
2. **PCA/ordination**: Reduce dimensionality
3. **Hypervolume construction**: Gaussian kernel density estimation
4. **Niche overlap**: Sørensen similarity between species
5. **Niche breadth**: Volume metrics, marginality, specialization
6. **Projection**: Map niche back to geographic space

## Tools available via EcoAgent
- `ecoagent.niche.hypervolume` — Hypervolume construction (R/hypervolume)
- `ecoagent.niche.overlap` — Niche overlap metrics
- `ecoagent.niche.ecospat` — PCA-env ordination
- `ecoagent.niche.breadth` — Niche breadth metrics

## Pitfalls
- Hypervolume is sensitive to kernel bandwidth parameter
- Low sample sizes produce unreliable hypervolumes
- Niche ≠ distribution — biotic interactions not captured
- Use multiple methods for robustness
