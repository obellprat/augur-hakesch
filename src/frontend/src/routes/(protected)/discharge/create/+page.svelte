<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
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
	import '../../../../../node_modules/ol/ol.css';
	import type { Coordinate } from 'ol/coordinate';
	import { _ } from 'svelte-i18n';

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = $_('page.discharge.title') + '-' + $_('page.discharge.create.createproject');

	let easting = $derived(2600000);
	let northing = $derived(1200000);

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
					<h3 class="my-0 lh-base">{$_('page.discharge.create.createproject')}</h3>
				</div>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<div class="col-lg-3">
					<form method="post">
						<div class="mb-3">
							<label for="title" class="form-label"
								>{$_('page.discharge.overview.projectTitle')}</label
							>
							<input type="text" name="title" id="title" class="form-control" />
						</div>

						<div class="mb-3">
							<label for="description" class="form-label"
								>{$_('page.discharge.overview.description')}</label
							>
							<textarea class="form-control" name="description" rows="2"></textarea>
						</div>

						<div class="mb-3">
							<label for="easting" class="form-label"
								>{$_('page.discharge.overview.pourpoint')}</label
							>
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

						<button type="submit" class="btn btn-primary">{$_('page.general.save')}</button>
					</form>
				</div>
				<!-- end col -->
				<div class="col-lg-9">
					<div class="py-2">
						{$_('page.discharge.overview.pourpoint')}
						<span class="text-muted">({$_('page.discharge.overview.changePoutPoint')})</span>
					</div>
					<div class="d-flex flex-grow-1" style="height:700px;" id="map"></div>
				</div>
			</div>
			<!-- end row-->
		</div>
	</div>
</div>
