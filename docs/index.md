# SnowSAR

SAR-based snow depth retrieval system for Northern Hemisphere mountain environments.

SnowSAR provides four complementary retrieval algorithms behind a common
data-provider abstraction, letting you run the same algorithm against either
Google Earth Engine or locally-downloaded Sentinel-1/NISAR data.

## Getting Started

```bash
uv sync
uv run snowsar serve
```

Then open `http://localhost:8000/api/docs` for the interactive API reference.

## Contents

- **[Algorithms](algorithms/lievens.md)** — per-algorithm documentation
- **[API Reference](api.md)** — REST endpoints
- **[Developer Guide](developer.md)** — contributing, testing, architecture
