#!/usr/bin/env python3
"""
Batch NAM Calculations Script

This script iterates through all entries in the NAM table, calls the NAM calculation function,
and saves the output values (HQ, Tc, TB, TFl, i, S, Pe) to a CSV file.

Usage:
    python batch_nam_calculations.py [--output output.csv] [--limit 100] [--dry-run]
"""

import os
import sys
import csv
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import required modules
from helpers.prisma import prisma
# Import the NAM function directly (not the task wrapper)
import calculations.nam

def get_all_nam_entries(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all NAM entries from the database with related data.
    
    Args:
        limit: Optional limit on number of entries to fetch
        
    Returns:
        List of NAM entries with related data
    """
    try:
        # Connect to database
        prisma.connect()
        
        # Build query
        nam_entries = prisma.nam.find_many(
            include={
                'Project': {
                    'include': {
                        'IDF_Parameters': True,
                        'Point': True
                    }
                },
                'Annuality': True,
                'WaterBalanceMode': True,
                'StormCenterMode': True,
                'RoutingMethod': True,
                'NAM_Result': True
            },
            take=limit if limit else None
        )
        
        print(f"Found {len(nam_entries)} NAM entries in database")
        return nam_entries
        
    except Exception as e:
        print(f"Error fetching NAM entries: {e}")
        traceback.print_exc()
        return []

def validate_nam_entry(nam_entry) -> bool:
    """
    Validate that a NAM entry has all required data for calculation.
    
    Args:
        nam_entry: NAM entry from database (Prisma object)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        if not hasattr(nam_entry, 'id') or not nam_entry.id:
            print(f"Missing required field: id")
            return False
        if not hasattr(nam_entry, 'x') or not nam_entry.x:
            print(f"Missing required field: x")
            return False
        if not hasattr(nam_entry, 'project_id') or not nam_entry.project_id:
            print(f"Missing required field: project_id")
            return False
        if not hasattr(nam_entry, 'Project') or not nam_entry.Project:
            print(f"Missing required field: Project")
            return False
        
        # Check project has required data
        project = nam_entry.Project
        if not hasattr(project, 'IDF_Parameters') or not project.IDF_Parameters:
            print(f"Project {getattr(project, 'id', 'unknown')} missing IDF_Parameters")
            return False
        
        # Check IDF parameters
        idf_params = project.IDF_Parameters
        required_idf_fields = ['P_low_1h', 'P_high_1h', 'P_low_24h', 'P_high_24h', 'rp_low', 'rp_high']
        for field in required_idf_fields:
            if not hasattr(idf_params, field) or getattr(idf_params, field) is None:
                print(f"Project {getattr(project, 'id', 'unknown')} missing IDF parameter: {field}")
                return False
        
        # Check catchment data
        if not hasattr(project, 'catchment_area') or not project.catchment_area or project.catchment_area <= 0:
            print(f"Project {getattr(project, 'id', 'unknown')} has invalid catchment_area: {getattr(project, 'catchment_area', None)}")
            return False
            
        if not hasattr(project, 'channel_length') or not project.channel_length or project.channel_length <= 0:
            print(f"Project {getattr(project, 'id', 'unknown')} has invalid channel_length: {getattr(project, 'channel_length', None)}")
            return False
            
        if not hasattr(project, 'delta_h') or not project.delta_h or project.delta_h <= 0:
            print(f"Project {getattr(project, 'id', 'unknown')} has invalid delta_h: {getattr(project, 'delta_h', None)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error validating NAM entry: {e}")
        return False

def call_nam_calculation(nam_entry) -> Optional[Dict[str, Any]]:
    """
    Call the NAM calculation function for a single entry.
    
    Args:
        nam_entry: NAM entry from database (Prisma object)
        
    Returns:
        Calculation results or None if failed
    """
    try:
        # Extract parameters
        nam_id = nam_entry.id
        project = nam_entry.Project
        idf_params = project.IDF_Parameters
        annuality = nam_entry.Annuality
        
        # IDF parameters
        P_low_1h = float(idf_params.P_low_1h)
        P_high_1h = float(idf_params.P_high_1h)
        P_low_24h = float(idf_params.P_low_24h)
        P_high_24h = float(idf_params.P_high_24h)
        rp_low = float(idf_params.rp_low)
        rp_high = float(idf_params.rp_high)
        
        # Return period - use the actual number from Annuality, not the ID
        x = int(nam_entry.Annuality.number)
        print(f"  Return period: {x} ({nam_entry.Annuality.description})")
        
        # Catchment parameters
        catchment_area = float(project.catchment_area)
        channel_length = float(project.channel_length)
        delta_h = float(project.delta_h)
        
        # Project and user IDs
        project_id = project.id
        user_id = project.userId
        
        # NAM parameters
        water_balance_mode = getattr(nam_entry, 'water_balance_mode', None)
        precipitation_factor = getattr(nam_entry, 'precipitation_factor', None)
        storm_center_mode = getattr(nam_entry, 'storm_center_mode', None)
        routing_method = getattr(nam_entry, 'routing_method', None)
        
        # Extract discharge point from project's Point relation
        discharge_point = None
        discharge_point_crs = "EPSG:2056"  # Swiss coordinate system
        
        if hasattr(project, 'Point') and project.Point:
            # Point coordinates are in EPSG:2056 (Swiss coordinate system)
            discharge_point = (project.Point.easting, project.Point.northing)
            print(f"  Discharge point: {discharge_point} (EPSG:2056)")
        else:
            print(f"  Warning: No discharge point found in project")
        
        # Use a default curve number (will be overridden by raster if available)
        curve_number = 70.0
        
        print(f"Calling NAM calculation for entry {nam_id} (project: {project_id})")
        print(f"  Return period: {x} ({getattr(annuality, 'description', 'unknown')})")
        print(f"  Catchment area: {catchment_area:.2f} km²")
        print(f"  Channel length: {channel_length:.1f} m")
        print(f"  Delta H: {delta_h:.1f} m")
        
        # Call the NAM function
        # Note: We need to create a mock task object since the function expects @app.task
        class MockTask:
            def update_state(self, state, meta=None):
                print(f"    Task state: {state} - {meta}")
        
        mock_task = MockTask()
        
        print(f"  Calling NAM function with parameters:")
        print(f"    project_id: {project_id}")
        print(f"    user_id: {user_id}")
        print(f"    water_balance_mode: {water_balance_mode}")
        print(f"    precipitation_factor: {precipitation_factor}")
        print(f"    storm_center_mode: {storm_center_mode}")
        print(f"    routing_method: {routing_method}")
        
        # Call the NAM function directly (not through Celery)
        # Get the underlying function from the module
        nam_function = calculations.nam.nam.__wrapped__
        
        # Create kwargs dict to avoid argument conflicts
        kwargs = {
            'P_low_1h': P_low_1h,
            'P_high_1h': P_high_1h,
            'P_low_24h': P_low_24h,
            'P_high_24h': P_high_24h,
            'rp_low': rp_low,
            'rp_high': rp_high,
            'x': x,
            'curve_number': curve_number,
            'catchment_area': catchment_area,
            'channel_length': channel_length,
            'delta_h': delta_h,
            'nam_id': nam_id,
            'project_id': project_id,
            'user_id': user_id,
            'water_balance_mode': water_balance_mode,
            'precipitation_factor': precipitation_factor,
            'storm_center_mode': storm_center_mode,
            'routing_method': routing_method,
            'discharge_point': discharge_point,
            'discharge_point_crs': discharge_point_crs
        }
        
        # Call the function without self parameter
        result = nam_function(**kwargs)
        
        print(f"  NAM calculation completed for entry {nam_id}")
        print(f"  Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Result keys: {list(result.keys())}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
        return result
        
    except Exception as e:
        print(f"Error in NAM calculation for entry {getattr(nam_entry, 'id', 'unknown')}: {e}")
        traceback.print_exc()
        return None

def save_results_to_csv(results: List[Dict[str, Any]], output_file: str):
    """
    Save calculation results to CSV file.
    
    Args:
        results: List of calculation results
        output_file: Output CSV file path
    """
    try:
        # Define CSV columns
        fieldnames = [
            'nam_id', 'project_id', 'project_name', 'user_id', 'return_period', 'return_period_desc',
            'catchment_area_km2', 'channel_length_m', 'delta_h_m',
            'water_balance_mode', 'precipitation_factor', 'storm_center_mode', 'routing_method',
            'HQ', 'Tc', 'TB', 'TFl', 'i', 'S', 'Pe', 'effective_curve_number',
            'calculation_status', 'error_message', 'calculation_time'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow(result)
        
        print(f"Results saved to: {output_file}")
        print(f"Total entries processed: {len(results)}")
        
    except Exception as e:
        print(f"Error saving results to CSV: {e}")
        traceback.print_exc()

def main():
    """Main function to run batch NAM calculations."""
    parser = argparse.ArgumentParser(description='Batch NAM Calculations')
    parser.add_argument('--output', default='nam_results.csv', 
                       help='Output CSV file (default: nam_results.csv)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of entries to process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without running calculations')
    
    args = parser.parse_args()
    
    print("=== Batch NAM Calculations ===")
    print(f"Output file: {args.output}")
    if args.limit:
        print(f"Limit: {args.limit} entries")
    if args.dry_run:
        print("DRY RUN MODE - No calculations will be performed")
    print()
    
    try:
        # Get all NAM entries
        nam_entries = get_all_nam_entries(limit=args.limit)
        
        if not nam_entries:
            print("No NAM entries found in database")
            return
        
        results = []
        
        # Process each entry
        for i, nam_entry in enumerate(nam_entries, 1):
            print(f"\n--- Processing entry {i}/{len(nam_entries)} ---")
            
            # Validate entry
            if not validate_nam_entry(nam_entry):
                print(f"Skipping invalid entry {nam_entry.get('id', 'unknown')}")
                continue
            
            # Prepare result record
            result_record = {
                'nam_id': nam_entry.id,
                'project_id': nam_entry.Project.id,
                'project_name': getattr(nam_entry.Project, 'title', ''),
                'user_id': nam_entry.Project.userId,
                'return_period': nam_entry.x,
                'return_period_desc': getattr(nam_entry.Annuality, 'description', ''),
                'catchment_area_km2': nam_entry.Project.catchment_area,
                'channel_length_m': nam_entry.Project.channel_length,
                'delta_h_m': nam_entry.Project.delta_h,
                'water_balance_mode': getattr(nam_entry, 'water_balance_mode', ''),
                'precipitation_factor': getattr(nam_entry, 'precipitation_factor', 1.0),
                'storm_center_mode': getattr(nam_entry, 'storm_center_mode', ''),
                'routing_method': getattr(nam_entry, 'routing_method', ''),
                'HQ': None,
                'Tc': None,
                'TB': None,
                'TFl': None,
                'i': None,
                'S': None,
                'Pe': None,
                'effective_curve_number': None,
                'calculation_status': 'pending',
                'error_message': '',
                'calculation_time': datetime.now().isoformat()
            }
            
            if args.dry_run:
                print(f"Would process: NAM ID {nam_entry.id}, Project {nam_entry.Project.id}")
                result_record['calculation_status'] = 'dry_run'
                results.append(result_record)
                continue
            
            # Run calculation
            start_time = datetime.now()
            calculation_result = call_nam_calculation(nam_entry)
            end_time = datetime.now()
            
            if calculation_result:
                # Extract results from calculation
                if isinstance(calculation_result, dict):
                    # Check if it's an error result
                    if 'error' in calculation_result:
                        result_record.update({
                            'calculation_status': 'failed',
                            'error_message': calculation_result['error']
                        })
                        print(f"  Error from NAM function: {calculation_result['error']}")
                    else:
                        # Success - extract the values
                        result_record.update({
                            'HQ': calculation_result.get('HQ'),
                            'Tc': calculation_result.get('Tc'),
                            'TB': calculation_result.get('TB'),
                            'TFl': calculation_result.get('TFl'),
                            'i': calculation_result.get('i'),
                            'S': calculation_result.get('S'),
                            'Pe': calculation_result.get('Pe'),
                            'effective_curve_number': calculation_result.get('effective_curve_number'),
                            'calculation_status': 'success'
                        })
                        print(f"  Successfully extracted results:")
                        print(f"    HQ: {result_record['HQ']}")
                        print(f"    Tc: {result_record['Tc']}")
                        print(f"    TB: {result_record['TB']}")
                        print(f"    TFl: {result_record['TFl']}")
                else:
                    result_record.update({
                        'calculation_status': 'unexpected_result',
                        'error_message': f'Unexpected result type: {type(calculation_result)}'
                    })
                    print(f"  Unexpected result type: {type(calculation_result)}")
                    print(f"  Result: {calculation_result}")
            else:
                result_record.update({
                    'calculation_status': 'failed',
                    'error_message': 'Calculation returned None - likely missing raster files (curvenumbers.tif, isozones_cog.tif)'
                })
                print(f"  Calculation returned None - likely missing raster files")
                print(f"  Expected files:")
                print(f"    data/{nam_entry.Project.userId}/{nam_entry.Project.id}/curvenumbers.tif")
                print(f"    data/{nam_entry.Project.userId}/{nam_entry.Project.id}/isozones_cog.tif")
            
            result_record['calculation_time'] = end_time.isoformat()
            results.append(result_record)
            
            print(f"Status: {result_record['calculation_status']}")
            if result_record['calculation_status'] == 'success':
                print(f"  HQ: {result_record['HQ']:.2f} m³/s")
                print(f"  Tc: {result_record['Tc']:.1f} min")
                print(f"  TB: {result_record['TB']:.1f} min")
                print(f"  TFl: {result_record['TFl']:.1f} min")
        
        # Save results
        save_results_to_csv(results, args.output)
        
        # Summary
        success_count = sum(1 for r in results if r['calculation_status'] == 'success')
        failed_count = sum(1 for r in results if r['calculation_status'] == 'failed')
        dry_run_count = sum(1 for r in results if r['calculation_status'] == 'dry_run')
        
        print(f"\n=== Summary ===")
        print(f"Total processed: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        if args.dry_run:
            print(f"Dry run: {dry_run_count}")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        traceback.print_exc()
    finally:
        # Disconnect from database
        try:
            prisma.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()
