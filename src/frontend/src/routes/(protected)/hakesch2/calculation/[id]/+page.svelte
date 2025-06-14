<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';

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
	$pageTitle = 'HAKESCH 2.0 - Projekt ' + data.project.title;

	let northing = $derived(data.project.Point.northing);
	let easting = $derived(data.project.Point.easting);

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	let returnPeriod = $state([
		{
			id: 2.3,
			text: `2.3`
		},
		{
			id: 20,
			text: `20`
		},
		{
			id: 100,
			text: `100`
		}
	]);

		let returnPeriodx = $state([
		{
			id: 0,
			text: `2.3`
		},
		{
			id: 1,
			text: `20`
		},
		{
			id: 2,
			text: `100`
		}
	]);
	onMount(async () => {
	});
</script>

<svelte:head>
	<title>{$pageTitle} - Berechnungen | AUGUR</title>
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
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<div class="col-lg-8">
					<div class="accordion" id="accordionPanelsStayOpenExample">
						<div class="accordion-item">
							<h2 class="accordion-header" id="panelsStayOpen-headingOne">
								<button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#panelsStayOpen-collapseOne" aria-expanded="true" aria-controls="panelsStayOpen-collapseOne">
									Allgemeine Angaben
								</button>
							</h2>
							<div id="panelsStayOpen-collapseOne" class="accordion-collapse collapse show" aria-labelledby="panelsStayOpen-headingOne" style="">
								<div class="accordion-body">
									<form
						method="post"  action="?/updatefnp"
						use:enhance={() => {
							return async ({ update }) => {
								await update();
								currentProject.title = data.project.title;
							};
						}}
					>				<input type="hidden" name="id" value={data.project.id} />
									<input type="hidden" name="idf_id" value={data.project.IDF_Parameters?.id} />
									<h4 class="text-muted">Angaben zur Berechnung der Niederschlags-Intensität</h4>
									<div class="row g-2 py-2 align-items-end">
                                        <div class="mb-3 col-md-4">
                                            <label for="P_low_1h" class="form-label">Precipitation [mm] for lower return period, 1 hour duration</label>
                                            <input type="number" class="form-control" name="P_low_1h" id="P_low_1h" value={Number(data.project.IDF_Parameters?.P_low_1h)}>
                                        </div>
                                        <div class="mb-3 col-md-4">
                                            <label for="P_low_24h" class="form-label">Precipitation [mm] for lower return period, 24 hour duration</label>
                                            <input type="number" class="form-control" id="P_low_24h" name="P_low_24h" value={Number(data.project.IDF_Parameters?.P_low_24h)}>
                                        </div>
										<div class="mb-3 col-md-4">
                                            <label for="rp_low" class="form-label">Lower return period</label>
                                            <select id="rp_low" name="rp_low" class="form-select"
												value={(data.project.IDF_Parameters?.rp_low)}
											>
												{#each returnPeriod as rp}
													<option value={rp.id}>
														{rp.text}
													</option>
												{/each}
											</select>
                                        </div>
                                    </div>
									<div class="row g-2 align-items-end">
                                        <div class="mb-3 col-md-4">
                                            <label for="P_high_1h" class="form-label">Precipitation [mm] for upper return period, 1 hour duration</label>
                                            <input type="number" class="form-control" id="P_high_1h" name="P_high_1h" value={Number(data.project.IDF_Parameters?.P_high_1h)}>
                                        </div>
                                        <div class="mb-3 col-md-4">
                                            <label for="P_high_24h" class="form-label">Precipitation [mm] for upper return period, 24 hour duration</label>
                                            <input type="number" class="form-control" id="P_high_24h" name="P_high_24h" value={Number(data.project.IDF_Parameters?.P_high_24h)}>
                                        </div>
										<div class="mb-3 col-md-4">
                                            <label for="rp_high" class="form-label">Upper return period</label>

											<select id="rp_high" name="rp_high" class="form-select"
												value={(data.project.IDF_Parameters?.rp_high)}
											>
												{#each returnPeriod as rp}
													<option value={rp.id}>
														{rp.text}
													</option>
												{/each}
											</select>
                                        </div>
                                    </div>
									<button type="submit" class="btn btn-primary">Save</button>
									</form>
								</div>
							</div>
						</div>
						<div class="accordion-item">
							<h1 class="accordion-header" id="panelsStayOpen-headingTwo">
								<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#panelsStayOpen-collapseTwo" aria-expanded="true" aria-controls="panelsStayOpen-collapseTwo">
									Modifiziertes Fliesszeitverfahren
								</button>
							</h1>
							<div id="panelsStayOpen-collapseTwo" class="collapse" aria-labelledby="panelsStayOpen-headingTwo" style="">
								<div class="accordion-body">
									<form
						method="post"  action="?/updatemfzv"
						use:enhance={() => {
							return async ({ update }) => {
								await update();
							};
						}}
					>				<input type="hidden" name="id" value={data.project.id} />
									<input type="hidden" name="mfzv_id" value={data.project.Mod_Fliesszeit?.id} />
									<div class="row g-2 py-2 align-items-end">
                                        <div class="mb-3 col-md-4">
                                            <label for="P_low_1h" class="form-label">Return period</label>
                                            <select id="x" name="x" class="form-select"
												value={(data.project.Mod_Fliesszeit.Annuality.number)}
											>
												{#each returnPeriod as rp}
													<option value={rp.id}>
														{rp.text}
													</option>
												{/each}
											</select>
                                        </div>
                                        <div class="mb-3 col-md-4">
                                            <label for="P_low_24h" class="form-label">Wetting volume for 20-year event [mm]</label>
                                            <input type="number" class="form-control" id="Vo20" name="Vo20" value={Number(data.project.Mod_Fliesszeit?.Vo20)}>
                                        </div>
										<div class="mb-3 col-md-4">
                                            <label for="P_low_24h" class="form-label">Peak flow coefficient [-]</label>
                                            <input type="number" class="form-control" id="psi" name="psi" value={Number(data.project.Mod_Fliesszeit?.psi)}>
                                        </div>
                                    </div>
									<button type="submit" class="btn btn-primary">Save</button>
									<button type="submit" class="btn btn-primary">Save And calculate</button>
									</form>
								</div>
							</div>
						</div>
						<div class="accordion-item">
							<h2 class="accordion-header" id="panelsStayOpen-headingThree">
								<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#panelsStayOpen-collapseThree" aria-expanded="false" aria-controls="panelsStayOpen-collapseThree">
									Kölla
								</button>
							</h2>
							<div id="panelsStayOpen-collapseThree" class="accordion-collapse collapse" aria-labelledby="panelsStayOpen-headingThree" style="">
								<div class="accordion-body">
									Noch nicht implementiert
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="col-lg-4">
					<div class="accordion" id="accordionPanelsResults">
						<div class="accordion-item">
							<h2 class="accordion-header" id="panelsResults-headingOne">
								<button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#panelsResults-collapseOne" aria-expanded="true" aria-controls="panelsResults-collapseOne">
									Resultate
								</button>
							</h2>
							<div id="panelsResults-collapseOne" class="accordion-collapse collapse show" aria-labelledby="panelsResults-headingOne" style="">
								<div class="accordion-body">
									
									<h4 class="text-muted">Modifiziertes Fliesszeitverfahren</h4>
								</div>
							</div>
						</div>
					</div>

				</div>
			</div>
		</div>
	</div>
</div>
