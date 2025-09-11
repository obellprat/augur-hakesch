import json
import os
import tempfile
import numpy as np
import rasterio
from unittest.mock import patch

from api.src.catchment.worker import create_task


def test_home(test_app):
    response = test_app.get("/")
    assert response.status_code == 200


def test_task():
    assert create_task.run(1)
    assert create_task.run(2)
    assert create_task.run(3)


@patch("worker.create_task.run")
def test_mock_task(mock_run):
    assert create_task.run(1)
    create_task.run.assert_called_once_with(1)

    assert create_task.run(2)
    assert create_task.run.call_count == 2

    assert create_task.run(3)
    assert create_task.run.call_count == 3


def test_task_status(test_app):
    response = test_app.post(
        "/tasks",
        data=json.dumps({"type": 1})
    )
    content = response.json()
    task_id = content["task_id"]
    assert task_id

    response = test_app.get(f"tasks/{task_id}")
    content = response.json()
    assert content == {"task_id": task_id, "task_status": "PENDING", "task_result": None}
    assert response.status_code == 200

    while content["task_status"] == "PENDING":
        response = test_app.get(f"tasks/{task_id}")
        content = response.json()
    assert content == {"task_id": task_id, "task_status": "SUCCESS", "task_result": True}


def test_rain_distribution_saving():
    """Test that rain distribution can be saved as TIFF file."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock storm distribution (similar to what's created in the nam function)
        shape = (100, 100)
        storm_distribution = np.random.uniform(0, 50, shape).astype(np.float32)
        
        # Create a mock valid mask (some cells are valid)
        valid_mask = np.random.choice([True, False], shape, p=[0.8, 0.2])
        
        # Create a mock rain distribution raster (only valid cells have values)
        rain_distribution_raster = np.zeros_like(storm_distribution, dtype=np.float32)
        rain_distribution_raster[valid_mask] = storm_distribution[valid_mask]
        
        # Create a test TIFF file
        test_file = os.path.join(temp_dir, "test_rain_distribution.tif")
        
        # Save as GeoTIFF
        profile = {
            'driver': 'GTiff',
            'height': rain_distribution_raster.shape[0],
            'width': rain_distribution_raster.shape[1],
            'count': 1,
            'dtype': rain_distribution_raster.dtype.name,
            'crs': 'EPSG:2056',  # Swiss coordinate system
            'transform': rasterio.Affine(5.0, 0.0, 0.0, 0.0, -5.0, 0.0),  # 5m resolution
            'nodata': 0,
            'compress': 'lzw'
        }
        
        with rasterio.open(test_file, 'w', **profile) as dst:
            dst.write(rain_distribution_raster, 1)
        
        # Verify the file was created
        assert os.path.exists(test_file)
        assert os.path.getsize(test_file) > 0
        
        # Verify the file can be read back
        with rasterio.open(test_file) as src:
            data = src.read(1)
            assert data.shape == shape
            assert np.allclose(data, rain_distribution_raster)
            assert src.crs == 'EPSG:2056'
        
        print(f"Test rain distribution TIFF created successfully: {test_file}")
        print(f"  - File size: {os.path.getsize(test_file) / 1024:.1f} KB")
        print(f"  - Precipitation range: {np.min(data[valid_mask]):.2f} - {np.max(data[valid_mask]):.2f} mm")
        print(f"  - Total precipitation: {np.sum(data[valid_mask]):.2f} mm")
