import { map, latLng, tileLayer, MapOptions, LatLng } from 'leaflet';

const options: MapOptions = {
	center: latLng(40.731253, -73.996139),
	zoom: 12
};

//const mymap = map('precipitationMap', options);

let baseLayer = tileLayer(
	'https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png',
	{
		attribution:
			'Map tiles by <a href="http://augur.world">AUGUR</a> and &copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/about/" target="_blank">OpenStreetMap contributors</a>',
		subdomains: 'abcd',
		minZoom: 0,
		maxZoom: 20,
		opacity: 0.5
	}
);

let tilesPeriod = 10;
let augurLayer = tileLayer(`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`, {
	detectRetina: true,
	opacity: 1
});

const basicMap = map('precipitationMap', {
	center: new LatLng(0, 0),
	zoom: 4,
	minZoom: 4,
	maxZoom: 9,
	zoomControl: false,
	// maxBounds: L.latLngBounds(L.latLng(50, -74.227), L.latLng(40.774, -74.125)),
	maxBounds: [
		[-50, -Infinity],
		[50, Infinity]
	],
	layers: [augurLayer, baseLayer]
});
