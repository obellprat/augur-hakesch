import os
import tempfile
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import pytest

from calculations.curvenumbers import load_own_soil_data


def test_load_own_soil_data():
    """Test loading user-provided soil data from shapefile."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test soil data
        test_geometries = [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
        ]
        
        test_hsg_values = ['A', 'B', 'C']
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'hsg': test_hsg_values,
            'geometry': test_geometries
        }, crs='EPSG:4326')
        
        # Save as shapefile
        soil_file = os.path.join(temp_dir, 'soil.shp')
        gdf.to_file(soil_file)
        
        # Test bbox that covers our test data
        bbox = [-0.1, -0.1, 2.1, 2.1]  # [min_lon, min_lat, max_lon, max_lat]
        
        # Test loading the soil data
        soil_data = load_own_soil_data(bbox, temp_dir)
        
        # Verify the results
        assert soil_data['source'] == 'OWN_SOIL'
        assert soil_data['soil_data'] is not None
        assert not soil_data['soil_data'].empty
        assert len(soil_data['soil_data']) == 3
        
        # Check HSG values
        hsg_values = soil_data['soil_data']['hsg'].tolist()
        assert set(hsg_values) == {'A', 'B', 'C'}
        
        print(f"Successfully loaded {len(soil_data['soil_data'])} soil features")
        print(f"HSG distribution: {soil_data['soil_data']['hsg'].value_counts().to_dict()}")


def test_load_own_soil_data_missing_file():
    """Test handling of missing soil file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        bbox = [0, 0, 1, 1]
        
        # Should raise FileNotFoundError when soil.shp doesn't exist
        with pytest.raises(FileNotFoundError):
            load_own_soil_data(bbox, temp_dir)


def test_load_own_soil_data_invalid_hsg():
    """Test handling of invalid HSG values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test soil data with invalid HSG values
        test_geometries = [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        ]
        
        test_hsg_values = ['A', 'X']  # 'X' is invalid
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'hsg': test_hsg_values,
            'geometry': test_geometries
        }, crs='EPSG:4326')
        
        # Save as shapefile
        soil_file = os.path.join(temp_dir, 'soil.shp')
        gdf.to_file(soil_file)
        
        bbox = [-0.1, -0.1, 2.1, 2.1]
        
        # Should filter out invalid HSG values
        soil_data = load_own_soil_data(bbox, temp_dir)
        
        # Should only have the valid HSG value
        assert len(soil_data['soil_data']) == 1
        assert soil_data['soil_data']['hsg'].iloc[0] == 'A'


def test_load_own_soil_data_missing_hsg_field():
    """Test handling of missing hsg field."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test soil data without hsg field
        test_geometries = [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        ]
        
        # Create GeoDataFrame without hsg field
        gdf = gpd.GeoDataFrame({
            'other_field': ['value1'],
            'geometry': test_geometries
        }, crs='EPSG:4326')
        
        # Save as shapefile
        soil_file = os.path.join(temp_dir, 'soil.shp')
        gdf.to_file(soil_file)
        
        bbox = [-0.1, -0.1, 1.1, 1.1]
        
        # Should raise ValueError for missing hsg field
        with pytest.raises(ValueError, match="missing required field: hsg"):
            load_own_soil_data(bbox, temp_dir)


if __name__ == "__main__":
    # Run tests
    test_load_own_soil_data()
    test_load_own_soil_data_missing_file()
    test_load_own_soil_data_invalid_hsg()
    test_load_own_soil_data_missing_hsg_field()
    print("All tests passed!")
