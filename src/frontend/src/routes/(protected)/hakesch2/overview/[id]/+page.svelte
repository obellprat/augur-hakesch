<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';

	import { Map, View } from 'ol';
	import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
	import WebGLTileLayer from 'ol/layer/WebGLTile';
	import { XYZ, GeoTIFF } from 'ol/source';
	import { defaults as defaultControls, ScaleLine } from 'ol/control';
	import { register } from 'ol/proj/proj4';
	import proj4 from 'proj4';
	import '../../../../../../node_modules/ol/ol.css';

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HAKESCH 2.0 - Projekt ' + data.project.title;

	let northing = $derived(data.project.Point.northing);
	let easting = $derived(data.project.Point.easting);

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	onMount(async () => {
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

		map.on('singleclick', function (e) {
			northing = Math.round(e.coordinate[1]);
			easting = Math.round(e.coordinate[0]);
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
					<a
						href="javascript: void(0);"
						class="btn btn-sm btn-icon btn-ghost-danger d-none d-xl-flex"
						data-bs-toggle="modal"
						data-bs-target="#userCall"
						data-bs-placement="top"
						title="Delete"
						aria-label="delete"
					>
						<i class="ti ti-trash fs-20"></i>
					</a>
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

						<button type="submit" class="btn btn-primary">Save</button>
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
</div>
