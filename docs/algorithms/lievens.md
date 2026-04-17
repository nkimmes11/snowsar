# Lievens Empirical Change-Detection

Empirical change-detection algorithm for C-band SAR snow depth retrieval.
Based on Lievens et al. (2019, 2022).

## Overview

Uses temporal changes in Sentinel-1 cross-polarization ratio (CR = VH - VV, in dB)
to estimate snow depth. Forest cover fraction (FCF) weighting blends CR-based
signal (more sensitive in open areas) with VV-based signal (more sensitive
under forest canopy).

## Inputs

- Sentinel-1 GRD dual-pol (VV + VH) in dB
- Forest cover fraction
- Optional snow cover mask (e.g., IMS, MODIS)

## Processing Chain

1. Compute cross-polarization ratio (CR)
2. Establish reference backscatter from snow-free or early-season period
3. Compute change from reference (ΔCR, ΔVV)
4. Apply FCF weighting: `Δσ = (1-FCF) · ΔCR + FCF · ΔVV`
5. Recursive temporal filter to accumulate snow signal
6. Empirical regression to snow depth: `SD = A·SI + B·SI² + C`
7. Quality flag assignment

## Parameters

See `snowsar.algorithms.lievens.LievensParams`.

---

*Full documentation coming in Phase 3.*
