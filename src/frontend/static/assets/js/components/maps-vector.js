/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Vector Maps
 */

class VectorMap {
	initWorldMapMarker() {
		const map = new jsVectorMap({
			map: 'world',
			selector: '#world-map-markers',
			zoomOnScroll: false,
			zoomButtons: true,
			markersSelectable: true,
			markers: [
				{ name: 'Greenland', coords: [72, -42] },
				{ name: 'Canada', coords: [56.1304, -106.3468] },
				{ name: 'Brazil', coords: [-14.235, -51.9253] },
				{ name: 'Egypt', coords: [26.8206, 30.8025] },
				{ name: 'Russia', coords: [61, 105] },
				{ name: 'China', coords: [35.8617, 104.1954] },
				{ name: 'United States', coords: [37.0902, -95.7129] },
				{ name: 'Norway', coords: [60.472024, 8.468946] },
				{ name: 'Ukraine', coords: [48.379433, 31.16558] }
			],
			markerStyle: {
				initial: { fill: '#3e60d5' },
				selected: { fill: '#3e60d56e' }
			},
			regionStyle: {
				initial: {
					fill: '#9ca3af69',
					fillOpacity: 1
				}
			},
			labels: {
				markers: {
					render: (marker) => marker.name
				}
			}
		});
	}

	// World Map Markers with Line
	initWorldMarkerLine() {
		const worldlinemap = new jsVectorMap({
			map: 'world_merc',
			selector: '#world-map-markers-line',
			zoomOnScroll: false,
			zoomButtons: false,
			markers: [
				{
					name: 'Greenland',
					coords: [72, -42]
				},
				{
					name: 'Canada',
					coords: [56.1304, -106.3468]
				},
				{
					name: 'Brazil',
					coords: [-14.235, -51.9253]
				},
				{
					name: 'Egypt',
					coords: [26.8206, 30.8025]
				},
				{
					name: 'Russia',
					coords: [61, 105]
				},
				{
					name: 'China',
					coords: [35.8617, 104.1954]
				},
				{
					name: 'United States',
					coords: [37.0902, -95.7129]
				},
				{
					name: 'Norway',
					coords: [60.472024, 8.468946]
				},
				{
					name: 'Ukraine',
					coords: [48.379433, 31.16558]
				}
			],
			lines: [
				{
					from: 'Canada',
					to: 'Egypt'
				},
				{
					from: 'Russia',
					to: 'Egypt'
				},
				{
					from: 'Greenland',
					to: 'Egypt'
				},
				{
					from: 'Brazil',
					to: 'Egypt'
				},
				{
					from: 'United States',
					to: 'Egypt'
				},
				{
					from: 'China',
					to: 'Egypt'
				},
				{
					from: 'Norway',
					to: 'Egypt'
				},
				{
					from: 'Ukraine',
					to: 'Egypt'
				}
			],
			regionStyle: {
				initial: {
					stroke: '#9ca3af',
					strokeWidth: 0.25,
					fill: '#9ca3af69',
					fillOpacity: 1
				}
			},
			markerStyle: {
				initial: { fill: '#9ca3af' },
				selected: { fill: '#9ca3af' }
			},
			lineStyle: {
				animation: true,
				strokeDasharray: '6 3 6'
			}
		});
	}

	initIndiaVectorMap() {
		const map = new jsVectorMap({
			map: 'in_mill',
			backgroundColor: 'transparent',
			selector: '#india-vector-map',
			regionStyle: {
				initial: {
					fill: '#16a7e9'
				}
			}
		});
	}

	initCanadaVectorMap() {
		const map = new jsVectorMap({
			map: 'canada',
			selector: '#canada-vector-map',
			zoomOnScroll: false,
			regionStyle: {
				initial: {
					fill: '#3e60d5'
				}
			}
		});
	}

	initRussiaVectorMap() {
		const map = new jsVectorMap({
			map: 'russia',
			selector: '#russia-vector-map',
			zoomOnScroll: false,
			regionStyle: {
				initial: {
					fill: '#5d7186'
				}
			}
		});
	}

	// US Map
	initUsVectorMap() {
		const map = new jsVectorMap({
			map: 'us_aea_en',
			selector: '#usa-vector-map',
			regionStyle: {
				initial: {
					fill: '#3e60d5'
				}
			}
		});
	}

	initIraqVectorMap() {
		const map = new jsVectorMap({
			map: 'iraq',
			selector: '#iraq-vector-map',
			zoomOnScroll: false,
			regionStyle: {
				initial: {
					fill: '#3e60d5'
				}
			}
		});
	}

	initSpainVectorMap() {
		const map = new jsVectorMap({
			map: 'spain',
			selector: '#spain-vector-map',
			zoomOnScroll: false,
			regionStyle: {
				initial: {
					fill: '#ffc35a'
				}
			}
		});
	}

	init() {
		this.initWorldMapMarker();
		this.initWorldMarkerLine();
		this.initIndiaVectorMap();
		this.initCanadaVectorMap();
		this.initRussiaVectorMap();
		this.initUsVectorMap();
		this.initIraqVectorMap();
		this.initSpainVectorMap();
	}
}

document.addEventListener('DOMContentLoaded', function (e) {
	new VectorMap().init();
});
