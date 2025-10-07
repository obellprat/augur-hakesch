# Time Values Routing Method for NAM Calculations

## Overview

A new routing method called `"time_values"` has been added to the NAM (Nedbør-Afstrømnings-Model) calculation in `src/api/calculations/nam.py`. This method uses the `time_values.tif` file to calculate HQ (peak discharge) for every 10-minute timestep.

## How it Works

### 1. Time Values File
The `time_values.tif` file contains the calculated travel time in minutes for each cell to reach the discharge point. This file is created by the `prepare_discharge_hydroparameters` function in `discharge.py` and contains:
- Travel time values in minutes for each cell
- NaN values for cells outside the catchment
- Values calculated as: `(distance) / (velocity * 60 * 100)` where velocity accounts for obstacles

### 2. Routing Process
The new routing method:

1. **Loads the time_values.tif file** from `data/{user_id}/{project_id}/time_values.tif`
2. **Calculates arrival timesteps** by dividing travel times by the timestep size (10 minutes)
3. **Groups cells by arrival timestep** and sums their runoff volumes
4. **Calculates discharge** for each 10-minute timestep
5. **Finds the maximum discharge (HQ)** and its timing

### 3. Key Features

- **Precise timing**: Uses actual calculated travel times instead of simplified estimates
- **10-minute resolution**: Calculates discharge for every 10-minute timestep
- **Automatic timestep extension**: Extends simulation time based on maximum travel time
- **Comprehensive logging**: Provides detailed statistics about travel times and routing

## Usage

To use the new routing method, set the `routing_method` parameter to `"time_values"`:

```python
result = nam(
    # ... other parameters ...
    routing_method="time_values"  # Use time_values.tif for routing
)
```

## Available Routing Methods

The NAM function now supports three routing methods:

1. **`"travel_time"`** (default): Uses calculated travel times based on distance and elevation
2. **`"isozone"`**: Uses discrete isozone classes for routing
3. **`"time_values"`** (new): Uses the time_values.tif file for precise travel time routing

## Implementation Details

### File Loading
```python
if routing_method == "time_values":
    time_values_file = f"data/{user_id}/{project_id}/time_values.tif"
    with rasterio.open(time_values_file) as src:
        time_values_data = src.read(1)
```

### Routing Logic
```python
# Calculate arrival timestep for each cell
arrival_timesteps = np.round(time_values_data / dt).astype(int)

# Calculate maximum timestep needed
max_time_value = np.nanmax(time_values_data[valid_mask])
max_timesteps_needed = int(np.ceil(max_time_value / dt)) + 10

# Group cells by arrival timestep and sum runoff volumes
for i in range(max_timesteps_needed):
    timestep_mask = (arrival_timesteps == i) & valid_time_mask
    if np.any(timestep_mask):
        runoff_volume = np.sum(runoff_volumes[timestep_mask])
        runoff_timesteps[i] += runoff_volume
```

### Output Information
The method provides detailed output including:
- Travel time statistics (min, max, mean)
- Number of valid cells
- Discharge at each timestep
- Maximum discharge (HQ) and timing
- Routing method used

## Advantages

1. **Accuracy**: Uses pre-calculated travel times that account for terrain, obstacles, and flow paths
2. **Efficiency**: Avoids recalculating travel times during NAM simulation
3. **Consistency**: Uses the same travel time calculations as other parts of the system
4. **Flexibility**: Can handle complex terrain and flow patterns

## Requirements

- The `time_values.tif` file must exist in the project directory
- The file must have the same spatial reference and resolution as other rasters
- Travel time values must be in minutes
- NaN values for cells outside the catchment

## Error Handling

- If `time_values.tif` is not found, the method falls back to `"travel_time"`
- If the file has different dimensions, it's resampled to match other rasters
- Invalid travel time values (NaN, negative) are excluded from calculations

## Example Output

```
Using time_values.tif-based routing method...
Time values routing: max_time=45.23min, dt=10min, max_timesteps=6
Valid time values cells: 1250 out of 1500
Timestep 0 (0min): 200 cells arrive, runoff_volume=15.234 m³
Timestep 1 (10min): 350 cells arrive, runoff_volume=28.567 m³
Timestep 2 (20min): 400 cells arrive, runoff_volume=32.891 m³
Timestep 3 (30min): 200 cells arrive, runoff_volume=18.234 m³
Timestep 4 (40min): 100 cells arrive, runoff_volume=8.567 m³
Maximum discharge: 32.891 m³/s at timestep 2
```

## Integration

This new routing method integrates seamlessly with the existing NAM calculation framework and provides a more accurate alternative to the existing routing methods while maintaining compatibility with all other NAM features. 