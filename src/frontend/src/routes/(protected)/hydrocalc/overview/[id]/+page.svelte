<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';
	import { base } from '$app/paths';

	import { Map, View, Feature } from 'ol';
	import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
	import { Point } from 'ol/geom';
	import { Vector as VectorSource } from 'ol/source';
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

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HydroCalc - Projekt ' + data.project.title;

	let northing = $derived(data.project.Point.northing);
	let easting = $derived(data.project.Point.easting);

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	onMount(async () => {
		const stroke = new Stroke({ color: 'black', width: 2 });
		const fill = new Fill({ color: 'blue' });

		var vectorSource = new VectorSource({});

		var vectorLayer = new VectorLayer({
			name: 'Pourpoint',
			zIndex: 100,
			source: vectorSource,
			style: new Style({
				image: new CircleStyle({
					radius: 7,
					fill: fill,
					stroke: stroke
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
			vectorSource = new VectorSource({});
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

		const map = new Map({
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

		map.on('singleclick', function (e) {
			northing = Math.round(e.coordinate[1]);
			easting = Math.round(e.coordinate[0]);
			addMarker([easting, northing]);
		});
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
						aria-controls="email-sidebar"
					>
						<i class="ri-menu-2-line fs-17"></i>
					</button>
					<h3 class="my-0 lh-base">
						{data.project.title}
					</h3>
				</div>
				<div class="d-flex align-items-center gap-2">
					<span
						class="btn btn-sm btn-icon btn-ghost-danger d-none d-xl-flex"
						data-bs-placement="top"
						title="Delete"
						aria-label="delete"
						data-bs-toggle="modal"
						data-bs-target="#delete-project-modal"
					>
						<i class="ti ti-trash fs-20"></i>
					</span>
					<a
						href="javascript: void(0);"
						class="btn btn-sm btn-icon btn-ghost-primary d-none d-xl-flex"
						data-bs-toggle="modal"
						data-bs-target="#userVideoCall"
						data-bs-placement="top"
						title="Export"
						aria-label="export"
					>
						<i class="ti ti-share fs-20"></i>
					</a>
				</div>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<div class="col-lg-6">
					<form
						method="post"
						action="?/update"
						use:enhance={() => {
							return async ({ update }) => {
								await update();
								currentProject.title = data.project.title;
							};
						}}
					>
						<input type="hidden" name="id" value={data.project.id} />
						<div class="mb-3">
							<label for="title" class="form-label">Projekttitel</label>
							<input
								type="text"
								name="title"
								id="title"
								class="form-control"
								value={data.project.title}
							/>
						</div>

						<div class="mb-3">
							<label for="description" class="form-label">Beschreibung</label>
							<textarea class="form-control" name="description" rows="5"
								>{data.project.description}</textarea
							>
						</div>

						<div class="mb-3">
							<label for="easting" class="form-label">Abflusspunkt</label>
							<div class="row">
								<div class="col-md-6">
									<input
										type="text"
										name="easting"
										id="easting"
										class="form-control"
										value={easting}
									/>
								</div>
								<div class="col-md-6">
									<input
										type="text"
										name="northing"
										id="northing"
										class="form-control"
										value={northing}
									/>
								</div>
							</div>
						</div>
						<div class="d-flex align-items-center justify-content-between py-1">
							<div class="d-flex align-items-center gap-2">
								<button type="submit" class="btn btn-primary">Save</button>
							</div>
							<div class="d-flex align-items-center gap-2">
								<a
									href="{base}/hydrocalc/geodata/{data.project.id}"
									type="button"
									class="btn btn-primary"
								>
									Geodaten <i class="ri-arrow-right-line"></i>
								</a>
							</div>
						</div>
					</form>
				</div>
				<!-- end col -->
				<div class="col-lg-6">
					<div class="py-2">
						Abflusspunkt <span class="text-muted">(mit einem Klick auf die Karte ändern)</span>
					</div>
					<div class="d-flex flex-grow-1" style="height:500px;" id="map"></div>
				</div>
			</div>
			<!-- end row-->
		</div>
	</div>

	<!-- Warning Header Modal -->
	<div
		id="delete-project-modal"
		class="modal fade"
		tabindex="-1"
		role="dialog"
		aria-labelledby="warning-header-modalLabel"
		aria-hidden="true"
	>
		<div class="modal-dialog">
			<div class="modal-content">
				<div class="modal-header text-bg-warning border-0">
					<h4 class="modal-title" id="warning-header-modalLabel">Projekt löschen</h4>
					<button
						type="button"
						class="btn-close btn-close-white"
						data-bs-dismiss="modal"
						aria-label="Close"
					></button>
				</div>
				<div class="modal-body">
					<p>Soll das Projekt {data.project.title} wirklich gelöscht werden?</p>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-light" data-bs-dismiss="modal">Abbrechen</button>
					<form method="POST" action="?/delete">
						<input type="hidden" name="id" value={data.project.id} />
						<button type="submit" class="btn btn-warning">Löschen</button>
					</form>
				</div>
			</div>
			<!-- /.modal-content -->
		</div>
		<!-- /.modal-dialog -->
	</div>
	<!-- /.modal -->
</div>
