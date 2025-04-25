import './style.css';

import proj4 from "proj4";
import GeoJSON from 'ol/format/GeoJSON.js';
import { Map, View } from "ol";
import { Tile as TileLayer, Vector as VectorLayer} from "ol/layer";
import { XYZ } from "ol/source";
import { defaults as defaultControls, ScaleLine } from "ol/control";
import { register } from "ol/proj/proj4";
import { Vector as VectorSource } from "ol/source";
import {Circle as CircleStyle, Fill, Stroke, Style} from 'ol/style.js';
import TileGrid from "ol/tilegrid/TileGrid";
import { TILEGRID_ORIGIN, TILEGRID_RESOLUTIONS, WMS_TILE_SIZE } from "./config";

// adding Swiss projections to proj4 (proj string comming from https://epsg.io/)
proj4.defs(
  "EPSG:2056",
  "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs"
);
proj4.defs(
  "EPSG:21781",
  "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.4,15.1,405.3,0,0,0,0 +units=m +no_defs"
);
register(proj4);

const backgroundLayer = new TileLayer({
  id: "background-layer",
  source: new XYZ({
    url: `https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg`
  })
});

const view = new View({
  projection: "EPSG:2056",
  center: [2605764, 1177523],
  zoom: 14
});

const map = new Map({
  target: "map",
  controls: defaultControls().extend([
    new ScaleLine({
      units: "metric"
    })
  ]),
  layers: [backgroundLayer],
  view: view
});

const styles = {
  'LineString': new Style({
    stroke: new Stroke({
      color: 'blue',
      width: 2,
    }),
  }),
  'Polygon': new Style({
    stroke: new Stroke({
      color: 'orange',
      lineDash: [4],
      width: 3,
    }),
    fill: new Fill({
      color: 'rgba(0, 0, 255, 0.1)',
    }),
  }),
};

const styleFunction = function (feature) {
  return styles[feature.getGeometry().getType()];
};

map.on('singleclick', function (e) {
  fetch('./catchment/?northing=' + e.coordinate[0] + '&easting=' + e.coordinate[1], {
    method: 'GET',
  })
  .then(response => response.json())
  .then(data => {
    const actTime = new Date();
    document.getElementById('progresstext').innerHTML = `${actTime.toUTCString()} Starting`;
    
    map.getTargetElement().classList.add('spinner');
    getStatus(data.task_id)
  })
});

function getStatus(taskID) {
  
  fetch(`./tasks/${taskID}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
  })
  .then(response => response.json())
  .then(res => {
    // write out the state
    const actTime = new Date();
    let html = `${actTime.toUTCString()} ${res.task_status} `;
    if (res.task_status != "SUCCESS") html = html + `${JSON.stringify(res.task_result.text)}`;
    document.getElementById('progresstext').innerHTML = html + '<br>' + document.getElementById('progresstext').innerHTML;

    const taskStatus = res.task_status;
    if (taskStatus === 'SUCCESS') {
      console.log(res);
      const result_html = `Coordinate: ${res.task_result.northing} ${res.task_result.easting}<br> Max outlet distance: ${res.task_result.max_outlet_distance}`;
      document.getElementById('result').innerHTML = result_html;

      const vectorSource = new VectorSource({
        features: new GeoJSON().readFeatures(res.task_result.geometry, 
          {
            dataProjection: 'EPSG:2056',
            featureProjection: map.getView().getProjection()
          }
        ),        
      });

      const vectorLayer = new VectorLayer({
        source: vectorSource,
        name: 'catchment',
        style: styleFunction
      });

      map.getLayers().forEach(layer => {
        if (layer && layer.get('name') && layer.get('name') == 'catchment'){
            map.removeLayer(layer)
        }
      });

      map.addLayer(vectorLayer);

      // add river network
      const riverSource = new VectorSource({
        features: new GeoJSON().readFeatures(res.task_result.rivernetwork, 
          {
            dataProjection: 'EPSG:2056',
            featureProjection: map.getView().getProjection()
          }
        ),        
      });

      const riverLayer = new VectorLayer({
        source: riverSource,
        name: 'rivernetwork',
        style: styleFunction
      });

      map.getLayers().forEach(layer => {
        if (layer && layer.get('name') && layer.get('name') == 'rivernetwork'){
            map.removeLayer(layer)
        }
      });

      map.addLayer(riverLayer);


    }
    if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
      map.getTargetElement().classList.remove('spinner');
      return false;
    }

    setTimeout(function() {
      getStatus(res.task_id);
    }, 1000);
  })
  .catch(err => console.log(err));
}

$('input[name="points_shapefile_zip"]').on('change', uploadShapefileZip);

function uploadShapefileZip() {
  var formData = new FormData($("#shpzipupload").get(0));
  var ajaxUrl = "./subcatchments/";
				
  $.ajax({
    url : ajaxUrl,
    type : "POST",
    data : formData,
    contentType : false,
    processData : false
  }).done(function(response){
    getSubCatchmentStatus(response.task_id, false);
  }).fail(function(){
    // Here you should treat the http errors (e.g., 403, 404)
  });
}

function getSubCatchmentStatus(taskID, wasrunning) {
  
  fetch(`./tasks/${taskID}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
  })
  .then(response => response.json())
  .then(res => {
    wasrunning = true;
    // write out the state
    const actTime = new Date();
    let html = `${actTime.toUTCString()} ${res.task_status} `;
    if (res.task_status != "SUCCESS") html = html + `${JSON.stringify(res.task_result.text)}`;
    document.getElementById('progresstext').innerHTML = html + '<br>' + document.getElementById('progresstext').innerHTML;

    const taskStatus = res.task_status;
    if (taskStatus === 'SUCCESS') {
      return false;
    }

    setTimeout(function() {
      getSubCatchmentStatus(res.task_id, wasrunning);
    }, 1000);
  })
  .catch(err => {
    // not a json anymore --> maybe it's 
    if (wasrunning)
    {
      const result_html = `Download result: <a href="file/${taskID}">Click here</a>`;
      document.getElementById('result').innerHTML = result_html;
    }
    
    console.log(err)}
  );
}