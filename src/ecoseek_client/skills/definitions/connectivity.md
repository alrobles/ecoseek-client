---
name: connectivity
description: Landscape connectivity and corridor analysis
category: ecology
triggers: [connectivity, corridor, landscape, fragmentation, graph theory]
---

# Landscape Connectivity Analysis

Corridor identification and landscape connectivity for conservation planning.

## Inputs
- Land cover / land use map (GeoTIFF)
- Resistance surface or permeability layer
- Source/destination patches (vector)
- Species dispersal distance

## Pipeline
1. **Resistance surface**: Build from land cover + expert weights
2. **Graph construction**: Nodes = habitat patches, edges = cost-weighted distance
3. **Circuit theory**: Circuitscape for current flow
4. **Least-cost paths**: LCP between key patches
5. **Pinch points**: Identify bottlenecks in connectivity
6. **Priority ranking**: Rank corridors by centrality measures

## Tools available via EcoAgent
- `ecoagent.connectivity.resistance` — Build resistance surface
- `ecoagent.connectivity.circuitscape` — Circuit theory analysis
- `ecoagent.connectivity.lcp` — Least-cost path corridors
- `ecoagent.connectivity.graph` — Graph topology metrics

## Pitfalls
- Resistance values must be justified (expert opinion or literature)
- Dispersal distance heavily affects results — use sensitivity analysis
- Circuit theory assumes symmetric resistance (undirected)
- Large landscapes may need tiling or HPC
