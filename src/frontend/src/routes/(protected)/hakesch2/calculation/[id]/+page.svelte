<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';

	import { env } from '$env/dynamic/public';	

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HAKESCH 2.0 - Projekt ' + data.project.title;

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

	let calulcationType = $state(0);
	let mod_verfahren = $derived(data.project.Mod_Fliesszeit);
	
	function addCalculation() {
		if (calulcationType==1) {
			// add modifiziertes Fliesszeitverfahren
			const mod_fliesszeit = {
				id: 0
			}
			mod_verfahren.push(mod_fliesszeit);
		}
	}
	
	function calculateModFliess(mod_fliesszeit_id: Number) {
		fetch(
				env.PUBLIC_HAKESCH_API_PATH +
					'/hakesch/modifizierte_fliesszeit?ProjectId='+ data.project.id+'&ModFliesszeitId='+mod_fliesszeit_id,
				{
					method: 'GET',
					headers: {
						'Authorization': 'Bearer ' + data.session.access_token,
					},
				}
			)
				.then((response) => response.json())
				.then((data) => {
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
				const taskStatus = res.task_status;
				if (taskStatus === 'SUCCESS') {
					invalidateAll();
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

	onMount(async () => {
		mod_verfahren = data.project.Mod_Fliesszeit;
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
				<div class="ms-auto d-xl-flex">
					<button type="button"
						class="btn btn-primary bg-gradient rounded-pill" data-bs-toggle="modal" data-bs-target="#generate-modal">Hydrologische Berechnung hinzufügen</button
					>
					
					<div id="generate-modal" class="modal fade" tabindex="-1" role="dialog" aria-labelledby="standard-modalLabel" aria-hidden="true">
						<div class="modal-dialog">
							<div class="modal-content">
								<div class="modal-header">
									<h4 class="modal-title" id="standard-modalLabel">Hydrologische Berechnung hinzufügen</h4>
									<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
								</div>
								<div class="modal-body">
									<h5>Welches Verfahren soll dem Projekt hinzugefügt weden?</h5>
									<hr>
									<select id="calculation_type" class="form-select"
												bind:value={calulcationType}
											>
											<option value="1">Modifiziertes Fliesszeitverfahren</option>
											<option value="2">Kölla</option>
											<option value="3">Clark-WSL</option>
									</select>
								</div>
								<div class="modal-footer">
									<button type="button" class="btn btn-light" data-bs-dismiss="modal" onclick={addCalculation}>Hinzufügen</button>
								</div>
							</div><!-- /.modal-content -->
						</div><!-- /.modal-dialog -->
					</div>

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
						
						{#each mod_verfahren as mod_fz}


						<div class="accordion-item">
							<h1 class="accordion-header" id="panelsStayOpen-modFZ{mod_fz.id}">
								<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#panelsStayOpen-collapsemodFZ{mod_fz.id}" aria-expanded="true" aria-controls="panelsStayOpen-collapsemodFZ{mod_fz.id}">
									Modifiziertes Fliesszeitverfahren 
									{#if mod_fz.Annuality}
										({mod_fz.Annuality.description})
									{/if}
								</button>
							</h1>
							<div id="panelsStayOpen-collapsemodFZ{mod_fz.id}" class="collapse" aria-labelledby="panelsStayOpen-modFZ{mod_fz.id}" style="">
								<div class="accordion-body">
									<form
						method="post"  action="?/updatemfzv"
					>				<input type="hidden" name="id" value={data.project.id} />
									<input type="hidden" name="mfzv_id" value={mod_fz.id} />
									<div class="row g-2 py-2 align-items-end">
                                        <div class="mb-3 col-md-4">
                                            <label for="P_low_1h" class="form-label">Return period</label>
                                            <select id="x" name="x" class="form-select"
												value={(mod_fz.Annuality?.number)}
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
                                            <input type="number" class="form-control" id="Vo20" name="Vo20" value={Number(mod_fz.Vo20)}>
                                        </div>
										<div class="mb-3 col-md-4">
                                            <label for="P_low_24h" class="form-label">Peak flow coefficient [-]</label>
                                            <input type="number" step="0.01"  class="form-control" id="psi" name="psi" value={Number(mod_fz.psi)}>
                                        </div>
                                    </div>
									<button type="submit" class="btn btn-primary">Save</button>
									<button type="button" class="btn btn-primary" onclick={() => calculateModFliess(mod_fz.id)}>Calculate</button>
									</form>
								</div>
							</div>
						</div>
						{/each}
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
									{#each mod_verfahren as mod_fz}
									<h4 class="text-muted">Modifiziertes Fliesszeitverfahren {#if mod_fz.Annuality}
										({mod_fz.Annuality.description})
									{/if}</h4>
									<p>Hq: {mod_fz.Mod_Fliesszeit_Result?.HQ.toFixed(2)}</p>
									{/each}
								</div>
							</div>
						</div>
					</div>

				</div>
			</div>
		</div>
	</div>
</div>
