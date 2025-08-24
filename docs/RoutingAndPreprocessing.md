# Routing & Preprocessing

This document describes how routing-related rasters are prepared and how the DEM is extracted for a project.

Key code: `src/api/calculations/discharge.py` (task `prepare_discharge_hydroparameters`) and `src/api/calculations/nam.py` (task `extract_dem`).

## Outputs

- `data/{userId}/{projectId}/isozones_cog.tif`
  - Discrete 10-minute travel-time classes (COG)
- `data/{userId}/{projectId}/time_values.tif`
  - Continuous per-cell travel time in minutes
- `data/{userId}/{projectId}/dem.tif`
  - DEM clipped to catchment

## Isozones & Time Values

Endpoint: `GET /discharge/prepare_discharge_hydroparameters`

Rendered diagrams

![Isozones & Time Values](./images/routing_preprocessing_isozones.svg)


- Parameters
  - `a_crit`: accumulation threshold to define streams (default 700)
  - `v_gerinne`: base velocity used for time conversion (default 1.5 m/s)
  - Obstacle layer: slows flow depending on slope and forest presence
  - Discretization: `floor((dist / (v_gerinne*60*100)) / 10) + 1`

## DEM Extraction

Endpoint: `GET /discharge/extract_dem`

![DEM Extraction Flow](./images/dem_extraction_flow.svg)

Mermaid source (for reference):

```mermaid
flowchart TD
  A[DEM: data/geotiffminusriver.tif] --> B[Read subset around outlet]
  B --> C[Fill pits → Fill depressions → Resolve flats]
  C --> D[Flow direction (D8) & Accumulation]
  D --> E[Snap outlet to stream (a_crit)]
  E --> F[Catchment delineation]
  F --> G[Clip to catchment]
  G --> H[Forest overlay (ch_wald.shp) & slope]
  H --> I[Obstacle layer (slowdown factors)]
  I --> J[Distance to outlet (weighted by obstacles)]
  J --> K[Raw time values (min) = dist / (v_gerinne*60*100)]
  K --> L[Discretize to 10-min classes → isozones]
  L --> M[Write isozones_cog.tif]
  K --> N[Write time_values.tif]
```

```mermaid
flowchart TD
  A[Project catchment_geojson (EPSG:2056)] --> B[Union polygons]
  B --> C[Bounds in EPSG:2056]
  C --> D[Open DEM: data/geotiffminusriver.tif]
  D --> E{CRS == EPSG:2056?}
  E -- no --> F[Transform catchment->DEM CRS]
  E -- yes --> G[Use original bounds]
  F & G --> H[Windowed read DEM]
  H --> I[Mask outside catchment]
  I --> J[Write data/{user}/{project}/dem.tif]
```

- Saves stats (min, mean, max) to logs; returns file path and metadata from the task.

## How NAM Uses These Rasters

- `curvenumbers.tif`: distributed CN per cell → retention `S`, abstraction `Ia`
- `isozones_cog.tif`: used when routing method is `isozone`; zone index = arrival timestep
- `time_values.tif`: used when routing method is `time_values`; minutes converted to timestep index
- `dem.tif`: enables slope-aware overland travel times for `travel_time` method; otherwise a simplified constant-velocity approach is used.
