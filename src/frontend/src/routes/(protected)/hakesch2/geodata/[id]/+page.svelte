<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';

	import GeoJSON from 'ol/format/GeoJSON.js';
	import { Map, View, Feature } from 'ol';
	import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
	import WebGLTileLayer from 'ol/layer/WebGLTile';
	import { Point } from 'ol/geom';
	import { Vector as VectorSource, GeoTIFF  } from 'ol/source';
	import Stroke from 'ol/style/Stroke';
	import Fill from 'ol/style/Fill';
	import CircleStyle from 'ol/style/Circle.js';
	import Style from 'ol/style/Style';
	import { XYZ } from 'ol/source';
	import { defaults as defaultControls, ScaleLine } from 'ol/control';
	import { register } from 'ol/proj/proj4';
	import proj4 from 'proj4';
	import '../../../../../../node_modules/ol/ol.css';
	import type { Coordinate } from 'ol/coordinate';
	import { base } from '$app/paths';
	
	import { env } from '$env/dynamic/public';

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HAKESCH 2.0 - Projekt ' + data.project.title;

	let northing = $derived(data.project.Point.northing);
	let easting = $derived(data.project.Point.easting);

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	let map: Map;

	async function calculateGeodatas() {
		fetch(
				PUBLIC_HAKESCH_API_PATH +
					'/isozones/?ProjectId='+ data.project.id,
				{
					method: 'GET',
					headers: {
						'Authorization': 'Bearer ' + data.session.access_token,
					},
				}
			)
				.then((response) => response.json())
				.then((data) => {
					const actTime = new Date();
					document.getElementById('progresstext')!.innerHTML = `${actTime.toUTCString()} Starting`;
					globalThis.$('.progress-bar').css('width', '0%').attr('aria-valuenow', 0);
					getStatus(data.task_id);
				});
	}
	function getStatus(taskID: String) {
		fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/${taskID}`, {
			method: 'GET',
			headers: {
				'Authorization': 'Bearer ' + data.session.access_token,
				'Content-Type': 'application/json'
			}
		})
			.then((response) => response.json())
			.then((res) => {
				console.log("res");
				console.log(res);
				// write out the state
				const actTime = new Date();
				//let html = `${actTime.toUTCString()} ${res.task_status} `;
				let html = ``;
				if (res.task_status != 'SUCCESS' && res.task_status != 'PENDING') {
					html = html + `${JSON.stringify(res.task_result.text)}`;
					
					globalThis.$('.progress-bar').css('width', res.task_result.progress + '%').attr('aria-valuenow', res.task_result.progress);
				}
				document.getElementById('progresstext')!.innerHTML = html; // + '<br>' + document.getElementById('progresstext').innerHTML;

				const taskStatus = res.task_status;
				if (taskStatus === 'SUCCESS') {
					
				}
				if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
					return false;
				}

				setTimeout(function () {
					getStatus(res.task_id);
				}, 1000);
			})
			.catch((err) => console.log(err));
	}

	function addCatchment() {
			const catchmentSource = new VectorSource({
				features: new GeoJSON().readFeatures(data.project.catchment_geojson, 
				{
					dataProjection: 'EPSG:2056',
					featureProjection: map.getView().getProjection()
				}
				),        
			});

			const catchmentLayer = new VectorLayer({
				source: catchmentSource,
				name: 'catchment',
				style: new Style({
					stroke: new Stroke({
					color: 'orange',
					lineDash: [4],
					width: 3,
					}),
					fill: new Fill({
					color: 'rgba(0, 0, 255, 0.1)',
					}),
				})
			});

			map.getLayers().forEach(layer => {
				if (layer && layer.get('name') && layer.get('name') == 'catchment'){
					map.removeLayer(layer)
				}
			});

			map.addLayer(catchmentLayer);
		}

	function addIsozones() {
		const isozone_source = new GeoTIFF({
							sources: [
								{
									url: env.PUBLIC_HAKESCH_API_PATH + '/data/' + data.session.myuser.id + '/' + data.project.id +  '/isozones_cog.tif'
								}
							],
							normalize: false
						});

						const isozone = new WebGLTileLayer({
							source: isozone_source,
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
						isozone.set('name', 'isozone');

						map.getLayers().forEach((layer) => {
							if (layer && layer.get('name') && layer.get('name') == 'isozone') {
								map.removeLayer(layer);
							}
						});

						map.addLayer(isozone);
	}

	onMount(async () => {

		const stroke = new Stroke({color: 'black', width: 2});	
		const fill = new Fill({color: 'blue'});
		var vectorSource = new VectorSource({
		});

		var vectorLayer = new VectorLayer({ 
			name: 'Pourpoint',
			zIndex: 100,
			source: vectorSource,
			style: new Style({
				image: new CircleStyle({
					radius: 7,
					fill: fill,
					stroke: stroke,
				})
			})
		});

		function addMarker(coordinates: Coordinate) {
			var marker = new Feature(new Point(coordinates));
			var zIndex = 1;
			

			map.getLayers().forEach((layer) => {
				if (layer && layer.get('name') && layer.get('name') == 'Pourpoint') {
					map.removeLayer(layer);
				}
			});
			vectorSource = new VectorSource({
				});
			vectorSource.addFeature(marker);
			vectorLayer.setSource(vectorSource);
			map.addLayer(vectorLayer);
		}

		

		proj4.defs(
			'EPSG:2056',
			'+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs'
		);
		register(proj4);

		const backgroundLayer = new TileLayer({
			source: new XYZ({
				url: `https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg`
			})
		});

		const view = new View({
			projection: 'EPSG:2056',
			center: [easting, northing],
			zoom: 14
		});

		map = new Map({
			target: 'map',
			controls: defaultControls().extend([
				new ScaleLine({
					units: 'metric'
				})
			]),
			layers: [backgroundLayer, vectorLayer],
			view: view
		});

		
		addMarker([easting, northing]);
		addCatchment();
		addIsozones();

	});
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="flex-grow-1 card">
	<div class="h-100">
		<div class="card-header py-2 px-3 border-bottom">
			<div class="d-flex align-items-center justify-content-between py-1">
				<div class="d-flex align-items-center gap-2">
					<button
						type="button"
						class="btn btn-light d-xxl-none d-flex p-1"
						data-bs-toggle="offcanvas"
						data-bs-target="#email-sidebar"
						aria-controls="email-sidebar" aria-label="Project menu"
					>
						<i class="ri-menu-2-line fs-17"></i>
					</button>
					<h3 class="my-0 lh-base">
						{data.project.title} - Geodaten
					</h3>
				</div>
				<div class="ms-auto d-xl-flex">
					<button type="button"
						onclick={calculateGeodatas}
						class="btn btn-primary bg-gradient rounded-pill" data-bs-toggle="modal" data-bs-target="#generate-modal">Geodaten neu berechnen</button
					>
					
					<div id="generate-modal" class="modal fade" tabindex="-1" role="dialog" aria-labelledby="standard-modalLabel" aria-hidden="true">
						<div class="modal-dialog">
							<div class="modal-content">
								<div class="modal-header">
									<h4 class="modal-title" id="standard-modalLabel">Berechnung der Geodaten</h4>
									<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
								</div>
								<div class="modal-body">
									<h5>Die Geodaten werden berechnet. Dieser Prozess dauert je nach Einzugsgebietsgrösse einige Minuten</h5>
									<hr>
									<p class="text-muted" id="progresstext"></p>
									<div class="progress mb-2">
										<div class="progress-bar" role="progressbar" style="width: 25%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
									</div>
								</div>
								<div class="modal-footer">
									<button type="button" class="btn btn-light" data-bs-dismiss="modal">Im Hintergrund berechnen lassen</button>
								</div>
							</div><!-- /.modal-content -->
						</div><!-- /.modal-dialog -->
					</div>

				</div>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				{#if data.project.isozones_taskid === ""}
						<p>Geodaten noch nicht berechnen. Neu berechnen?</p>
					{:else if data.project.isozones_running}
						<p>Daten werden aktuell neu berechnet. Bitte warten</p>
					{:else}
				<div class="col-lg-12">
					
					<div class="table-responsive-sm">
						<table class="table table-striped mb-0">
							<thead>
								<tr>
									<th>Einzugsgebietsgrösse [km<sup>2</sup>]</th>
									<th>Max Fliesslänge [m]</th>
									<th>Isozonen</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td>
										{data.project.catchment_area} km<sup>2</sup>
									</td>
									<td>{data.project.channel_length} m</td>
									<td class="text-muted">
										<a href="javascript: void(0);" class="link-reset fs-20 p-1"> Herunterladen</a>
									</td>
								</tr>

							</tbody>
						</table>
					</div>
				</div>
				
					{/if}
				<!-- end col -->
				<div class="col-lg-12">
					<div class="py-2">
					</div>
					<div class="d-flex flex-grow-1" style="height:500px;" id="map"></div>
				</div>
			</div>
			<!-- end row-->
		</div>
	</div>


</div>
