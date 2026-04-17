# DpRSE Dual-Polarimetric

Dual-Polarimetric Radar Snow Estimation using the DpRVIc conditioning index.
Based on the DpRSE framework (2024).

## Overview

Addresses soil-scattering interference in standard cross-polarization methods
by combining the dual-polarimetric radar vegetation index (DpRVI) with a
conditioning factor derived from a soil purity metric. Applicable to treeless
areas only; shrub cover degrades accuracy.

## Inputs

- Sentinel-1 GRD dual-pol (VV + VH) — converted internally to linear power
- Optional land-cover / forest cover mask

## Processing Chain

1. Convert dB to linear power
2. Compute pseudo-coherency matrix elements (C11 = VV², C22 = VH², span)
3. Compute degree of polarization and soil purity metric
4. Compute base DpRVI index
5. Apply conditioning factor: `DpRVIc = DpRVI · (1 - soil_purity)^k`
6. Empirical regression to snow depth: `SD = m · DpRVIc + b`
7. Quality flag assignment (forest, soil purity, range checks)

## Parameters

See `snowsar.algorithms.dprse.DpRSEParams`.

---

*Full documentation coming in Phase 3.*
