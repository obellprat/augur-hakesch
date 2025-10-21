<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { toast } from '@zerodevx/svelte-toast';
	import { _ } from 'svelte-i18n';
	import type ApexCharts from 'apexcharts';
	import type { ApexOptions } from 'apexcharts';

	import type { Action } from 'svelte/action';

	import { env } from '$env/dynamic/public';
	//import Apexchart from '$lib/apexchart.svelte';

	type Chart = {
		options: ApexOptions;
		node?: HTMLDivElement;
		ref?: ApexCharts;
	};

	function getPctForZone(zone: string, clarkwsl: any) {
		if (clarkwsl.Fractions === undefined || clarkwsl.Fractions.length === 0) {
			return 0;
		}
		const found = clarkwsl.Fractions.find(
			(f: { ZoneParameterTyp: string }) => f.ZoneParameterTyp === zone
		);
		return found ? found.pct : 0;
	}

	const renderChart: Action<HTMLDivElement, Chart> = (node, parameter) => {
		import('apexcharts')
			.then((module) => module.default)
			.then((ApexCharts) => {
				const chart = new ApexCharts(node, parameter.options);
				parameter.node = node;
				parameter.ref = chart;
				chart.render();
			});
		return {
			destroy: () => {
				parameter.ref?.destroy();
			}
		};
	};

	const chartOneOptions: any = {
		series: [
			{
				name: 'Clark-WSL',
				data: [2.3, 2.5, 2.8],
				color: '#13e4ef'
			}
		],
		chart: {
			type: 'bar',
			height: 350
		},
		plotOptions: {
			bar: {
				horizontal: false,
				columnWidth: '70%',
				borderRadius: 5,
				borderRadiusApplication: 'end'
			}
		},
		dataLabels: {
			enabled: false
		},
		stroke: {
			show: true,
			width: 2,
			colors: ['transparent']
		},
		xaxis: {
			categories: ['2.3', '20', '100']
		},
		yaxis: {
			title: {
				text: 'HQ [m3/s]'
			}
		},
		fill: {
			opacity: 1
		},
		tooltip: {
			y: {
				formatter: function (val) {
					return '$ ' + val + '  m3/s';
				}
			}
		}
	};

	const chart: Chart = {
		options: chartOneOptions
	};

	let { data, form }: { data: PageServerData & { session: any }; form: ActionData } = $props();
	$pageTitle = $_('page.discharge.overview.discharge-projekt') + ' ' + data.project.title;

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;
	let zones = data.zones;

	let isGeneralSaving = $state(false);
	let isMFZSaving = $state(false);
	let isKoellaSaving = $state(false);
	let isClarkWSLSaving = $state(false);
	let isNAMSaving = $state(false);
	let isUploading = $state(false);
	let couldCalculate = $state(false);
	let soilFileExists = $state(false);
	let useOwnSoilData = $state(false);
	let isCheckingSoilFile = $state(false);

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
	let mod_verfahren = $state(data.project.Mod_Fliesszeit);
	let koella = $state(data.project.Koella);
	let clark_wsl = $state(data.project.ClarkWSL);
	let nam = $state(data.project.NAM);
	//k.Koella_Result?.HQ.toFixed(2)

	function showResults() {
		let mod_fliesszeit_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Mod. Fliesszeitverfahren',
			color: '#1376ef',
			data: []
		};
		mod_fliesszeit_data.data.push(
			mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 2.3)
				?.Mod_Fliesszeit_Result?.HQ
				? Number(
						mod_verfahren
							.find((mf) => mf.Annuality?.number == 2.3)
							.Mod_Fliesszeit_Result.HQ.toFixed(2)
					)
				: null
		);
		mod_fliesszeit_data.data.push(
			mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 20)
				?.Mod_Fliesszeit_Result?.HQ
				? Number(
						mod_verfahren
							.find((mf) => mf.Annuality?.number == 20)
							.Mod_Fliesszeit_Result.HQ.toFixed(2)
					)
				: null
		);
		mod_fliesszeit_data.data.push(
			mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 100)
				?.Mod_Fliesszeit_Result?.HQ
				? Number(
						mod_verfahren
							.find((mf) => mf.Annuality?.number == 100)
							.Mod_Fliesszeit_Result.HQ.toFixed(2)
					)
				: null
		);
		let koella_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Kölla',
			color: '#1e13ef',
			data: []
		};
		koella_data.data.push(
			koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 2.3)
				?.Koella_Result?.HQ
				? Number(koella.find((k) => k.Annuality?.number == 2.3).Koella_Result.HQ.toFixed(2))
				: null
		);
		koella_data.data.push(
			koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 20)
				?.Koella_Result?.HQ
				? Number(koella.find((k) => k.Annuality?.number == 20).Koella_Result.HQ.toFixed(2))
				: null
		);
		koella_data.data.push(
			koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 100)
				?.Koella_Result?.HQ
				? Number(koella.find((k) => k.Annuality?.number == 100).Koella_Result.HQ.toFixed(2))
				: null
		);
		let clark_wsl_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Clark WSL',
			color: '#13e4ef',
			data: []
		};
		clark_wsl_data.data.push(
			clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 2.3)
				?.ClarkWSL_Result?.Q
				? Number(clark_wsl.find((c) => c.Annuality?.number == 2.3).ClarkWSL_Result.Q.toFixed(2))
				: null
		);
		clark_wsl_data.data.push(
			clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 20)
				?.ClarkWSL_Result?.Q
				? Number(clark_wsl.find((c) => c.Annuality?.number == 20).ClarkWSL_Result.Q.toFixed(2))
				: null
		);
		clark_wsl_data.data.push(
			clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 100)
				?.ClarkWSL_Result?.Q
				? Number(clark_wsl.find((c) => c.Annuality?.number == 100).ClarkWSL_Result.Q.toFixed(2))
				: null
		);
		let nam_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'NAM',
			color: '#ef1313',
			data: []
		};
		nam_data.data.push(
			nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 2.3)
				?.NAM_Result?.HQ
				? Number(nam.find((n) => n.Annuality?.number == 2.3).NAM_Result.HQ.toFixed(2))
				: null
		);
		nam_data.data.push(
			nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 20)
				?.NAM_Result?.HQ
				? Number(nam.find((n) => n.Annuality?.number == 20).NAM_Result.HQ.toFixed(2))
				: null
		);
		nam_data.data.push(
			nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 100)
				?.NAM_Result?.HQ
				? Number(nam.find((n) => n.Annuality?.number == 100).NAM_Result.HQ.toFixed(2))
				: null
		);
		chartOneOptions.series = [mod_fliesszeit_data, koella_data, clark_wsl_data, nam_data];
		chart.ref?.updateSeries(chartOneOptions.series);
	}
	$effect(() => {
		showResults();
	});

	// Update local state when data changes
	$effect(() => {
		mod_verfahren = data.project.Mod_Fliesszeit;
		koella = data.project.Koella;
		clark_wsl = data.project.ClarkWSL;
		nam = data.project.NAM;
	});

	function addCalculation() {
		if (calulcationType == 1) {
			// add modifiziertes Fliesszeitverfahren
			const mod_fliesszeit = {
				id: 0,
				project_id: data.project.id
			};
			mod_verfahren.push(mod_fliesszeit);
		} else if (calulcationType == 2) {
			// add Koella
			const newkoella = {
				id: 0,
				project_id: data.project.id
			};
			koella.push(newkoella);
		} else if (calulcationType == 3) {
			// add Clark WSL
			const newclark_wsl = {
				id: 0,
				project_id: data.project.id
			};
			clark_wsl.push(newclark_wsl);
		} else if (calulcationType == 4) {
			// add NAM
			const newnam = {
				id: 0,
				project_id: data.project.id,
				precipitation_factor: 0.7,
				readiness_to_drain: 1,
				water_balance_mode: 'cumulative',
				storm_center_mode: 'centroid',
				routing_method: 'time_values'
			};
			nam.push(newnam);
		}
	}

	function calculateModFliess(project_id: Number, mod_fliesszeit_id: Number) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		fetch(
			env.PUBLIC_HAKESCH_API_PATH +
				'/discharge/modifizierte_fliesszeit?ProjectId=' +
				project_id +
				'&ModFliesszeitId=' +
				mod_fliesszeit_id,
			{
				method: 'GET',
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				}
			}
		)
			.then((response) => response.json())
			.then((data) => {
				getStatus(data.task_id);
			});
	}
	function calculateKoella(project_id: Number, koella_id: Number) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		fetch(
			env.PUBLIC_HAKESCH_API_PATH +
				'/discharge/koella?ProjectId=' +
				project_id +
				'&KoellaId=' +
				koella_id,
			{
				method: 'GET',
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				}
			}
		)
			.then((response) => response.json())
			.then((data) => {
				getStatus(data.task_id);
			});
	}
	function calculateClarkWSL(project_id: Number, clark_wsl_id: Number) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		fetch(
			env.PUBLIC_HAKESCH_API_PATH +
				'/discharge/clark-wsl?ProjectId=' +
				project_id +
				'&ClarkWSLId=' +
				clark_wsl_id,
			{
				method: 'GET',
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				}
			}
		)
			.then((response) => response.json())
			.then((data) => {
				getStatus(data.task_id);
			});
	}
	function calculateNAM(project_id: Number, nam_id: Number) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		fetch(
			env.PUBLIC_HAKESCH_API_PATH +
				'/discharge/nam?ProjectId=' +
				project_id +
				'&NAMId=' +
				nam_id,
			{
				method: 'GET',
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				}
			}
		)
			.then((response) => response.json())
			.then((data) => {
				getStatus(data.task_id);
			});
	}

	async function checkSoilFileExists(project_id: Number) {
		isCheckingSoilFile = true;
		try {
			const response = await fetch(
				env.PUBLIC_HAKESCH_API_PATH + `/file/check-soil-shp/${project_id}`,
				{
					method: 'GET',
					headers: {
						Authorization: 'Bearer ' + data.session.access_token
					}
				}
			);
			
			if (response.ok) {
				const result = await response.json();
				soilFileExists = result.exists;
			} else {
				soilFileExists = false;
			}
		} catch (error) {
			console.error('Error checking soil file:', error);
			soilFileExists = false;
		} finally {
			isCheckingSoilFile = false;
		}
	}

	async function uploadZipFile(project_id: Number, file: File) {
		if (!file) return;
		
		isUploading = true;
		const formData = new FormData();
		formData.append('file', file);
		
		try {
			const response = await fetch(
				env.PUBLIC_HAKESCH_API_PATH + `/file/upload-zip/${project_id}`,
				{
					method: 'POST',
					headers: {
						Authorization: 'Bearer ' + data.session.access_token
					},
					body: formData
				}
			);
			
			if (response.ok) {
				toast.push($_('page.discharge.calculation.zipUploadSuccess'), {
					theme: {
						'--toastColor': 'mintcream',
						'--toastBackground': 'rgba(72,187,120,0.9)',
						'--toastBarBackground': '#2F855A'
					}
				});
				// Recheck if soil file exists after upload
				await checkSoilFileExists(project_id);
			} else {
				const errorData = await response.json();
				toast.push(
					'<h3 style="padding:5;">' +
						$_('page.discharge.calculation.zipUploadError') +
						'</h3>' +
						errorData.detail,
					{
						theme: {
							'--toastColor': 'white',
							'--toastBackground': 'darkred'
						},
						initial: 0
					}
				);
			}
		} catch (error) {
			toast.push(
				'<h3 style="padding:5;">' +
					$_('page.discharge.calculation.zipUploadError') +
					'</h3>' +
					(error instanceof Error ? error.message : String(error)),
				{
					theme: {
						'--toastColor': 'white',
						'--toastBackground': 'darkred'
					},
					initial: 0
				}
			);
		} finally {
			isUploading = false;
		}
	}
	function getStatus(taskID: String) {
		fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/${taskID}`, {
			method: 'GET',
			headers: {
				Authorization: 'Bearer ' + data.session.access_token,
				'Content-Type': 'application/json'
			}
		})
			.then((response) => response.json())
			.then((res) => {
				// write out the state
				const actTime = new Date();
				//let html = `${actTime.toUTCString()} ${res.task_status} `;
				let html = ``;
				const taskStatus = res.task_status;
				if (taskStatus === 'SUCCESS') {
					toast.pop();
					toast.push($_('page.discharge.calculation.calcsuccess'), {
						theme: {
							'--toastColor': 'mintcream',
							'--toastBackground': 'rgba(72,187,120,0.9)',
							'--toastBarBackground': '#2F855A'
						}
					});
					invalidateAll();

					return false;
				} else if (taskStatus === 'FAILURE') {
					toast.pop();
					toast.push(
						'<h3 style="padding:5;">' +
							$_('page.discharge.calculation.calcerror') +
							'</h3>' +
							res.task_result,
						{
							theme: {
								'--toastColor': 'white',
								'--toastBackground': 'darkred'
							},
							initial: 0
						}
					);
					invalidateAll();

					return false;
				}
				setTimeout(function () {
					getStatus(res.task_id);
				}, 1000);
			})
			.catch((err) => console.log(err));
	}

	function calculateProject(project_id: Number) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		fetch(env.PUBLIC_HAKESCH_API_PATH + '/discharge/calculate_project?ProjectId=' + project_id, {
			method: 'GET',
			headers: {
				Authorization: 'Bearer ' + data.session.access_token
			}
		})
			.then((response) => response.json())
			.then((data) => {
				getGroupStatus(data.task_id);
			});
	}
	function getGroupStatus(taskID: String) {
		fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/group/${taskID}`, {
			method: 'GET',
			headers: {
				Authorization: 'Bearer ' + data.session.access_token,
				'Content-Type': 'application/json'
			}
		})
			.then((response) => response.json())
			.then((res) => {
				// write out the state
				const actTime = new Date();
				//let html = `${actTime.toUTCString()} ${res.task_status} `;
				let html = ``;
				const completed = res.completed;
				const total = res.total;
				if (completed === total) {
					toast.pop();
					toast.push($_('page.discharge.calculation.calcsuccess'), {
						theme: {
							'--toastColor': 'mintcream',
							'--toastBackground': 'rgba(72,187,120,0.9)',
							'--toastBarBackground': '#2F855A'
						}
					});
					invalidateAll();
					return;
				} else if (res.status === 'FAILURE') {
					toast.pop();
					toast.push(
						'<h3 style="padding:5;">' +
							$_('page.discharge.calculation.calcerror') +
							'</h3>' +
							res.task_result,
						{
							theme: {
								'--toastColor': 'white',
								'--toastBackground': 'darkred'
							},
							initial: 0
						}
					);
					invalidateAll();

					return false;
				}

				setTimeout(function () {
					getGroupStatus(res.group_id);
				}, 1000);
			})
			.catch((err) => console.log(err));
	}

	onMount(async () => {
		// Check if soil shape-file exists
		await checkSoilFileExists(data.project.id);

		if (data.project.isozones_taskid === '' || data.project.isozones_running) {
			(globalThis as any).$('#missinggeodata-modal').modal('show');
		}
		else {
			couldCalculate = true;
		}
	});
</script>

<svelte:head>
	<title>{$pageTitle} - {$_('page.discharge.calculation.calculationTitle')} | AUGUR</title>
</svelte:head>

<!-- Missing geodata dialog -->
 <div
	id="missinggeodata-modal"
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
					{$_('page.discharge.calculation.missinggeodataTitle')}
				</h4>
				<button
					type="button"
					class="btn-close"
					data-bs-dismiss="modal"
					aria-label={$_('page.general.close')}
				></button>
			</div>
			<div class="modal-body">
				<h5>{$_('page.discharge.calculation.missingGeodata')}</h5>
			</div>
			<div class="modal-footer">
				<button
					type="button"
					class="btn btn-light"
					data-bs-dismiss="modal"
					onclick={addCalculation}>{$_('page.general.ok')}</button
				>
			</div>
		</div>
		<!-- /.modal-content -->
	</div>
	<!-- /.modal-dialog -->
</div>

<div class="flex-grow-1 card">
	<div class="h-100">
		<div class="card-header py-2 px-3 border-bottom">
			<div class="d-flex align-items-center justify-content-between py-1">
				<div class="d-flex align-items-center gap-2">
					<h3 class="my-0 lh-base">
						{data.project.title}
					</h3>
				</div>
				<div class="d-xl-flex align-items-center gap-2">
					<button
						type="button"
						onclick={() => calculateProject(data.project.id)}
						class="btn btn-sm btn-icon btn-ghost-primary"
						title={$_('page.discharge.calculation.calculate')}
						aria-label={$_('page.discharge.calculation.calculate')}
					>
						<i class="ti ti-calculator fs-24"></i>
					</button>
					<button
						type="button"
						class="btn btn-sm btn-icon btn-ghost-primary"
						data-bs-toggle="modal"
						data-bs-target="#generate-modal"
						title={$_('page.discharge.calculation.addcalculation')}
						aria-label={$_('page.discharge.calculation.addcalculation')}
					>
						<i class="ti ti-plus fs-24"></i>
					</button>

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
									<h4 class="modal-title" id="standard-modalLabel">
										{$_('page.discharge.calculation.addcalculation')}
									</h4>
									<button
										type="button"
										class="btn-close"
										data-bs-dismiss="modal"
										aria-label={$_('page.general.close')}
									></button>
								</div>
								<div class="modal-body">
									<h5>{$_('page.discharge.calculation.typeOfCalculation')}</h5>
									<hr />
									<select id="calculation_type" class="form-select" bind:value={calulcationType}>
										<option value="1">{$_('page.discharge.calculation.modFliesszeit')}</option>
										<option value="2">{$_('page.discharge.calculation.koells')}</option>
										<option value="3">{$_('page.discharge.calculation.clarkwsl')}</option>
										<option value="4">{$_('page.discharge.calculation.nam')}</option>
									</select>
								</div>
								<div class="modal-footer">
									<button
										type="button"
										class="btn btn-light"
										data-bs-dismiss="modal"
										onclick={addCalculation}>{$_('page.general.add')}</button
									>
								</div>
							</div>
							<!-- /.modal-content -->
						</div>
						<!-- /.modal-dialog -->
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
								<button
									class="accordion-button"
									type="button"
									data-bs-toggle="collapse"
									data-bs-target="#panelsStayOpen-collapseOne"
									aria-expanded="true"
									aria-controls="panelsStayOpen-collapseOne"
								>
									{$_('page.discharge.calculation.generalInput')}
								</button>
							</h2>
							<div
								id="panelsStayOpen-collapseOne"
								class="accordion-collapse collapse show"
								aria-labelledby="panelsStayOpen-headingOne"
								style=""
							>
								<div class="accordion-body">
									<form
										method="post"
										action="?/updatefnp"
										use:enhance={() => {
											isGeneralSaving = true;
											return async ({ update }) => {
												await update();
												currentProject.title = data.project.title;
												isGeneralSaving = false;
											};
										}}
									>
										<input type="hidden" name="id" value={data.project.id} />
										<input type="hidden" name="idf_id" value={data.project.IDF_Parameters?.id} />
										<h4 class="text-muted">
											{$_('page.discharge.calculation.inputsForPrecipitationIntensity')}
										</h4>
										<div class="row g-2 py-2 align-items-end">
											<div class="mb-3 col-md-4">
												<label for="P_low_1h" class="form-label"
													>{$_('page.discharge.calculation.idf.precipLowerPeriod1h')}</label
												>
												<input
													type="number"
													class="form-control"
													name="P_low_1h"
													id="P_low_1h"
													value={Number(data.project.IDF_Parameters?.P_low_1h)}
												/>
											</div>
											<div class="mb-3 col-md-4">
												<label for="P_low_24h" class="form-label"
													>{$_('page.discharge.calculation.idf.precipLowerPeriod24h')}</label
												>
												<input
													type="number"
													class="form-control"
													id="P_low_24h"
													name="P_low_24h"
													value={Number(data.project.IDF_Parameters?.P_low_24h)}
												/>
											</div>
											<div class="mb-3 col-md-4">
												<label for="rp_low" class="form-label"
													>{$_('page.discharge.calculation.idf.returnPeriod')}</label
												>
												<select
													id="rp_low"
													name="rp_low"
													class="form-select"
													value={data.project.IDF_Parameters?.rp_low}
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
												<label for="P_high_1h" class="form-label"
													>{$_('page.discharge.calculation.idf.precipUpperPeriod1h')}</label
												>
												<input
													type="number"
													class="form-control"
													id="P_high_1h"
													name="P_high_1h"
													value={Number(data.project.IDF_Parameters?.P_high_1h)}
												/>
											</div>
											<div class="mb-3 col-md-4">
												<label for="P_high_24h" class="form-label"
													>{$_('page.discharge.calculation.idf.precipUpperPeriod24h')}</label
												>
												<input
													type="number"
													class="form-control"
													id="P_high_24h"
													name="P_high_24h"
													value={Number(data.project.IDF_Parameters?.P_high_24h)}
												/>
											</div>
											<div class="mb-3 col-md-4">
												<label for="rp_high" class="form-label"
													>{$_('page.discharge.calculation.idf.upperReturnPeriod')}</label
												>

												<select
													id="rp_high"
													name="rp_high"
													class="form-select"
													value={data.project.IDF_Parameters?.rp_high}
												>
													{#each returnPeriod as rp}
														<option value={rp.id}>
															{rp.text}
														</option>
													{/each}
												</select>
											</div>
										</div>
										<button type="submit" class="btn btn-primary" disabled={isGeneralSaving}>
											{#if isGeneralSaving}
												<span
													class="spinner-border spinner-border-sm me-2"
													role="status"
													aria-hidden="true"
												></span>
											{/if}
											{$_('page.general.save')}
										</button>
									</form>
								</div>
							</div>
						</div>
						{#if mod_verfahren.length > 0}
							<div class="accordion-item">
								<h2 class="accordion-header" id="panelsStayOpen-headingMFZ">
									<button
										class="accordion-button collapsed"
										type="button"
										data-bs-toggle="collapse"
										data-bs-target="#panelsStayOpen-collapseMFZ"
										aria-expanded="false"
										aria-controls="panelsStayOpen-collapseThree"
									>
										{$_('page.discharge.calculation.modFliesszeit')}
									</button>
								</h2>
								<div
									id="panelsStayOpen-collapseMFZ"
									class="accordion-collapse collapse"
									aria-labelledby="panelsStayOpen-headingMFZ"
									style=""
								>
									<div class="accordion-body">
										<div class="accordion" id="accordionPanelsMFZ">
											{#each mod_verfahren as mod_fz}
												<div class="accordion-item">
													<h1 class="accordion-header" id="panelsStayOpen-modFZ{mod_fz.id}">
														<button
															class="accordion-button collapsed"
															type="button"
															data-bs-toggle="collapse"
															data-bs-target="#panelsStayOpen-collapsemodFZ{mod_fz.id}"
															aria-expanded="true"
															aria-controls="panelsStayOpen-collapsemodFZ{mod_fz.id}"
														>
															{$_('page.discharge.calculation.szenario')}
															{#if mod_fz.Annuality}
																({mod_fz.Annuality.description})
															{/if}
														</button>
													</h1>
													<div
														id="panelsStayOpen-collapsemodFZ{mod_fz.id}"
														class="collapse"
														aria-labelledby="panelsStayOpen-modFZ{mod_fz.id}"
														style=""
													>
														<div class="accordion-body">
															<form
																method="post"
																action="?/updatemfzv"
																use:enhance={({ formElement, formData, action, cancel, submitter }) => {
																	isMFZSaving = true;
																	return async ({ result, update }) => {
																		await update({ reset: false });
																		if (result.type === 'success' && result.data) {
																			data.project = result.data;
																		}
																		isMFZSaving = false;

																		if (submitter?.id=="calcMFZButton"){
																			calculateModFliess(mod_fz.project_id, mod_fz.id);
																		}
																		else {
																			toast.push($_('page.discharge.calculation.successfullsave'), {
																				theme: {
																					'--toastColor': 'mintcream',
																					'--toastBackground': 'rgba(72,187,120,0.9)',
																					'--toastBarBackground': '#2F855A'
																				}
																			});
																		}
																	};
																}}
															>
																<input type="hidden" name="id" value={mod_fz.project_id} />
																<input type="hidden" name="mfzv_id" value={mod_fz.id} />
																<div class="row g-2 py-2 align-items-end">
																	<div class="mb-3 col-md-4">
																		<label for="P_low_1h" class="form-label"
																			>{$_('page.discharge.calculation.returnPeriod')}</label
																		>
																		<select
																			id="x"
																			name="x"
																			class="form-select"
																			value={mod_fz.Annuality?.number}
																		>
																			{#each returnPeriod as rp}
																				<option value={rp.id}>
																					{rp.text}
																				</option>
																			{/each}
																		</select>
																	</div>
																	<div class="mb-3 col-md-4">
																		<label for="P_low_24h" class="form-label"
																			>{$_(
																				'page.discharge.calculation.modFZV.wettingVolume'
																			)}</label
																		>
																		<input
																			type="number"
																			step="any"
																			class="form-control"
																			id="Vo20"
																			name="Vo20"
																			value={Number(mod_fz.Vo20)}
																		/>
																	</div>
																	<div class="mb-3 col-md-4">
																		<label for="P_low_24h" class="form-label"
																			>{$_('page.discharge.calculation.modFZV.peakFlow')}</label
																		>
																		<input
																			type="number"
																			step="any"
																			class="form-control"
																			id="psi"
																			name="psi"
																			value={Number(mod_fz.psi)}
																		/>
																	</div>
																</div>
																<div class="d-flex align-items-center justify-content-between py-1">
																	<div class="d-flex align-items-center gap-2">
																		<button
																			type="submit"
																			class="btn btn-primary"
																			disabled={isMFZSaving}
																		>
																			{#if isMFZSaving}
																				<span
																					class="spinner-border spinner-border-sm me-2"
																					role="status"
																					aria-hidden="true"
																				></span>
																			{/if}
																			{$_('page.general.save')}
																		</button>
																		<button
																			type="submit" id="calcMFZButton"
																			class="btn btn-primary"
																			disabled={isMFZSaving || !couldCalculate}
																			>{$_('page.general.calculate')}</button
																		>
																	</div>
																	<div class="d-flex align-items-center gap-2">
																		<span
																			class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
																			data-bs-placement="top"
																			title={$_('page.general.delete')}
																			aria-label="delete"
																			data-bs-toggle="modal"
																			data-bs-target="#delete-project-modal{mod_fz.id}"
																		>
																			<i class="ti ti-trash fs-20"></i>
																		</span>
																	</div>
																</div>
															</form>
															<!-- Delete Calculation Modal -->
															<div
																id="delete-project-modal{mod_fz.id}"
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
																				{$_('page.discharge.calculation.deleteCalculation')}
																			</h4>
																			<button
																				type="button"
																				class="btn-close btn-close-white"
																				data-bs-dismiss="modal"
																				aria-label={$_('page.general.close')}
																			></button>
																		</div>
																		<div class="modal-body">
																			<p>
																				{$_('page.discharge.calculation.deleteCalculationQuestion')}
																			</p>
																		</div>
																		<div class="modal-footer">
																			<button
																				type="button"
																				class="btn btn-light"
																				data-bs-dismiss="modal">{$_('page.general.cancel')}</button
																			>
																			<form method="POST" action="?/delete">
																				<input type="hidden" name="id" value={mod_fz.id} />
																				<button type="submit" class="btn btn-warning"
																					>{$_('page.general.delete')}</button
																				>
																			</form>
																		</div>
																	</div>
																	<!-- /.modal-content -->
																</div>
																<!-- /.modal-dialog -->
															</div>
															<!-- /.modal -->
														</div>
													</div>
												</div>
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						{#if koella.length > 0}
							<div class="accordion-item">
								<h2 class="accordion-header" id="panelsStayOpen-headingThree">
									<button
										class="accordion-button collapsed"
										type="button"
										data-bs-toggle="collapse"
										data-bs-target="#panelsStayOpen-collapseKoella"
										aria-expanded="false"
										aria-controls="panelsStayOpen-collapseKoella"
									>
										{$_('page.discharge.calculation.koells')}
									</button>
								</h2>
								<div
									id="panelsStayOpen-collapseKoella"
									class="accordion-collapse collapse"
									aria-labelledby="panelsStayOpen-headingKoella"
									style=""
								>
									<div class="accordion-body">
										<div class="accordion" id="accordionPanelsKoella">
											{#each koella as k}
												<div class="accordion-item">
													<h1 class="accordion-header" id="panelsStayOpen-Koella{k.id}">
														<button
															class="accordion-button collapsed"
															type="button"
															data-bs-toggle="collapse"
															data-bs-target="#panelsStayOpen-collapseKoella{k.id}"
															aria-expanded="true"
															aria-controls="panelsStayOpen-collapseKoella{k.id}"
														>
															{$_('page.discharge.calculation.szenario')}
															{#if k.Annuality}
																({k.Annuality.description})
															{/if}
														</button>
													</h1>
													<div
														id="panelsStayOpen-collapseKoella{k.id}"
														class="collapse"
														aria-labelledby="panelsStayOpen-Koella{k.id}"
														style=""
													>
														<div class="accordion-body">
															<form
																method="post"
																action="?/updatekoella"
																use:enhance={({ formElement, formData, action, cancel, submitter }) => {
																	isKoellaSaving = true;
																	return async ({ result, update }) => {
																		await update({ reset: false });
																		if (result.type === 'success' && result.data) {
																			data.project = result.data;
																		}
																		isKoellaSaving = false;
																		if (submitter?.id=="calcKoellaButton"){
																			calculateKoella(k.project_id, k.id);
																		}
																		else {
																			toast.push($_('page.discharge.calculation.successfullsave'), {
																				theme: {
																					'--toastColor': 'mintcream',
																					'--toastBackground': 'rgba(72,187,120,0.9)',
																					'--toastBarBackground': '#2F855A'
																				}
																			});
																		}
																	};
																}}
															>
																<input type="hidden" name="id" value={k.project_id} />
																<input type="hidden" name="koella_id" value={k.id} />
																<div class="row g-2 py-2 align-items-end">
																	<div class="mb-3 col-md-4">
																		<label for="x" class="form-label"
																			>{$_('page.discharge.calculation.returnPeriod')}</label
																		>
																		<select
																			id="x"
																			name="x"
																			class="form-select"
																			value={k.Annuality?.number}
																		>
																			{#each returnPeriod as rp}
																				<option value={rp.id}>
																					{rp.text}
																				</option>
																			{/each}
																		</select>
																	</div>
																	<div class="mb-3 col-md-4">
																		<label for="Vo20" class="form-label"
																			>{$_(
																				'page.discharge.calculation.modFZV.wettingVolume'
																			)}</label
																		>
																		<input
																			type="number"
																			step="any"
																			class="form-control"
																			id="Vo20"
																			name="Vo20"
																			value={Number(k.Vo20)}
																		/>
																	</div>
																	<div class="mb-3 col-md-4">
																		<label for="P_low_24h" class="form-label"
																			>{$_('page.discharge.calculation.koella.glacierArea')} km<sup
																				>2</sup
																			></label
																		>
																		<input
																			type="number"
																			step="1"
																			class="form-control"
																			id="psi"
																			name="glacier_area"
																			value={Number(k.glacier_area)}
																		/>
																	</div>
																</div>
																<div class="d-flex align-items-center justify-content-between py-1">
																	<div class="d-flex align-items-center gap-2">
																		<button
																			type="submit"
																			class="btn btn-primary"
																			disabled={isKoellaSaving}
																		>
																			{#if isKoellaSaving}
																				<span
																					class="spinner-border spinner-border-sm me-2"
																					role="status"
																					aria-hidden="true"
																				></span>
																			{/if}
																			{$_('page.general.save')}
																		</button>
																		<button
																			type="submit" id="calcKoellaButton"
																			class="btn btn-primary"
																			disabled={isKoellaSaving || !couldCalculate}
																			>{$_('page.general.calculate')}</button
																		>
																	</div>
																	<div class="d-flex align-items-center gap-2">
																		<span
																			class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
																			data-bs-placement="top"
																			title={$_('page.general.delete')}
																			aria-label="delete"
																			data-bs-toggle="modal"
																			data-bs-target="#delete-koella-modal{k.id}"
																		>
																			<i class="ti ti-trash fs-20"></i>
																		</span>
																	</div>
																</div>
															</form>
															<!-- Delete Calculation Modal -->
															<div
																id="delete-koella-modal{k.id}"
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
																				{$_('page.discharge.calculation.deleteCalculation')}
																			</h4>
																			<button
																				type="button"
																				class="btn-close btn-close-white"
																				data-bs-dismiss="modal"
																				aria-label="Close"
																			></button>
																		</div>
																		<div class="modal-body">
																			<p>
																				{$_('page.discharge.calculation.deleteCalculationQuestion')}
																			</p>
																		</div>
																		<div class="modal-footer">
																			<button
																				type="button"
																				class="btn btn-light"
																				data-bs-dismiss="modal">{$_('page.general.cancel')}</button
																			>
																			<form method="POST" action="?/deleteKoella">
																				<input type="hidden" name="id" value={k.id} />
																				<button type="submit" class="btn btn-warning"
																					>{$_('page.general.delete')}</button
																				>
																			</form>
																		</div>
																	</div>
																	<!-- /.modal-content -->
																</div>
																<!-- /.modal-dialog -->
															</div>
															<!-- /.modal -->
														</div>
													</div>
												</div>
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						{#if clark_wsl.length > 0}
							<div class="accordion-item">
								<h2 class="accordion-header" id="panelsStayOpen-headingClarkWSL">
									<button
										class="accordion-button collapsed"
										type="button"
										data-bs-toggle="collapse"
										data-bs-target="#panelsStayOpen-collapseClarkWSL"
										aria-expanded="false"
										aria-controls="panelsStayOpen-collapseClarkWSL"
									>
										{$_('page.discharge.calculation.clarkwslname')}
									</button>
								</h2>
								<div
									id="panelsStayOpen-collapseClarkWSL"
									class="accordion-collapse collapse"
									aria-labelledby="panelsStayOpen-headingClarkWSL"
									style=""
								>
									<div class="accordion-body">
										<div class="accordion" id="accordionPanelsClarkWSL">
											{#each clark_wsl as k}
												<div class="accordion-item">
													<h1 class="accordion-header" id="panelsStayOpen-ClarkWSL{k.id}">
														<button
															class="accordion-button collapsed"
															type="button"
															data-bs-toggle="collapse"
															data-bs-target="#panelsStayOpen-collapseClarkWSL{k.id}"
															aria-expanded="true"
															aria-controls="panelsStayOpen-collapseClarkWSL{k.id}"
														>
															{$_('page.discharge.calculation.szenario')}
															{#if k.Annuality}
																({k.Annuality.description})
															{/if}
														</button>
													</h1>
													<div
														id="panelsStayOpen-collapseClarkWSL{k.id}"
														class="collapse"
														aria-labelledby="panelsStayOpen-ClarkWSL{k.id}"
														style=""
													>
														<div class="accordion-body">
															<form
																method="post"
																action="?/updateclarkwsl"
																use:enhance={({ formElement, formData, action, cancel, submitter}) => {
																	isClarkWSLSaving = true;
																	return async ({ result, update }) => {
																		await update({ reset: false });
																		if (result.type === 'success' && result.data) {
																			data.project = result.data;
																		}
																		isClarkWSLSaving = false;
																		if (submitter?.id=="calcClarkWSLButton"){
																			calculateClarkWSL(k.project_id, k.id);
																		}
																		else {
																			toast.push($_('page.discharge.calculation.successfullsave'), {
																				theme: {
																					'--toastColor': 'mintcream',
																					'--toastBackground': 'rgba(72,187,120,0.9)',
																					'--toastBarBackground': '#2F855A'
																				}
																			});
																		}
																	};
																}}
															>
																<input type="hidden" name="id" value={k.project_id} />
																<input type="hidden" name="clarkwsl_id" value={k.id} />
																<div class="row g-2 py-2 align-items-start">
																	<div class="mb-3 col-md-4">
																		<label for="x" class="form-label"
																			>{$_('page.discharge.calculation.returnPeriod')}</label
																		>
																		<select
																			id="x"
																			name="x"
																			class="form-select"
																			value={k.Annuality?.number}
																		>
																			{#each returnPeriod as rp}
																				<option value={rp.id}>
																					{rp.text}
																				</option>
																			{/each}
																		</select>
																	</div>
																	<div class="mb-3 col-md-8 d-flex">
																		<div
																			class="d-flex align-items-stretch align-self-center justify-content-between flex-column"
																		>
																			{#each zones as z, i}
																				<div class="d-flex align-items-center gap-2 flex-row">
																					<label for="zone_{i}" class="flex-fill text-end"
																						>{z.typ}</label
																					>
																					<div class="" style="max-width:130px;">
																						<input
																							type="number"
																							step="any"
																							class="form-control text-end"
																							style="-webkit-appearance: none; -moz-appearance: textfield;"
																							id="zone_{i}"
																							name="zone_{i}"
																							value={getPctForZone(z.typ, k)}
																						/>
																					</div>
																					<div class="text-start">%</div>
																				</div>
																			{/each}
																		</div>
																	</div>
																</div>
																<div class="d-flex align-items-center justify-content-between py-1">
																	<div class="d-flex align-items-center gap-2">
																		<button
																			type="submit"
																			class="btn btn-primary"
																			disabled={isClarkWSLSaving}
																		>
																			{#if isClarkWSLSaving}
																				<span
																					class="spinner-border spinner-border-sm me-2"
																					role="status"
																					aria-hidden="true"
																				></span>
																			{/if}
																			{$_('page.general.save')}
																		</button>
																		<button
																			type="submit" id="calcClarkWSLButton"
																			class="btn btn-primary"
																			disabled={isClarkWSLSaving || !couldCalculate}
																			>{$_('page.general.calculate')}</button
																		>
																	</div>
																	<div class="d-flex align-items-center gap-2">
																		<span
																			class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
																			data-bs-placement="top"
																			title={$_('page.general.delete')}
																			aria-label="delete"
																			data-bs-toggle="modal"
																			data-bs-target="#delete-clarkwsl-modal{k.id}"
																		>
																			<i class="ti ti-trash fs-20"></i>
																		</span>
																	</div>
																</div>
															</form>
															<!-- Delete Calculation Modal -->
															<div
																id="delete-clarkwsl-modal{k.id}"
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
																				{$_('page.discharge.calculation.deleteCalculation')}
																			</h4>
																			<button
																				type="button"
																				class="btn-close btn-close-white"
																				data-bs-dismiss="modal"
																				aria-label="Close"
																			></button>
																		</div>
																		<div class="modal-body">
																			<p>
																				{$_('page.discharge.calculation.deleteCalculationQuestion')}
																			</p>
																		</div>
																		<div class="modal-footer">
																			<button
																				type="button"
																				class="btn btn-light"
																				data-bs-dismiss="modal">{$_('page.general.cancel')}</button
																			>
																			<form method="POST" action="?/deleteClarkWSL">
																				<input type="hidden" name="id" value={k.id} />
																				<button type="submit" class="btn btn-warning"
																					>{$_('page.general.delete')}</button
																				>
																			</form>
																		</div>
																	</div>
																	<!-- /.modal-content -->
																</div>
																<!-- /.modal-dialog -->
															</div>
															<!-- /.modal -->
														</div>
													</div>
												</div>
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						{#if nam.length > 0}
							<div class="accordion-item">
								<h2 class="accordion-header" id="panelsStayOpen-headingNAM">
									<button
										class="accordion-button collapsed"
										type="button"
										data-bs-toggle="collapse"
										data-bs-target="#panelsStayOpen-collapseNAM"
										aria-expanded="false"
										aria-controls="panelsStayOpen-collapseNAM"
									>
										{$_('page.discharge.calculation.nam')}
									</button>
								</h2>
								<div
									id="panelsStayOpen-collapseNAM"
									class="accordion-collapse collapse"
									aria-labelledby="panelsStayOpen-headingNAM"
									style=""
								>
									<div class="accordion-body">
										<div class="accordion" id="accordionPanelsNAM">
											{#each nam as n}
												<div class="accordion-item">
													<h1 class="accordion-header" id="panelsStayOpen-NAM{n.id}">
														<button
															class="accordion-button collapsed"
															type="button"
															data-bs-toggle="collapse"
															data-bs-target="#panelsStayOpen-collapseNAM{n.id}"
															aria-expanded="true"
															aria-controls="panelsStayOpen-collapseNAM{n.id}"
														>
															{$_('page.discharge.calculation.szenario')}
															{#if n.Annuality}
																({n.Annuality.description})
															{/if}
														</button>
													</h1>
													<div
														id="panelsStayOpen-collapseNAM{n.id}"
														class="collapse"
														aria-labelledby="panelsStayOpen-NAM{n.id}"
														style=""
													>
														<div class="accordion-body">
															<form
																method="post"
																action="?/updatenam"
																use:enhance={({ formElement, formData, action, cancel, submitter}) => {
																	isNAMSaving = true;
																	return async ({ result, update }) => {
																		await update({ reset: false });
																		if (result.type === 'success' && result.data) {
																			data.project = result.data;
																		}
																		isNAMSaving = false;
																		if (submitter?.id=="calcNAMButton"){
																			calculateNAM(n.project_id, n.id);
																		}
																		else {
																			toast.push($_('page.discharge.calculation.successfullsave'), {
																				theme: {
																					'--toastColor': 'mintcream',
																					'--toastBackground': 'rgba(72,187,120,0.9)',
																					'--toastBarBackground': '#2F855A'
																				}
																			});
																		}
																	};
																}}
															>
																<input type="hidden" name="id" value={n.project_id} />
																<input type="hidden" name="nam_id" value={n.id} />
																<div class="row g-2 py-2 align-items-end">
																	<div class="mb-3 col-md-4">
																		<label for="x" class="form-label"
																			>{$_('page.discharge.calculation.returnPeriod')}</label
																		>
																		<select
																			id="x"
																			name="x"
																			class="form-select"
																			value={n.Annuality?.number}
																		>
																			{#each returnPeriod as rp}
																				<option value={rp.id}>
																					{rp.text}
																				</option>
																			{/each}
																		</select>
																	</div>
																	<div class="mb-3 col-md-4" style="display:none;">
																		<label for="precipitation_factor" class="form-label"
																			>{$_('page.discharge.calculation.namParams.precipitationFactor')}</label
																		>
																		<input
																			type="number"
																			step="any"
																			class="form-control"
																			id="precipitation_factor"
																			name="precipitation_factor"
																			value={Number(n.precipitation_factor)}
																		/>
																	</div>
																	<div class="mb-3 col-md-4" style="display:none;">
																		<label for="readiness_to_drain" class="form-label"
																			>{$_('page.discharge.calculation.namParams.readinessToDrain')}</label
																		>
																		<input
																			type="number"
																			step="1"
																			class="form-control"
																			id="readiness_to_drain"
																			name="readiness_to_drain"
																			value={Number(n.readiness_to_drain)}
																		/>
																	</div>
																</div>
																<div class="row g-2 py-2 align-items-end" style="display:none;">
																	<div class="mb-3 col-md-4">
																		<label for="water_balance_mode" class="form-label"
																			>{$_('page.discharge.calculation.namParams.waterBalanceMode')}</label
																		>
																		<select
																			id="water_balance_mode"
																			name="water_balance_mode"
																			class="form-select"
																			value={n.water_balance_mode}
																		>
																			<option value="simple">{$_('page.discharge.calculation.namParams.simple')}</option>
																			<option value="cumulative">{$_('page.discharge.calculation.namParams.advanced')}</option>
																		</select>
																	</div>
																	<div class="mb-3 col-md-4" style="display:none;">
																		<label for="storm_center_mode" class="form-label"
																			>{$_('page.discharge.calculation.namParams.stormCenterMode')}</label
																		>
																		<select
																			id="storm_center_mode"
																			name="storm_center_mode"
																			class="form-select"
																			value={n.storm_center_mode}
																		>
																			<option value="centroid">{$_('page.discharge.calculation.namParams.centroid')}</option>
																			<option value="discharge_point">{$_('page.discharge.calculation.namParams.dischargePoint')}</option>
																		</select>
																	</div>
																	<div class="mb-3 col-md-4" style="display:none;">
																		<label for="routing_method" class="form-label"
																			>{$_('page.discharge.calculation.namParams.routingMethod')}</label
																		>
																		<select
																			id="routing_method"
																			name="routing_method"
																			class="form-select"
																			value={n.routing_method}
																		>
																			<option value="time_values">{$_('page.discharge.calculation.namParams.timeValues')}</option>
																			<option value="travel_time">{$_('page.discharge.calculation.namParams.traveltime')}</option>
																			<option value="isozone">{$_('page.discharge.calculation.namParams.traveltime')}</option>
																		</select>
																	</div>
																</div>
																<div class="row g-2 py-2 align-items-end">
																	<div class="mb-3 col-md-12">
																		{#if soilFileExists}
																			<div class="mb-3">
																				<div class="form-check">
																					<input
																						class="form-check-input"
																						type="checkbox"
																						id="use_own_soil_data"
																						bind:checked={useOwnSoilData}
																					/>
																					<label class="form-check-label" for="use_own_soil_data">
																						{$_('page.discharge.calculation.namParams.useOwnSoilData')}
																					</label>
																				</div>
																				<div class="form-text">
																					{$_('page.discharge.calculation.namParams.useOwnSoilDataHelp')}
																				</div>
																			</div>
																		{/if}
																		
																		{#if !soilFileExists || useOwnSoilData}
																			<label for="zip_upload" class="form-label">
																				{$_('page.discharge.calculation.namParams.uploadZipFile')}
																			</label>
																			<input
																				type="file"
																				class="form-control"
																				id="zip_upload"
																				accept=".zip"
																				onchange={(e) => {
																					const target = e.target as HTMLInputElement;
																					const file = target.files?.[0];
																					if (file) {
																						uploadZipFile(n.project_id, file);
																					}
																				}}
																				disabled={isUploading || isCheckingSoilFile}
																			/>
																			<div class="form-text">
																				{$_('page.discharge.calculation.namParams.uploadZipFileHelp')}
																			</div>
																		{:else}
																			<div class="alert alert-info">
																				<i class="ti ti-info-circle me-2"></i>
																				{$_('page.discharge.calculation.namParams.soilFileExists')}
																			</div>
																		{/if}
																	</div>
																</div>
																<div class="d-flex align-items-center justify-content-between py-1">
																	<div class="d-flex align-items-center gap-2">
																		<button
																			type="submit"
																			class="btn btn-primary"
																			disabled={isNAMSaving}
																		>
																			{#if isNAMSaving}
																				<span
																					class="spinner-border spinner-border-sm me-2"
																					role="status"
																					aria-hidden="true"
																				></span>
																			{/if}
																			{$_('page.general.save')}
																		</button>
																		<button
																			type="submit" id="calcNAMButton"
																			class="btn btn-primary"
																			disabled={isNAMSaving || !couldCalculate}
																			>{$_('page.general.calculate')}</button
																		>
																	</div>
																	<div class="d-flex align-items-center gap-2">
																		<span
																			class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
																			data-bs-placement="top"
																			title={$_('page.general.delete')}
																			aria-label="delete"
																			data-bs-toggle="modal"
																			data-bs-target="#delete-nam-modal{n.id}"
																		>
																			<i class="ti ti-trash fs-20"></i>
																		</span>
																	</div>
																</div>
															</form>
															<!-- Delete Calculation Modal -->
															<div
																id="delete-nam-modal{n.id}"
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
																				{$_('page.discharge.calculation.deleteCalculation')}
																			</h4>
																			<button
																				type="button"
																				class="btn-close btn-close-white"
																				data-bs-dismiss="modal"
																				aria-label="Close"
																			></button>
																		</div>
																		<div class="modal-body">
																			<p>
																				{$_('page.discharge.calculation.deleteCalculationQuestion')}
																			</p>
																		</div>
																		<div class="modal-footer">
																			<button
																				type="button"
																				class="btn btn-light"
																				data-bs-dismiss="modal">{$_('page.general.cancel')}</button
																			>
																			<form method="POST" action="?/deleteNAM">
																				<input type="hidden" name="id" value={n.id} />
																				<button type="submit" class="btn btn-warning"
																					>{$_('page.general.delete')}</button
																				>
																			</form>
																		</div>
																	</div>
																	<!-- /.modal-content -->
																</div>
																<!-- /.modal-dialog -->
															</div>
															<!-- /.modal -->
														</div>
													</div>
												</div>
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
				<div class="col-lg-4">
					<div class="accordion" id="accordionPanelsResults">
						<div class="accordion-item">
							<h2 class="accordion-header" id="panelsResults-headingOne">
								<button
									class="accordion-button"
									type="button"
									data-bs-toggle="collapse"
									data-bs-target="#panelsResults-collapseOne"
									aria-expanded="true"
									aria-controls="panelsResults-collapseOne"
								>
									{$_('page.discharge.calculation.results')}
								</button>
							</h2>
							<div
								id="panelsResults-collapseOne"
								class="accordion-collapse collapse show"
								aria-labelledby="panelsResults-headingOne"
								style=""
							>
								<div class="accordion-body">
									<div use:renderChart={chart}></div>

									{#if mod_verfahren.length > 0}
										<h4 class="text-muted">{$_('page.discharge.calculation.modFliesszeit')}</h4>

										<table class="table mb-0">
											<thead>
												<tr>
													<th>{$_('page.discharge.calculation.returnPeriod')}</th>
													<th>{$_('page.discharge.calculation.hq')} [m<sup>3</sup>/s]</th>
												</tr>
											</thead>
											<tbody>
												{#each mod_verfahren as mod_fz}
													<tr>
														<td>
															{#if mod_fz.Annuality}
																{mod_fz.Annuality.description}
															{/if}
														</td>
														<td>{mod_fz.Mod_Fliesszeit_Result?.HQ.toFixed(2)}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									{/if}
									{#if koella.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.koells')}</h4>

										<table class="table mb-0">
											<thead>
												<tr>
													<th>{$_('page.discharge.calculation.returnPeriod')}</th>
													<th>{$_('page.discharge.calculation.hq')} [m<sup>3</sup>/s]</th>
												</tr>
											</thead>
											<tbody>
												{#each koella as k}
													<tr>
														<td>
															{#if k.Annuality}
																{k.Annuality.description}
															{/if}
														</td>
														<td>{k.Koella_Result?.HQ.toFixed(2)}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									{/if}
									{#if clark_wsl.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.clarkwsl')}</h4>

										<table class="table mb-0">
											<thead>
												<tr>
													<th>{$_('page.discharge.calculation.returnPeriod')}</th>
													<th>{$_('page.discharge.calculation.hq')} [m<sup>3</sup>/s]</th>
												</tr>
											</thead>
											<tbody>
												{#each clark_wsl as k}
													<tr>
														<td>
															{#if k.Annuality}
																{k.Annuality.description}
															{/if}
														</td>
														<td>{k.ClarkWSL_Result?.Q.toFixed(2)}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									{/if}
									{#if nam.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.nam')}</h4>

										<table class="table mb-0">
											<thead>
												<tr>
													<th>{$_('page.discharge.calculation.returnPeriod')}</th>
													<th>{$_('page.discharge.calculation.hq')} [m<sup>3</sup>/s]</th>
												</tr>
											</thead>
											<tbody>
												{#each nam as n}
													<tr>
														<td>
															{#if n.Annuality}
																{n.Annuality.description}
															{/if}
														</td>
														<td>{n.NAM_Result?.HQ.toFixed(2)}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
