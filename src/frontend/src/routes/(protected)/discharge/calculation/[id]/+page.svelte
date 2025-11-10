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
				formatter: function (val: number) {
					return '$ ' + val + '  m3/s';
				}
			}
		}
	};

	const chart: Chart = {
		options: chartOneOptions
	};

	// Function to create multi-annuality discharge chart options
	function getMultiAnnualityDischargeChartOptions(namResults: any[], scenarioIndex: number): Chart {
		if (!namResults || namResults.length === 0) {
			return {
				options: {
					series: [],
					chart: { type: 'line', height: 200 },
					xaxis: { categories: [] },
					yaxis: { title: { text: $_('page.discharge.calculation.chart.dischargeUnit') } }
				}
			};
		}

		try {
			const series = [];
			const colors = ['#1376ef', '#4a90e2', '#7bb3f0']; // Different shades of blue
			let dischargeDataArray = [];
			let globalStartIndex = Infinity;
			let globalEndIndex = 0;
			
			// First pass: collect all data and find the actual data range
			for (let i = 0; i < namResults.length; i++) {
				const nam = namResults[i];
				const namResult = getResultField(nam, 'NAM_Result');
				if (namResult?.HQ_time) {
					const dischargeData = JSON.parse(namResult.HQ_time);
					dischargeDataArray.push(dischargeData);
					
					// Find the actual data range for this series
					let startIndex = 0;
					let endIndex = dischargeData.length;
					
					// Find first non-zero value
					for (let j = 0; j < dischargeData.length; j++) {
						if (dischargeData[j] > 0) {
							startIndex = Math.max(0, j - 1);
							break;
						}
					}
					
					// Find last non-zero value
					for (let j = dischargeData.length - 1; j >= 0; j--) {
						if (dischargeData[j] > 0) {
							endIndex = Math.min(dischargeData.length, j + 2);
							break;
						}
					}
					
					// Update global range
					globalStartIndex = Math.min(globalStartIndex, startIndex);
					globalEndIndex = Math.max(globalEndIndex, endIndex);
				}
			}
			
			// Create time scale only for the actual data range
			const dataLength = globalEndIndex - globalStartIndex;
			const timeSteps = Array.from({length: dataLength}, (_, index) => (globalStartIndex + index) * 10);
			
			// Process each annuality
			for (let i = 0; i < namResults.length; i++) {
				const nam = namResults[i];
				const namResult = getResultField(nam, 'NAM_Result');
				if (namResult?.HQ_time) {
					const dischargeData = dischargeDataArray[i];
					
					// Extract only the relevant data range
					const filteredData = dischargeData.slice(globalStartIndex, globalEndIndex);
					
					series.push({
						name: nam.Annuality?.description || `Annuality ${i + 1}`,
						data: filteredData,
						color: colors[i % colors.length]
					});
				}
			}
			
			// Calculate overall data range for better scaling
			const allSeriesData = series.flatMap((s: any) => s.data);
			const maxDischarge = Math.max(...allSeriesData);
			const minDischarge = Math.min(...allSeriesData);
			
			return {
				options: {
					series: series,
					chart: {
						type: 'line',
						height: 200,
						toolbar: {
							show: false
						},
						zoom: {
							enabled: true,
							type: 'x',
							autoScaleYaxis: true
						}
					},
					stroke: {
						curve: 'smooth',
						width: 2
					},
					xaxis: {
						categories: timeSteps,
						title: {
							text: $_('page.discharge.calculation.chart.timeUnit')
						},
						labels: {
							formatter: function(value: string) {
								return parseInt(value).toString();
							}
						}
					},
					yaxis: {
						title: {
							text: $_('page.discharge.calculation.chart.dischargeUnit')
						},
						min: Math.max(0, minDischarge * 0.9),
						max: maxDischarge * 1.1,
						labels: {
							formatter: function (val: number) {
								return val.toFixed(2);
							}
						}
					},
					tooltip: {
						y: {
							formatter: function (val: number) {
								return val.toFixed(2) + ' ' + $_('page.discharge.calculation.chart.dischargeTooltip');
							}
						},
						x: {
							formatter: function (val: number, opts: any) {
								// Get the actual time value from the categories array
								const timeValue = timeSteps[opts.dataPointIndex];
								return timeValue + ' min';
							}
						}
					},
					
					grid: {
						show: true,
						borderColor: '#e0e0e0'
					},
					dataLabels: {
						enabled: false
					},
					legend: {
						show: true,
						position: 'top',
						horizontalAlign: 'right'
					}
				}
			};
		} catch (error) {
			console.error('Error parsing multi-annuality HQ_time data:', error);
			return {
				options: {
					series: [],
					chart: { type: 'line', height: 200 },
					xaxis: { categories: [] },
					yaxis: { title: { text: $_('page.discharge.calculation.chart.dischargeUnit') } }
				}
			};
		}
	}

	// Function to create discharge timesteps chart options
	function getDischargeChartOptions(hqTimeData: string | null, title: string): Chart {
		if (!hqTimeData) {
			return {
				options: {
					series: [],
					chart: { type: 'line', height: 200 },
					xaxis: { categories: [] },
					yaxis: { title: { text: $_('page.discharge.calculation.chart.dischargeUnit') } }
				}
			};
		}

		try {
			const dischargeData = JSON.parse(hqTimeData);
			console.log('HQ_time data received:', {
				length: dischargeData.length,
				sample: dischargeData.slice(0, 10),
				max: Math.max(...dischargeData),
				min: Math.min(...dischargeData),
				nonZeroCount: dischargeData.filter((x: number) => x > 0).length
			});
			
			// Filter out leading and trailing zeros to focus on the actual discharge period
			let startIndex = 0;
			let endIndex = dischargeData.length;
			
			// Find first non-zero value
			for (let i = 0; i < dischargeData.length; i++) {
				if (dischargeData[i] > 0) {
					startIndex = Math.max(0, i - 1); // Include one point before
					break;
				}
			}
			
			// Find last non-zero value
			for (let i = dischargeData.length - 1; i >= 0; i--) {
				if (dischargeData[i] > 0) {
					endIndex = Math.min(dischargeData.length, i + 2); // Include one point after
					break;
				}
			}
			
			// Extract the relevant data range
			const filteredData = dischargeData.slice(startIndex, endIndex);
			const timeSteps = filteredData.map((_: any, index: number) => (startIndex + index) * 10); // 10-minute timesteps
			
			// Calculate data range for better scaling
			const maxDischarge = Math.max(...filteredData);
			const minDischarge = Math.min(...filteredData);
			
			return {
				options: {
					series: [{
						name: $_('page.discharge.calculation.chart.discharge'),
						data: filteredData,
						color: '#1376ef'
					}],
					chart: {
						type: 'line',
						height: 200,
						toolbar: {
							show: false
						},
						zoom: {
							enabled: true,
							type: 'x',
							autoScaleYaxis: true
						}
					},
					stroke: {
						curve: 'smooth',
						width: 2
					},
					xaxis: {
						categories: timeSteps,
						title: {
							text: $_('page.discharge.calculation.chart.timeUnit')
						},
						labels: {
							formatter: function(value: string) {
								return parseInt(value).toString();
							}
						}
					},
					yaxis: {
						title: {
							text: $_('page.discharge.calculation.chart.dischargeUnit')
						},
						min: Math.max(0, minDischarge * 0.9), // Start from 0 or slightly below min
						max: maxDischarge * 1.1, // Slightly above max for better visualization
						labels: {
							formatter: function (val: number) {
								return val.toFixed(2);
							}
						}
					},
					tooltip: {
						y: {
							formatter: function (val: number) {
								return val.toFixed(2) + ' ' + $_('page.discharge.calculation.chart.dischargeTooltip');
							}
						},
						x: {
							formatter: function (val: number) {
								return val + ' min';
							}
						}
					},
					title: {
						text: title,
						align: 'left',
						style: {
							fontSize: '14px',
							fontWeight: 'bold'
						}
					},
					grid: {
						show: true,
						borderColor: '#e0e0e0'
					},
					dataLabels: {
						enabled: false
					}
				}
			};
		} catch (error) {
			console.error('Error parsing HQ_time data:', error);
			return {
				options: {
					series: [],
					chart: { type: 'line', height: 200 },
					xaxis: { categories: [] },
					yaxis: { title: { text: $_('page.discharge.calculation.chart.dischargeUnit') } }
				}
			};
		}
	}

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
	
	// Climate scenario selection state
	let selectedClimateScenario = $state<string>('current');
	
	// Climate scenario options
	const climateScenarios = [
		{ value: 'current', label: 'Current Climate' },
		{ value: '1_5_degree', label: '+1.5°C' },
		{ value: '2_degree', label: '+2.0°C' },
		{ value: '3_degree', label: '+3.0°C' }	
	];
	
	// Helper function to get the appropriate result field based on selected climate scenario
	function getResultField(item: any, baseFieldName: string) {
		const fieldMap: Record<string, string> = {
			'current': baseFieldName,
			'1_5_degree': `${baseFieldName}_1_5`,
			'2_degree': `${baseFieldName}_2`,
			'3_degree': `${baseFieldName}_3`
		};
		return item[fieldMap[selectedClimateScenario]];
	}

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

	// Group calculations by scenarios (groups of 3 annualities)
	// Each scenario should have entries for annualities 2.3, 20, and 100
	function groupByScenario(calculations: any[]) {
		// Sort by ID to ensure consistent grouping
		const sorted = [...calculations].sort((a, b) => a.id - b.id);
		const scenarios = [];
		
		// Group every 3 consecutive entries as one scenario
		for (let i = 0; i < sorted.length; i += 3) {
			scenarios.push(sorted.slice(i, i + 3));
		}
		
		return scenarios;
	}

	// Create derived state for scenarios
	let mod_fliesszeit_scenarios = $derived(groupByScenario(mod_verfahren));
	let koella_scenarios = $derived(groupByScenario(koella));
	let clark_wsl_scenarios = $derived(groupByScenario(clark_wsl));
	let nam_scenarios = $derived(groupByScenario(nam));

	function showResults() {
		let mod_fliesszeit_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Mod. Fliesszeitverfahren',
			color: '#1376ef',
			data: []
		};
		const mf_23 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 2.3);
		const mf_20 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 20);
		const mf_100 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 100);
		
		mod_fliesszeit_data.data.push(
			getResultField(mf_23, 'Mod_Fliesszeit_Result')?.HQ
				? Number(getResultField(mf_23, 'Mod_Fliesszeit_Result').HQ.toFixed(2))
				: null
		);
		mod_fliesszeit_data.data.push(
			getResultField(mf_20, 'Mod_Fliesszeit_Result')?.HQ
				? Number(getResultField(mf_20, 'Mod_Fliesszeit_Result').HQ.toFixed(2))
				: null
		);
		mod_fliesszeit_data.data.push(
			getResultField(mf_100, 'Mod_Fliesszeit_Result')?.HQ
				? Number(getResultField(mf_100, 'Mod_Fliesszeit_Result').HQ.toFixed(2))
				: null
		);
		let koella_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Kölla',
			color: '#1e13ef',
			data: []
		};
		const k_23 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 2.3);
		const k_20 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 20);
		const k_100 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 100);
		
		koella_data.data.push(
			getResultField(k_23, 'Koella_Result')?.HQ
				? Number(getResultField(k_23, 'Koella_Result').HQ.toFixed(2))
				: null
		);
		koella_data.data.push(
			getResultField(k_20, 'Koella_Result')?.HQ
				? Number(getResultField(k_20, 'Koella_Result').HQ.toFixed(2))
				: null
		);
		koella_data.data.push(
			getResultField(k_100, 'Koella_Result')?.HQ
				? Number(getResultField(k_100, 'Koella_Result').HQ.toFixed(2))
				: null
		);
		let clark_wsl_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Clark WSL',
			color: '#13e4ef',
			data: []
		};
		const c_23 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 2.3);
		const c_20 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 20);
		const c_100 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 100);
		
		clark_wsl_data.data.push(
			getResultField(c_23, 'ClarkWSL_Result')?.Q
				? Number(getResultField(c_23, 'ClarkWSL_Result').Q.toFixed(2))
				: null
		);
		clark_wsl_data.data.push(
			getResultField(c_20, 'ClarkWSL_Result')?.Q
				? Number(getResultField(c_20, 'ClarkWSL_Result').Q.toFixed(2))
				: null
		);
		clark_wsl_data.data.push(
			getResultField(c_100, 'ClarkWSL_Result')?.Q
				? Number(getResultField(c_100, 'ClarkWSL_Result').Q.toFixed(2))
				: null
		);
		let nam_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'NAM',
			color: '#ef1313',
			data: []
		};
		const n_23 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 2.3);
		const n_20 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 20);
		const n_100 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 100);
		
		nam_data.data.push(
			getResultField(n_23, 'NAM_Result')?.HQ
				? Number(getResultField(n_23, 'NAM_Result').HQ.toFixed(2))
				: null
		);
		nam_data.data.push(
			getResultField(n_20, 'NAM_Result')?.HQ
				? Number(getResultField(n_20, 'NAM_Result').HQ.toFixed(2))
				: null
		);
		nam_data.data.push(
			getResultField(n_100, 'NAM_Result')?.HQ
				? Number(getResultField(n_100, 'NAM_Result').HQ.toFixed(2))
				: null
		);
		chartOneOptions.series = [mod_fliesszeit_data, koella_data, clark_wsl_data, nam_data];
		chart.ref?.updateSeries(chartOneOptions.series);
	}
	$effect(() => {
		// Re-run when climate scenario changes
		selectedClimateScenario;
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

	async function calculateModFliess(scenario: any[]) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		
		// Each annuality gets its own API call
		// Each call returns a group task_id (for all climate scenarios of that annuality)
		const groupTaskIds: string[] = [];
		
		for (const mod_fz of scenario) {
			try {
				const response = await fetch(
					env.PUBLIC_HAKESCH_API_PATH +
						'/discharge/modifizierte_fliesszeit?ProjectId=' +
						mod_fz.project_id +
						'&ModFliesszeitId=' +
						mod_fz.id,
					{
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token
						}
					}
				);
				const result = await response.json();
				// Each API call returns a group task_id for all climate scenarios
				groupTaskIds.push(result.task_id);
			} catch (error) {
				console.error('Error calculating ModFliess:', error);
			}
		}
		
		// Monitor all group tasks
		if (groupTaskIds.length > 0) {
			getMultipleGroupStatus(groupTaskIds);
		} else {
			toast.pop();
			toast.push($_('page.discharge.calculation.calcerror'), {
				theme: {
					'--toastColor': 'white',
					'--toastBackground': 'darkred'
				}
			});
		}
	}
	
	async function calculateKoella(scenario: any[]) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		
		// Each annuality gets its own API call
		// Each call returns a group task_id (for all climate scenarios of that annuality)
		const groupTaskIds: string[] = [];
		
		for (const k of scenario) {
			try {
				const response = await fetch(
					env.PUBLIC_HAKESCH_API_PATH +
						'/discharge/koella?ProjectId=' +
						k.project_id +
						'&KoellaId=' +
						k.id,
					{
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token
						}
					}
				);
				const result = await response.json();
				// Each API call returns a group task_id for all climate scenarios
				groupTaskIds.push(result.task_id);
			} catch (error) {
				console.error('Error calculating Koella:', error);
			}
		}
		
		// Monitor all group tasks
		if (groupTaskIds.length > 0) {
			getMultipleGroupStatus(groupTaskIds);
		} else {
			toast.pop();
			toast.push($_('page.discharge.calculation.calcerror'), {
				theme: {
					'--toastColor': 'white',
					'--toastBackground': 'darkred'
				}
			});
		}
	}
	
	async function calculateClarkWSL(scenario: any[]) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		
		// Each annuality gets its own API call
		// Each call returns a group task_id (for all climate scenarios of that annuality)
		const groupTaskIds: string[] = [];
		
		for (const k of scenario) {
			try {
				const response = await fetch(
					env.PUBLIC_HAKESCH_API_PATH +
						'/discharge/clark-wsl?ProjectId=' +
						k.project_id +
						'&ClarkWSLId=' +
						k.id,
					{
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token
						}
					}
				);
				const result = await response.json();
				// Each API call returns a group task_id for all climate scenarios
				groupTaskIds.push(result.task_id);
			} catch (error) {
				console.error('Error calculating ClarkWSL:', error);
			}
		}
		
		// Monitor all group tasks
		if (groupTaskIds.length > 0) {
			getMultipleGroupStatus(groupTaskIds);
		} else {
			toast.pop();
			toast.push($_('page.discharge.calculation.calcerror'), {
				theme: {
					'--toastColor': 'white',
					'--toastBackground': 'darkred'
				}
			});
		}
	}
	
	async function calculateNAM(scenario: any[]) {
		toast.push($_('page.discharge.calculation.calcrunning'), {
			initial: 0
		});
		
		// Each annuality gets its own API call
		// Each call returns a group task_id (for all climate scenarios of that annuality)
		const groupTaskIds: string[] = [];
		
		for (const n of scenario) {
			try {
				const response = await fetch(
					env.PUBLIC_HAKESCH_API_PATH +
						'/discharge/nam?ProjectId=' +
						n.project_id +
						'&NAMId=' +
						n.id,
					{
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token
						}
					}
				);
				const result = await response.json();
				// Each API call returns a group task_id for all climate scenarios
				groupTaskIds.push(result.task_id);
			} catch (error) {
				console.error('Error calculating NAM:', error);
			}
		}
		
		// Monitor all group tasks
		if (groupTaskIds.length > 0) {
			getMultipleGroupStatus(groupTaskIds);
		} else {
			toast.pop();
			toast.push($_('page.discharge.calculation.calcerror'), {
				theme: {
					'--toastColor': 'white',
					'--toastBackground': 'darkred'
				}
			});
		}
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

	async function getStatusMultiple(taskIDs: string[]) {
		const taskStatuses = new Map<string, string>();
		taskIDs.forEach(id => taskStatuses.set(id, 'PENDING'));
		
		const checkAllTasks = async () => {
			let allCompleted = true;
			let anyFailed = false;
			let failureMessages: string[] = [];
			
			for (const taskID of taskIDs) {
				try {
					const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/${taskID}`, {
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token,
							'Content-Type': 'application/json'
						}
					});
					const res = await response.json();
					const taskStatus = res.task_status;
					
					taskStatuses.set(taskID, taskStatus);
					
					if (taskStatus === 'FAILURE') {
						anyFailed = true;
						failureMessages.push(res.task_result || 'Unknown error');
					} else if (taskStatus !== 'SUCCESS') {
						allCompleted = false;
					}
				} catch (err) {
					console.error('Error checking task status:', err);
					allCompleted = false;
				}
			}
			
			if (allCompleted || anyFailed) {
				toast.pop();
				
				if (anyFailed) {
					const errorMessage = failureMessages.join('<br>');
					toast.push(
						'<h3 style="padding:5;">' +
							$_('page.discharge.calculation.calcerror') +
							'</h3>' +
							errorMessage,
						{
							theme: {
								'--toastColor': 'white',
								'--toastBackground': 'darkred'
							},
							initial: 0
						}
					);
				} else {
					toast.push($_('page.discharge.calculation.calcsuccess'), {
						theme: {
							'--toastColor': 'mintcream',
							'--toastBackground': 'rgba(72,187,120,0.9)',
							'--toastBarBackground': '#2F855A'
						}
					});
				}
				
				invalidateAll();
			} else {
				// Continue polling
				setTimeout(checkAllTasks, 1000);
			}
		};
		
		checkAllTasks();
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

	async function getMultipleGroupStatus(groupTaskIds: string[]) {
		// Track status of all groups
		const groupStatuses = new Map<string, { completed: number; total: number; status: string }>();
		groupTaskIds.forEach(id => groupStatuses.set(id, { completed: 0, total: 0, status: 'PENDING' }));
		
		const checkAllGroups = async () => {
			let allCompleted = true;
			let anyFailed = false;
			let totalCompleted = 0;
			let totalTasks = 0;
			
			for (const groupTaskId of groupTaskIds) {
				try {
					const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/task/group/${groupTaskId}`, {
						method: 'GET',
						headers: {
							Authorization: 'Bearer ' + data.session.access_token,
							'Content-Type': 'application/json'
						}
					});
					const res = await response.json();
					
					groupStatuses.set(groupTaskId, {
						completed: res.completed,
						total: res.total,
						status: res.status
					});
					
					totalCompleted += res.completed;
					totalTasks += res.total;
					
					if (res.status === 'FAILURE') {
						anyFailed = true;
					} else if (res.completed !== res.total) {
						allCompleted = false;
					}
				} catch (err) {
					console.error('Error checking group task status:', err);
					allCompleted = false;
				}
			}
			
			if (anyFailed) {
				toast.pop();
				toast.push($_('page.discharge.calculation.calcerror'), {
					theme: {
						'--toastColor': 'white',
						'--toastBackground': 'darkred'
					}
				});
				invalidateAll();
				return;
			}
			
			if (allCompleted) {
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
			}
			
			// Continue polling
			setTimeout(() => {
				checkAllGroups();
			}, 1000);
		};
		
		checkAllGroups();
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
					
				</div>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<!-- Input Part -->
				<div class="col-lg-8">
					<div class="accordion" id="accordionPanelsStayOpenExample">
						<!-- General Input Part -->
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
						<!-- End of General Input Part -->
						<!-- Mod. Fliesszeit Part -->
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
											{#each mod_fliesszeit_scenarios as scenario, scenarioIndex}
												
												<form
													method="post"
													action="?/updateScenario"
													use:enhance={({ formElement, formData, action, cancel, submitter }) => {
														isMFZSaving = true;
														return async ({ result, update }) => {
															await update({ reset: false });
															if (result.type === 'success' && result.data) {
																data.project = result.data;
															}
															isMFZSaving = false;

														if (submitter?.id==`calcMFZButton-scenario${scenarioIndex}`){
															// Calculate all 3 annualities in the scenario
															calculateModFliess(scenario);
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
													<input type="hidden" name="project_id" value={scenario[0].project_id} />
													<input type="hidden" name="type" value="modfliesszeit" />
													{#each scenario as mod_fz}
														<input type="hidden" name="ids[]" value={mod_fz.id} />
													{/each}
													
													<div class="row g-2 py-2 align-items-end">
														<div class="mb-3 col-md-6">
															<label for="Vo20-scenario{scenarioIndex}" class="form-label"
																>{$_(
																	'page.discharge.calculation.modFZV.wettingVolume'
																)}</label
															>
															<input
																type="number"
																step="any"
																class="form-control"
																id="Vo20-scenario{scenarioIndex}"
																name="Vo20"
																value={Number(scenario[0].Vo20)}
															/>
														</div>
														<div class="mb-3 col-md-6">
															<label for="psi-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.modFZV.peakFlow')}</label
															>
															<input
																type="number"
																step="any"
																class="form-control"
																id="psi-scenario{scenarioIndex}"
																name="psi"
																value={Number(scenario[0].psi)}
															/>
														</div>
													</div>
													<div class="d-flex align-items-center justify-content-between py-1 mb-3">
														<div class="d-flex align-items-center gap-2">
															<button
																type="submit"
																class="btn btn-sm btn-primary"
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
																type="submit" id="calcMFZButton-scenario{scenarioIndex}"
																class="btn btn-sm btn-primary"
																disabled={isMFZSaving || !couldCalculate}
																>{$_('page.general.calculate')}</button
															>
														</div>
													</div>
												</form>
												
												<div class="d-flex align-items-center justify-content-end py-1">
													<span
														class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
														data-bs-placement="top"
														title={$_('page.general.delete')}
														aria-label="delete"
														data-bs-toggle="modal"
														data-bs-target="#delete-scenario-mfz-modal{scenarioIndex}"
													>
														<i class="ti ti-trash fs-20"></i>
													</span>
												</div>
												
												<!-- Delete Scenario Modal -->
												<div
													id="delete-scenario-mfz-modal{scenarioIndex}"
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
																<form method="POST" action="?/deleteScenario">
																	{#each scenario as mod_fz}
																		<input type="hidden" name="ids[]" value={mod_fz.id} />
																	{/each}
																	<input type="hidden" name="type" value="modfliesszeit" />
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
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						<!-- End of Mod. Fliesszeit Part -->
						<!-- Koella Part -->
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
											{#each koella_scenarios as scenario, scenarioIndex}
												
												<form
													method="post"
													action="?/updateScenario"
													use:enhance={({ formElement, formData, action, cancel, submitter }) => {
														isKoellaSaving = true;
														return async ({ result, update }) => {
															await update({ reset: false });
															if (result.type === 'success' && result.data) {
																data.project = result.data;
															}
															isKoellaSaving = false;
														if (submitter?.id==`calcKoellaButton-scenario${scenarioIndex}`){
															// Calculate all 3 annualities in the scenario
															calculateKoella(scenario);
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
													<input type="hidden" name="project_id" value={scenario[0].project_id} />
													<input type="hidden" name="type" value="koella" />
													{#each scenario as k}
														<input type="hidden" name="ids[]" value={k.id} />
													{/each}
													
													<div class="row g-2 py-2 align-items-end">
														<div class="mb-3 col-md-6">
															<label for="Vo20-koella-scenario{scenarioIndex}" class="form-label"
																>{$_(
																	'page.discharge.calculation.modFZV.wettingVolume'
																)}</label
															>
															<input
																type="number"
																step="any"
																class="form-control"
																id="Vo20-koella-scenario{scenarioIndex}"
																name="Vo20"
																value={Number(scenario[0].Vo20)}
															/>
														</div>
														<div class="mb-3 col-md-6">
															<label for="glacier_area-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.koella.glacierArea')} km<sup
																	>2</sup
																></label
															>
															<input
																type="number"
																step="1"
																class="form-control"
																id="glacier_area-scenario{scenarioIndex}"
																name="glacier_area"
																value={Number(scenario[0].glacier_area)}
															/>
														</div>
													</div>
													<div class="d-flex align-items-center justify-content-between py-1 mb-3">
														<div class="d-flex align-items-center gap-2">
															<button
																type="submit"
																class="btn btn-sm btn-primary"
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
																type="submit" id="calcKoellaButton-scenario{scenarioIndex}"
																class="btn btn-sm btn-primary"
																disabled={isKoellaSaving || !couldCalculate}
																>{$_('page.general.calculate')}</button
															>
														</div>
													</div>
												</form>
												
												<div class="d-flex align-items-center justify-content-end py-1">
													<span
														class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
														data-bs-placement="top"
														title={$_('page.general.delete')}
														aria-label="delete"
														data-bs-toggle="modal"
														data-bs-target="#delete-scenario-koella-modal{scenarioIndex}"
													>
														<i class="ti ti-trash fs-20"></i>
													</span>
												</div>
												
												<!-- Delete Scenario Modal -->
												<div
													id="delete-scenario-koella-modal{scenarioIndex}"
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
																<form method="POST" action="?/deleteScenario">
																	{#each scenario as k}
																		<input type="hidden" name="ids[]" value={k.id} />
																	{/each}
																	<input type="hidden" name="type" value="koella" />
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
											{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						<!-- End of Koella Part -->
						<!-- Clark WSL Part -->
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
											{#each clark_wsl_scenarios as scenario, scenarioIndex}
												<form
													method="post"
													action="?/updateScenario"
													use:enhance={({ formElement, formData, action, cancel, submitter}) => {
														isClarkWSLSaving = true;
														return async ({ result, update }) => {
															await update({ reset: false });
															if (result.type === 'success' && result.data) {
																data.project = result.data;
															}
															isClarkWSLSaving = false;
														if (submitter?.id==`calcClarkWSLButton-scenario${scenarioIndex}`){
															// Calculate all 3 annualities in the scenario
															calculateClarkWSL(scenario);
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
													<input type="hidden" name="project_id" value={scenario[0].project_id} />
													<input type="hidden" name="type" value="clarkwsl" />
													{#each scenario as k}
														<input type="hidden" name="ids[]" value={k.id} />
													{/each}
													
													<div class="row g-2 py-2 align-items-start">
													<div class="mb-3 col-md-12 d-flex">
														<div
															class="d-flex align-items-stretch align-self-center justify-content-between flex-column"
														>
															{#each zones as z, i}
																<div class="d-flex align-items-center gap-2 flex-row">
																	<label for="zone_{i}-scenario{scenarioIndex}" class="flex-fill text-end"
																		>{z.typ}</label
																	>
																	<div class="" style="max-width:130px;">
																		<input
																			type="number"
																			step="any"
																			class="form-control text-end"
																			style="-webkit-appearance: none; -moz-appearance: textfield;"
																			id="zone_{i}-scenario{scenarioIndex}"
																			name="zone_{i}"
																			value={getPctForZone(z.typ, scenario[0])}
																		/>
																	</div>
																	<div class="text-start">%</div>
																</div>
															{/each}
														</div>
													</div>
												</div>
												<div class="d-flex align-items-center justify-content-between py-1 mb-3">
													<div class="d-flex align-items-center gap-2">
														<button
															type="submit"
															class="btn btn-sm btn-primary"
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
															type="submit" id="calcClarkWSLButton-scenario{scenarioIndex}"
															class="btn btn-sm btn-primary"
															disabled={isClarkWSLSaving || !couldCalculate}
															>{$_('page.general.calculate')}</button
														>
													</div>
												</div>
											</form>
											
											<div class="d-flex align-items-center justify-content-end py-1">
												<span
													class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
													data-bs-placement="top"
													title={$_('page.general.delete')}
													aria-label="delete"
													data-bs-toggle="modal"
													data-bs-target="#delete-scenario-clarkwsl-modal{scenarioIndex}"
												>
													<i class="ti ti-trash fs-20"></i>
												</span>
											</div>
											
											<!-- Delete Scenario Modal -->
											<div
												id="delete-scenario-clarkwsl-modal{scenarioIndex}"
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
															<form method="POST" action="?/deleteScenario">
																{#each scenario as k}
																	<input type="hidden" name="ids[]" value={k.id} />
																{/each}
																<input type="hidden" name="type" value="clarkwsl" />
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
										{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						<!-- End of Clark WSL Part -->
						<!-- NAM Part -->
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
											{#each nam_scenarios as scenario, scenarioIndex}
												<form
													method="post"
													action="?/updateScenario"
													use:enhance={({ formElement, formData, action, cancel, submitter}) => {
														isNAMSaving = true;
														return async ({ result, update }) => {
															await update({ reset: false });
															if (result.type === 'success' && result.data) {
																data.project = result.data;
															}
															isNAMSaving = false;
														if (submitter?.id==`calcNAMButton-scenario${scenarioIndex}`){
															// Calculate all 3 annualities in the scenario
															calculateNAM(scenario);
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
													<input type="hidden" name="project_id" value={scenario[0].project_id} />
													<input type="hidden" name="type" value="nam" />
													{#each scenario as n}
														<input type="hidden" name="ids[]" value={n.id} />
													{/each}
													
													<div class="row g-2 py-2 align-items-end"  style="display:none;">
														<div class="mb-3 col-md-4">
															<label for="precipitation_factor-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.namParams.precipitationFactor')}</label
															>
															<input
																type="number"
																step="any"
																class="form-control"
																id="precipitation_factor-scenario{scenarioIndex}"
																name="precipitation_factor"
																value={Number(scenario[0].precipitation_factor)}
															/>
														</div>
														<div class="mb-3 col-md-4">
															<label for="readiness_to_drain-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.namParams.readinessToDrain')}</label
															>
															<input
																type="number"
																step="1"
																class="form-control"
																id="readiness_to_drain-scenario{scenarioIndex}"
																name="readiness_to_drain"
																value={Number(scenario[0].readiness_to_drain)}
															/>
														</div>
													</div>
													<div class="row g-2 py-2 align-items-end" style="display:none;">
														<div class="mb-3 col-md-4">
															<label for="water_balance_mode-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.namParams.waterBalanceMode')}</label
															>
															<select
																id="water_balance_mode-scenario{scenarioIndex}"
																name="water_balance_mode"
																class="form-select"
																value={scenario[0].water_balance_mode}
															>
																<option value="simple">{$_('page.discharge.calculation.namParams.simple')}</option>
																<option value="cumulative">{$_('page.discharge.calculation.namParams.advanced')}</option>
															</select>
														</div>
														<div class="mb-3 col-md-4">
															<label for="storm_center_mode-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.namParams.stormCenterMode')}</label
															>
															<select
																id="storm_center_mode-scenario{scenarioIndex}"
																name="storm_center_mode"
																class="form-select"
																value={scenario[0].storm_center_mode}
															>
																<option value="centroid">{$_('page.discharge.calculation.namParams.centroid')}</option>
																<option value="discharge_point">{$_('page.discharge.calculation.namParams.dischargePoint')}</option>
															</select>
														</div>
														<div class="mb-3 col-md-4">
															<label for="routing_method-scenario{scenarioIndex}" class="form-label"
																>{$_('page.discharge.calculation.namParams.routingMethod')}</label
															>
															<select
																id="routing_method-scenario{scenarioIndex}"
																name="routing_method"
																class="form-select"
																value={scenario[0].routing_method}
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
																<label for="zip_upload-scenario{scenarioIndex}" class="form-label">
																	{$_('page.discharge.calculation.namParams.uploadZipFile')}
																</label>
																<input
																	type="file"
																	class="form-control"
																	id="zip_upload-scenario{scenarioIndex}"
																	accept=".zip"
																	onchange={(e) => {
																		const target = e.target as HTMLInputElement;
																		const file = target.files?.[0];
																		if (file) {
																			uploadZipFile(scenario[0].project_id, file);
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
													<div class="d-flex align-items-center justify-content-between py-1 mb-3">
														<div class="d-flex align-items-center gap-2">
															<button
																type="submit"
																class="btn btn-sm btn-primary"
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
																type="submit" id="calcNAMButton-scenario{scenarioIndex}"
																class="btn btn-sm btn-primary"
																disabled={isNAMSaving || !couldCalculate}
																>{$_('page.general.calculate')}</button
															>
														</div>
													</div>
												</form>
											
											<div class="d-flex align-items-center justify-content-end py-1">
												<span
													class="btn btn-sm btn-icon btn-ghost-danger d-xl-flex"
													data-bs-placement="top"
													title={$_('page.general.delete')}
													aria-label="delete"
													data-bs-toggle="modal"
													data-bs-target="#delete-scenario-nam-modal{scenarioIndex}"
												>
													<i class="ti ti-trash fs-20"></i>
												</span>
											</div>
											
											<!-- Delete Scenario Modal -->
											<div
												id="delete-scenario-nam-modal{scenarioIndex}"
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
															<form method="POST" action="?/deleteScenario">
																{#each scenario as n}
																	<input type="hidden" name="ids[]" value={n.id} />
																{/each}
																<input type="hidden" name="type" value="nam" />
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
										{/each}
										</div>
									</div>
								</div>
							</div>
						{/if}
						<!-- End of NAM Part -->
					</div>
				</div>
				<!-- End of Input Part -->
				<!-- Results Part -->
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
									<!-- Climate Scenario Selector -->
									<div class="mb-3">
										<label for="climateScenario" class="form-label">
											<strong>Climate Scenario</strong>
										</label>
										<select 
											id="climateScenario" 
											class="form-select"
											bind:value={selectedClimateScenario}
										>
											{#each climateScenarios as scenario}
												<option value={scenario.value}>{scenario.label}</option>
											{/each}
										</select>
									</div>
									
									{#key selectedClimateScenario}
										<div use:renderChart={chart}></div>
									{/key}
									
									<!-- NAM Discharge Timesteps Graph -->
									{#if nam.some((n: any) => getResultField(n, 'NAM_Result')?.HQ_time)}
										<div class="mt-4">
											<h5 class="text-muted">{$_('page.discharge.calculation.chart.dischargeTimeSeries')}</h5>
											<div class="card">
												<div class="card-body">
													{#key selectedClimateScenario}
														<div class="mb-0">
															<div 
																class="discharge-chart" 
																style=""
																use:renderChart={getMultiAnnualityDischargeChartOptions(nam, 0)}
															></div>
														</div>
													{/key}
												</div>
											</div>
										</div>
									{/if}
									{#if mod_verfahren.length > 0}
										<h4 class="text-muted">{$_('page.discharge.calculation.modFliesszeit')}</h4>

										<div class="table-responsive">
											<table class="table table-sm mb-0">
												<thead>
													<tr>
														<th>{$_('page.discharge.calculation.returnPeriod')}</th>
														<th class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>Current</th>
														<th class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>+1.5°C</th>
														<th class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>+2.0°C</th>
														<th class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>+3.0°C</th>
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
															<td class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>
																{mod_fz.Mod_Fliesszeit_Result?.HQ ? mod_fz.Mod_Fliesszeit_Result.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>
																{mod_fz.Mod_Fliesszeit_Result_1_5?.HQ ? mod_fz.Mod_Fliesszeit_Result_1_5.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>
																{mod_fz.Mod_Fliesszeit_Result_2?.HQ ? mod_fz.Mod_Fliesszeit_Result_2.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>
																{mod_fz.Mod_Fliesszeit_Result_3?.HQ ? mod_fz.Mod_Fliesszeit_Result_3.HQ.toFixed(2) : '-'}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									{/if}
									{#if koella.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.koells')}</h4>

										<div class="table-responsive">
											<table class="table table-sm mb-0">
												<thead>
													<tr>
														<th>{$_('page.discharge.calculation.returnPeriod')}</th>
														<th class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>Current</th>
														<th class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>+1.5°C</th>
														<th class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>+2.0°C</th>
														<th class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>+3.0°C</th>
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
															<td class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>
																{k.Koella_Result?.HQ ? k.Koella_Result.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>
																{k.Koella_Result_1_5?.HQ ? k.Koella_Result_1_5.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>
																{k.Koella_Result_2?.HQ ? k.Koella_Result_2.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>
																{k.Koella_Result_3?.HQ ? k.Koella_Result_3.HQ.toFixed(2) : '-'}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									{/if}
									{#if clark_wsl.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.clarkwsl')}</h4>

										<div class="table-responsive">
											<table class="table table-sm mb-0">
												<thead>
													<tr>
														<th>{$_('page.discharge.calculation.returnPeriod')}</th>
														<th class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>Current</th>
														<th class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>+1.5°C</th>
														<th class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>+2.0°C</th>
														<th class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>+3.0°C</th>
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
															<td class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>
																{k.ClarkWSL_Result?.Q ? k.ClarkWSL_Result.Q.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>
																{k.ClarkWSL_Result_1_5?.Q ? k.ClarkWSL_Result_1_5.Q.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>
																{k.ClarkWSL_Result_2?.Q ? k.ClarkWSL_Result_2.Q.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>
																{k.ClarkWSL_Result_3?.Q ? k.ClarkWSL_Result_3.Q.toFixed(2) : '-'}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									{/if}
									{#if nam.length > 0}
										<h4 class="text-muted mt-4">{$_('page.discharge.calculation.nam')}</h4>

										<div class="table-responsive">
											<table class="table table-sm mb-0">
												<thead>
													<tr>
														<th>{$_('page.discharge.calculation.returnPeriod')}</th>
														<th class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>Current</th>
														<th class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>+1.5°C</th>
														<th class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>+2.0°C</th>
														<th class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>+3.0°C</th>
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
															<td class:fw-bold={selectedClimateScenario === 'current'} class:text-primary={selectedClimateScenario === 'current'}>
																{n.NAM_Result?.HQ ? n.NAM_Result.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '1_5_degree'} class:text-primary={selectedClimateScenario === '1_5_degree'}>
																{n.NAM_Result_1_5?.HQ ? n.NAM_Result_1_5.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '2_degree'} class:text-primary={selectedClimateScenario === '2_degree'}>
																{n.NAM_Result_2?.HQ ? n.NAM_Result_2.HQ.toFixed(2) : '-'}
															</td>
															<td class:fw-bold={selectedClimateScenario === '3_degree'} class:text-primary={selectedClimateScenario === '3_degree'}>
																{n.NAM_Result_3?.HQ ? n.NAM_Result_3.HQ.toFixed(2) : '-'}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>
				<!-- End of Results Part -->
			</div>
		</div>
	</div>
</div>
