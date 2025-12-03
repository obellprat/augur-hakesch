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
	import proj4 from 'proj4';
	//import Apexchart from '$lib/apexchart.svelte';

	type Chart = {
		options: ApexOptions;
		node?: HTMLDivElement;
		ref?: ApexCharts;
	};

type ScenarioIdentifiers = {
	ids: number[];
	projectId: string;
};

type ModScenarioForm = ScenarioIdentifiers & {
	vo20: number;
	psi: number;
};

type KoellaScenarioForm = ScenarioIdentifiers & {
	vo20: number;
	glacier_area: number;
};

type ClarkScenarioForm = ScenarioIdentifiers & {
	fractions: Record<string, number>;
};

type NamScenarioForm = ScenarioIdentifiers & {
	precipitation_factor: number;
	readiness_to_drain: number;
	water_balance_mode: string;
	storm_center_mode: string;
	routing_method: string;
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
			categories: ['30', '100', '300']
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
			// Sort by annuality number in ascending order
			const sortedNamResults = namResults.slice().sort((a, b) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0));
			
			const series = [];
			const colors = ['#1376ef', '#4a90e2', '#7bb3f0']; // Different shades of blue
			let dischargeDataArray = [];
			let globalStartIndex = Infinity;
			let globalEndIndex = 0;
			let dischargeDataIndex = 0;
			
			// First pass: collect all data and find the actual data range
			for (let i = 0; i < sortedNamResults.length; i++) {
				const nam = sortedNamResults[i];
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
			for (let i = 0; i < sortedNamResults.length; i++) {
				const nam = sortedNamResults[i];
				const namResult = getResultField(nam, 'NAM_Result');
				if (namResult?.HQ_time) {
					const dischargeData = dischargeDataArray[dischargeDataIndex];
					
					// Extract only the relevant data range
					const filteredData = dischargeData.slice(globalStartIndex, globalEndIndex);
					
					series.push({
						name: nam.Annuality?.description || `Annuality ${i + 1}`,
						data: filteredData,
						color: colors[series.length % colors.length]
					});
					
					dischargeDataIndex++;
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
	let zones: { typ: string }[] = data.zones;

const API_ERROR_KEY = 'page.discharge.overview.apiUnavailable';
function getApiErrorFallback() {
	return $_(API_ERROR_KEY);
}
let apiErrorMessage = $state(getApiErrorFallback());
$effect(() => {
	apiErrorMessage = getApiErrorFallback();
});

function showApiErrorModal(detail?: string) {
	const fallback = getApiErrorFallback();
	apiErrorMessage = detail ? `${fallback} (${detail})` : fallback;
	(globalThis as any).$('#api-error-modal').modal('show');
}

function handleApiError(context: string, error: unknown) {
	console.error(context, error);
	const detail = error instanceof Error ? error.message : undefined;
	showApiErrorModal(detail);
}

function hasValidIdfInputs() {
	return pLow1h > 0 && pLow24h > 0 && pHigh1h > 0 && pHigh24h > 0;
}

function showMissingIdfModal() {
	(globalThis as any).$('#missing-idf-modal').modal('show');
}

function ensureIdfInputs() {
	if (hasValidIdfInputs()) {
		return true;
	}
	showMissingIdfModal();
	return false;
}

	let isUploading = $state(false);
	let couldCalculate = $state(false);
	let soilFileExists = $state(false);
	let useOwnSoilData = $state(false);
	let isCheckingSoilFile = $state(false);
	let isBulkSaving = $state(false);
	let bulkSaveForm: HTMLFormElement | null = null;
	let bulkPayload = $state('{}');

	let modScenarioForms = $state<ModScenarioForm[]>([]);
	let koellaScenarioForms = $state<KoellaScenarioForm[]>([]);
	let clarkScenarioForms = $state<ClarkScenarioForm[]>([]);
	let namScenarioForms = $state<NamScenarioForm[]>([]);
	let sharedVo20Values = $state<number[]>([]);

	const createRange = (count: number): number[] => Array.from({ length: Math.max(count, 0) }, (_, index) => index);
	let combinedScenarioRange = $state<number[]>([]);
	let clarkScenarioRange = $state<number[]>([]);
	let namScenarioRange = $state<number[]>([]);
	
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
		if (!item) return undefined;
		const fieldMap: Record<string, string> = {
			'current': baseFieldName,
			'1_5_degree': `${baseFieldName}_1_5`,
			'2_degree': `${baseFieldName}_2`,
			'3_degree': `${baseFieldName}_3`
		};
		return item[fieldMap[selectedClimateScenario]];
	}
	let isFetchingHades = $state(false);

	// Reactive state for IDF parameters
	let pLow1h = $state(Number(data.project.IDF_Parameters?.P_low_1h) || 0);
	let pLow24h = $state(Number(data.project.IDF_Parameters?.P_low_24h) || 0);
	let pHigh1h = $state(Number(data.project.IDF_Parameters?.P_high_1h) || 0);
	let pHigh24h = $state(Number(data.project.IDF_Parameters?.P_high_24h) || 0);
	let rpLow = $state(data.project.IDF_Parameters?.rp_low || 30);
	let rpHigh = $state(data.project.IDF_Parameters?.rp_high || 100);

	// Update state when data changes
	$effect(() => {
		pLow1h = Number(data.project.IDF_Parameters?.P_low_1h) || 0;
		pLow24h = Number(data.project.IDF_Parameters?.P_low_24h) || 0;
		pHigh1h = Number(data.project.IDF_Parameters?.P_high_1h) || 0;
		pHigh24h = Number(data.project.IDF_Parameters?.P_high_24h) || 0;
		rpLow = data.project.IDF_Parameters?.rp_low || 30;
		rpHigh = data.project.IDF_Parameters?.rp_high || 100;
	});

	let returnPeriod = $state([
		{
			id: 30,
			text: `30`
		},
		{
			id: 100,
			text: `100`
		},
		{
			id: 300,
			text: `300`
		}
	]);
	let calulcationType = $state(0);
	let mod_verfahren = $state(data.project.Mod_Fliesszeit || []);
	let koella = $state(data.project.Koella || []);
	let clark_wsl = $state(data.project.ClarkWSL || []);
	let nam = $state(data.project.NAM || []);
	//k.Koella_Result?.HQ.toFixed(2)

	// Group calculations by scenarios (groups of 3 annualities)
	// Each scenario should have entries for annualities 2.3, 20, and 100
	function groupByScenario(calculations: any[]) {
		if (!calculations || !Array.isArray(calculations)) {
			return [];
		}
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

	function sanitizeNumber(value: number | string | null | undefined): number {
		const numeric = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(numeric) ? numeric : 0;
	}

	function initializeScenarioForms() {
		const newModForms: ModScenarioForm[] = mod_fliesszeit_scenarios.map((scenario) => {
			const base = scenario[0];
			return {
				ids: scenario.map((entry: any) => entry.id),
				projectId: base?.project_id ?? data.project.id,
				vo20: sanitizeNumber(base?.Vo20),
				psi: sanitizeNumber(base?.psi)
			};
		});

		const newKoellaForms: KoellaScenarioForm[] = koella_scenarios.map((scenario) => {
			const base = scenario[0];
			return {
				ids: scenario.map((entry: any) => entry.id),
				projectId: base?.project_id ?? data.project.id,
				vo20: sanitizeNumber(base?.Vo20),
				glacier_area: sanitizeNumber(base?.glacier_area)
			};
		});

		const newClarkForms: ClarkScenarioForm[] = clark_wsl_scenarios.map((scenario) => {
			const base = scenario[0];
			const fractions: Record<string, number> = {};
		(zones || []).forEach((zone: { typ: string }) => {
				const pct =
					base?.Fractions?.find(
						(fraction: { ZoneParameterTyp: string }) => fraction.ZoneParameterTyp === zone.typ
					)?.pct ?? 0;
				fractions[zone.typ] = sanitizeNumber(pct);
			});
			return {
				ids: scenario.map((entry: any) => entry.id),
				projectId: base?.project_id ?? data.project.id,
				fractions
			};
		});

		const newNamForms: NamScenarioForm[] = nam_scenarios.map((scenario) => {
			const base = scenario[0];
			return {
				ids: scenario.map((entry: any) => entry.id),
				projectId: base?.project_id ?? data.project.id,
				precipitation_factor: sanitizeNumber(base?.precipitation_factor ?? 0.7),
				readiness_to_drain: sanitizeNumber(base?.readiness_to_drain ?? 0),
				water_balance_mode: base?.water_balance_mode || 'cumulative',
				storm_center_mode: base?.storm_center_mode || 'centroid',
				routing_method: base?.routing_method || 'time_values'
			};
		});

		modScenarioForms = newModForms;
		koellaScenarioForms = newKoellaForms;
		clarkScenarioForms = newClarkForms;
		namScenarioForms = newNamForms;

		const maxLength = Math.max(newModForms.length, newKoellaForms.length);
		sharedVo20Values = createRange(maxLength).map((index) => {
			const modValue = newModForms[index]?.vo20;
			const koellaValue = newKoellaForms[index]?.vo20;
			if (typeof modValue === 'number') {
				return modValue;
			}
			if (typeof koellaValue === 'number') {
				return koellaValue;
			}
			return 0;
		});
	}

	function updateSharedVo20(index: number, value: number) {
		const sanitized = sanitizeNumber(value);
		sharedVo20Values = sharedVo20Values.map((current, idx) => (idx === index ? sanitized : current));
		modScenarioForms = modScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, vo20: sanitized } : scenario
		);
		koellaScenarioForms = koellaScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, vo20: sanitized } : scenario
		);
	}

	function updateModPsi(index: number, value: number) {
		const sanitized = sanitizeNumber(value);
		modScenarioForms = modScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, psi: sanitized } : scenario
		);
	}

	function updateGlacierArea(index: number, value: number) {
		const sanitized = sanitizeNumber(value);
		koellaScenarioForms = koellaScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, glacier_area: sanitized } : scenario
		);
	}

	function updateFractionValue(index: number, zoneTyp: string, value: number) {
		const sanitized = sanitizeNumber(value);
		clarkScenarioForms = clarkScenarioForms.map((scenario, idx) =>
			idx === index
				? { ...scenario, fractions: { ...scenario.fractions, [zoneTyp]: sanitized } }
				: scenario
		);
	}

	type NamEditableKey = Exclude<keyof NamScenarioForm, 'ids' | 'projectId'>;

	function updateNamScenario(index: number, key: NamEditableKey, value: number | string) {
		const sanitized =
			typeof value === 'string' && (key === 'water_balance_mode' || key === 'storm_center_mode' || key === 'routing_method')
				? value
				: sanitizeNumber(value as number);

		namScenarioForms = namScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, [key]: sanitized } : scenario
		);
	}

	function buildBulkPayload() {
		return {
			idf: {
				idf_id: data.project.IDF_Parameters?.id ?? null,
				P_low_1h: sanitizeNumber(pLow1h),
				P_high_1h: sanitizeNumber(pHigh1h),
				P_low_24h: sanitizeNumber(pLow24h),
				P_high_24h: sanitizeNumber(pHigh24h),
				rp_low: sanitizeNumber(rpLow),
				rp_high: sanitizeNumber(rpHigh)
			},
			modFliesszeit: modScenarioForms.map((scenario, index) => ({
				ids: scenario.ids,
				project_id: scenario.projectId,
				Vo20: sharedVo20Values[index] ?? scenario.vo20,
				psi: scenario.psi
			})),
			koella: koellaScenarioForms.map((scenario, index) => ({
				ids: scenario.ids,
				project_id: scenario.projectId,
				Vo20: sharedVo20Values[index] ?? scenario.vo20,
				glacier_area: scenario.glacier_area
			})),
			clarkWSL: clarkScenarioForms.map((scenario) => ({
				ids: scenario.ids,
				project_id: scenario.projectId,
				fractions: scenario.fractions
			})),
			nam: namScenarioForms.map((scenario) => ({
				ids: scenario.ids,
				project_id: scenario.projectId,
				precipitation_factor: scenario.precipitation_factor,
				readiness_to_drain: scenario.readiness_to_drain,
				water_balance_mode: scenario.water_balance_mode,
				storm_center_mode: scenario.storm_center_mode,
				routing_method: scenario.routing_method
			}))
		};
	}

	$effect(() => {
		mod_fliesszeit_scenarios;
		koella_scenarios;
		clark_wsl_scenarios;
		nam_scenarios;
		initializeScenarioForms();
	});

	$effect(() => {
		modScenarioForms;
		koellaScenarioForms;
		clarkScenarioForms;
		namScenarioForms;
		combinedScenarioRange = createRange(Math.max(modScenarioForms.length, koellaScenarioForms.length));
		clarkScenarioRange = createRange(clarkScenarioForms.length);
		namScenarioRange = createRange(namScenarioForms.length);
	});

	$effect(() => {
		bulkPayload = JSON.stringify(buildBulkPayload());
	});

	function showResults() {
		let mod_fliesszeit_data: { name: string; color: string; data: (number | null)[] } = {
			name: 'Mod. Fliesszeitverfahren',
			color: '#1376ef',
			data: []
		};
		const mf_23 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 30);
		const mf_20 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 100);
		const mf_100 = mod_verfahren.find((mf: { Annuality: { number: number } }) => mf.Annuality?.number == 300);
		
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
		const k_23 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 30);
		const k_20 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 100);
		const k_100 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 300);
		
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
		const c_23 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 30);
		const c_20 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 100);
		const c_100 = clark_wsl.find((c: { Annuality: { number: number } }) => c.Annuality?.number == 300);
		
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
		const n_23 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 	30);
		const n_20 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 100);
		const n_100 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 300);
		
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
		mod_verfahren = data.project.Mod_Fliesszeit || [];
		koella = data.project.Koella || [];
		clark_wsl = data.project.ClarkWSL || [];
		nam = data.project.NAM || [];
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
	if (!ensureIdfInputs()) {
		return;
	}
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
			if (!response.ok) {
				throw new Error(`API returned status ${response.status}`);
			}
			const result = await response.json();
			if (!result?.task_id) {
				throw new Error('API response missing task_id');
			}
			// Each API call returns a group task_id for all climate scenarios
			groupTaskIds.push(result.task_id);
		} catch (error) {
			handleApiError('Error calculating ModFliess', error);
			toast.pop();
			return;
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
	if (!ensureIdfInputs()) {
		return;
	}
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
			if (!response.ok) {
				throw new Error(`API returned status ${response.status}`);
			}
			const result = await response.json();
			if (!result?.task_id) {
				throw new Error('API response missing task_id');
			}
			// Each API call returns a group task_id for all climate scenarios
			groupTaskIds.push(result.task_id);
		} catch (error) {
			handleApiError('Error calculating Koella', error);
			toast.pop();
			return;
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
	if (!ensureIdfInputs()) {
		return;
	}
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
			if (!response.ok) {
				throw new Error(`API returned status ${response.status}`);
			}
			const result = await response.json();
			if (!result?.task_id) {
				throw new Error('API response missing task_id');
			}
			// Each API call returns a group task_id for all climate scenarios
			groupTaskIds.push(result.task_id);
		} catch (error) {
			handleApiError('Error calculating ClarkWSL', error);
			toast.pop();
			return;
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
	if (!ensureIdfInputs()) {
		return;
	}
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
			if (!response.ok) {
				throw new Error(`API returned status ${response.status}`);
			}
			const result = await response.json();
			if (!result?.task_id) {
				throw new Error('API response missing task_id');
			}
			// Each API call returns a group task_id for all climate scenarios
			groupTaskIds.push(result.task_id);
		} catch (error) {
			handleApiError('Error calculating NAM', error);
			toast.pop();
			return;
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

	async function calculateProject(project_id: Number) {
	if (!ensureIdfInputs()) {
		return;
	}
		// Show modal and initialize progress
		(globalThis as any).$('#calculation-progress-modal').modal('show');
		const progressBarEl = document.querySelector('#calculation-progress-modal .progress-bar') as HTMLElement;

		if (progressBarEl) {
			progressBarEl.style.width = '0%';
			progressBarEl.setAttribute('aria-valuenow', '0');
		}
		
		try {
			const response = await fetch(
				env.PUBLIC_HAKESCH_API_PATH + '/discharge/calculate_project?ProjectId=' + project_id,
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
				throw new Error('API response missing task_id');
			}
			getGroupStatus(payload.task_id);
		} catch (error) {
			handleApiError('calculateProject failed', error);
			(globalThis as any).$('#calculation-progress-modal').modal('hide');
		}
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
				const completed = res.completed;
				const total = res.total;
				const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
				
				// Update progress bar
				const progressBarEl = document.querySelector('#calculation-progress-modal .progress-bar') as HTMLElement;
				const progressTextEl = document.getElementById('calculation-progresstext');
				
				if (progressBarEl) {
					progressBarEl.style.width = progress + '%';
					progressBarEl.setAttribute('aria-valuenow', progress.toString());
				}
				
				if (progressTextEl) {
					progressTextEl.innerHTML = `${completed} / ${total} (${progress}%)`;
				}
				
				if (completed === total) {
					(globalThis as any).$('#calculation-progress-modal').modal('hide');
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
					(globalThis as any).$('#calculation-progress-modal').modal('hide');
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
			.catch((err) => {
				console.log(err);
				(globalThis as any).$('#calculation-progress-modal').modal('hide');
			});
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

	// Coordinate conversion from EPSG:2056 (Swiss CH1903+ / LV95) to WGS84 lat/lon
	function convertEPSG2056ToWGS84(easting: number, northing: number): { lat: number; lon: number } {
		// Define EPSG:2056 projection if not already defined
		if (!proj4.defs('EPSG:2056')) {
			proj4.defs(
				'EPSG:2056',
				'+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs'
			);
		}
		
		// Convert from EPSG:2056 to WGS84 (EPSG:4326)
		// proj4 returns [lon, lat] for EPSG:4326
		const [lon, lat] = proj4('EPSG:2056', 'EPSG:4326', [easting, northing]);
		
		return { lat, lon };
	}

	async function fetchHadesValues() {
		if (!data.project.Point) {
			toast.push($_('page.discharge.calculation.hadesValuesNoCoordinates'), {
				theme: {
					'--toastColor': 'white',
					'--toastBackground': 'darkred'
				},
				initial: 0
			});
			return;
		}

		isFetchingHades = true;
		
		try {
			// Convert coordinates from EPSG:2056 to lat/lon
			const { lat, lon } = convertEPSG2056ToWGS84(data.project.Point.easting, data.project.Point.northing);
			
			// Fetch precipitation data from the API
			const response = await fetch(
				`${env.PUBLIC_HAKESCH_API_PATH}/netcdf/precipitation?lon=${lon}&lat=${lat}`,
				{
					method: 'GET',
					headers: {
						Authorization: 'Bearer ' + data.session.access_token
					}
				}
			);
			
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			
			const precipitationData = await response.json();
			
			// Extract the 50% probability values (median) for the IDF parameters
			const data10y60m = precipitationData.data['10_years_60_minutes'];
			const data10y24h = precipitationData.data['10_years_24h'];
			const data30y60m = precipitationData.data['30_years_60_minutes'];
			const data30y24h = precipitationData.data['30_years_24h'];
			const data100y60m = precipitationData.data['100_years_60_minutes'];
			const data100y24h = precipitationData.data['100_years_24h'];
			
			// Fill in the form values using reactive state
			pLow1h = Math.round(data30y60m.probability_levels['50%']*100)/100;
			pHigh1h = Math.round(data100y60m.probability_levels['50%']*100)/100;
			pLow24h = Math.round(data30y24h.probability_levels['50%']*100)/100;
			pHigh24h = Math.round(data100y24h.probability_levels['50%']*100)/100;
			
			// Set return periods
			rpLow = 30;
			rpHigh = 100;
			
			toast.push($_('page.discharge.calculation.hadesValuesSuccess'), {
				theme: {
					'--toastColor': 'mintcream',
					'--toastBackground': 'rgba(72,187,120,0.9)',
					'--toastBarBackground': '#2F855A'
				}
			});
			
		} catch (error) {
			console.error('Error fetching HADES values:', error);
			toast.push(
				'<h3 style="padding:5;">' + $_('page.discharge.calculation.hadesValuesError') + '</h3>' +
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
			isFetchingHades = false;
		}
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

<div
	id="missing-idf-modal"
	class="modal fade"
	tabindex="-1"
	role="dialog"
	aria-labelledby="missing-idf-modal-label"
	aria-hidden="true"
>
	<div class="modal-dialog modal-dialog-centered">
		<div class="modal-content">
			<div class="modal-header">
				<h4 class="modal-title" id="missing-idf-modal-label">
					{$_('page.discharge.calculation.missingIdfTitle')}
				</h4>
				<button
					type="button"
					class="btn-close"
					data-bs-dismiss="modal"
					aria-label={$_('page.general.close')}
				></button>
			</div>
			<div class="modal-body">
				<p>{$_('page.discharge.calculation.missingIdfMessage')}</p>
			</div>
			<div class="modal-footer">
				<button
					type="button"
					class="btn btn-primary"
					data-bs-dismiss="modal">{$_('page.general.ok')}</button
				>
			</div>
		</div>
	</div>
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
				<h4 class="modal-title" id="api-error-modal-label">
					{$_('page.discharge.calculation.calcerror')}
				</h4>
				<button
					type="button"
					class="btn-close btn-close-white"
					data-bs-dismiss="modal"
					aria-label={$_('page.general.close')}
				></button>
			</div>
			<div class="modal-body">
				<p>{apiErrorMessage}</p>
			</div>
			<div class="modal-footer border-0">
				<button
					type="button"
					class="btn btn-danger"
					data-bs-dismiss="modal">{$_('page.general.close')}</button
				>
			</div>
		</div>
	</div>
</div>

<!-- Calculation Progress Modal -->
<div
	id="calculation-progress-modal"
	class="modal fade"
	tabindex="-1"
	role="dialog"
	aria-labelledby="calculation-progress-modal-label"
	aria-hidden="true"
	data-bs-backdrop="static"
	data-bs-keyboard="false"
>
	<div class="modal-dialog">
		<div class="modal-content">
			<div class="modal-header">
				<h4 class="modal-title" id="calculation-progress-modal-label">
					{$_('page.discharge.calculation.calcrunning')}
				</h4>
			</div>
			<div class="modal-body">
				<div class="progress mb-2">
					<div
						class="progress-bar"
						role="progressbar"
						style="width: 0%"
						aria-valuenow="0"
						aria-valuemin="0"
						aria-valuemax="100"
					></div>
				</div>
			</div>
		</div>
	</div>
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
							class="dropdown-item"
							onclick={() => bulkSaveForm?.requestSubmit()}
							disabled={isBulkSaving}
							title={$_('page.general.save')}
							aria-label={$_('page.general.save')}
						>
							{#if isBulkSaving}
								<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
							{/if}
							<i class="ti ti-device-floppy me-1 fs-24 align-middle"></i>
							<span class="align-middle">{$_('page.general.save')}</span>
						</button>
						<button
							type="button"
							class="dropdown-item"
							onclick={() => calculateProject(data.project.id)}
							disabled={!couldCalculate || isBulkSaving}
							
							title={$_('page.general.calculate')}
							aria-label={$_('page.general.calculate')}
						>
							<i class="ti ti-calculator fs-24 me-1 fs-24 align-middle"></i>
							<span class="align-middle">{$_('page.general.calculate')}</span>
						</button>
						
					</div>
				</div>
				<!-- End dropdown -->

				<div class="d-none d-xl-flex align-items-center gap-2">
					<button
						type="button"
						class="btn btn-sm btn-icon btn-ghost-primary d-flex"
						onclick={() => bulkSaveForm?.requestSubmit()}
						disabled={isBulkSaving}
						title={$_('page.general.save')}
						aria-label={$_('page.general.save')}
					>
						{#if isBulkSaving}
							<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
						{/if}
						<i class="ti ti-device-floppy fs-24"></i>
					</button>
					<button
						type="button"
						class="btn btn-sm btn-icon btn-ghost-primary d-flex"
						onclick={() => calculateProject(data.project.id)}
						disabled={!couldCalculate || isBulkSaving}
						
						title={$_('page.general.calculate')}
						aria-label={$_('page.general.calculate')}
					>
						<i class="ti ti-calculator fs-24"></i>
					</button>

				</div>
			</div>

		</div>
		<div class="card-body">
			<div class="row">
				<!-- Input Part -->
                <div class="col-lg-4">
                    <form
                        class="d-none"
                        method="post"
                        action="?/bulkSave"
                        bind:this={bulkSaveForm}
                        use:enhance={() => {
                            isBulkSaving = true;
                            return async ({ result, update }) => {
                                await update({ reset: false });
                                isBulkSaving = false;
                                if (result.type === 'success' && result.data) {
                                    data.project = result.data;
                                    toast.push($_('page.discharge.calculation.successfullsave'), {
                                        theme: {
                                            '--toastColor': 'mintcream',
                                            '--toastBackground': 'rgba(72,187,120,0.9)',
                                            '--toastBarBackground': '#2F855A'
                                        }
                                    });
                                } else if (result.type === 'failure') {
                                    const failure = (result.data as { message?: string })?.message || $_('page.discharge.calculation.calcerror');
                                    toast.push(
                                        '<h3 style="padding:5;">' + failure + '</h3>',
                                        {
                                            theme: {
                                                '--toastColor': 'white',
                                                '--toastBackground': 'darkred'
                                            },
                                            initial: 0
                                        }
                                    );
                                }
                            };
                        }}
                    >
                        <input type="hidden" name="project_id" value={data.project.id} />
                        <input type="hidden" name="payload" value={bulkPayload} />
                    </form>

                    <div class="d-flex flex-wrap gap-2 mb-4">
                        <button
                            type="button"
                            class="btn btn-primary d-flex align-items-center gap-2"
                            onclick={() => bulkSaveForm?.requestSubmit()}
                            disabled={isBulkSaving}
                            title={$_('page.general.save')}
                            aria-label={$_('page.general.save')}
                        >
                            {#if isBulkSaving}
                                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                            {/if}
                            <i class="ti ti-device-floppy fs-20"></i>
                            <span>{$_('page.general.save')}</span>
                        </button>
                        <button
                            type="button"
                            class="btn btn-outline-primary d-flex align-items-center gap-2"
                            onclick={() => calculateProject(data.project.id)}
                            disabled={!couldCalculate || isBulkSaving}
                            title={$_('page.general.calculate')}
                            aria-label={$_('page.general.calculate')}
                        >
                            <i class="ti ti-calculator fs-20"></i>
                            <span>{$_('page.general.calculate')}</span>
                        </button>
                    </div>

                    <section class="mb-5">
                        <h4 class="text-muted">
                            {$_('page.discharge.calculation.inputsForPrecipitationIntensity')}
                        </h4>
                        <div class="row g-2 py-2 align-items-end">
                            <div class="mb-3 col-md-6">
                                <label for="P_low_1h" class="form-label">
                                    {$_('page.discharge.calculation.idf.precipLowerPeriod1h')}
                                </label>
                                <input
                                    type="number"
                                    step="any"
                                    class="form-control"
                                    id="P_low_1h"
                                    name="P_low_1h"
                                    bind:value={pLow1h}
                                />
                            </div>
                            <div class="mb-3 col-md-6">
                                <label for="P_low_24h" class="form-label">
                                    {$_('page.discharge.calculation.idf.precipLowerPeriod24h')}
                                </label>
                                <input
                                    type="number"
                                    step="any"
                                    class="form-control"
                                    id="P_low_24h"
                                    name="P_low_24h"
                                    bind:value={pLow24h}
                                />
                            </div>
                            <div class="mb-3 col-md-4"  style="display:none;">
                                <label for="rp_low" class="form-label">
                                    {$_('page.discharge.calculation.idf.returnPeriod')}
                                </label>
                                <select id="rp_low" name="rp_low" class="form-select" bind:value={rpLow}>
                                    {#each returnPeriod as rp}
                                        <option value={rp.id}>{rp.text}</option>
                                    {/each}
                                </select>
                            </div>
                        </div>
                        <div class="row g-2 align-items-end">
                            <div class="mb-3 col-md-6">
                                <label for="P_high_1h" class="form-label">
                                    {$_('page.discharge.calculation.idf.precipUpperPeriod1h')}
                                </label>
                                <input
                                    type="number"
                                    step="any"
                                    class="form-control"
                                    id="P_high_1h"
                                    name="P_high_1h"
                                    bind:value={pHigh1h}
                                />
                            </div>
                            <div class="mb-3 col-md-6">
                                <label for="P_high_24h" class="form-label">
                                    {$_('page.discharge.calculation.idf.precipUpperPeriod24h')}
                                </label>
                                <input
                                    type="number"
                                    step="any"
                                    class="form-control"
                                    id="P_high_24h"
                                    name="P_high_24h"
                                    bind:value={pHigh24h}
                                />
                            </div>
                            <div class="mb-3 col-md-4" style="display:none;">
                                <label for="rp_high" class="form-label">
                                    {$_('page.discharge.calculation.idf.upperReturnPeriod')}
                                </label>
                                <select id="rp_high" name="rp_high" class="form-select" bind:value={rpHigh}>
                                    {#each returnPeriod as rp}
                                        <option value={rp.id}>{rp.text}</option>
                                    {/each}
                                </select>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <button type="button" class="btn btn-secondary" onclick={fetchHadesValues} disabled={isFetchingHades}>
                                {#if isFetchingHades}
                                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                {/if}
                                {$_('page.discharge.calculation.hadesValues')}
                            </button>
                        </div>
                    </section>

                    {#if mod_verfahren.length > 0 || koella.length > 0}
                        <section class="mb-5">
                            <h4 class="text-muted mb-3">
                                {$_('page.discharge.calculation.modFliesszeit')} &amp; {$_('page.discharge.calculation.koells')}
                            </h4>
                            {#each combinedScenarioRange as scenarioIndex}
								<div class="row g-3 align-items-end">
									<div class="col-md-4">
										<label for={`shared-vo20-${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.modFZV.wettingVolume')}
										</label>
										<input
											id={`shared-vo20-${scenarioIndex}`}
											type="number"
											step="any"
											class="form-control"
											value={sharedVo20Values[scenarioIndex] ?? 0}
											oninput={(event) => {
												const target = event.currentTarget as HTMLInputElement;
												updateSharedVo20(
													scenarioIndex,
													sanitizeNumber(target.valueAsNumber ?? Number(target.value))
												);
											}}
										/>
									</div>
									{#if modScenarioForms[scenarioIndex]}
										<div class="col-md-4">
											<label for={`psi-scenario${scenarioIndex}`} class="form-label">
												{$_('page.discharge.calculation.modFZV.peakFlow')}
											</label>
											<input
												id={`psi-scenario${scenarioIndex}`}
												type="number"
												step="any"
												class="form-control"
												value={modScenarioForms[scenarioIndex].psi}
												oninput={(event) => {
													const target = event.currentTarget as HTMLInputElement;
													updateModPsi(
														scenarioIndex,
														sanitizeNumber(target.valueAsNumber ?? Number(target.value))
													);
												}}
											/>
										</div>
									{/if}
									{#if koellaScenarioForms[scenarioIndex]}
										<div class="col-md-4">
											<label for={`glacier_area-scenario${scenarioIndex}`} class="form-label">
												{$_('page.discharge.calculation.koella.glacierArea')} km<sup>2</sup>
											</label>
											<input
												id={`glacier_area-scenario${scenarioIndex}`}
												type="number"
												step="1"
												class="form-control"
												value={koellaScenarioForms[scenarioIndex].glacier_area}
												oninput={(event) => {
													const target = event.currentTarget as HTMLInputElement;
													updateGlacierArea(
														scenarioIndex,
														sanitizeNumber(target.valueAsNumber ?? Number(target.value))
													);
												}}
											/>
										</div>
									{/if}
								</div>
                            {/each}
                        </section>
                    {/if}

                    {#if clark_wsl.length > 0 || nam.length > 0}
                        <div class="row g-4">
                            {#if clark_wsl.length > 0}
                                <div class="col-12 col-xl-6">
                                    <section class="mb-5 mb-xl-0 h-100">
                                        <h4 class="text-muted mb-3">{$_('page.discharge.calculation.clarkwslname')}</h4>
                                        {#each clarkScenarioRange as scenarioIndex}
											<div class="row g-2 py-2 align-items-start">
												<div class="mb-3 col-md-12 d-flex">
													<div class="d-flex flex-column gap-2 w-100">
														{#each zones as z, i}
															<div class="d-flex align-items-center gap-2 flex-row">
																<label for={`zone_${i}-scenario${scenarioIndex}`} class="flex-fill text-end" style="max-width:100px;">{z.typ}</label>
																<div style="max-width:130px;">
																	<input
																		type="number"
																		step="any"
																		class="form-control text-end"
																		style="-webkit-appearance: none; -moz-appearance: textfield;"
																		id={`zone_${i}-scenario${scenarioIndex}`}
																		name={`zone_${i}`}
																		value={clarkScenarioForms[scenarioIndex]?.fractions?.[z.typ] ?? 0}
																		oninput={(event) => {
																			const target = event.currentTarget as HTMLInputElement;
																			updateFractionValue(
																				scenarioIndex,
																				z.typ,
																				sanitizeNumber(target.valueAsNumber ?? Number(target.value))
																			);
																		}}
																	/>
																</div>
																<div class="text-start">%</div>
															</div>
														{/each}
													</div>
												</div>
											</div>
                                        {/each}
                                    </section>
                                </div>
                            {/if}
                            {#if nam.length > 0}
                                <div class="col-12 col-xl-6">
                                    <section class="mb-5 mb-xl-0 h-100">
                                        <h4 class="text-muted mb-3">{$_('page.discharge.calculation.nam')}</h4>
                                        {#each namScenarioRange as scenarioIndex}
								<div class="row g-2 py-2 align-items-end" style="display:none;">
									<div class="mb-3 col-md-4">
										<label for={`precipitation_factor-scenario${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.namParams.precipitationFactor')}
										</label>
										<input
											type="number"
											step="any"
											class="form-control"
											id={`precipitation_factor-scenario${scenarioIndex}`}
											name="precipitation_factor"
											value={namScenarioForms[scenarioIndex]?.precipitation_factor ?? 0}
											oninput={(event) => {
												const target = event.currentTarget as HTMLInputElement;
												updateNamScenario(
													scenarioIndex,
													'precipitation_factor',
													sanitizeNumber(target.valueAsNumber ?? Number(target.value))
												);
											}}
										/>
									</div>
									<div class="mb-3 col-md-4">
										<label for={`readiness_to_drain-scenario${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.namParams.readinessToDrain')}
										</label>
										<input
											type="number"
											step="1"
											class="form-control"
											id={`readiness_to_drain-scenario${scenarioIndex}`}
											name="readiness_to_drain"
											value={namScenarioForms[scenarioIndex]?.readiness_to_drain ?? 0}
											oninput={(event) => {
												const target = event.currentTarget as HTMLInputElement;
												updateNamScenario(
													scenarioIndex,
													'readiness_to_drain',
													sanitizeNumber(target.valueAsNumber ?? Number(target.value))
												);
											}}
										/>
									</div>
								</div>
								<div class="row g-2 py-2 align-items-end" style="display:none;">
									<div class="mb-3 col-md-4">
										<label for={`water_balance_mode-scenario${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.namParams.waterBalanceMode')}
										</label>
										<select
											id={`water_balance_mode-scenario${scenarioIndex}`}
											name="water_balance_mode"
											class="form-select"
											value={namScenarioForms[scenarioIndex]?.water_balance_mode}
											onchange={(event) => {
												const target = event.currentTarget as HTMLSelectElement;
												updateNamScenario(scenarioIndex, 'water_balance_mode', target.value);
											}}
										>
											<option value="simple">{$_('page.discharge.calculation.namParams.simple')}</option>
											<option value="cumulative">{$_('page.discharge.calculation.namParams.advanced')}</option>
										</select>
									</div>
									<div class="mb-3 col-md-4">
										<label for={`storm_center_mode-scenario${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.namParams.stormCenterMode')}
										</label>
										<select
											id={`storm_center_mode-scenario${scenarioIndex}`}
											name="storm_center_mode"
											class="form-select"
											value={namScenarioForms[scenarioIndex]?.storm_center_mode}
											onchange={(event) => {
												const target = event.currentTarget as HTMLSelectElement;
												updateNamScenario(scenarioIndex, 'storm_center_mode', target.value);
											}}
										>
											<option value="centroid">{$_('page.discharge.calculation.namParams.centroid')}</option>
											<option value="discharge_point">{$_('page.discharge.calculation.namParams.dischargePoint')}</option>
										</select>
									</div>
									<div class="mb-3 col-md-4">
										<label for={`routing_method-scenario${scenarioIndex}`} class="form-label">
											{$_('page.discharge.calculation.namParams.routingMethod')}
										</label>
										<select
											id={`routing_method-scenario${scenarioIndex}`}
											name="routing_method"
											class="form-select"
											value={namScenarioForms[scenarioIndex]?.routing_method}
											onchange={(event) => {
												const target = event.currentTarget as HTMLSelectElement;
												updateNamScenario(scenarioIndex, 'routing_method', target.value);
											}}
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
											<label for={`zip_upload-scenario${scenarioIndex}`} class="form-label">
												{$_('page.discharge.calculation.namParams.uploadZipFile')}
											</label>
											<input
												type="file"
												class="form-control"
												id={`zip_upload-scenario${scenarioIndex}`}
												accept=".zip"
											onchange={(event) => {
													const target = event.currentTarget as HTMLInputElement;
													const file = target.files?.[0];
													const projectId = nam_scenarios[scenarioIndex]?.[0]?.project_id;
													if (file && projectId) {
														uploadZipFile(projectId, file);
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
                                        
                                    {/each}
                                    </section>
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
				<!-- End of Input Part -->
				<!-- Results Part -->
				<div class="col-lg-8">
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
											<strong>Klimaszenario (CH2025)</strong>
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
									
									<div class="row">
										<!-- Input Part -->
										<div class="col-lg-6">
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
										</div>
										<div class="col-lg-6">
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
															{#each mod_verfahren.slice().sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as mod_fz}
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
															{#each koella.slice().sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as k}
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
															{#each clark_wsl.slice().sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as k}
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
															{#each nam.slice().sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as n}
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
					</div>
				</div>
				<!-- End of Results Part -->
			</div>
		</div>
	</div>
</div>
