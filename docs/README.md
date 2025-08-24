# Hydrologic Calculations Documentation

This documentation summarizes how curve numbers and NAM-based discharge are prepared and calculated in this repository. It focuses on:

- Curve number raster creation
- Routing preprocessing (isozones and time values), and DEM extraction
- NAM rainfall–runoff computation, parameters, and effects

Contents

- [Curve Numbers](./CurveNumbers.md)
- [Routing & Preprocessing](./RoutingAndPreprocessing.md)
- [NAM Model](./NAM.md)

Source code locations

- Calculations: `src/api/calculations/nam.py`, `src/api/calculations/discharge.py`
- Routers: `src/api/routers/discharge.py`, `src/api/routers/file.py`

