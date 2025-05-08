//import './style.css';
import { Map, View } from 'ol';
import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
import WebGLTileLayer from 'ol/layer/WebGLTile';
import { XYZ, GeoTIFF } from 'ol/source';
import { defaults as defaultControls, ScaleLine } from 'ol/control';
import { register } from 'ol/proj/proj4';
import proj4 from 'proj4';
import { CupertinoPane, CupertinoSettings } from 'cupertino-pane';

// adding Swiss projections to proj4 (proj string comming from https://epsg.io/)
proj4.defs(
	'EPSG:2056',
	'+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs'
);
register(proj4);

const backgroundLayer = new TileLayer({
	id: 'background-layer',
	source: new XYZ({
		url: `https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg`
	})
});

const view = new View({
	projection: 'EPSG:2056',
	center: [2605764, 1177523],
	zoom: 14
});

const map = new Map({
	target: 'map',
	controls: defaultControls().extend([
		new ScaleLine({
			units: 'metric'
		})
	]),
	layers: [backgroundLayer],
	view: view
});

let mapcontainer = document.getElementById('mapcontainer');
let body = document.querySelector('body');
let mapcontainer_bounding = mapcontainer.getBoundingClientRect();
let body_bounding = body.getBoundingClientRect();

let settings = {
	parentElement: mapcontainer,
	breaks: {
		middle: {
			enabled: false
		},
		bottom: {
			enabled: true,
			height: body_bounding.height - mapcontainer_bounding.height + 50
		}
	},
	initialBreak: 'bottom',
	buttonDestroy: false
};

let myPane = new CupertinoPane('.cupertino-pane', settings);

(async () => {
	await myPane.present({ animate: true });
})();

const styleFunction = function (feature) {
	return styles[feature.getGeometry().getType()];
};

map.on('singleclick', function (e) {
	fetch('./isozones/?northing=' + e.coordinate[0] + '&easting=' + e.coordinate[1], {
		method: 'GET'
	})
		.then((response) => response.json())
		.then((data) => {
			const actTime = new Date();
			document.getElementById('progresstext').innerHTML = `${actTime.toUTCString()} Starting`;

			map.getTargetElement().classList.add('spinner');
			getStatus(data.task_id);
		});
});

function getStatus(taskID) {
	fetch(`./task/${taskID}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then((response) => response.json())
		.then((res) => {
			// write out the state
			const actTime = new Date();
			//let html = `${actTime.toUTCString()} ${res.task_status} `;
			let html = `${res.task_status} `;
			if (res.task_status != 'SUCCESS') html = html + `${JSON.stringify(res.task_result.text)}`;
			document.getElementById('progresstext').innerHTML = html; // + '<br>' + document.getElementById('progresstext').innerHTML;

			const taskStatus = res.task_status;
			if (taskStatus === 'SUCCESS') {
				console.log(res);

				const isozone_source = new GeoTIFF({
					sources: [
						{
							url: './data/temp/' + res.task_id + '/isozones_cog.tif'
						}
					],
					normalize: false
				});

				const isozone = new WebGLTileLayer({
					source: isozone_source,
					name: 'isozone',
					style: {
						color: [
							'interpolate',
							['linear'],
							['band', 1],
							-1, // undefined
							[0, 0, 0, 0],
							0, // undefined
							[255, 0, 0],
							5,
							[255, 210, 210]
						]
					}
				});

				map.getLayers().forEach((layer) => {
					if (layer && layer.get('name') && layer.get('name') == 'isozone') {
						map.removeLayer(layer);
					}
				});

				map.addLayer(isozone);
			}
			if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
				map.getTargetElement().classList.remove('spinner');
				return false;
			}

			setTimeout(function () {
				getStatus(res.task_id);
			}, 1000);
		})
		.catch((err) => console.log(err));
}
