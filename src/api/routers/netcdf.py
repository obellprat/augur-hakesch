from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import xarray as xr
import os
import numpy as np
from typing import Dict, Any, Optional

router = APIRouter(prefix="/netcdf", tags=["netcdf"])

def get_data_directory() -> str:
    """Get the data directory from environment variable or use default."""
    return os.getenv('DATA_DIR', 'data')

def read_netcdf_data(file_path: str) -> xr.Dataset:
    """Read NetCDF file and return dataset."""
    try:
        return xr.open_dataset(file_path, decode_times=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading NetCDF file: {str(e)}")

def find_closest_grid_point(ds: xr.Dataset, lon: float, lat: float) -> tuple:
    """Find the closest grid point to the given longitude and latitude."""
    if 'lon' not in ds.coords or 'lat' not in ds.coords:
        raise HTTPException(status_code=400, detail="Longitude and latitude coordinates not found in dataset")
    
    # Calculate distances to all grid points
    lon_diff = np.abs(ds.lon.values - lon)
    lat_diff = np.abs(ds.lat.values - lat)
    
    # Calculate combined distance
    distance = np.sqrt(lon_diff**2 + lat_diff**2)
    
    # Find the closest point
    min_idx = np.unravel_index(np.argmin(distance), distance.shape)
    
    return min_idx[1], min_idx[0]  # Return (E, N) indices

def extract_precipitation_data(ds: xr.Dataset, return_period: str, lon: Optional[float] = None, lat: Optional[float] = None) -> Dict[str, Any]:
    """Extract precipitation data for a specific return period."""
    if return_period not in ds.data_vars:
        raise HTTPException(status_code=400, detail=f"Return period {return_period} not found in dataset")
    
    # Get the data for the return period (shape: time, probability, N, E)
    data = ds[return_period]
    
    def clean_numpy_array(arr):
        """Convert numpy array to JSON-serializable format, handling NaN and inf values."""
        # Replace NaN and inf values with None for JSON serialization
        arr_clean = np.where(np.isnan(arr) | np.isinf(arr), None, arr)
        return arr_clean.tolist()
    
    # If location is specified, extract data for that specific point
    if lon is not None and lat is not None:
        try:
            lon_idx, lat_idx = find_closest_grid_point(ds, lon, lat)
            closest_lon = float(ds.lon.isel(N=lat_idx, E=lon_idx).values)
            closest_lat = float(ds.lat.isel(N=lat_idx, E=lon_idx).values)
            
            # Extract data for the specific point
            point_data = data.isel(time=0, N=lat_idx, E=lon_idx)
            
            result = {
                "return_period": return_period,
                "location": {
                    "requested": {"lon": lon, "lat": lat},
                    "closest_grid_point": {"lon": closest_lon, "lat": closest_lat},
                    "grid_indices": {"N": int(lat_idx), "E": int(lon_idx)}
                },
                "probability_levels": {
                    "2.5%": float(point_data.isel(probability=0).values) if not np.isnan(point_data.isel(probability=0).values) else None,
                    "50%": float(point_data.isel(probability=1).values) if not np.isnan(point_data.isel(probability=1).values) else None,
                    "97.5%": float(point_data.isel(probability=2).values) if not np.isnan(point_data.isel(probability=2).values) else None
                }
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error finding location: {str(e)}")
    else:
        # Extract data for all grid points
        result = {
            "return_period": return_period,
            "probability_levels": {
                "2.5%": clean_numpy_array(data.isel(time=0, probability=0).values),
                "50%": clean_numpy_array(data.isel(time=0, probability=1).values),
                "97.5%": clean_numpy_array(data.isel(time=0, probability=2).values)
            },
            "dimensions": {
                "N": int(ds.sizes['N']),
                "E": int(ds.sizes['E'])
            },
            "coordinates": {
                "lon": clean_numpy_array(ds.lon.values) if 'lon' in ds.coords else None,
                "lat": clean_numpy_array(ds.lat.values) if 'lat' in ds.coords else None
            }
        }
    
    return result

@router.get("/precipitation")
def get_precipitation_data(
    lon: Optional[float] = Query(None, description="Longitude for specific location"),
    lat: Optional[float] = Query(None, description="Latitude for specific location")
):
    """
    Get precipitation data from NetCDF files for different return periods and durations.
    
    Returns data for:
    - 10 years 60 minutes (closest to 20 years)
    - 10 years 24h (closest to 20 years) 
    - 100 years 60 minutes
    - 100 years 24h
    
    If lon and lat are provided, returns data for the closest grid point to that location.
    If not provided, returns data for all grid points.
    """
    try:
        data_dir = get_data_directory()
        
        # File paths
        file_24h = os.path.join(data_dir, 'xspace.data.for.hades.24h.nc')
        file_60m = os.path.join(data_dir, 'xspace.data.for.hades.60m.nc')
        
        # Check if files exist
        if not os.path.exists(file_24h):
            raise HTTPException(status_code=404, detail=f"24h NetCDF file not found: {file_24h}")
        if not os.path.exists(file_60m):
            raise HTTPException(status_code=404, detail=f"60m NetCDF file not found: {file_60m}")
        
        # Read NetCDF files
        ds_24h = read_netcdf_data(file_24h)
        ds_60m = read_netcdf_data(file_60m)
        
        # Extract data for requested return periods
        # Using X10 as closest to 20 years, and X100 for 100 years
        result = {
            "metadata": {
                "data_directory": data_dir,
                "files": {
                    "24h": file_24h,
                    "60m": file_60m
                },
                "note": "Using X10 (10-year return period) as closest to requested 20-year return period",
                "location_requested": {"lon": lon, "lat": lat} if lon is not None and lat is not None else None
            },
            "data": {
                "10_years_60_minutes": extract_precipitation_data(ds_60m, "X10", lon, lat),
                "10_years_24h": extract_precipitation_data(ds_24h, "X10", lon, lat),
                "100_years_60_minutes": extract_precipitation_data(ds_60m, "X100", lon, lat),
                "100_years_24h": extract_precipitation_data(ds_24h, "X100", lon, lat)
            }
        }
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
