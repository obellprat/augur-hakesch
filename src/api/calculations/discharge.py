from pysheds.grid import Grid
import numpy as np
import gc
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rasterio.io import MemoryFile
import rasterio
from pysheds.view import Raster,View
from scipy.ndimage import gaussian_filter
import geopandas as gpd
from shapely import geometry, ops
import pandas as pd
import os
from prisma import Prisma
from calculations.calculations import app
try:
    from prisma.engine.errors import EngineConnectionError
except ImportError:
    # Fallback for different Prisma versions
    from prisma.errors import EngineConnectionError
try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
import fiona
import json
from fiona.crs import CRS
from shapely.geometry import shape
from typing import Optional, Tuple
import pyproj
import time
import random
import threading

from calculations.calculations import app

# Semaphore to limit concurrent Prisma connections
# Set to 8 to allow some parallelism while preventing connection exhaustion
# This is higher than worker concurrency (4) to allow retries but lower than unlimited
_prisma_connection_semaphore = threading.Semaphore(8)


def connect_prisma_with_retry(max_retries=10, base_delay=0.2, max_delay=5.0):
    """
    Connect to Prisma with exponential backoff retry logic and connection limiting.
    This helps handle concurrent connection attempts from parallel Celery tasks.
    
    Uses a semaphore to limit concurrent connection attempts, preventing connection
    pool exhaustion when many tasks run in parallel.
    
    Args:
        max_retries: Maximum number of connection retry attempts (increased from 5 to 10)
        base_delay: Base delay in seconds for exponential backoff (increased from 0.1 to 0.2)
        max_delay: Maximum delay in seconds between retries (increased from 2.0 to 5.0)
    
    Returns:
        Prisma instance with established connection
    
    Raises:
        EngineConnectionError: If connection fails after all retries
    """
    # Acquire semaphore to limit concurrent connections
    # This prevents overwhelming the Prisma query engine
    _prisma_connection_semaphore.acquire()
    
    prisma = Prisma()
    
    try:
        for attempt in range(max_retries):
            try:
                # Add random jitter to prevent thundering herd
                # Jitter increases with attempt number to spread out retries
                jitter = random.uniform(0, base_delay * (1 + attempt * 0.5))
                delay = min(base_delay * (2 ** attempt) + jitter, max_delay)
                
                if attempt > 0:
                    time.sleep(delay)
                
                prisma.connect()
                return prisma
            except Exception as e:
                # Check if it's a connection-related error
                is_connection_error = isinstance(e, (EngineConnectionError, ConnectionError, OSError))
                if not is_connection_error and _HTTPX_AVAILABLE:
                    try:
                        is_connection_error = isinstance(e, httpx.ConnectError)
                    except:
                        pass
                if not is_connection_error:
                    # Not a connection error, re-raise immediately
                    raise
                if attempt == max_retries - 1:
                    # Last attempt failed, clean up and raise
                    try:
                        prisma.disconnect()
                    except:
                        pass
                    raise EngineConnectionError(
                        f'Could not connect to the query engine after {max_retries} attempts'
                    ) from e
                # Continue to next retry
                continue
        
        # Should never reach here, but just in case
        raise EngineConnectionError('Could not connect to the query engine')
    finally:
        # Always release semaphore, even if connection fails
        # This ensures other tasks can proceed
        _prisma_connection_semaphore.release()


@app.task(name="modifizierte_fliesszeit", bind=True)
def modifizierte_fliesszeit(self, 
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x:float,
    Vo20:int,           # Wetting volume for 20-year event [mm]
    L:float,              # Channel length up to the watershed ridge [m] 
    delta_H:float,        # Elevation difference along L [m]
    psi:float,            # Peak flow coefficient [-]
    E:float,              # Catchment area [km²]
    mod_fliesszeit_id:int, # db id for updating results
    project_easting: Optional[float] = None,
    project_northing: Optional[float] = None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    TB_start=10,    # Initial value for TB [min]
    istep=0.1,        # Step size for TB [min]
    tol=1,          # Convergence tolerance [mm]
    max_iter=10000
):
    result_data = {}    
    if x == 2.3 or x == 100 or x == 20:
        result_data = modifizierte_fliesszeit_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            x, Vo20, L, delta_H, psi, E, mod_fliesszeit_id, project_easting, project_northing, cc_degree, climate_scenario, TB_start, istep, tol, max_iter)
    elif x == 30 or x == 300:
        result_data_20 = modifizierte_fliesszeit_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            20, Vo20, L, delta_H, psi, E, mod_fliesszeit_id, project_easting, project_northing, cc_degree, climate_scenario, TB_start, istep, tol, max_iter)
        result_data_100 = modifizierte_fliesszeit_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            100, Vo20, L, delta_H, psi, E, mod_fliesszeit_id, project_easting, project_northing, cc_degree, climate_scenario, TB_start, istep, tol, max_iter)
        hq = loglog_interp_targets(20, result_data_20['HQ'], 100, result_data_100['HQ'])
        result_data = {
            "HQ": hq[x],
            "Tc": result_data_20['Tc'],
            "TB": result_data_20['TB'],
            "TFl": result_data_20['TFl'],
            "i": result_data_20['i'],
            "Vox": result_data_20['Vox']
        }
    else:
        raise ValueError("Return period x must be 2.3, 20 or 100.")

    prisma = None
    try:
        # Use retry logic to handle concurrent connection attempts
        prisma = connect_prisma_with_retry()
        
        # Use conditional logic to set the correct relation field
        if climate_scenario == "1_5_degree":
            data_update = {
                'Mod_Fliesszeit_Result_1_5': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "2_degree":
            data_update = {
                'Mod_Fliesszeit_Result_2': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "3_degree":
            data_update = {
                'Mod_Fliesszeit_Result_3': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "4_degree":
            data_update = {
                'Mod_Fliesszeit_Result_4': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        else:  # current
            data_update = {
                'Mod_Fliesszeit_Result': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        
        updatedResults = prisma.mod_fliesszeit.update(
            where = {
                'id' : mod_fliesszeit_id
            },
            data = data_update
        )
    finally:
        # Ensure cleanup even if update fails
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except:
                pass
    return result_data


def modifizierte_fliesszeit_standardVo(self, 
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x:float,
    Vo20:int,           # Wetting volume for 20-year event [mm]
    L:float,              # Channel length up to the watershed ridge [m] 
    delta_H:float,        # Elevation difference along L [m]
    psi:float,            # Peak flow coefficient [-]
    E:float,              # Catchment area [km²]
    mod_fliesszeit_id:int, # db id for updating results
    project_easting: Optional[float] = None,
    project_northing: Optional[float] = None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    TB_start=10,    # Initial value for TB [min]
    istep=0.1,        # Step size for TB [min]
    tol=1,          # Convergence tolerance [mm]
    max_iter=10000
):
    # Map climate scenario to cc_degree if not explicitly set
    scenario_to_degree = {
        "current": 0.0,
        "1_5_degree": 1.5,
        "2_degree": 2.0,
        "3_degree": 3.0,
        "4_degree": 4.0
    }
    
    # Use climate_scenario to determine cc_degree
    if climate_scenario in scenario_to_degree:
        cc_degree = scenario_to_degree[climate_scenario]
    
    # Compute climate change factor from project coordinates if available
    cc_factor = 0.0
    try:
        if project_easting is not None and project_northing is not None:
            lon, lat = _project_to_wgs84(project_easting, project_northing)
            #cc_factor = _load_cc_factor(lon, lat, cc_degree)
            cc_factor = _load_cc_factor_simple(cc_degree)
    except Exception:
        cc_factor = 0.0

    intensity_fn = construct_idf_curve(
        P_low_1h,
        P_high_1h,
        P_low_24h,
        P_high_24h,
        rp_low,
        rp_high,
        cc_factor
    )
    # 1. Wetting volume depending on x
    if x == 2.3:
        Vox = 0.5 * Vo20
    elif x == 100:
        Vox = 1.3 * Vo20
    elif x == 20:
        Vox = Vo20
    else:
        raise ValueError("Return period x must be 2.3, 20 or 100.")

    # Always Vo20 is used in HAKESCH
    Vox = Vo20
    
    # 2. Flow time according to Kirpich
    J = delta_H / L
    TFl = 0.0245 * (L ** 0.77) * (J ** -0.385)

    # 3. Iteration to determine TB
    TB = TB_start
    for _ in range(max_iter):
        Tc = TB + TFl
        ix = intensity_fn(rp_years = x, duration_minutes = Tc)  # [mm/h]
        #ix = ix * (1 + cc_factor)
        #print(f"Current TB: {TB}, Intensity: {ix}")
        #print(f"Vox: {Vox}, TFl: {TFl}, Tc: {Tc}")
        #print(f"criterion:{abs(TB / 60 * ix - Vox)}")
        if abs(TB / 60 * ix - Vox) < tol:
            # Convergence reached
            break 
        else: 
            if TB * ix < Vox:
                TB_new = TB - istep
            else:
                TB_new = TB + istep
            TB = TB_new
    else:
        raise RuntimeError("TB iteration did not converge.")

    Tc = TB + TFl
    i_final = intensity_fn(rp_years = x, duration_minutes = Tc)
    HQ = 0.278 * i_final * psi * E

    return {
        "HQ": HQ,
        "Tc": Tc,
        "TB": TB,
        "TFl": TFl,
        "i": i_final,
        "Vox": Vox
    }

@app.task(name="koella", bind=True)
def koella(self,
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x,                      # Recurrence interval: "2.3", "20", "100"
    Vo20,                   # Wetting volume for 20-year event [mm]
    Lg,                     # Cumulative channel length [km]
    E,                      # Catchment area [km²]
    glacier_area,           # Glacier area [km²]
    koella_id,              # db id for updating results
    project_easting: Optional[float] = None,
    project_northing: Optional[float] = None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    rs=4,                   # Meltwater equivalent [mm / h]
    snow_melt=False,         # Consider snowmelt [bool]
    TB_start=10,            # Start value for TB [min]
    tol=1,                  # Convergence tolerance [mm]
    istep=0.1,                # Step size for TB [min]
    max_iter=10000            # Max. iterations
):
    result_data = {}    
    if x == 2.3 or x == 100 or x == 20:
        result_data = koella_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            x, Vo20, Lg, E, glacier_area, koella_id, project_easting, project_northing, cc_degree, climate_scenario, rs, snow_melt, TB_start, tol, istep, max_iter)
    elif x == 30 or x == 300:
        result_data_20 = koella_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            x, Vo20, Lg, E, glacier_area, koella_id, project_easting, project_northing, cc_degree, climate_scenario, rs, snow_melt, TB_start, tol, istep, max_iter)
        result_data_100 = koella_standardVo(self, 
            P_low_1h,
            P_high_1h,
            P_low_24h,
            P_high_24h,
            rp_low,
            rp_high,  
            x, Vo20, Lg, E, glacier_area, koella_id, project_easting, project_northing, cc_degree, climate_scenario, rs, snow_melt, TB_start, tol, istep, max_iter)
        hq = loglog_interp_targets(20, result_data_20['HQ'], 100, result_data_100['HQ'])
        result_data = {
            "HQ": hq[x],
            "Tc": result_data_20['Tc'],
            "TB": result_data_20['TB'],
            "TFl": result_data_20['TFl'],
            "FLeff": result_data_20['FLeff'],
            "i_final": result_data_20['i_final'],
            "i_korrigiert": result_data_20['i_korrigiert']
        }
    else:
        raise ValueError("Return period x must be 2.3, 20 or 100.")
    
    prisma = None
    try:
        # Use retry logic to handle concurrent connection attempts
        prisma = connect_prisma_with_retry()
        
        # Use conditional logic to set the correct relation field
        if climate_scenario == "1_5_degree":
            data_update = {
                'Koella_Result_1_5': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "2_degree":
            data_update = {
                'Koella_Result_2': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "3_degree":
            data_update = {
                'Koella_Result_3': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "4_degree":
            data_update = {
                'Koella_Result_4': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        else:  # current
            data_update = {
                'Koella_Result': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
       
        updatedResults = prisma.koella.update(
            where = {
                'id' : koella_id
            },
            data = data_update
        )
    finally:
        # Ensure cleanup even if update fails
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except:
                pass
    return result_data


def koella_standardVo(self,
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x,                      # Recurrence interval: "2.3", "20", "100"
    Vo20,                   # Wetting volume for 20-year event [mm]
    Lg,                     # Cumulative channel length [km]
    E,                      # Catchment area [km²]
    glacier_area,           # Glacier area [km²]
    koella_id,              # db id for updating results
    project_easting: Optional[float] = None,
    project_northing: Optional[float] = None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    rs=4,                   # Meltwater equivalent [mm / h]
    snow_melt=False,         # Consider snowmelt [bool]
    TB_start=10,            # Start value for TB [min]
    tol=0.1,                  # Convergence tolerance [mm]
    istep=1,                # Step size for TB [min]
    max_iter=10000            # Max. iterations
):
    # Map climate scenario to cc_degree if not explicitly set
    scenario_to_degree = {
        "current": 0.0,
        "1_5_degree": 1.5,
        "2_degree": 2.0,
        "3_degree": 3.0,
        "4_degree": 4.0
    }
    
    # Use climate_scenario to determine cc_degree
    if climate_scenario in scenario_to_degree:
        cc_degree = scenario_to_degree[climate_scenario]
    
    # Compute climate change factor from project coordinates if available
    cc_factor = 0.0
    try:
        if project_easting is not None and project_northing is not None:
            lon, lat = _project_to_wgs84(project_easting, project_northing)
            #cc_factor = _load_cc_factor(lon, lat, cc_degree)
            cc_factor = _load_cc_factor_simple(cc_degree)
    except Exception:
        cc_factor = 0.0

    intensity_fn = construct_idf_curve(
        P_low_1h,
        P_high_1h,
        P_low_24h,
        P_high_24h,
        rp_low,
        rp_high,
        cc_factor
    )
    
    # Effective contributing area in km²
    FLeff = 0.13 * (Lg ** 1.02)  

    if x == 2.3:
        Vox = 0.5 * Vo20
        f = 0.1 * Vox
    elif x == 100:
        Vox = 1.3 * Vo20
        f = 0.1 * Vox
    elif x == 20:
        Vox = Vo20
        f = 0.1 * Vo20
    else:
        raise ValueError("Invalid recurrence interval (x)")

    # Correction according to recurrence interval
    
    def get_kF_values(Vo20):
        # Table mapping Vo20 to kF2.33 and kF100
        table = {
            20: (0.9, 1.1),
            25: (0.8, 1.15),
            30: (0.75, 1.2),
            35: (0.7, 1.25),
            40: (0.65, 1.3),
            45: (0.6, 1.3)
        }
        # Find closest Vo20 in table if not exact
        keys = sorted(table.keys())
        closest = min(keys, key=lambda k: abs(k - Vo20))
        return table[closest]

    kF2_33, kF100 = get_kF_values(Vo20)

    # Compute HQ depending on recurrence interval period
    if x == 2.3:
        kF = kF2_33
    elif x == 100:
        kF = kF100 
    elif x == 20:
        kF = 1.0

    TFl_h = (FLeff * kF) ** 0.2 
    TFl = TFl_h * 60  # min
    kGang = 1 # Initial value for hydrograph correction factor

    TB = TB_start
    for _ in range(max_iter):
        Tc = TB + TFl
        ix = intensity_fn(rp_years = x, duration_minutes = Tc) 
        #ix = ix * (1 + cc_factor)
        if abs(TB / 60 * ix - Vox) < tol:
            # Convergence reached
            break 
        else: 
            if TB * ix < Vox:
                TB_new = TB - istep
            else:
                TB_new = TB + istep
            TB = TB_new
    else:
        raise RuntimeError("TB iteration did not converge.")
      
    # Hydrograph correction (rain duration = Tc)
    if Tc <= 60:
        if E > 1:
            kGang = 1 + (10 - E) / 9 * 0.2
        else:
            kGang = 1.2
    elif Tc <= 180:
        TRx = Tc / 60  # Rain duration in hours 
        if E > 1:
            kGang = 1 + (3 - TRx) / 2 * (10 - E) / 9 * 0.2
        else:
            kGang = 1 + (3 - TRx) / 2 * 0.2

    i_final = intensity_fn(rp_years = x, duration_minutes = Tc) * (1 + cc_factor)
    if snow_melt:
        i_final += rs

    #i_corrected = max(i_final - f, 0)

    QGle = 0.5 * glacier_area

    precipitation_correction = 0.1 * Vox 
    i_corrected = max(i_final - precipitation_correction,0)

    # 1/3.6 factor for conversion from mm/h to m³/s
    i_corrected_units = i_corrected / 3.6 
    HQ = FLeff * kF * i_corrected_units * kGang + QGle

    return {
        "HQ": HQ,
        "Tc": Tc,
        "TB": TB,
        "TFl": TFl,
        "FLeff": FLeff,
        "i_final": i_final,
        "i_korrigiert": i_corrected,
    }

@app.task(name="clark-wsl", bind=True)
def clark_wsl_modified(self,
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high, 
    discharge_types_parameters,# dict: ID -> {"WSV", "psi"}
    x,                         # Return period [y]
    fractions_dict,            # Dict with fractions by zone
    clark_wsl,                 # Clark WSL id
    project_id,                # Project ID for getting isozone raster
    user_id,                   # User ID for getting isozone raster
    project_easting: Optional[float] = None,
    project_northing: Optional[float] = None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    intensity_fn=None,         # Precipitation intensity function: i(x, Tc) in mm/h
    dt=10,                     # Time step [min]
    pixel_area_m2=25           # Cell area [m²] (e.g. 5x5 m)
):
    # Map climate scenario to cc_degree if not explicitly set
    scenario_to_degree = {
        "current": 0.0,
        "1_5_degree": 1.5,
        "2_degree": 2.0,
        "3_degree": 3.0,
        "4_degree": 4.0
    }
    
    # Use climate_scenario to determine cc_degree
    if climate_scenario in scenario_to_degree:
        cc_degree = scenario_to_degree[climate_scenario]
    
    # Compute climate change factor from project coordinates if available
    cc_factor = 0.0
    try:
        if project_easting is not None and project_northing is not None:
            lon, lat = _project_to_wgs84(project_easting, project_northing)
            #cc_factor = _load_cc_factor(lon, lat, cc_degree)
            cc_factor = _load_cc_factor_simple(cc_degree)
    except Exception:
        cc_factor = 0.0
    intensity_fn = construct_idf_curve(
        P_low_1h,
        P_high_1h,
        P_low_24h,
        P_high_24h,
        rp_low,
        rp_high,
        cc_factor
    )
    
    # read the isozone_raster
    isozone = f"data/{user_id}/{project_id}/isozones_cog.tif"
    grid = Grid.from_raster(isozone)
    isozone_raster = grid.read_raster(isozone)

    fractions = fractions_dict

    max_zone = int(np.nanmax(isozone_raster))
    Tc = dt * (max_zone + 1)
    Ptotal = intensity_fn(rp_years = x, duration_minutes = Tc) * (1 + cc_factor) * Tc / 60  # mm
    W_iso = np.zeros((1, max_zone + 1))
    WSV_weighted_sum = 0
    total_area = 0
    P_deficit = 0

    for z in range(max_zone + 1):
        zone_mask = isozone_raster == z
        if not np.any(zone_mask):
            continue

        zone_area = np.sum(zone_mask) * pixel_area_m2  # m²
                
        for typ, pct in fractions.items():
            if pd.isna(pct) or pct == 0:
                continue
            frac = pct / 100
            area = frac * zone_area  # m²
            total_area += area

            if typ not in discharge_types_parameters:
                continue
          
            params = discharge_types_parameters[typ]
            WSV60min = params["WSV"]
            
            # WSV correction
            WSVcorr = WSV60min * (0.5 + Tc / 120)

            # Effective precipitation
            Peff = ((Ptotal - 0.2 * WSVcorr) ** 2) / (Ptotal + 0.8 * WSVcorr)
            Pinfilt_total = Ptotal - Peff

            # Infiltration capacity
            if WSV60min >= 30:
                f0_fc = 1
                r_val = 0.0000001
            elif 25 <= WSV60min < 30:
                f0_fc = 2
                r_val = 0.02
            elif 20 <= WSV60min < 25:
                f0_fc = 5
                r_val = 0.04
            else:  # WSV < 20
                f0_fc = 8
                r_val = 0.06

            r = r_val
            t_sec_z = Tc * 60 / (max_zone + 1) 

            # Step 1: Distribute total infiltration across zones
            Pinfilt_available = Pinfilt_total / (max_zone + 1)

            # Step 2: Compute fc from that available infiltration
            denominator = t_sec_z + ((f0_fc - 1) / r) * (1 - np.exp(-r * t_sec_z))
            fc = Pinfilt_available / denominator
            f0 = f0_fc * fc

            # Step 3: Reconstruct cumulative infiltration for the zone
            Pinfilt_z = fc * t_sec_z + ((f0 - fc) / r) * (1 - np.exp(-r * t_sec_z))

            # Step 4: Ensure that cumulative infiltration does not exceed available
            Pinfilt_z = min(Pinfilt_z, Pinfilt_available)
                      
            # Effective precipitation after infiltration and deficit from previous time step
            P_step = Ptotal / (max_zone + 1) - Pinfilt_z - P_deficit
            if P_step < 0:
                P_step = 0
            else:
                P_deficit = 0

            Q_step = P_step * area / 1000 / 60 / dt # [m³/s]
            WSV_weighted_sum += WSV60min * area
            WSV_corr_weighted_sum = WSVcorr * area
            W_iso[0][z] += Q_step

    # Clark W(t) by time step
    W = np.zeros(max_zone + 1)
    for t in range(len(W)):
        for z in range(len(W_iso[0])):
            if t - z >= 0:
                W[t] += W_iso[0, t - z]

    # Linear reservoir
    WSV_mean = WSV_weighted_sum / total_area
    WSV_corr_mean = WSV_corr_weighted_sum / total_area

    K = 2.0 * WSV_mean - 18.5  # in minutes
    K_sec = K * 60 

    # Muskingum routing
    c1 = dt * 60 / (2 * K_sec + dt * 60)
    c2 = c1
    c3 = (2 * K_sec - dt * 60) / (2 * K_sec + dt * 60)

    Q = np.zeros_like(W)
    for t in range(1, len(Q)):
        Q[t] = c1 * W[t] + c2 * W[t - 1] + c3 * Q[t - 1]

    prisma = None
    try:
        # Use retry logic to handle concurrent connection attempts
        prisma = connect_prisma_with_retry()

        Q_max = float(np.max(Q))

        # Build the update data based on climate scenario
        result_data = {
            "Q": Q_max,
            "W": 0,
            "K": 0,
            "Tc": 0
        }
        
        # Use conditional logic to set the correct relation field
        if climate_scenario == "1_5_degree":
            data_update = {
                'ClarkWSL_Result_1_5': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "2_degree":
            data_update = {
                'ClarkWSL_Result_2': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "3_degree":
            data_update = {
                'ClarkWSL_Result_3': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "4_degree":
            data_update = {
                'ClarkWSL_Result_4': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        else:  # current
            data_update = {
                'ClarkWSL_Result': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }

        updatedResults = prisma.clarkwsl.update(
            where = {
                'id' : clark_wsl
            },
            data = data_update
        )
    finally:
        # Ensure cleanup even if update fails
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except:
                pass

    return {
        "Q": Q.tolist(),
        "W": W.tolist(),
        # "K": K,
        "Tc": Tc
    }

def _load_cc_factor_simple(degree: float = 2.0) -> float:
    if degree == 1.5:
        return 0.063
    elif degree == 2.0:
        return 0.098
    elif degree == 3.0:
        return 0.196
    else:
        return 0.0

def _project_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """Convert EPSG:2056 easting/northing to lon/lat (EPSG:4326)."""
    transformer = pyproj.Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return lon, lat


def _load_cc_factor(lon: float, lat: float, degree: float = 2.0) -> float:
    """Sample climate change factor from CC raster at lon/lat.

    Returns 0.0 if outside raster or value is nodata/NaN.
    The factor is assumed additive on a relative basis (e.g., 0.2 means +20%).
    """
    print(f"Loading CC factor for {lon}, {lat} with degree {degree}")
    # Map degree to filename
    degree_str = str(degree).replace(".0", "")
    filename = f"data/CC/rx1day_{degree_str}degree_europe.tif"
    if not os.path.exists(filename):
        print(f"CC raster not found: {filename}")
        return 0.0
    try:
        with rasterio.open(filename) as ds:
            # Ensure coordinates are in the raster CRS
            src_crs = ds.crs
            x, y = lon, lat
            if src_crs is not None and src_crs.to_string() not in ("EPSG:4326", "OGC:CRS84"):
                to_src = pyproj.Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
                x, y = to_src.transform(lon, lat)
            row, col = ds.index(x, y)
            if row < 0 or col < 0 or row >= ds.height or col >= ds.width:
                print(f"Row or column out of bounds: {row}, {col}")
                return 0.0
            val = ds.read(1)[row, col] / 100.0
            if val is None or np.isnan(val):
                print(f"Value is None or NaN: {val}")
                return 0.0
            print(f"Value: {val}")
            return float(val)
    except Exception:
        return 0.0

def loglog_interp_targets(x1, y1, x2, y2, targets=(30, 100, 300), clip_min=1e-12, allow_extrapolate=True):
    """
    Log-log interpolate (or extrapolate) values y at return periods x.

    Parameters
    ----------
    x1, y1 : numeric
        Known return period and corresponding model output (e.g. 20, HQ20).
    x2, y2 : numeric
        Known return period and corresponding model output (e.g. 100, HQ100).
    targets : iterable of numeric
        Return periods to compute (default: (30, 100, 300)).
    clip_min : float
        Minimum positive value to avoid zero/negative results when exponentiating logs.
    allow_extrapolate : bool
        If False, targets outside [min(x1,x2), max(x1,x2)] will return np.nan.

    Returns
    -------
    dict
        Mapping target_return_period -> interpolated value (float or np.nan).

    """
    import numpy as np

    # ensure numeric
    try:
        x1 = float(x1); x2 = float(x2)
    except Exception:
        raise ValueError("x1 and x2 must be numeric return periods")

    # handle invalid y inputs
    y1_val = np.nan if y1 is None else (np.nan if (isinstance(y1, float) and np.isnan(y1)) else y1)
    y2_val = np.nan if y2 is None else (np.nan if (isinstance(y2, float) and np.isnan(y2)) else y2)

    # if either y is nan -> cannot interpolate
    if not np.isfinite(y1_val) or not np.isfinite(y2_val):
        return {int(t): np.nan for t in targets}

    # both y must be positive for log-log; otherwise clip to clip_min
    y1_clip = max(float(y1_val), clip_min)
    y2_clip = max(float(y2_val), clip_min)

    # logs
    lx1, lx2 = np.log(x1), np.log(x2)
    ly1, ly2 = np.log(y1_clip), np.log(y2_clip)

    results = {}
    xmin, xmax = min(x1, x2), max(x1, x2)
    for t in targets:
        try:
            t_f = float(t)
        except Exception:
            results[int(t)] = np.nan
            continue

        # optional extrapolation guard
        if (not allow_extrapolate) and (t_f < xmin or t_f > xmax):
            results[int(t_f)] = np.nan
            continue

        # if exactly equal to a known rp, return exact value (original sign if possible)
        if np.isclose(t_f, x1):
            results[int(t_f)] = float(y1_val)
            continue
        if np.isclose(t_f, x2):
            results[int(t_f)] = float(y2_val)
            continue
        # perform log-log interpolation / extrapolation
        ly_t = np.interp(np.log(t_f), [lx1, lx2], [ly1, ly2])
        y_t = float(np.exp(ly_t))
        results[int(t_f)] = y_t

    return results

def construct_idf_curve(
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high2,
    cc_factor
):
    
    """
    Constructs an IDF curve with user-defined lower and upper return periods.
    Inputs:
        P_low_1h:   Precipitation [mm] for lower return period, 1 hour duration
        P_high_1h:  Precipitation [mm] for upper return period, 1 hour duration
        P_low_24h:  Precipitation [mm] for lower return period, 24 hour duration
        P_high_24h: Precipitation [mm] for upper return period, 24 hour duration
        rp_low:     Lower return period (e.g. 2.33) as string
        rp_high:    Upper return period (e.g. 100) as string
        cc_factor:  Climate change factor
    Returns:
        idf_intensity: function(duration_minutes, return_period_years) -> intensity [mm/h]
    """

    # Convert return periods from string to float
    log_rp = np.log10([rp_low, rp_high2])
    P_1h = [P_low_1h * (1 + cc_factor), P_high_1h * (1 + cc_factor)]
    P_24h = [P_low_24h * (1 + cc_factor), P_high_24h * (1 + cc_factor)]

    # Linear fit for 1h and 24h precipitation
    coeffs_1h = np.polyfit(log_rp, P_1h, 1)
    coeffs_24h = np.polyfit(log_rp, P_24h, 1)

    # Climate change factor is applied in hydrologic tasks, not here

    def precipitation_amount(duration_h, rp_years):
        log_rp_val = np.log10(rp_years)
        if duration_h == 1:
            return coeffs_1h[0] * log_rp_val + coeffs_1h[1]
        elif duration_h == 24:
            return coeffs_24h[0] * log_rp_val + coeffs_24h[1]
        else:
            raise ValueError("Only 1h and 24h durations supported for precipitation amount.")

    def idf_intensity(rp_years, duration_minutes):
        # Convert return periods from string to float
        duration_h = duration_minutes / 60.0
        P1 = precipitation_amount(1, rp_years)
        P24 = precipitation_amount(24, rp_years)
        I1 = P1 / 1.0
        I24 = P24 / 24.0
        log_durations = np.log10([1, 24])
        log_intensities = np.log10([I1, I24])
        slope, intercept = np.polyfit(log_durations, log_intensities, 1)
        log_duration = np.log10(duration_h)
        log_intensity = slope * log_duration + intercept
        return 10 ** log_intensity

    return idf_intensity

# Example usage:
# idf_fn = construct_idf_curve(25, 50, 60, 120, 2.33, 100)

@app.task(name="prepare_discharge_hydroparameters", bind=True)
def prepare_discharge_hydroparameters(self, projectId: str, userId: int, northing: float, easting: float, a_crit = 3000, v_gerinne = 1.5):
    # Send immediate progress update to indicate task has started
    self.update_state(state='PROGRESS',
                meta={'text': 'Task started, initializing...', 'progress' : 5})
    
    # Definitions
    cell_size = 5

    # Rertrieve and load DEM
    # ----------------------

    dem_file = 'data/geotiffminusriver.tif'
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    
    # Optimized: Use rasterio directly for windowed reading (faster than Grid.from_raster + read_raster)
    # This avoids opening the full raster file before reading the window
    self.update_state(state='PROGRESS',
                meta={'text': 'Reading DEM window', 'progress' : 10})
    
    # Calculate window bounds
    window_bounds = (northing - 9000, easting - 9000, northing + 9000, easting + 9000)
    
    # Use rasterio directly for faster windowed reading
    with rasterio.open(dem_file) as src:
        # Get CRS from source
        dem_crs = src.crs
        # Calculate window from bounds
        window = rasterio.windows.from_bounds(
            window_bounds[0], window_bounds[1], window_bounds[2], window_bounds[3],
            src.transform
        )
        # Read the windowed data directly
        dem_data = src.read(1, window=window)
        window_transform = rasterio.windows.transform(window, src.transform)
        
        # Save the windowed DEM to temp file for Grid operations
        temp_dem_path = 'data/temp/smalldem.tif'
        os.makedirs(os.path.dirname(temp_dem_path), exist_ok=True)
        
        profile = src.profile.copy()
        profile.update({
            'height': window.height,
            'width': window.width,
            'transform': window_transform
        })
        
        with rasterio.open(temp_dem_path, 'w', **profile) as dst:
            dst.write(dem_data, 1)
    
    # Now create Grid from the smaller windowed file (much faster)
    self.update_state(state='PROGRESS',
                meta={'text': 'Processing DEM', 'progress' : 15})
    grid = Grid.from_raster(temp_dem_path)
    dem = grid.read_raster(temp_dem_path)
    grid.clip_to(dem)
    small_view = grid.view(dem)
    grid.to_raster(dem, temp_dem_path, target_view=small_view)

    del grid
    gc.collect()

    self.update_state(state='PROGRESS',
                meta={'text': 'Reading flow direction', 'progress' : 25})

    d8_file = 'data/d8_be.tif'
    
    # Optimized: Use rasterio directly for windowed reading (same optimization as DEM)
    with rasterio.open(d8_file) as src:
        # Calculate window from bounds (same as DEM)
        window = rasterio.windows.from_bounds(
            window_bounds[0], window_bounds[1], window_bounds[2], window_bounds[3],
            src.transform
        )
        # Read the windowed data directly
        fdir_data = src.read(1, window=window)
        window_transform = rasterio.windows.transform(window, src.transform)
        
        # Save the windowed flow direction to temp file
        temp_fdir_path = 'data/temp/smallfdir.tif'
        os.makedirs(os.path.dirname(temp_fdir_path), exist_ok=True)
        
        profile = src.profile.copy()
        profile.update({
            'height': window.height,
            'width': window.width,
            'transform': window_transform
        })
        
        with rasterio.open(temp_fdir_path, 'w', **profile) as dst:
            dst.write(fdir_data, 1)
    
    # Create Grid from the smaller windowed file
    grid = Grid.from_raster(temp_fdir_path)
    fdir = grid.read_raster(temp_fdir_path)
    grid.clip_to(fdir)
    small_view = grid.view(fdir)
    grid.to_raster(fdir, temp_fdir_path, target_view=small_view)

    del grid
    gc.collect()


    grid2 = Grid.from_raster('data/temp/smallfdir.tif')
    """    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Fill pits', 'progress' : 8})
    

    # calculate accumulation

    pit_filled_dem = grid2.fill_pits(dem)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Fill depressions', 'progress' : 16})
    flooded_dem = grid2.fill_depressions(pit_filled_dem)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Resolve flats', 'progress' : 22})
    inflated_dem = grid2.resolve_flats(flooded_dem)
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Accumulation', 'progress' : 40})
    fdir = grid2.flowdir(inflated_dem, dirmap=dirmap)    
    """
    
    acc = grid2.accumulation(fdir, dirmap=dirmap)

    
    self.update_state(state='PROGRESS',
                meta={'text': 'Delineate the catchment', 'progress' : 50})
    

    # Delineate the catchment
    x_snap, y_snap = grid2.snap_to_mask(acc > a_crit, (northing, easting))
    catch = grid2.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                        xytype='coordinate')

    # Clip the bounding box to the catchment
    grid2.clip_to(catch)

    # calculate catchment area
    num_cells = np.sum(catch)
    cell_area = cell_size ** 2
    catchment_area = num_cells * cell_area
    catchmentkm2 = catchment_area/(1000*1000)

    # Extract river network and calculate cumulative length
    branches = grid2.extract_river_network(fdir, acc > a_crit, dirmap=dirmap)
    L_cum = cumulative_length(branches)

    # Reload DEM with grid2 for compatibility (grid2 has catchment-clipped view)
    dem = grid2.read_raster(temp_dem_path)
    dem_view = grid2.view(dem)
    dem_view[dem_view < 0] = np.nan
    delta_H = float(np.nanmax(dem_view) - np.nanmin(dem_view)) 

    # calculate slope
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculating slope', 'progress' : 60})
    slope = grid2.cell_slopes(fdir=fdir, dirmap=dirmap, dem=dem, nodata=0)
    slope_percentage = slope * 100


    # create wald raster    
    self.update_state(state='PROGRESS',
                meta={'text': 'Getting forest', 'progress' : 70})
    forests = gpd.read_file('data/ch_wald.shp')
    grid2.clip_to(catch)
    # Convert catchment raster to vector geometry and find intersection
    shapes = grid2.polygonize()

    objektart = 'objektart'
    catchment_polygon = ops.unary_union([geometry.shape(shape)
                                        for shape, value in shapes])
    forests = forests[forests.intersects(catchment_polygon)]
    catchment_forests = gpd.GeoDataFrame(forests, 
                                    geometry=forests.intersection(catchment_polygon))

    # Convert forest to simple integer values
    forest_types = np.unique(catchment_forests[objektart])
    forest_types = pd.Series(np.arange(forest_types.size), index=forest_types)
    catchment_forests[objektart] = catchment_forests[objektart].map(forest_types)
    forests_polygons = zip(catchment_forests.geometry.values, catchment_forests[objektart].values)
    forests_raster = grid2.rasterize(forests_polygons, fill=-1)
    forests_raster[forests_raster >= 0] = 1
    forests_raster[forests_raster < 0] = 0

    # calculate "Hindernislayer".
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculating obstacle layer', 'progress' : 80})
    acc_view = grid2.view(acc)
    obstacle_grid = acc_view.copy()
    
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage < 1,slope_percentage>-100), forests_raster==1), 3000,obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage < 1,slope_percentage>-100), forests_raster==0), 1500,obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 1,slope_percentage<5), forests_raster==1), 1500, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 1,slope_percentage<5), forests_raster==0), 750, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 5,slope_percentage<10), forests_raster==1), 750, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 5,slope_percentage<10), forests_raster==0), 375, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 10,slope_percentage<20), forests_raster==1), 500, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 10,slope_percentage<20), forests_raster==0), 250, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 20,slope_percentage<40), forests_raster==1), 375, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 20,slope_percentage<40), forests_raster==0), 188, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(slope_percentage >= 40, forests_raster==1), 300, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(slope_percentage >= 40, forests_raster==0), 150, obstacle_grid)
    obstacle_grid = np.where(acc_view>a_crit, 100, obstacle_grid)

    obstacle_raster = Raster(obstacle_grid, viewfinder=grid2.viewfinder)

    # Compute maximum distance to outlet
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculate distance', 'progress' : 85})
    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap)  
    dist = dist * cell_size
    dist[dist == np.inf] = -1000000
    dist_max = np.nanmax(dist)

    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap, weights=obstacle_raster)

    #dist = dist * cell_size
    dist = dist * cell_size
    dist[dist == np.inf] = -1000000
    dist[dist <= 0] = -1000000
    
    # Save raw time values before discretization
    raw_time_values = dist.copy()
    raw_time_values[raw_time_values == -1000000] = np.nan
    raw_time_values = (raw_time_values)/(v_gerinne * 60 * 100)
    
    # Discretize into time classes for isozones
    dist = np.floor(((dist)/(v_gerinne * 60 * 100)) / 10) + 1  # strecke / geschwindigkeit * 60(-> für m/min) * 100 (hindernislayer) / 10 (-> 10 Minuten klassen) +1 da wir bei Klasse 1 starten

    dist[dist<=0] = None


    # writing cloud optimized geotiff
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Writing isozone file', 'progress' : 90})
    # Defining the output COG filename
    if not os.path.exists(f"data/{userId}"):
        os.makedirs(f"data/{userId}")

    if not os.path.exists(f"data/{userId}/{projectId}"):
        os.makedirs(f"data/{userId}/{projectId}")

    cog_filename = f"data/{userId}/{projectId}/isozones_cog.tif"

    src_profile = dict(
        driver="GTiff",
        dtype="int"
    )

    target_view = dist.viewfinder
    small_view2 = View.view(dist, target_view)

    height, width = small_view2.shape
    default_profile = {
        'driver' : 'GTiff',
        'blockxsize' : 256,
        'blockysize' : 256,
        'count': 1
    }
    profile = default_profile
    profile_updates = {
        'crs' : dist.crs.srs,
        'transform' : dist.affine,
        'dtype' : dist.dtype.name,
        'nodata' : 0,
        'height' : height,
        'width' : width
    }
    profile.update(profile_updates)

    with MemoryFile() as memfile:
        # Opening an empty MemoryFile for in memory operation - faster
        with memfile.open(**profile) as mem:
            # Writing the array values to MemoryFile using the rasterio.io module
            # https://rasterio.readthedocs.io/en/stable/api/rasterio.io.html
            mem.write(np.asarray(dist), 1)

            dst_profile = cog_profiles.get("deflate")

            # Creating destination COG
            cog_translate(
                mem,
                cog_filename,
                dst_profile,
                use_cog_driver=True,
                in_memory=False
            )

    # Save raw time values as TIF
    self.update_state(state='PROGRESS',
                meta={'text': 'Writing time values file', 'progress' : 91})
    
    # Create raw time values raster
    raw_time_raster = Raster(raw_time_values, viewfinder=grid2.viewfinder)
    
    # Define the output filename for raw time values
    raw_time_filename = f"data/{userId}/{projectId}/time_values.tif"
    
    # Profile for raw time values (float data type)
    raw_time_profile = default_profile.copy()
    raw_time_profile_updates = {
        'crs' : raw_time_raster.crs.srs,
        'transform' : raw_time_raster.affine,
        'dtype' : 'float32',
        'nodata' : np.nan,
        'height' : height,
        'width' : width
    }
    raw_time_profile.update(raw_time_profile_updates)
    
    with MemoryFile() as memfile:
        with memfile.open(**raw_time_profile) as mem:
            mem.write(np.asarray(raw_time_raster), 1)
            
            # Save as regular GeoTIFF (not COG for raw values)
            with rasterio.open(raw_time_filename, 'w', **raw_time_profile) as dst:
                dst.write(np.asarray(raw_time_raster), 1)

    self.update_state(state='PROGRESS',
                meta={'text': 'Polygonize catchment', 'progress' : 92})
    # Create a vector representation of the catchment mask
    catch_view = grid2.view(catch, dtype=np.uint8)
    shapes = grid2.polygonize(catch_view)

    # Specify schema
    schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Creating geometry', 'progress' : 95})
    with fiona.open(f"data/{userId}/{projectId}/catchment.geojson", 'w',
                    driver='GeoJSON',
                    crs=grid2.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL' : str(value)}
            rec['id'] = str(i)
            c.write(rec)
            i += 1

    with open(f"data/{userId}/{projectId}/catchment.geojson", 'r') as file:
        data = json.load(file)


    self.update_state(state='PROGRESS',
            meta={'text': 'Save to database', 'progress' : 99})    

    prisma = None
    try:
        # Use retry logic to handle concurrent connection attempts
        prisma = connect_prisma_with_retry()
        
        updatedProject = prisma.project.update(
            where = {
                'id' :  projectId
            },
            data = {
                'isozones_running': False,
                'catchment_geojson': json.dumps(data),
                'branches_geojson': json.dumps(branches),
                'channel_length': dist_max.item(),
                'catchment_area': catchmentkm2.item(),
                'cummulative_channel_length': L_cum,
                'delta_h': delta_H,

            },
            )
    finally:
        # Ensure cleanup even if update fails
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except:
                pass
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Finish', 'progress' : 100})
    return


def cumulative_length(geojson_featurecollection):
    total_length = 0.0
    for feature in geojson_featurecollection['features']:
        geom = shape(feature['geometry'])
        # For LineString or MultiLineString
        total_length += geom.length
    return total_length


