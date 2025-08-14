#!/usr/bin/env python3
"""
Database import script for dbimport.csv
Imports project data with related entities into the database
"""

import csv
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from helpers.prisma import prisma

def load_csv_data(file_path):
    """Load data from CSV file"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:  # utf-8-sig handles BOM
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                data.append(row)
        print(f"Loaded {len(data)} rows from {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return None
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def ensure_reference_data():
    """Ensure required reference data exists in the database"""
    print("Ensuring reference data exists...")
    
    # Ensure User exists
    try:
        user = prisma.user.find_unique(where={'id': 1})
        if not user:
            print("Creating default user...")
            prisma.user.create(data={
                'email': 'default@example.com',
                'name': 'Default User'
            })
            user = prisma.user.find_unique(where={'email': 'default@example.com'})
            print(f"User created with ID: {user.id}")
        else:
            print(f"User with ID 1 already exists")
    except Exception as e:
        print(f"Error ensuring user exists: {e}")
        return False
    
    # Ensure Annualities exist
    annualities_data = [
        {'description': '2.33 years', 'number': 2.33},
        {'description': '3 years', 'number': 3.0},
        {'description': '5 years', 'number': 5.0},
        {'description': '10 years', 'number': 10.0},
        {'description': '20 years', 'number': 20.0},
        {'description': '50 years', 'number': 50.0},
        {'description': '100 years', 'number': 100.0}
    ]
    
    for ann_data in annualities_data:
        try:
            existing = prisma.annualities.find_unique(where={'number': ann_data['number']})
            if not existing:
                print(f"Creating annuality: {ann_data['description']}")
                prisma.annualities.create(data=ann_data)
            else:
                print(f"Annuality {ann_data['number']} already exists")
        except Exception as e:
            print(f"Error creating annuality {ann_data['number']}: {e}")
    
    # Ensure WaterBalanceMode exists
    water_balance_modes = [
        {'mode': 'simple', 'description': 'Simple water balance approach'},
        {'mode': 'uniform', 'description': 'Uniform precipitation approach'},
        {'mode': 'cumulative', 'description': 'Cumulative water balance approach'}
    ]
    
    for mode_data in water_balance_modes:
        try:
            existing = prisma.waterbalancemode.find_unique(where={'mode': mode_data['mode']})
            if not existing:
                print(f"Creating water balance mode: {mode_data['mode']}")
                prisma.waterbalancemode.create(data=mode_data)
        except Exception as e:
            print(f"Error creating water balance mode {mode_data['mode']}: {e}")
    
    # Ensure StormCenterMode exists
    storm_center_modes = [
        {'mode': 'centroid', 'description': 'Storm center at catchment centroid'},
        {'mode': 'user_point', 'description': 'Storm center at user-provided point'},
        {'mode': 'discharge_point', 'description': 'Storm center at discharge point'}
    ]
    
    for mode_data in storm_center_modes:
        try:
            existing = prisma.stormcentermode.find_unique(where={'mode': mode_data['mode']})
            if not existing:
                print(f"Creating storm center mode: {mode_data['mode']}")
                prisma.stormcentermode.create(data=mode_data)
        except Exception as e:
            print(f"Error creating storm center mode {mode_data['mode']}: {e}")
    
    # Ensure RoutingMethod exists
    routing_methods = [
        {'method': 'time_values', 'description': 'Time values routing method'},
        {'method': 'isozone', 'description': 'Isozone-based routing'},
        {'method': 'travel_time', 'description': 'Travel time-based routing'}
    ]
    
    for method_data in routing_methods:
        try:
            existing = prisma.routingmethod.find_unique(where={'method': method_data['method']})
            if not existing:
                print(f"Creating routing method: {method_data['method']}")
                prisma.routingmethod.create(data=method_data)
        except Exception as e:
            print(f"Error creating routing method {method_data['method']}: {e}")
    
    print("Reference data check completed")
    return True

def import_project_data(row):
    """Import a single project with all related data"""
    try:
        print(f"\nImporting project: {row['project_title']}")
        
        # Check if project already exists
        existing_project = prisma.project.find_first(where={'title': row['project_title']})
        if existing_project:
            print(f"  ⚠️  Project '{row['project_title']}' already exists with ID: {existing_project.id}")
            print(f"  Skipping import to avoid duplicates")
            return True
        
        # 1. Create Point
        try:
            point = prisma.point.create(data={
                'northing': float(row['point_northing']),
                'easting': float(row['point_easting'])
            })
            print(f"  Created Point with ID: {point.id}")
        except Exception as e:
            print(f"  ✗ Error creating Point: {e}")
            if "Unique constraint failed" in str(e):
                print(f"  💡 This is likely a sequence issue. Run the fix_sequences.sql script first.")
            raise e
        
        # 2. Create IDF_Parameters
        try:
            idf_params = prisma.idf_parameters.create(data={
                'P_low_1h': float(row['idf_parameters_P_low_1h']),
                'P_high_1h': float(row['idf_parameters_P_high_1h']),
                'P_low_24h': float(row['idf_parameters_P_low_24h']),
                'P_high_24h': float(row['idf_parameters_P_high_24h']),
                'rp_low': float(row['idf_parameters_rp_low']),
                'rp_high': float(row['idf_parameters_rp_high'])
            })
            print(f"  Created IDF_Parameters with ID: {idf_params.id}")
        except Exception as e:
            print(f"  ✗ Error creating IDF_Parameters: {e}")
            if "Unique constraint failed" in str(e):
                print(f"  💡 This is likely a sequence issue. Run the fix_sequences.sql script first.")
            raise e
        
        # 3. Create Project
        project = prisma.project.create(data={
            'title': row['project_title'],
            'description': f"Imported project: {row['project_title']}",
            'lastModified': datetime.now(),
            'pointId': point.id,
            'userId': int(row['project_userid']),
            'idfParameterId': idf_params.id
        })
        print(f"  Created Project with ID: {project.id}")
        
        # 4. Create Mod_Fliesszeit if data exists
        if row['Mod_Fliesszeit_x'] and row['Mod_Fliesszeit_Vo20'] and row['Mod_Fliesszeit_psi']:
            try:
                # Find the annuality
                annuality = prisma.annualities.find_unique(where={'number': float(row['Mod_Fliesszeit_x'])})
                if annuality:
                    # Check if Mod_Fliesszeit already exists for this project and annuality
                    existing_mod_fliesszeit = prisma.mod_fliesszeit.find_first(where={
                        'project_id': project.id,
                        'x': annuality.id
                    })
                    if existing_mod_fliesszeit:
                        print(f"  Mod_Fliesszeit already exists for this project and annuality (ID: {existing_mod_fliesszeit.id})")
                    else:
                        mod_fliesszeit = prisma.mod_fliesszeit.create(data={
                            'x': annuality.id,
                            'Vo20': float(row['Mod_Fliesszeit_Vo20']),
                            'psi': float(row['Mod_Fliesszeit_psi']),
                            'project_id': project.id
                        })
                        print(f"  Created Mod_Fliesszeit with ID: {mod_fliesszeit.id}")
                else:
                    print(f"  Warning: Annuality {row['Mod_Fliesszeit_x']} not found for Mod_Fliesszeit")
            except Exception as e:
                print(f"  Error creating Mod_Fliesszeit: {e}")
                raise e
        
        # 5. Create Koella if data exists
        if row['Koella_x'] and row['Koella_Vo20'] and row['Koella_glacier_area']:
            try:
                # Find the annuality
                annuality = prisma.annualities.find_unique(where={'number': float(row['Koella_x'])})
                if annuality:
                    # Check if Koella already exists for this project and annuality
                    existing_koella = prisma.koella.find_first(where={
                        'project_id': project.id,
                        'x': annuality.id
                    })
                    if existing_koella:
                        print(f"  Koella already exists for this project and annuality (ID: {existing_koella.id})")
                    else:
                        koella = prisma.koella.create(data={
                            'x': annuality.id,
                            'Vo20': float(row['Koella_Vo20']),
                            'glacier_area': int(row['Koella_glacier_area']),
                            'project_id': project.id
                        })
                        print(f"  Created Koella with ID: {koella.id}")
                else:
                    print(f"  Warning: Annuality {row['Koella_x']} not found for Koella")
            except Exception as e:
                print(f"  Error creating Koella: {e}")
                raise e
        
        # 6. Create NAM if data exists
        if row['NAM_x']:
            try:
                # Find the annuality
                annuality = prisma.annualities.find_unique(where={'number': float(row['NAM_x'])})
                if annuality:
                    # Check if NAM already exists for this project and annuality
                    existing_nam = prisma.nam.find_first(where={
                        'project_id': project.id,
                        'x': annuality.id
                    })
                    if existing_nam:
                        print(f"  NAM already exists for this project and annuality (ID: {existing_nam.id})")
                    else:
                        nam_data = {
                            'x': annuality.id,
                            'project_id': project.id,
                            'readiness_to_drain': int(row.get('NAM_readiness_to_drain', 0))
                        }
                        
                        # Add optional parameters if they exist
                        if row.get('NAM_precipitation_factor'):
                            nam_data['precipitation_factor'] = float(row['NAM_precipitation_factor'])
                        if row.get('NAM_water_balance_mode'):
                            nam_data['water_balance_mode'] = row['NAM_water_balance_mode']
                        if row.get('NAM_storm_center_mode'):
                            nam_data['storm_center_mode'] = row['NAM_storm_center_mode']
                        if row.get('NAM_routing_method'):
                            nam_data['routing_method'] = row['NAM_routing_method']
                        
                        nam = prisma.nam.create(data=nam_data)
                        print(f"  Created NAM with ID: {nam.id}")
                else:
                    print(f"  Warning: Annuality {row['NAM_x']} not found for NAM")
            except Exception as e:
                print(f"  Error creating NAM: {e}")
                raise e
        
        print(f"  ✓ Successfully imported project: {row['project_title']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error importing project {row['project_title']}: {e}")
        print(f"  Error type: {type(e).__name__}")
        if hasattr(e, 'message'):
            print(f"  Error message: {e.message}")
        return False

def main():
    """Main import function"""
    print("Starting database import from dbimport.csv...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Connect to database
    try:
        prisma.connect()
        print("Connected to database")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    
    # Load CSV data
    csv_file = os.path.join(os.path.dirname(__file__), 'dbimport.csv')
    data = load_csv_data(csv_file)
    if not data:
        prisma.disconnect()
        sys.exit(1)
    
    # Ensure reference data exists
    if not ensure_reference_data():
        prisma.disconnect()
        sys.exit(1)
    
    # Import each row
    success_count = 0
    total_count = len(data)
    
    for row in data:
        if import_project_data(row):
            success_count += 1
    
    # Summary
    print(f"\n=== Import Summary ===")
    print(f"Total rows processed: {total_count}")
    print(f"Successful imports: {success_count}")
    print(f"Failed imports: {total_count - success_count}")
    
    if success_count == total_count:
        print("✓ All imports successful!")
    else:
        print("⚠ Some imports failed. Check the logs above.")
    
    # Disconnect from database
    prisma.disconnect()
    print("Disconnected from database")

if __name__ == "__main__":
    main()
