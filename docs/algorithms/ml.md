# ML-Enhanced Retrieval

Machine-learning-based snow depth retrieval using gradient-boosted regression
trees (XGBoost by default) trained on SAR + ancillary feature vectors.

!!! warning "Experimental — No Production Model Available"

    The ML retrieval **framework** (feature assembly, model registry, algorithm
    wrapper) is implemented and tested, but **no production-trained ML model
    currently exists** in the registry.

    Until a production model is published (see Phase 5 of the implementation
    plan), the ML algorithm will not produce usable snow depth estimates
    out-of-the-box. Users with their own labeled snow depth data can train a
    regional model via `snowsar.models.training` and register it for use.

## Overview

Combines SAR backscatter with ancillary environmental features
(temperature, land cover, topography) to predict snow depth without
relying on hand-tuned empirical coefficients. The model is trained against
coincident SAR observations and ground-truth snow depth (airborne lidar,
SNOTEL, GPR).

## Inputs

- Sentinel-1 GRD dual-pol (VV + VH)
- Topography: elevation, slope, aspect
- Forest cover fraction
- ERA5-Land 2m air temperature
- ESA WorldCover land cover class

## Processing Chain

1. Assemble feature matrix from the input Dataset
2. Download/load pre-trained model from the registry (or a user-supplied model)
3. Predict snow depth per-pixel per-time
4. Apply wet-snow and out-of-range masks
5. Assign quality flags

## Model Registry

Models are declared in `models/registry.json` and downloaded on-demand
from Zenodo via `pooch`, cached in `~/.snowsar/models/`. Each registry
entry includes a SHA256 checksum for integrity verification.

## Parameters

See `snowsar.algorithms.ml.MLParams`.

## Training Your Own Model

See `snowsar.models.training` for the retraining utilities and Phase 5
of the implementation plan for the full training recipe.

---

*Full documentation coming in Phase 3.*
