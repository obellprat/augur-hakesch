<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount, onDestroy } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';

	import GeoJSON from 'ol/format/GeoJSON.js';
	import { Map, View, Feature } from 'ol';
	import { Tile as TileLayer, Vector as VectorLayer } from 'ol/layer';
	import WebGLTileLayer from 'ol/layer/WebGLTile';
	import { Point } from 'ol/geom';
	import { Vector as VectorSource, GeoTIFF } from 'ol/source';
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

	import { env } from '$env/dynamic/public';
	import { _ } from 'svelte-i18n';

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = $_('page.discharge.overview.discharge-projekt') + ': ' + data.project.title;

	let northing = $derived(data.project.Point.northing);
	let easting = $derived(data.project.Point.easting);

	let title = $derived(data.project.title);
	let description = $derived(data.project.description);
	let geojson = $derived(data.project.catchment_geojson);
	let branches_geojson = $derived(data.project.branches_geojson);

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	let map: Map;
	const API_ERROR_KEY = 'page.discharge.overview.apiUnavailable';
	function getApiErrorFallback() {
		return $_(API_ERROR_KEY);
	}
	let apiErrorMessage = $state(getApiErrorFallback());
	$effect(() => {
		apiErrorMessage = getApiErrorFallback();
	});

	// Track if component is mounted to prevent invalidateAll() calls after destruction
	let isMounted = $state(true);
	let statusCheckTimeout: ReturnType<typeof setTimeout> | null = null;

	// Safe wrapper for invalidateAll that checks if component is still mounted
	async function safeInvalidateAll() {
		if (!isMounted) return;
		try {
			// invalidateAll() returns a Promise and needs to be awaited
			await invalidateAll();
		} catch (error) {
			// If invalidateAll fails (e.g., context lost or component destroyed), just log it
			// Don't try to navigate as that can cause more issues
			if (isMounted) {
				console.debug('invalidateAll failed (component may be destroyed):', error);
			}
		}
	}

	async function calculateGeodatas() {
		try {
			await fetch('?/update', {
				body: new FormData(document.getElementById('project-form') as HTMLFormElement),
				method: 'post'
			});
			await safeInvalidateAll();
			const response = await fetch(
				env.PUBLIC_HAKESCH_API_PATH +
					'/discharge/prepare_discharge_hydroparameters?ProjectId=' +
					data.project.id,
				{
					method: 'GET',
					headers: {
						Authorization: 'Bearer ' + data.session.access_token
					}
				}
			);
			if (!response.ok) {
				throw new Error(`API returned status ${response.status}`);
			}
			const payload = await response.json();
			if (!payload?.task_id) {
				throw new Error($_('page.discharge.overview.api-without-task_id'));
			}
			const actTime = new Date();
			const progressTextEl = document.getElementById('progresstext');
			if (progressTextEl) {
				progressTextEl.innerHTML = `${actTime.toUTCString()} Starting`;
			}
			const jq = (globalThis as any).$;
			if (jq) {
				jq('.progress-bar').css('width', '0%').attr('aria-valuenow', 0);
			}
			getStatus(payload.task_id);
		} catch (error) {
			console.error('calculateGeodatas failed', error);
			const detail = error instanceof Error ? error.message : '';
			showApiErrorModal(detail);
		}
	}

	function showApiErrorModal(detail?: string) {
		const fallback = getApiErrorFallback();
		apiErrorMessage = detail ? `${fallback} (${detail})` : fallback;
		const jq = (globalThis as any).$;
		if (jq) {
			jq('#generate-modal').modal('hide');
			jq('#api-error-modal').modal('show');
		}
	}
	function getStatus(taskID: String) {
		if (!isMounted) return;
		
		fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/${taskID}`, {
			method: 'GET',
			headers: {
				Authorization: 'Bearer ' + data.session.access_token,
				'Content-Type': 'application/json'
			}
		})
			.then((response) => response.json())
			.then((res) => {
				if (!isMounted) return;
				
				// write out the state
				const actTime = new Date();
				try {
					let obj = JSON.parse(res.task_result);
					//let html = `${actTime.toUTCString()} ${res.task_status} `;
					let html = ``;
					if (
						res.task_status != 'SUCCESS' &&
						res.task_status != 'PENDING' &&
						res.task_status != 'FAILURE'
					) {
						html = `${JSON.stringify(obj.text)}`;

						const jq = (globalThis as any).$;
						if (jq) {
							jq('.progress-bar')
								.css('width', obj.progress + '%')
								.attr('aria-valuenow', obj.progress);
						}
					} else if (res.task_status == 'PENDING') {
						html = $_('page.discharge.overview.recalculating');
					} else if (res.task_status == 'FAILURE') {
						html =
							$_('page.discharge.overview.errorrecalculating') +
							'Fehler: ' +
							obj.text;
					} else if (res.task_status == 'SUCCESS') {
						html = $_('page.discharge.overview.geodatasuccess');

						const jq = (globalThis as any).$;
						if (jq) {
							jq('#generate-modal').modal('hide');
						}
						// Call safeInvalidateAll without await to avoid blocking, errors are handled internally
						safeInvalidateAll().catch(() => {
							// Errors are already handled in safeInvalidateAll
						});
						if (isMounted) {
							addIsozones();
							addBranches();
						}
					}
					if (isMounted) {
						const progressTextEl = document.getElementById('progresstext');
						if (progressTextEl) {
							progressTextEl.innerHTML = html;
						}
					}
				} catch (e) {
					console.log(e);
				}
				const taskStatus = res.task_status;
				if (taskStatus === 'SUCCESS') {
				}
				if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
					return false;
				}

				if (isMounted) {
					statusCheckTimeout = setTimeout(function () {
						getStatus(taskID);
					}, 1000);
				}
			})
			.catch((err) => console.log(err));
	}

	function addCatchment() {
		if (!geojson || !map) return;
		
		try {
			const catchmentSource = new VectorSource({
				features: new GeoJSON().readFeatures(geojson, {
					dataProjection: 'EPSG:2056',
					featureProjection: map.getView().getProjection()
				})
			});

			const catchmentLayer = new VectorLayer({
				source: catchmentSource,
				name: 'catchment',
				style: new Style({
					stroke: new Stroke({
						color: 'orange',
						lineDash: [4],
						width: 3
					}),
					fill: new Fill({
						color: 'rgba(0, 0, 255, 0.1)'
					})
				})
			});

			map.getLayers().forEach((layer) => {
				if (layer && layer.get('name') && layer.get('name') == 'catchment') {
					map.removeLayer(layer);
				}
			});

			map.addLayer(catchmentLayer);
		} catch (error) {
			// GeoJSON might be empty or invalid, just log and continue
			console.debug('Failed to add catchment layer:', error);
		}
	}

	function addBranches() {
		if (!branches_geojson || !map) return;
		
		try {
			const branchesSource = new VectorSource({
				features: new GeoJSON().readFeatures(branches_geojson, {
					dataProjection: 'EPSG:2056',
					featureProjection: map.getView().getProjection()
				})
			});

			const branchesLayer = new VectorLayer({
				source: branchesSource,
				name: 'branches',
				style: new Style({
					stroke: new Stroke({
						color: 'blue',
						width: 3
					}),
					fill: new Fill({
						color: 'rgba(0, 0, 255, 0.1)'
					})
				})
			});

			map.getLayers().forEach((layer) => {
				if (layer && layer.get('name') && layer.get('name') == 'branches') {
					map.removeLayer(layer);
				}
			});

			map.addLayer(branchesLayer);
		} catch (error) {
			// GeoJSON might be empty or invalid, just log and continue
			console.debug('Failed to add branches layer:', error);
		}
	}

	function addIsozones() {
		if (!map) return;
		
		// Only load isozones if they exist (not empty taskid and not currently running)
		// This prevents trying to load the file when it doesn't exist yet
		if (!data.project.isozones_taskid || data.project.isozones_taskid === '' || data.project.isozones_running) {
			// Remove existing isozone layer if it exists
			map.getLayers().forEach((layer) => {
				if (layer && layer.get('name') && layer.get('name') == 'isozone') {
					map.removeLayer(layer);
				}
			});
			return;
		}
		
		// Set up a temporary unhandled rejection handler to suppress GeoTIFF errors
		// The GeoTIFF source may fail to load if the file doesn't exist, which is expected
		let rejectionHandler: ((event: PromiseRejectionEvent) => void) | null = null;
		
		try {
			// Create a handler that suppresses errors related to isozones_cog.tif
			rejectionHandler = (event: PromiseRejectionEvent) => {
				const reason = event.reason;
				// Check if this is a GeoTIFF AggregateError related to isozones
				if (reason?.name === 'AggregateError' || 
				    (reason?.errors && Array.isArray(reason.errors))) {
					const errorString = JSON.stringify(reason);
					if (errorString.includes('isozones_cog.tif') || 
					    errorString.includes('Request failed')) {
						// Suppress this error - file doesn't exist yet, which is expected
						event.preventDefault();
						return;
					}
				}
			};
			
			// Add the handler temporarily
			window.addEventListener('unhandledrejection', rejectionHandler);
			
			const isozone_source = new GeoTIFF({
				sources: [
					{
						url:
							env.PUBLIC_HAKESCH_API_PATH +
							'/data/' +
							data.session.myuser.id +
							'/' +
							data.project.id +
							'/isozones_cog.tif?rndstr=' +
							Date.now()
					}
				],
				normalize: false
			});

			// Suppress async errors from GeoTIFF source (e.g., 404 when file doesn't exist)
			isozone_source.on('tileloaderror', () => {
				// Silently handle tile load errors
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
			
			// Suppress errors on the layer
			isozone.on('error', () => {
				// Silently handle layer errors (file might not exist yet)
			});
			
			isozone.set('name', 'isozone');

			map.getLayers().forEach((layer) => {
				if (layer && layer.get('name') && layer.get('name') == 'isozone') {
					map.removeLayer(layer);
				}
			});

			map.addLayer(isozone);
			
			// Remove the rejection handler after a delay to allow async errors to be caught
			setTimeout(() => {
				if (rejectionHandler) {
					window.removeEventListener('unhandledrejection', rejectionHandler);
				}
			}, 2000);
		} catch (error) {
			// Remove the rejection handler immediately on error
			if (rejectionHandler) {
				window.removeEventListener('unhandledrejection', rejectionHandler);
			}
			// GeoTIFF might not exist yet or failed to load, just log and continue
			console.debug('Failed to add isozones layer (file may not exist yet):', error);
		}
	}

	async function downloadFile(url: string, filename: string) {
		try {
			const response = await fetch(url, {
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				}
			});
			if (!response.ok) {
				throw new Error($_('page.discharge.overview.download-failed'));
			}
			const blob = await response.blob();
			const link = document.createElement('a');
			link.href = URL.createObjectURL(blob);
			link.download = filename;
			document.body.appendChild(link);
			link.click();
			link.remove();
			URL.revokeObjectURL(link.href);
		} catch (e) {
			console.error(e);
		}
	}

	function downloadIsozones() {
		return downloadFile(
			`${env.PUBLIC_HAKESCH_API_PATH}/file/isozones/${data.project.id}`,
			`isozones_${data.project.id}.tif`
		);
	}

	function downloadCatchment() {
		return downloadFile(
			`${env.PUBLIC_HAKESCH_API_PATH}/file/catchment/${data.project.id}`,
			`catchment_${data.project.id}.geojson`
		);
	}

	function downloadBranches() {
		return downloadFile(
			`${env.PUBLIC_HAKESCH_API_PATH}/file/branches/${data.project.id}`,
			`branches_${data.project.id}.geojson`
		);
	}

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
		//addCatchment();

		$effect(() => {
			addIsozones();
			addCatchment();
			addBranches();
		});

		map.on('singleclick', function (e) {
			northing = Math.round(e.coordinate[1]);
			easting = Math.round(e.coordinate[0]);
			addMarker([easting, northing]);

			globalThis.$('#recalculate-modal').modal('show');
		});

		if (!data.project.isozones_taskid || data.project.isozones_taskid === '') {
			const jq = (globalThis as any).$;
			if (jq) {
				jq('#missinggeodata-modal').modal('show');
			}
		}
	});

	onDestroy(() => {
		isMounted = false;
		if (statusCheckTimeout) {
			clearTimeout(statusCheckTimeout);
			statusCheckTimeout = null;
		}
	});
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="flex-grow-1 card">
	<form
		id="project-form"
		method="post"
		action="?/update"
		use:enhance={() => {
			return async ({ update }) => {
				await update();
				currentProject.title = data.project.title;
				await safeInvalidateAll();
			};
		}}
	>
		<div class="h-100">
			<div class="card-header py-2 px-3 border-bottom">
				<div class="d-flex align-items-center justify-content-between py-1">
					<div class="d-flex align-items-center gap-2">
						<h3 class="my-0 lh-base">
							{data.project.title}
						</h3>
					</div>
					<!-- Modals -->
					<div
						id="generate-modal"
						class="modal fade"
						tabindex="-1"
						role="dialog"
						aria-labelledby="standard-modalLabel"
						aria-hidden="true"
					>
						<div class="modal-dialog">
							<div class="modal-content">
								<div class="modal-header">
									<h4 class="modal-title" id="standard-modalLabel">{$_('page.discharge.overview.calculation')}</h4>
									<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="$_('page.general.close')"
									></button>
								</div>
								<div class="modal-body">
									<h5>
										{$_('page.discharge.overview.recalculationDialogText')}
									</h5>
									<hr />
									<p class="text-muted" id="progresstext"></p>
									<div class="progress mb-2">
										<div
											class="progress-bar"
											role="progressbar"
											style="width: 25%"
											aria-valuenow="0"
											aria-valuemin="0"
											aria-valuemax="100"
										></div>
									</div>
								</div>
								<div class="modal-footer">
									<button type="button" class="btn btn-light" data-bs-dismiss="modal"
										>{$_('page.discharge.overview.background-calculation')}</button
									>
								</div>
							</div>
							<!-- /.modal-content -->
						</div>
						<!-- /.modal-dialog -->
					</div>

					<div
						id="recalculate-modal"
						class="modal fade"
						tabindex="-1"
						role="dialog"
						aria-labelledby="standard-modalLabel"
						aria-hidden="true"
					>
						<div class="modal-dialog">
							<div class="modal-content">
								<div class="modal-header">
									<h4 class="modal-title" id="standard-modalLabel">
										{$_('page.discharge.overview.shouldgeodatabecalculated')}
									</h4>
									<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label={$_('page.general.close')}
									></button>
								</div>
								<div class="modal-body">
									<h5>
										{$_('page.discharge.overview.shouldrecalcbecausenewpoint')}
									</h5>
									<hr />
								</div>
								<div class="modal-footer">
									<button
										type="button"
										class="btn btn-primary"
										data-bs-dismiss="modal"
										data-bs-toggle="modal"
										data-bs-target="#generate-modal"
										onclick={calculateGeodatas}>{$_('page.general.yes')}</button
									><button type="button" class="btn btn-light" data-bs-dismiss="modal">{$_('page.general.no')}</button>
								</div>
							</div>
							<!-- /.modal-content -->
						</div>
						<!-- /.modal-dialog -->
					</div>

					<div
						id="missinggeodata-modal"
						class="modal fade"
						tabindex="-1"
						role="dialog"
						aria-labelledby="missinggeodata-modal-label"
						aria-hidden="true"
					>
						<div class="modal-dialog">
							<div class="modal-content">
								<div class="modal-header">
									<h4 class="modal-title" id="missinggeodata-modal-label">
										{$_('page.discharge.overview.missinggeodataTitle')}
									</h4>
									<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label={$_('page.general.close')}
									></button>
								</div>
								<div class="modal-body">
									<p>{$_('page.discharge.overview.missingGeodata')}</p>
								</div>
								<div class="modal-footer">
									<button type="button" class="btn btn-light" data-bs-dismiss="modal">{$_('page.general.cancel')}</button>
									<button
										type="button"
										class="btn btn-primary"
										data-bs-dismiss="modal"
										data-bs-toggle="modal"
										data-bs-target="#generate-modal"
										onclick={calculateGeodatas}
									>
										{$_('page.discharge.overview.calculateGeodata')}
									</button>
								</div>
							</div>
							<!-- /.modal-content -->
						</div>
						<!-- /.modal-dialog -->
					</div>

					<div
						id="api-error-modal"
						class="modal fade"
						tabindex="-1"
						role="dialog"
						aria-labelledby="api-error-modal-label"
						aria-hidden="true"
					>
						<div class="modal-dialog modal-dialog-centered">
							<div class="modal-content">
								<div class="modal-header text-bg-danger border-0">
									<h4 class="modal-title" id="api-error-modal-label">{$_('page.general.connectionerror')}</h4>
									<button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="${'page.general.close'}"
									></button>
								</div>
								<div class="modal-body">
									<p>{apiErrorMessage}</p>
								</div>
								<div class="modal-footer border-0">
									<button type="button" class="btn btn-danger" data-bs-dismiss="modal">{$_('page.general.close')}</button>
								</div>
							</div>
						</div>
					</div>

					<!-- End Modals -->
					<!-- Dropdown -->
					<div class="dropdown align-items-center d-flex d-xl-none">
						<a
							class="dropdown-toggle drop-arrow-none px-2"
							data-bs-toggle="dropdown"
							data-bs-offset="0,10"
							type="button"
							aria-haspopup="false"
							aria-expanded="false"
							aria-label="Tools"
							title="Tools"
						>
							<span class="pt-2 align-middle"> <i class="ri-arrow-down-s-line ms-1 fs-2"></i></span>
						</a>

						<div class="dropdown-menu dropdown-menu-end">
							<!-- item-->

							<button
								type="button"
								onclick={calculateGeodatas}
								class="dropdown-item"
								data-bs-toggle="modal"
								data-bs-target="#generate-modal"
								title={$_('page.discharge.overview.calculateGeodata')}
								aria-label={$_('page.discharge.overview.calculateGeodata')}
							>
								<i class="ti ti-restore me-1 fs-24 align-middle"></i>
								<span class="align-middle">{$_('page.discharge.overview.calculateGeodata')}</span>
							</button>

							<button
								type="submit"
								class="dropdown-item"
								title={$_('page.general.save')}
								aria-label={$_('page.general.save')}
							>
								<i class="ti ti-device-floppy me-1 fs-24 align-middle"></i>
								<span class="align-middle">{$_('page.general.save')}</span>
							</button>
							<button
								type="button"
								class="dropdown-item"
								data-bs-toggle="modal"
								data-bs-target="#delete-project-modal"
								title={$_('page.general.delete')}
								aria-label={$_('page.general.delete')}
							>
								<i class="ti ti-trash me-1 fs-24 align-middle"></i>
								<span class="align-middle">{$_('page.general.delete')}</span>
							</button>
							<button
								type="button"
								class="dropdown-item"
								data-bs-toggle="modal"
								data-bs-target="#delete-project-modal"
								title="$_('page.general.export')"
								aria-label="$_('page.general.export')"
							>
								<i class="ti ti-share me-1 fs-24 align-middle"></i>
								<span class="align-middle">{$_}</span>
							</button>
							<div class="dropdown-divider"></div>
							<a
								href="{base}/discharge/calculation/{data.project.id}"
								type="button"
								class="btn btn-primary bg-gradient rounded-pill align-middle mx-2 my-2 d-flex"
							>
								{$_('page.discharge.calculate')} <i class="ri-arrow-right-line"></i>
							</a>
						</div>
					</div>
					<!-- End dropdown -->

					<div class="d-none d-xl-flex align-items-center gap-2">
						<button
							type="button"
							onclick={calculateGeodatas}
							class="btn btn-sm btn-icon btn-ghost-primary d-flex"
							data-bs-toggle="modal"
							data-bs-target="#generate-modal"
							title={$_('page.discharge.overview.calculateGeodata')}
							aria-label={$_('page.discharge.overview.calculateGeodata')}
						>
							<i class="ti ti-restore fs-24"></i>
						</button>

						<button
							type="submit"
							class="btn btn-sm btn-icon btn-ghost-primary d-flex"
							title={$_('page.general.save')}
							aria-label={$_('page.general.save')}
						>
							<i class="ti ti-device-floppy fs-24"></i>
						</button>
						<span
							class="btn btn-sm btn-icon btn-ghost-danger d-flex"
							data-bs-placement="top"
							title={$_('page.general.delete')}
							aria-label={$_('page.general.delete')}
							data-bs-toggle="modal"
							data-bs-target="#delete-project-modal"
						>
							<i class="ti ti-trash fs-20"></i>
						</span>
						<a
							href="javascript: void(0);"
							class="btn btn-sm btn-icon btn-ghost-primary d-flex"
							data-bs-toggle="modal"
							data-bs-target="#userVideoCall"
							data-bs-placement="top"
							title="${'page.general.export'}"
							aria-label="${'page.general.export'}"
						>
							<i class="ti ti-share fs-20"></i>
						</a>
						|
						<a
							href="{base}/discharge/calculation/{data.project.id}"
							type="button"
							class="btn btn-primary bg-gradient rounded-pill d-none d-xl-flex"
						>
							{$_('page.discharge.calculate')} <i class="ri-arrow-right-line"></i>
						</a>

						<a
							href="{base}/discharge/calculation/{data.project.id}"
							type="button"
							class="btn btn-primary bg-gradient rounded-pill d-flex d-xl-none"
							title={$_('page.discharge.calculate')}
							aria-label={$_('page.discharge.calculate')}
						>
							<i class="ri-arrow-right-line"></i>
						</a>
					</div>
				</div>
			</div>
			<div class="card-body">
				<div class="row">
					<div class="col-lg-12">
						<input type="hidden" name="id" value={data.project.id} />
						<div class="mb-3">
							<label for="title" class="form-label"
								>{$_('page.discharge.overview.projectTitle')}</label
							>
							<input type="text" name="title" id="title" class="form-control" value={title} />
						</div>

						<div class="mb-3">
							<label for="description" class="form-label"
								>{$_('page.discharge.overview.description')}</label
							>
							<textarea class="form-control" name="description" rows="2">{description}</textarea>
						</div>
					</div>

					<div class="col-lg-12">
						<div class="py-2">
							{$_('page.discharge.overview.pourpoint')}: {northing} // {easting}
							<input
								type="hidden"
								name="easting"
								id="easting"
								class="form-control"
								value={easting}
							/>
							<input
								type="hidden"
								name="northing"
								id="northing"
								class="form-control"
								value={northing}
							/>
							<span class="text-muted">({$_('page.discharge.overview.changePoutPoint')})</span>
						</div>
						<div class="d-flex flex-grow-1" style="height:500px;" id="map"></div>
					</div>
					<div class="col-lg-12">
						<div class="card border-secondary border mt-3">
							<div class="card-body">
								<h3 class="card-title">{$_('page.discharge.geodata')}</h3>
								{#if data.project.isozones_taskid === ''}
									<p>{$_('page.discharge.overview.missingGeodata')}</p>
								{:else if data.project.isozones_running}
									<p>{$_('page.discharge.overview.isozonesRunning')}</p>
								{:else}
									<div class="table-responsive-sm">
										<table class="table table-striped mb-0">
											<thead>
												<tr>
													<th>{$_('page.discharge.overview.catchmentArea')} [km<sup>2</sup>]</th>
													<th>{$_('page.discharge.overview.maxFlowLength')} [m]</th>
													<th>{$_('page.discharge.overview.cumulativeFlowLength')} [m]</th>
													<th>{$_('page.discharge.overview.heightDifference')} [m]</th>
													<th>{$_('page.discharge.overview.isozones')}</th>
													<th>{$_('page.discharge.overview.catchmentArea')}</th>
													<th>{$_('page.discharge.overview.channel')}</th>
												</tr>
											</thead>
											<tbody>
												<tr>
													<td>
														{Math.round(data.project.catchment_area*10)/10} km<sup>2</sup>
													</td>
													<td>{data.project.channel_length} m</td>
													<td>{Math.round(data.project.cummulative_channel_length)} m</td>
													<td>{Math.round(data.project.delta_h)} m</td>
													<td class="text-muted">
														<a
															href="javascript: void(0);"
															class="link-reset fs-20 p-1"
															onclick={downloadIsozones}
														>
															{$_('page.discharge.overview.download')}</a
														>
													</td>
													<td class="text-muted">
														<a
															href="javascript: void(0);"
															class="link-reset fs-20 p-1"
															onclick={downloadCatchment}
														>
															{$_('page.discharge.overview.download')}</a
														>
													</td>
													<td class="text-muted">
														<a
															href="javascript: void(0);"
															class="link-reset fs-20 p-1"
															onclick={downloadBranches}
														>
															{$_('page.discharge.overview.download')}</a
														>
													</td>
												</tr>
											</tbody>
										</table>
									</div>
								{/if}
							</div>
							<!-- end card-body-->
						</div>
					</div>
				</div>
				<!-- end row-->
			</div>
		</div>
	</form>
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
					<h4 class="modal-title" id="warning-header-modalLabel">
						{$_('page.discharge.overview.deleteProject')}
					</h4>
					<button
						type="button"
						class="btn-close btn-close-white"
						data-bs-dismiss="modal"
						aria-label="${'page.general.close'}"
					></button>
				</div>
				<div class="modal-body">
					<p>
						{$_('page.discharge.overview.shoulddeleteproject', {
							values: { title: data.project.title }
						})}
					</p>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-light" data-bs-dismiss="modal"
						>{$_('page.general.cancel')}</button
					>
					<form method="POST" action="?/delete">
						<input type="hidden" name="id" value={data.project.id} />
						<input type="hidden" name="userid" value={data.session?.myuser.id} />
						<button type="submit" class="btn btn-warning">{$_('page.general.delete')}</button>
					</form>
				</div>
			</div>
			<!-- /.modal-content -->
		</div>
		<!-- /.modal-dialog -->
	</div>
	<!-- /.modal -->
</div>
