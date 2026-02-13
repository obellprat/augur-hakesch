<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import { currentProject } from '$lib/state.svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { base } from '$app/paths';
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

	const initTooltip: Action<HTMLElement> = (node) => {
		let tooltip: any = null;
		let checkInterval: ReturnType<typeof setInterval> | null = null;

		const init = () => {
			if (typeof (window as any).bootstrap !== 'undefined') {
				tooltip = new (window as any).bootstrap.Tooltip(node);
				if (checkInterval) {
					clearInterval(checkInterval);
					checkInterval = null;
				}
			}
		};

		// Try to initialize immediately
		init();

		// If Bootstrap isn't available yet, check periodically
		if (!tooltip) {
			checkInterval = setInterval(init, 100);
			// Stop checking after 5 seconds
			setTimeout(() => {
				if (checkInterval) {
					clearInterval(checkInterval);
					checkInterval = null;
				}
			}, 5000);
		}

		return {
			destroy: () => {
				if (checkInterval) {
					clearInterval(checkInterval);
				}
				if (tooltip) {
					tooltip.dispose();
				}
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
			type: 'line',
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
			const sortedNamResults = namResults
				.slice()
				.sort((a, b) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0));

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
			const timeSteps = Array.from(
				{ length: dataLength },
				(_, index) => (globalStartIndex + index) * 10
			);

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
							formatter: function (value: string) {
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
								return val.toFixed(1);
							}
						}
					},
					tooltip: {
						y: {
							formatter: function (val: number) {
								return (
									val.toFixed(1) + ' ' + $_('page.discharge.calculation.chart.dischargeTooltip')
								);
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
					series: [
						{
							name: $_('page.discharge.calculation.chart.discharge'),
							data: filteredData,
							color: '#1376ef'
						}
					],
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
							formatter: function (value: string) {
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
								return val.toFixed(1);
							}
						}
					},
					tooltip: {
						y: {
							formatter: function (val: number) {
								return (
									val.toFixed(1) + ' ' + $_('page.discharge.calculation.chart.dischargeTooltip')
								);
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
	let zones: { typ: string; V0_20?: number; WSV?: number; psi?: number; alpha?: number }[] =
		data.zones;

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
	
	// Track which values have been manually edited (so they don't get overwritten by calculations)
	let manuallyEditedVo20 = $state<Set<number>>(new Set());
	let manuallyEditedPsi = $state<Set<number>>(new Set());
	let isInitialized = $state(false);

	const createRange = (count: number): number[] =>
		Array.from({ length: Math.max(count, 0) }, (_, index) => index);
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
			current: baseFieldName,
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
	//k.Koella_Result?.HQ.toFixed(1)

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
				precipitation_factor: sanitizeNumber(base?.precipitation_factor ?? 0.748),
				readiness_to_drain: sanitizeNumber(base?.readiness_to_drain ?? 0),
				water_balance_mode: base?.water_balance_mode || 'uniform',
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
		
		// Check if database values differ from calculated values (indicating manual edits)
		// Only do this on first initialization to avoid reactive loops
		if (!isInitialized) {
			const newManuallyEditedVo20 = new Set<number>();
			const newManuallyEditedPsi = new Set<number>();
			
			// Compare database values with calculated values
			for (let index = 0; index < Math.max(newModForms.length, newClarkForms.length); index++) {
				if (newClarkForms[index] !== undefined) {
					const calculatedVo20 = calculateSummaryV0_20(index);
					const calculatedPsi = calculateSummaryPsi(index);
					const dbVo20 = sharedVo20Values[index] ?? 0;
					const dbPsi = newModForms[index]?.psi ?? 0;
					
					// If database value differs significantly from calculated, mark as manually edited
					if (Math.abs(dbVo20 - calculatedVo20) > 0.01) {
						newManuallyEditedVo20.add(index);
					}
					if (Math.abs(dbPsi - calculatedPsi) > 0.0001) {
						newManuallyEditedPsi.add(index);
					}
				}
			}
			
			manuallyEditedVo20 = newManuallyEditedVo20;
			manuallyEditedPsi = newManuallyEditedPsi;
			isInitialized = true;
		}
	}

	function updateSharedVo20(index: number, value: number) {
		const sanitized = sanitizeNumber(value);
		// Mark as manually edited
		manuallyEditedVo20 = new Set([...manuallyEditedVo20, index]);
		sharedVo20Values = sharedVo20Values.map((current, idx) =>
			idx === index ? sanitized : current
		);
		modScenarioForms = modScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, vo20: sanitized } : scenario
		);
		koellaScenarioForms = koellaScenarioForms.map((scenario, idx) =>
			idx === index ? { ...scenario, vo20: sanitized } : scenario
		);
	}

	function updateModPsi(index: number, value: number) {
		const sanitized = sanitizeNumber(value);
		// Mark as manually edited
		manuallyEditedPsi = new Set([...manuallyEditedPsi, index]);
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
		
		// Always recalculate and update psi and vo20 values when percentage changes
		// This overwrites any previous manual edits when percentages are changed
		// Assuming clark scenario index aligns with combined scenario index
		const calculatedPsi = calculateSummaryPsi(index);
		const calculatedVo20 = calculateSummaryV0_20(index);
		
		// Update psi in modScenarioForms if it exists
		if (modScenarioForms[index] !== undefined) {
			modScenarioForms = modScenarioForms.map((scenario, idx) =>
				idx === index ? { ...scenario, psi: calculatedPsi } : scenario
			);
		}
		
		// Update vo20 in sharedVo20Values and both mod and koella forms
		if (index < sharedVo20Values.length) {
			sharedVo20Values = sharedVo20Values.map((current, idx) =>
				idx === index ? calculatedVo20 : current
			);
		}
		if (modScenarioForms[index] !== undefined) {
			modScenarioForms = modScenarioForms.map((scenario, idx) =>
				idx === index ? { ...scenario, vo20: calculatedVo20 } : scenario
			);
		}
		if (koellaScenarioForms[index] !== undefined) {
			koellaScenarioForms = koellaScenarioForms.map((scenario, idx) =>
				idx === index ? { ...scenario, vo20: calculatedVo20 } : scenario
			);
		}
		
		// Remove from manually edited sets since we're overwriting with calculated values
		manuallyEditedVo20.delete(index);
		manuallyEditedPsi.delete(index);
	}

	function calculateSummaryV0_20(scenarioIndex: number): number {
		const scenario = clarkScenarioForms[scenarioIndex];
		if (!scenario || !scenario.fractions) return 0;

		let sum = 0;
		zones.forEach((zone: any) => {
			const pct = scenario.fractions[zone.typ] ?? 0;
			const v0_20 = zone.V0_20 ?? 0;
			sum += (pct / 100) * v0_20;
		});
		return Math.round(sum * 100) / 100;
	}

	function calculateSummaryPsi(scenarioIndex: number): number {
		const scenario = clarkScenarioForms[scenarioIndex];
		if (!scenario || !scenario.fractions) return 0;

		let sum = 0;
		zones.forEach((zone: any) => {
			const pct = scenario.fractions[zone.typ] ?? 0;
			const psi = zone.psi ?? 0;
			sum += (pct / 100) * psi;
		});
		return Math.round(sum * 100) / 100;
	}

	function calculatePercentageSum(scenarioIndex: number): number {
		const scenario = clarkScenarioForms[scenarioIndex];
		if (!scenario || !scenario.fractions) return 0;

		let sum = 0;
		zones.forEach((zone: any) => {
			const pct = scenario.fractions[zone.typ] ?? 0;
			sum += pct;
		});
		return Math.round(sum * 100) / 100;
	}

	type NamEditableKey = Exclude<keyof NamScenarioForm, 'ids' | 'projectId'>;

	function updateNamScenario(index: number, key: NamEditableKey, value: number | string) {
		const sanitized =
			typeof value === 'string' &&
			(key === 'water_balance_mode' || key === 'storm_center_mode' || key === 'routing_method')
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
		combinedScenarioRange = createRange(
			Math.max(modScenarioForms.length, koellaScenarioForms.length)
		);
		clarkScenarioRange = createRange(clarkScenarioForms.length);
		namScenarioRange = createRange(namScenarioForms.length);
	});

	$effect(() => {
		bulkPayload = JSON.stringify(buildBulkPayload());
	});

	function showResults() {
		let mod_fliesszeit_data: { name: string; color: string; data: (number | null)[]; type?: string } = {
			name: 'Mod. Fliesszeitverfahren',
			color: '#1376ef',
			data: []
		};
		const mf_23 = mod_verfahren.find(
			(mf: { Annuality: { number: number } }) => mf.Annuality?.number == 30
		);
		const mf_20 = mod_verfahren.find(
			(mf: { Annuality: { number: number } }) => mf.Annuality?.number == 100
		);
		const mf_100 = mod_verfahren.find(
			(mf: { Annuality: { number: number } }) => mf.Annuality?.number == 300
		);

		const mf_30_value = getResultField(mf_23, 'Mod_Fliesszeit_Result')?.HQ
			? Number(getResultField(mf_23, 'Mod_Fliesszeit_Result').HQ.toFixed(1))
			: null;
		const mf_100_value = getResultField(mf_20, 'Mod_Fliesszeit_Result')?.HQ
			? Number(getResultField(mf_20, 'Mod_Fliesszeit_Result').HQ.toFixed(1))
			: null;
		const mf_300_value = getResultField(mf_100, 'Mod_Fliesszeit_Result')?.HQ
			? Number(getResultField(mf_100, 'Mod_Fliesszeit_Result').HQ.toFixed(1))
			: null;

		mod_fliesszeit_data.data.push(mf_30_value);
		mod_fliesszeit_data.data.push(mf_100_value);
		mod_fliesszeit_data.data.push(mf_300_value);

		let koella_data: { name: string; color: string; data: (number | null)[]; type?: string } = {
			name: 'Kölla',
			color: '#1e13ef',
			data: []
		};
		const k_23 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 30);
		const k_20 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 100);
		const k_100 = koella.find((k: { Annuality: { number: number } }) => k.Annuality?.number == 300);

		const k_30_value = getResultField(k_23, 'Koella_Result')?.HQ
			? Number(getResultField(k_23, 'Koella_Result').HQ.toFixed(1))
			: null;
		const k_100_value = getResultField(k_20, 'Koella_Result')?.HQ
			? Number(getResultField(k_20, 'Koella_Result').HQ.toFixed(1))
			: null;
		const k_300_value = getResultField(k_100, 'Koella_Result')?.HQ
			? Number(getResultField(k_100, 'Koella_Result').HQ.toFixed(1))
			: null;

		koella_data.data.push(k_30_value);
		koella_data.data.push(k_100_value);
		koella_data.data.push(k_300_value);

		let clark_wsl_data: { name: string; color: string; data: (number | null)[]; type?: string } = {
			name: 'Clark WSL',
			color: '#13e4ef',
			data: []
		};
		const c_23 = clark_wsl.find(
			(c: { Annuality: { number: number } }) => c.Annuality?.number == 30
		);
		const c_20 = clark_wsl.find(
			(c: { Annuality: { number: number } }) => c.Annuality?.number == 100
		);
		const c_100 = clark_wsl.find(
			(c: { Annuality: { number: number } }) => c.Annuality?.number == 300
		);

		const c_30_value = getResultField(c_23, 'ClarkWSL_Result')?.Q
			? Number(getResultField(c_23, 'ClarkWSL_Result').Q.toFixed(1))
			: null;
		const c_100_value = getResultField(c_20, 'ClarkWSL_Result')?.Q
			? Number(getResultField(c_20, 'ClarkWSL_Result').Q.toFixed(1))
			: null;
		const c_300_value = getResultField(c_100, 'ClarkWSL_Result')?.Q
			? Number(getResultField(c_100, 'ClarkWSL_Result').Q.toFixed(1))
			: null;

		clark_wsl_data.data.push(c_30_value);
		clark_wsl_data.data.push(c_100_value);
		clark_wsl_data.data.push(c_300_value);

		let nam_data: { name: string; color: string; data: (number | null)[]; type?: string } = {
			name: 'NAM',
			color: '#ef1313',
			data: []
		};
		const n_23 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 30);
		const n_20 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 100);
		const n_100 = nam.find((n: { Annuality: { number: number } }) => n.Annuality?.number == 300);

		nam_data.data.push(
			getResultField(n_23, 'NAM_Result')?.HQ
				? Number(getResultField(n_23, 'NAM_Result').HQ.toFixed(1))
				: null
		);
		nam_data.data.push(
			getResultField(n_20, 'NAM_Result')?.HQ
				? Number(getResultField(n_20, 'NAM_Result').HQ.toFixed(1))
				: null
		);
		nam_data.data.push(
			getResultField(n_100, 'NAM_Result')?.HQ
				? Number(getResultField(n_100, 'NAM_Result').HQ.toFixed(1))
				: null
		);

		// Calculate mean (average) values for each group (30, 100, 300) from the three methods
		function calculateMean(values: (number | null)[]): number | null {
			const validValues = values.filter((v): v is number => v !== null && typeof v === 'number');
			if (validValues.length === 0) return null;
			const sum = validValues.reduce((acc, val) => acc + val, 0);
			return sum / validValues.length;
		}

		// Calculate mean values for each group (30, 100, 300) from the three methods
		const mean_30 = calculateMean([mf_30_value, k_30_value, c_30_value]);
		const mean_100 = calculateMean([mf_100_value, k_100_value, c_100_value]);
		const mean_300 = calculateMean([mf_300_value, k_300_value, c_300_value]);

		// Set bar series type explicitly
		mod_fliesszeit_data.type = 'column';
		koella_data.type = 'column';
		clark_wsl_data.type = 'column';
		nam_data.type = 'column';

		chartOneOptions.series = [
			mod_fliesszeit_data,
			koella_data,
			clark_wsl_data,
			nam_data
		];

		// Helper to draw custom medium lines after chart render/update
		const drawMediumLines = (apexChart: any) => {
			try {
				if (!apexChart || !apexChart.w || !apexChart.w.globals) {
					return;
				}

				// Wait a bit for SVG to be fully rendered
				const findElements = () => {
					const el = apexChart.el;
					if (!el) return null;
					
					const svg = el.querySelector('svg');
					if (!svg) return null;
					
					// plotArea is inside the apexcharts-inner element
					const innerGroup = svg.querySelector('g.apexcharts-inner') as SVGGElement;
					if (!innerGroup) return null;
					
					// Find plotArea inside innerGroup, or use innerGroup itself
					const plotArea = innerGroup.querySelector('.apexcharts-plot-area') as SVGGElement || innerGroup;
					if (!plotArea) return null;
					
					return { svg, plotArea };
				};

				const elements = findElements();
				if (!elements) {
					// Try again after a short delay
					setTimeout(() => {
						const retryElements = findElements();
						if (retryElements) {
							drawMediumLines(apexChart);
						}
					}, 200);
					return;
				}

				const { svg, plotArea } = elements;

				const globals = apexChart.w.globals;
				const plotWidth = globals.gridWidth;
				const plotHeight = globals.gridHeight;
				const yMin = globals.minY;
				const yMax = globals.maxY;

				if (!plotWidth || !plotHeight || yMax === yMin) {
					return;
				}

				// Calculate y position (relative to plotArea)
				const getY = (val: number) => {
					return plotHeight - ((val - yMin) / (yMax - yMin)) * plotHeight;
				};

				// Get actual x positions by finding the bars for each category
				// ApexCharts creates bars with class 'apexcharts-bar-area'
				const bars = svg.querySelectorAll('.apexcharts-bar-area rect');
				const barsPerCategory = 4; // We have 4 series
				const categoryCenters: number[] = [];
				
				// Calculate center of each category group
				// Use simpler approach: calculate based on category index with offsets
				const categoryWidth = plotWidth / 3;
				
				for (let catIndex = 0; catIndex < 3; catIndex++) {
					// Base position for each category (center of category)
					let baseCenter = categoryWidth * (catIndex + 0.5);
					
					// Try to get actual bar positions if available for more accurate positioning
					const firstBarIndex = catIndex * barsPerCategory;
					const lastBarIndex = firstBarIndex + barsPerCategory - 1;
					
					// Use smaller fixed pixel offsets for subtle positioning
					const leftOffset = -30; // Move left line 30 pixels to the left
					const rightOffset = 30;  // Move right line 30 pixels to the right
					
					if (firstBarIndex < bars.length && lastBarIndex < bars.length) {
						const firstBar = bars[firstBarIndex] as SVGRectElement;
						const lastBar = bars[lastBarIndex] as SVGRectElement;
						const firstBarX = parseFloat(firstBar.getAttribute('x') || '0');
						const lastBarX = parseFloat(lastBar.getAttribute('x') || '0');
						const lastBarWidth = parseFloat(lastBar.getAttribute('width') || '0');
						
						// Use actual bar center as base
						baseCenter = (firstBarX + lastBarX + lastBarWidth) / 2;
						
						// Apply fixed pixel offsets: move left line left, right line right
						if (catIndex === 0) {
							// Move left line to the left by fixed pixels
							baseCenter = baseCenter + leftOffset;
						} else if (catIndex === 2) {
							// Move right line to the right by fixed pixels
							baseCenter = baseCenter + rightOffset;
						}
					} else {
						// Fallback: use calculated positions with fixed pixel offsets
						if (catIndex === 0) {
							// Move left - shift by fixed pixels to the left
							baseCenter = baseCenter + leftOffset;
						} else if (catIndex === 2) {
							// Move right - shift by fixed pixels to the right
							baseCenter = baseCenter + rightOffset;
						}
					}
					
					categoryCenters.push(baseCenter);
				}

				// Calculate line width based on actual bar group width
				// Make lines shorter so the shift is more visible
				let lineHalfWidth = plotWidth / 3 * 0.25; // Default - shorter lines
				if (bars.length > 0) {
					const firstBar = bars[0] as SVGRectElement;
					const barWidth = parseFloat(firstBar.getAttribute('width') || '0');
					lineHalfWidth = (barWidth * barsPerCategory) * 0.25; // Shorter lines
				}

				// Remove any existing medium lines and labels
				const existingLines = svg.querySelectorAll('.medium-line, .medium-line-label');
				existingLines.forEach((element: SVGElement) => element.remove());

				const makeLine = (centerX: number, value: number | null, label: string) => {
					if (value === null || !Number.isFinite(value)) return;
					const y = getY(value);
					
					// Create the dashed line (teal/cyan blue that contrasts well with other blue bars)
					const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
					line.setAttribute('class', 'medium-line');
					line.setAttribute('x1', String(centerX - lineHalfWidth));
					line.setAttribute('x2', String(centerX + lineHalfWidth));
					line.setAttribute('y1', String(y));
					line.setAttribute('y2', String(y));
					line.setAttribute('stroke', '#00a8cc'); // Bright teal/cyan that contrasts with blue bars
					line.setAttribute('stroke-width', '2.5'); // Slightly thicker
					line.setAttribute('stroke-dasharray', '5,5');
					line.setAttribute('opacity', '1');
					line.setAttribute('style', 'pointer-events: none;');
					plotArea.appendChild(line);
					
					// Create text label for the value (teal color, with m3/s unit)
					const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					text.setAttribute('class', 'medium-line-label');
					text.setAttribute('x', String(centerX + lineHalfWidth + 5)); // Position to the right of the line
					text.setAttribute('y', String(y - 3)); // Slightly above the line
					text.setAttribute('fill', '#00a8cc'); // Bright teal color
					text.setAttribute('font-size', '12px');
					text.setAttribute('font-weight', '600'); // Bolder for better readability
					text.setAttribute('font-family', 'Arial, sans-serif');
					text.setAttribute('style', 'pointer-events: none;');
					text.textContent = `${value.toFixed(1)} m³/s`;
					plotArea.appendChild(text);
				};

				makeLine(categoryCenters[0], mean_30, 'Mean 30');
				makeLine(categoryCenters[1], mean_100, 'Mean 100');
				makeLine(categoryCenters[2], mean_300, 'Mean 300');
			} catch (error) {
				// Silently handle errors
			}
		};

		// Set up event handlers for drawing lines
		chartOneOptions.chart.events = {
			...(chartOneOptions.chart.events || {}),
			drawn: (chartContext: any, config: any) => {
				setTimeout(() => {
					drawMediumLines(chartContext);
				}, 100);
			},
			animationEnd: (chartContext: any, config: any) => {
				setTimeout(() => {
					drawMediumLines(chartContext);
				}, 100);
			},
			resized: (chartContext: any, config: any) => {
				// Wait longer for chart to fully resize
				setTimeout(() => {
					drawMediumLines(chartContext);
				}, 300);
			},
			dataPointSelection: (chartContext: any, config: any) => {
				// Redraw lines after any interaction
				setTimeout(() => {
					drawMediumLines(chartContext);
				}, 100);
			}
		};

		// Update chart
		if (chart.ref) {
			chart.ref.updateSeries(chartOneOptions.series);
			chart.ref.updateOptions(chartOneOptions);
			
			// Draw lines after update
			setTimeout(() => {
				if (chart.ref) {
					drawMediumLines(chart.ref);
				}
			}, 500);
		}
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
				precipitation_factor: 0.748,
				readiness_to_drain: 1,
				water_balance_mode: 'uniform',
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
			const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/file/upload-zip/${project_id}`, {
				method: 'POST',
				headers: {
					Authorization: 'Bearer ' + data.session.access_token
				},
				body: formData
			});

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
		taskIDs.forEach((id) => taskStatuses.set(id, 'PENDING'));

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
		const progressBarEl = document.querySelector(
			'#calculation-progress-modal .progress-bar'
		) as HTMLElement;

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
				const progressBarEl = document.querySelector(
					'#calculation-progress-modal .progress-bar'
				) as HTMLElement;
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
		groupTaskIds.forEach((id) =>
			groupStatuses.set(id, { completed: 0, total: 0, status: 'PENDING' })
		);

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
			const { lat, lon } = convertEPSG2056ToWGS84(
				data.project.Point.easting,
				data.project.Point.northing
			);

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
			pLow1h = Math.round(Math.round(data30y60m.probability_levels['50%'] * 100) / 100);
			pHigh1h = Math.round(Math.round(data100y60m.probability_levels['50%'] * 100) / 100);
			pLow24h = Math.round(Math.round(data30y24h.probability_levels['50%'] * 100) / 100);
			pHigh24h = Math.round(Math.round(data100y24h.probability_levels['50%'] * 100) / 100);

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
				'<h3 style="padding:5;">' +
					$_('page.discharge.calculation.hadesValuesError') +
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
			isFetchingHades = false;
		}
	}

	// Add window resize listener to redraw lines when window is resized
	let resizeTimeout: ReturnType<typeof setTimeout> | null = null;
	const handleResize = () => {
		// Debounce resize events
		if (resizeTimeout) {
			clearTimeout(resizeTimeout);
		}
		resizeTimeout = setTimeout(() => {
			if (chart.ref) {
				// Wait for ApexCharts to finish resizing, then redraw lines
				setTimeout(() => {
					// Redraw the lines by calling showResults which will trigger the drawn event
					showResults();
				}, 300);
			}
		}, 150);
	};

	onMount(async () => {
		// Check if soil shape-file exists
		await checkSoilFileExists(data.project.id);

		if (data.project.isozones_taskid === '' || data.project.isozones_running) {
			(globalThis as any).$('#missinggeodata-modal').modal('show');
		} else {
			couldCalculate = true;
		}

		// Add window resize listener to redraw lines when window is resized
		window.addEventListener('resize', handleResize);
	});

	// Cleanup on component destroy
	$effect(() => {
		return () => {
			window.removeEventListener('resize', handleResize);
			if (resizeTimeout) {
				clearTimeout(resizeTimeout);
			}
		};
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
				<button type="button" class="btn btn-light" data-bs-dismiss="modal" onclick={addCalculation}
					>{$_('page.general.ok')}</button
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
				<button type="button" class="btn btn-primary" data-bs-dismiss="modal"
					>{$_('page.general.ok')}</button
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
				<button type="button" class="btn btn-danger" data-bs-dismiss="modal"
					>{$_('page.general.close')}</button
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

<!-- ClarkWSL Help Modal -->
<div
	id="clarkwsl-help-modal"
	class="modal fade"
	tabindex="-1"
	role="dialog"
	aria-labelledby="clarkwsl-help-modal-label"
	aria-hidden="true"
>
	<div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
		<div class="modal-content">
			<div class="modal-header">
				<h4 class="modal-title" id="clarkwsl-help-modal-label">ClarkWSL - Abflussprozesse</h4>
				<button
					type="button"
					class="btn-close"
					data-bs-dismiss="modal"
					aria-label={$_('page.general.close')}
				></button>
			</div>
			<div class="modal-body">
				<p>
					Bei der Hochwasserabflussbildung spielen neben der Dauer und der Intensität von
					Starkniederschlägen und der Grösse/Topographie des Einzugsgebiets die auftretenden
					Abflussprozesse eine entscheidende Rolle. Zu den wichtigsten bei Starkregen auftretenden
					Abflussprozessen zählen der Oberflächenabfluss aufgrund von Infiltrationshemmnissen (HOF),
					der gesättigte Oberflächenabfluss (SOF), der Abfluss im Boden (SSF) und die
					Tiefenversickerung (DP). Die Abflussprozesstypen können zusätzlich nach ihrer Reaktion in
					rasch beitragend (z.B. SSF1), verzögert beitragend (z.B. SSF2) und stark verzögert
					beitragend (z.B. SSF3) unterschieden werden. Methoden zur Bestimmung der im Einzugsgebiet
					auftretenden Abflussprozesse sind z.B. in [1], [2] oder [3] beschrieben.
				</p>
				<p>
					Eine flächendifferenzierte Ansprache der Abflusstypen mit Zuordnung der
					Reaktionsfreudigkeit erfordert einen hohen Arbeitsaufwand und ist mit Unschärfen
					verbunden. Stattdessen wird vorgeschlagen, die Abflussprozesse nach ihrer Abflussreaktion
					in Abflussklassen zu unterteilen:
				</p>
				<table class="table table-sm table-bordered">
					<thead>
						<tr>
							<th>Abflussreaktion Klasse</th>
							<th>Beschreibung</th>
							<th>Abflussprozesse</th>
						</tr>
					</thead>
					<tbody>
						<tr>
							<td>Klasse 1</td>
							<td>rasch und stark beitragend</td>
							<td>HOF1, SOF1</td>
						</tr>
						<tr>
							<td>Klasse 2</td>
							<td>leicht verzögert beitragend</td>
							<td>HOF2, SOF2, SSF1</td>
						</tr>
						<tr>
							<td>Klasse 3</td>
							<td>verzögert beitragend</td>
							<td>SOF3, SSF2</td>
						</tr>
						<tr>
							<td>Klasse 4</td>
							<td>stark verzögert beitragend</td>
							<td>SOF3, SSF3</td>
						</tr>
						<tr>
							<td>Klasse 5</td>
							<td>sehr stark verzögert beitragend</td>
							<td>DP</td>
						</tr>
					</tbody>
				</table>
				<p class="mt-3">
					<strong>Literatur:</strong>
				</p>
				<ol>
					<li>
						«Hochwasserabschätzung in schweizerischen Einzugsgebieten Praxishilfe Berichte des BWG,
						Serie Wasser Nr. 4, Bern 2003.
					</li>
					<li>
						«Automatisch hergeleitete Abflussprozesskarten – ein neues Werkzeug zur Abschätzung von
						Hochwasserabflüssen, Felix Naef et al., «Wasser Energie Luft» – 99. Jahrgang, 2007, Heft
						3, CH-5401 Baden.
					</li>
					<li>
						Scherrer, S. (2006): Bestimmungsschlüssel zur Identifikation von hochwasserrelevanten
						Flächen, Herausgeber: Landesamt für Umwelt, Wasserwirtschaft und Gewerbeaufsicht
						Rheinland-Pfalz (LUWG).
					</li>
				</ol>
			</div>
			<div class="modal-footer">
				<button type="button" class="btn btn-primary" data-bs-dismiss="modal">
					{$_('page.general.close')}
				</button>
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
				<a
					href="{base}/assets/documents/Be01_HydrologieBE_20240715_VersionPDF.pdf"
					target="_blank"
					rel="noopener noreferrer"
					class="btn btn-sm btn-outline-primary d-flex align-items-center gap-2"
					title="Arbeitshilfe Hochwasserabschätzung"
					aria-label="Arbeitshilfe Hochwasserabschätzung"
				>
					<i class="ti ti-info-circle"></i>
					<span>Arbeitshilfe Hochwasserabschätzung</span>
				</a>
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
									const failure =
										(result.data as { message?: string })?.message ||
										$_('page.discharge.calculation.calcerror');
									toast.push('<h3 style="padding:5;">' + failure + '</h3>', {
										theme: {
											'--toastColor': 'white',
											'--toastBackground': 'darkred'
										},
										initial: 0
									});
								}
							};
						}}
					>
						<input type="hidden" name="project_id" value={data.project.id} />
						<input type="hidden" name="payload" value={bulkPayload} />
					</form>

					<section class="mb-1">
						<h4 class="text-muted">
							{$_('page.discharge.calculation.inputsForPrecipitationIntensity')}
						</h4>
						<div class="d-flex align-items-center gap-2 mt-3 mb-3">
							<button
								type="button"
								class="btn btn-secondary"
								onclick={fetchHadesValues}
								disabled={isFetchingHades}
							>
								{#if isFetchingHades}
									<span
										class="spinner-border spinner-border-sm me-2"
										role="status"
										aria-hidden="true"
									></span>
								{/if}
								{$_('page.discharge.calculation.hadesValues')}
							</button>
						</div>
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
							<div class="mb-3 col-md-4" style="display:none;">
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
					</section>

					<section class="">
						<h4 class="text-muted mb-3">
							{$_('page.discharge.calculation.hydrologicalCalculation')}
							<button
									type="button"
									class="btn btn-sm btn-link p-0"
									style="line-height: 1; color: var(--bs-info);"
									data-bs-toggle="modal"
									data-bs-target="#clarkwsl-help-modal"
									aria-label="ClarkWSL Hilfe"
									title="ClarkWSL Hilfe"
								>
									<i class="ti ti-info-circle fs-18"></i>
								</button>
						</h4>
		
						{#each clarkScenarioRange as scenarioIndex}
							<div class="row g-2 py-2 align-items-start">
								<div class="mb-3 col-md-12">
									<table class="table table-sm table-bordered">
										<thead>
											<tr>
												<th style="width: 30%;">Zone</th>
												<th style="width: 20%;">{$_('page.discharge.calculation.percentage')}</th>
												<th style="width: 15%;">{$_('page.discharge.calculation.modFZV.wettingVolume')}
													<span
														class="badge badge-circle"
														data-bs-toggle="tooltip"
														data-bs-trigger="hover"
														data-bs-placement="top"
														data-bs-title={$_('page.discharge.calculation.modFZV.wettingVolumeTooltip')}
														style="cursor: help; display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; padding: 0;"
														use:initTooltip
													>
														<i class="ri-question-line mb-1" style="font-weight: 100;"></i>
													</span></th>
												<th style="width: 15%;">WSV</th>
												<th style="width: 20%;">{$_('page.discharge.calculation.modFZV.peakFlow')}
													<span
														class="badge badge-circle"
														data-bs-toggle="tooltip"
														data-bs-trigger="hover"
														data-bs-placement="top"
														data-bs-title={$_('page.discharge.calculation.modFZV.peakFlowTooltip')}
														style="cursor: help; display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; padding: 0;"
														use:initTooltip
													>
														<i class="ri-question-line mb-1" style="font-weight: 100;"></i>
													</span></th>
											</tr>
										</thead>
										<tbody>
											{#each zones as z, i}
												<tr>
													<td>{z.typ}</td>
													<td>
														<input
															type="number"
															step="any"
															class="form-control text-end"
															style="-webkit-appearance: none; -moz-appearance: textfield;"
															id={`zone_${i}-scenario${scenarioIndex}`}
															name={`zone_${i}`}
															value={clarkScenarioForms[scenarioIndex]?.fractions?.[
																z.typ
															] ?? 0}
															oninput={(event) => {
																const target = event.currentTarget as HTMLInputElement;
																updateFractionValue(
																	scenarioIndex,
																	z.typ,
																	sanitizeNumber(
																		target.valueAsNumber ?? Number(target.value)
																	)
																);
															}}
														/>
													</td>
													<td class="text-end">{z.V0_20 ?? 0}</td>
													<td class="text-end">{z.WSV ?? 0}</td>
													<td class="text-end">{z.psi ?? 0}</td>
												</tr>
											{/each}
											{#each combinedScenarioRange as combinedIndex}
												<tr>
													<td></td>
													<td class="text-end fw-bold">{calculatePercentageSum(scenarioIndex)}%</td>
													<td><input
														id={`shared-vo20-${combinedIndex}`}
														type="number"
														step="any"
														max="99.999"
														class="form-control"
														class:is-invalid={(() => {
															const val = manuallyEditedVo20.has(combinedIndex)
																? (sharedVo20Values[combinedIndex] ?? 0)
																: (clarkScenarioForms[combinedIndex] !== undefined 
																	? calculateSummaryV0_20(combinedIndex) 
																	: (sharedVo20Values[combinedIndex] ?? 0));
															return val >= 100;
														})()}
														value={manuallyEditedVo20.has(combinedIndex)
															? (sharedVo20Values[combinedIndex] ?? 0)
															: (clarkScenarioForms[combinedIndex] !== undefined 
																? calculateSummaryV0_20(combinedIndex) 
																: (sharedVo20Values[combinedIndex] ?? 0))}
														oninput={(event) => {
															const target = event.currentTarget as HTMLInputElement;
															const inputValue = sanitizeNumber(target.valueAsNumber ?? Number(target.value));
															if (inputValue >= 100) {
																target.classList.add('is-invalid');
																toast.push($_('page.discharge.calculation.vo20ValidationError') || 'Vo20 value must be less than 100', {
																	theme: {
																		'--toastColor': 'white',
																		'--toastBackground': 'darkorange'
																	}
																});
															} else {
																target.classList.remove('is-invalid');
																updateSharedVo20(
																	combinedIndex,
																	inputValue
																);
															}
														}}
													/></td>	
													<td></td>
													<td><input
														id={`psi-scenario${combinedIndex}`}
														type="number"
														step="any"
														max="0.999"
														class="form-control"
														class:is-invalid={(() => {
															const val = manuallyEditedPsi.has(combinedIndex)
																? (modScenarioForms[combinedIndex]?.psi ?? 0)
																: (clarkScenarioForms[combinedIndex] !== undefined 
																	? calculateSummaryPsi(combinedIndex) 
																	: (modScenarioForms[combinedIndex]?.psi ?? 0));
															return val >= 1;
														})()}
														value={manuallyEditedPsi.has(combinedIndex)
															? (modScenarioForms[combinedIndex]?.psi ?? 0)
															: (clarkScenarioForms[combinedIndex] !== undefined 
																? calculateSummaryPsi(combinedIndex) 
																: (modScenarioForms[combinedIndex]?.psi ?? 0))}
														oninput={(event) => {
															const target = event.currentTarget as HTMLInputElement;
															const inputValue = sanitizeNumber(target.valueAsNumber ?? Number(target.value));
															if (inputValue >= 1) {
																target.classList.add('is-invalid');
																toast.push($_('page.discharge.calculation.psiValidationError') || 'Psi value must be less than 1', {
																	theme: {
																		'--toastColor': 'white',
																		'--toastBackground': 'darkorange'
																	}
																});
															} else {
																target.classList.remove('is-invalid');
																updateModPsi(
																	combinedIndex,
																	inputValue
																);
															}
														}}
													/></td>
												</tr>
										{/each}
										</tbody>
									</table>
									<div class="row g-2 mt-2">
										<div class="col-md-4">
											{#if koellaScenarioForms[scenarioIndex]}
												<div class="row g-2 py-2 align-items-end">
													<div class="col-md-12">
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
												</div>
												{/if}
										</div>
										<div class="col-md-8">
											{#each namScenarioRange as scenarioIndex}
											<div class="row g-2 py-2 align-items-end" style="display:none;">
												<div class="mb-3 col-md-4">
													<label
														for={`precipitation_factor-scenario${scenarioIndex}`}
														class="form-label"
													>
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
													<label
														for={`readiness_to_drain-scenario${scenarioIndex}`}
														class="form-label"
													>
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
													<label
														for={`water_balance_mode-scenario${scenarioIndex}`}
														class="form-label"
													>
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
														<option value="simple"
															>{$_('page.discharge.calculation.namParams.simple')}</option
														>
														<option value="cumulative"
															>{$_('page.discharge.calculation.namParams.advanced')}</option
														>
													</select>
												</div>
												<div class="mb-3 col-md-4">
													<label
														for={`storm_center_mode-scenario${scenarioIndex}`}
														class="form-label"
													>
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
														<option value="centroid"
															>{$_('page.discharge.calculation.namParams.centroid')}</option
														>
														<option value="discharge_point"
															>{$_('page.discharge.calculation.namParams.dischargePoint')}</option
														>
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
														<option value="time_values"
															>{$_('page.discharge.calculation.namParams.timeValues')}</option
														>
														<option value="travel_time"
															>{$_('page.discharge.calculation.namParams.traveltime')}</option
														>
														<option value="isozone"
															>{$_('page.discharge.calculation.namParams.traveltime')}</option
														>
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
										</div>
										
									</div>
								</div>
							</div>
						{/each}
						
					</section>
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
								<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"
								></span>
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
											<strong>{$_('page.discharge.calculation.climateScenario')} (CH2025)</strong>
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
													<h5 class="text-muted">
														{$_('page.discharge.calculation.chart.dischargeTimeSeries')}
													</h5>
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
																<th
																	class:fw-bold={selectedClimateScenario === 'current'}
																	class:text-primary={selectedClimateScenario === 'current'}
																	>Current</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '1_5_degree'}
																	class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>+1.5°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '2_degree'}
																	class:text-primary={selectedClimateScenario === '2_degree'}
																	>+2.0°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '3_degree'}
																	class:text-primary={selectedClimateScenario === '3_degree'}
																	>+3.0°C</th
																>
															</tr>
														</thead>
														<tbody>
															{#each mod_verfahren
																.slice()
																.sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as mod_fz}
																<tr>
																	<td>
																		{#if mod_fz.Annuality}
																			{mod_fz.Annuality.description}
																		{/if}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === 'current'}
																		class:text-primary={selectedClimateScenario === 'current'}
																	>
																		{mod_fz.Mod_Fliesszeit_Result?.HQ
																			? mod_fz.Mod_Fliesszeit_Result.HQ.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '1_5_degree'}
																		class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>
																		{mod_fz.Mod_Fliesszeit_Result_1_5?.HQ
																			? mod_fz.Mod_Fliesszeit_Result_1_5.HQ.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '2_degree'}
																		class:text-primary={selectedClimateScenario === '2_degree'}
																	>
																		{mod_fz.Mod_Fliesszeit_Result_2?.HQ
																			? mod_fz.Mod_Fliesszeit_Result_2.HQ.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '3_degree'}
																		class:text-primary={selectedClimateScenario === '3_degree'}
																	>
																		{mod_fz.Mod_Fliesszeit_Result_3?.HQ
																			? mod_fz.Mod_Fliesszeit_Result_3.HQ.toFixed(1)
																			: '-'}
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
																<th
																	class:fw-bold={selectedClimateScenario === 'current'}
																	class:text-primary={selectedClimateScenario === 'current'}
																	>Current</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '1_5_degree'}
																	class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>+1.5°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '2_degree'}
																	class:text-primary={selectedClimateScenario === '2_degree'}
																	>+2.0°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '3_degree'}
																	class:text-primary={selectedClimateScenario === '3_degree'}
																	>+3.0°C</th
																>
															</tr>
														</thead>
														<tbody>
															{#each koella
																.slice()
																.sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as k}
																<tr>
																	<td>
																		{#if k.Annuality}
																			{k.Annuality.description}
																		{/if}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === 'current'}
																		class:text-primary={selectedClimateScenario === 'current'}
																	>
																		{k.Koella_Result?.HQ ? k.Koella_Result.HQ.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '1_5_degree'}
																		class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>
																		{k.Koella_Result_1_5?.HQ
																			? k.Koella_Result_1_5.HQ.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '2_degree'}
																		class:text-primary={selectedClimateScenario === '2_degree'}
																	>
																		{k.Koella_Result_2?.HQ ? k.Koella_Result_2.HQ.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '3_degree'}
																		class:text-primary={selectedClimateScenario === '3_degree'}
																	>
																		{k.Koella_Result_3?.HQ ? k.Koella_Result_3.HQ.toFixed(1) : '-'}
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
																<th
																	class:fw-bold={selectedClimateScenario === 'current'}
																	class:text-primary={selectedClimateScenario === 'current'}
																	>Current</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '1_5_degree'}
																	class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>+1.5°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '2_degree'}
																	class:text-primary={selectedClimateScenario === '2_degree'}
																	>+2.0°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '3_degree'}
																	class:text-primary={selectedClimateScenario === '3_degree'}
																	>+3.0°C</th
																>
															</tr>
														</thead>
														<tbody>
															{#each clark_wsl
																.slice()
																.sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as k}
																<tr>
																	<td>
																		{#if k.Annuality}
																			{k.Annuality.description}
																		{/if}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === 'current'}
																		class:text-primary={selectedClimateScenario === 'current'}
																	>
																		{k.ClarkWSL_Result?.Q ? k.ClarkWSL_Result.Q.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '1_5_degree'}
																		class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>
																		{k.ClarkWSL_Result_1_5?.Q
																			? k.ClarkWSL_Result_1_5.Q.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '2_degree'}
																		class:text-primary={selectedClimateScenario === '2_degree'}
																	>
																		{k.ClarkWSL_Result_2?.Q
																			? k.ClarkWSL_Result_2.Q.toFixed(1)
																			: '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '3_degree'}
																		class:text-primary={selectedClimateScenario === '3_degree'}
																	>
																		{k.ClarkWSL_Result_3?.Q
																			? k.ClarkWSL_Result_3.Q.toFixed(1)
																			: '-'}
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
																<th
																	class:fw-bold={selectedClimateScenario === 'current'}
																	class:text-primary={selectedClimateScenario === 'current'}
																	>Current</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '1_5_degree'}
																	class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>+1.5°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '2_degree'}
																	class:text-primary={selectedClimateScenario === '2_degree'}
																	>+2.0°C</th
																>
																<th
																	class:fw-bold={selectedClimateScenario === '3_degree'}
																	class:text-primary={selectedClimateScenario === '3_degree'}
																	>+3.0°C</th
																>
															</tr>
														</thead>
														<tbody>
															{#each nam
																.slice()
																.sort((a: any, b: any) => (a.Annuality?.number || 0) - (b.Annuality?.number || 0)) as n}
																<tr>
																	<td>
																		{#if n.Annuality}
																			{n.Annuality.description}
																		{/if}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === 'current'}
																		class:text-primary={selectedClimateScenario === 'current'}
																	>
																		{n.NAM_Result?.HQ ? n.NAM_Result.HQ.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '1_5_degree'}
																		class:text-primary={selectedClimateScenario === '1_5_degree'}
																	>
																		{n.NAM_Result_1_5?.HQ ? n.NAM_Result_1_5.HQ.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '2_degree'}
																		class:text-primary={selectedClimateScenario === '2_degree'}
																	>
																		{n.NAM_Result_2?.HQ ? n.NAM_Result_2.HQ.toFixed(1) : '-'}
																	</td>
																	<td
																		class:fw-bold={selectedClimateScenario === '3_degree'}
																		class:text-primary={selectedClimateScenario === '3_degree'}
																	>
																		{n.NAM_Result_3?.HQ ? n.NAM_Result_3.HQ.toFixed(1) : '-'}
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
