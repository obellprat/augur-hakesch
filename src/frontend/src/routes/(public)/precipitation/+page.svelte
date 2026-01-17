<script lang="ts">
	import { onMount } from 'svelte';
	import { tick } from 'svelte';
	import pageTitle from '$lib/page/pageTitle';
	import { _ } from 'svelte-i18n';
	import type ApexCharts from 'apexcharts';
	import type { ApexOptions } from 'apexcharts';
	import type { PageData } from './$types';
	import type { Action } from 'svelte/action';
	import { base } from '$app/paths';

	import 'leaflet/dist/leaflet.css';

	export let data: PageData;

	$pageTitle = $_('page.precipitation.title');

	// Chart type definition
	type Chart = {
		options: ApexOptions;
		node?: HTMLDivElement;
		ref?: ApexCharts;
	};

	// Chart render action
	const renderChart: Action<HTMLDivElement, Chart> = (node, parameter) => {
		import('apexcharts')
			.then((module) => module.default)
			.then((ApexCharts) => {
				// If chart already exists, update it instead of creating a new one
				if (parameter.ref) {
					parameter.ref.updateOptions(parameter.options, false, false, false);
					parameter.ref.updateSeries(parameter.options.series || []);
				} else {
					// Create new chart instance
					const chart = new ApexCharts(node, parameter.options);
					parameter.node = node;
					parameter.ref = chart;
					chart.render();
				}
			});
		return {
			destroy: () => {
				parameter.ref?.destroy();
			}
		};
	};

	// Reactive variables
	let map: any;
	let precipitationChart: Chart | undefined;
	let selectedLocation: { lat: number; lng: number } | null = null;
	let precipitationData: any = null;
	let isLoading = false;
	let tilesPeriod = 20;
	let climateChangePeriod = '2030';
	let showUncertainty = false;
	let clickMarker: L.Marker | null = null;
	let autocompleteSuggestions: Array<{ display_name: string; lat: string; lon: string }> = [];
	let showAutocomplete = false;
	let searchQuery = '';
	let autocompleteTimeout: ReturnType<typeof setTimeout> | null = null;
	let showShareModal = false;
	let shareUrl = '';
	let shareUrlInput: HTMLInputElement;

	// Focus the URL input when modal opens
	$: if (showShareModal && shareUrlInput) {
		tick().then(() => {
			shareUrlInput?.focus();
			shareUrlInput?.select();
		});
	}

	// Bottom sheet state
	let isBottomSheetOpen = false;
	let isDragging = false;
	let startY = 0;
	let currentY = 0;
	let sheetHeight = 0;

	// DOM elements
	let mapContainer: HTMLElement;
	let bottomSheet: HTMLElement;
	let sheetHandle: HTMLElement;
	let periodSelect: HTMLSelectElement;
	let climatePeriodSelect: HTMLSelectElement;
	let uncertaintyCheckbox: HTMLInputElement;
	let searchInput: HTMLInputElement;

	onMount(async () => {
		const L = (await import('leaflet')).default;

		// Configure base tile layer
		let baseLayer = L.tileLayer(
			'https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png',
			{
				attribution:
					'Map tiles by <a href="http://augur.world">AUGUR</a> and &copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/about/" target="_blank">OpenStreetMap contributors</a>',
				subdomains: 'abcd',
				minZoom: 0,
				maxZoom: 20,
				opacity: 0.5
			}
		);

		// Configure AUGUR precipitation layer
		let augurLayer = L.tileLayer(
			`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`,
			{
				detectRetina: true,
				opacity: 1
			}
		);

		// Create map
		map = L.map(mapContainer, {
			center: L.latLng(0, 0),
			zoom: 4,
			minZoom: 4,
			maxZoom: 9,
			zoomControl: false,
			maxBounds: [
				[-50, -Infinity],
				[50, Infinity]
			],
			layers: [augurLayer, baseLayer]
		});

		// Initialize bottom sheet
		sheetHeight = bottomSheet.offsetHeight;

		// Add touch event listeners for bottom sheet
		sheetHandle.addEventListener('touchstart', handleTouchStart);
		sheetHandle.addEventListener('touchmove', handleTouchMove);
		sheetHandle.addEventListener('touchend', handleTouchEnd);

		// Add mouse event listeners for desktop
		sheetHandle.addEventListener('mousedown', handleMouseStart);

		// orange pin icon (SVG data URL)
		const orangePinSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41"><path d="M12.5 0C7 0 2.7 4.3 2.7 9.8c0 7.1 9.8 21 9.8 21s9.8-13.9 9.8-21C22.3 4.3 18 0 12.5 0z" fill="#ff7f00"/><circle cx="12.5" cy="9.8" r="3.5" fill="#ffffff"/></svg>`;
		const orangeIcon = L.icon({
			iconUrl: 'data:image/svg+xml;utf8,' + encodeURIComponent(orangePinSvg),
			iconSize: [25, 41],
			iconAnchor: [12, 41],
			popupAnchor: [1, -34]
		});

		// Handle initial location from URL parameters
		if (data.initialLocation) {
			selectedLocation = data.initialLocation;
			
			// Set climate period from URL if provided
			if (data.initialClimatePeriod) {
				climateChangePeriod = data.initialClimatePeriod;
				if (climatePeriodSelect) {
					climatePeriodSelect.value = climateChangePeriod;
				}
			}
			
			// Place marker at the location
			const latlng = L.latLng(data.initialLocation.lat, data.initialLocation.lng);
			if (clickMarker) {
				clickMarker.setLatLng(latlng);
				clickMarker.setIcon(orangeIcon);
			} else {
				clickMarker = L.marker(latlng, { icon: orangeIcon, riseOnHover: true }).addTo(map);
			}
			
			map.setView([data.initialLocation.lat, data.initialLocation.lng], 6);
			// Set loading state and open bottom sheet immediately to show spinner
			isLoading = true;
			if (bottomSheet) {
				bottomSheet.style.transform = '';
			}
			isBottomSheetOpen = true;
			await fetchPrecipitationData(data.initialLocation.lat, data.initialLocation.lng);
		}

		// Map click handler
		map.on('click', async (e: any) => {
            const latlng = e.latlng;
            const { lat, lng } = latlng;
            selectedLocation = { lat, lng };

            if (clickMarker) {
                clickMarker.setLatLng(latlng);
				clickMarker.setIcon(orangeIcon);
            } else {
            	clickMarker = L.marker(latlng, { icon: orangeIcon, riseOnHover: true }).addTo(map);
            }

            // Set loading state and open bottom sheet immediately to show spinner
            isLoading = true;
            if (bottomSheet) {
                bottomSheet.style.transform = '';
            }
            isBottomSheetOpen = true;
            
            // Fetch data (this will update isLoading when done)
            await fetchPrecipitationData(lat, lng);
		});

		// Event listeners for controls
		periodSelect.addEventListener('change', async (e) => {
			tilesPeriod = parseInt((e.target as HTMLSelectElement).value);
			await updateMapLayer();
		});

		climatePeriodSelect.addEventListener('change', (e) => {
			climateChangePeriod = (e.target as HTMLSelectElement).value;
			if (selectedLocation) {
				fetchPrecipitationData(selectedLocation.lat, selectedLocation.lng);
			}
		});

		uncertaintyCheckbox.addEventListener('change', (e) => {
			showUncertainty = (e.target as HTMLInputElement).checked;
			if (precipitationData) {
				updateChart();
			}
		});

		// Initialize location button
		document.getElementById('getLocation')?.addEventListener('click', getCurrentLocation);

		// Initialize search functionality
		searchInput.addEventListener('keypress', async (e) => {
			if (e.key === 'Enter') {
				const query = searchInput.value.trim();
				if (query) {
					showAutocomplete = false;
					await searchLocation(query);
				}
			}
		});

		// Initialize autocomplete on input
		searchInput.addEventListener('input', (e) => {
			const query = (e.target as HTMLInputElement).value.trim();
			searchQuery = query;
			if (query.length >= 2) {
				debounceAutocomplete(query);
			} else {
				autocompleteSuggestions = [];
				showAutocomplete = false;
			}
		});

		// Close autocomplete when clicking outside
		const handleClickOutside = (e: MouseEvent) => {
			const target = e.target as Node;
			const dropdown = document.querySelector('.autocomplete-dropdown');
			if (
				searchInput &&
				!searchInput.contains(target) &&
				dropdown &&
				!dropdown.contains(target)
			) {
				showAutocomplete = false;
			}
		};
		document.addEventListener('click', handleClickOutside);

		// Handle Escape key to close autocomplete
		searchInput.addEventListener('keydown', (e) => {
			if (e.key === 'Escape') {
				showAutocomplete = false;
			}
		});
	});

	// Touch event handlers for bottom sheet
	function handleTouchStart(e: TouchEvent) {
		isDragging = true;
		startY = e.touches[0].clientY;
		currentY = startY;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging) return;
		e.preventDefault();
		currentY = e.touches[0].clientY;
		const deltaY = currentY - startY;

		if (deltaY > 0) {
			// Dragging down - close the sheet
			const progress = Math.min(deltaY / 100, 1);
			bottomSheet.style.transform = `translateY(${progress * 100}%)`;
		}
	}

	function handleTouchEnd(e: TouchEvent) {
		if (!isDragging) return;
		isDragging = false;

		const deltaY = currentY - startY;
		if (deltaY > 50) {
			// Close the sheet
			isBottomSheetOpen = false;
		} else {
			// Snap back to open position
			bottomSheet.style.transform = 'translateY(0)';
		}
	}

	// Mouse event handlers for desktop
	function handleMouseStart(e: MouseEvent) {
		isDragging = true;
		startY = e.clientY;
		currentY = startY;

		const handleMouseMove = (e: MouseEvent) => {
			if (!isDragging) return;
			currentY = e.clientY;
			const deltaY = currentY - startY;

			if (deltaY > 0) {
				const progress = Math.min(deltaY / 100, 1);
				bottomSheet.style.transform = `translateY(${progress * 100}%)`;
			}
		};

		const handleMouseUp = () => {
			if (!isDragging) return;
			isDragging = false;

			const deltaY = currentY - startY;
			if (deltaY > 50) {
				isBottomSheetOpen = false;
			} else {
				bottomSheet.style.transform = 'translateY(0)';
			}

			document.removeEventListener('mousemove', handleMouseMove);
			document.removeEventListener('mouseup', handleMouseUp);
		};

		document.addEventListener('mousemove', handleMouseMove);
		document.addEventListener('mouseup', handleMouseUp);
	}

	async function fetchPrecipitationData(lat: number, lng: number) {
		isLoading = true;
		try {
			const response = await fetch(`/abfluss/precipitation/api/location?lat=${lat}&lng=${lng}`);
			precipitationData = await response.json();
			updateChart();
		} catch (error) {
			// Error handled silently
		} finally {
			isLoading = false;
		}
	}

	async function updateMapLayer() {
		if (map) {
			// Remove existing AUGUR layer
			map.eachLayer((layer: any) => {
				if (layer._url && layer._url.includes('augur.world')) {
					map.removeLayer(layer);
				}
			});

			// Add new AUGUR layer with updated period
			const L = (await import('leaflet')).default;
			const newAugurLayer = L.tileLayer(
				`https://augur.world/tilesaugur/tiles${tilesPeriod}/{z}/{x}/{y}.png`,
				{
					detectRetina: true,
					opacity: 1
				}
			);
			map.addLayer(newAugurLayer);
		}
	}

	function updateChart() {
		if (!precipitationData) return;

		const periods = Object.keys(precipitationData.period[climateChangePeriod].years);
		const presentValues = periods.map(
			(period: string) => precipitationData.period[climateChangePeriod].years[period].present
		);
		const climateChangeValues = periods.map(
			(period: string) => precipitationData.period[climateChangePeriod].years[period].climate_change
		);

		const chartOptions: ApexOptions = {
			chart: {
				type: 'bar',
				height: 200,
				animations: {
					enabled: false
				},
				stacked: false
			},
			series: [
				{
					name: 'Present',
					data: presentValues
				},
				{
					name: `Climate Change (${climateChangePeriod})`,
					data: climateChangeValues
				}
			],
			xaxis: {
				categories: periods.map((p: string) => `${p}-year`),
				title: {
					text: 'Return Period (years)'
				}
			},
			yaxis: {
				title: {
					text: 'Precipitation (mm/day)'
				}
			},
			colors: ['#3B82F6', '#87CEEB'], // Darker blue for present, light blue for climate change
			plotOptions: {
				bar: {
					horizontal: false,
					columnWidth: '70%',
					borderRadius: 4
				}
			},
			dataLabels: {
				enabled: false
			},
			legend: {
				position: 'top',
				labels: {
					colors: ['#000000', '#000000']
				}
			},
			tooltip: {
				y: {
					formatter: function (val: number) {
						return val + ' mm/day';
					}
				}
			}
		};

		// Always update the options property
		if (!precipitationChart) {
			precipitationChart = { options: chartOptions };
		} else {
			precipitationChart.options = chartOptions;
		}

		// If chart already exists, update it directly
		if (precipitationChart.ref) {
			precipitationChart.ref.updateOptions(chartOptions, false, false, false);
			precipitationChart.ref.updateSeries(chartOptions.series || []);
		}
	}

	function getCurrentLocation() {
		if (navigator.geolocation) {
			navigator.geolocation.getCurrentPosition(
				async (position) => {
					const { latitude, longitude } = position.coords;
					map.setView([latitude, longitude], 6);
					selectedLocation = { lat: latitude, lng: longitude };
					// Set loading state and open bottom sheet immediately to show spinner
					isLoading = true;
					if (bottomSheet) {
						bottomSheet.style.transform = '';
					}
					isBottomSheetOpen = true;
					await fetchPrecipitationData(latitude, longitude);
				},
				(error) => {
					alert('Unable to get your location. Please click on the map to select a location.');
				}
			);
		} else {
			alert('Geolocation is not supported by this browser.');
		}
	}

	function downloadData() {
		if (!precipitationData || !selectedLocation) return;

		const dataStr = JSON.stringify(precipitationData, null, 2);
		const dataBlob = new Blob([dataStr], { type: 'application/json' });
		const url = URL.createObjectURL(dataBlob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `precipitation_data_${selectedLocation.lat}_${selectedLocation.lng}.json`;
		link.click();
		URL.revokeObjectURL(url);
	}

	function debounceAutocomplete(query: string) {
		if (autocompleteTimeout) {
			clearTimeout(autocompleteTimeout);
		}
		autocompleteTimeout = setTimeout(() => {
			fetchAutocompleteSuggestions(query);
		}, 300);
	}

	async function fetchAutocompleteSuggestions(query: string) {
		try {
			// Use OpenStreetMap Nominatim for autocomplete
			const response = await fetch(
				`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`
			);
			const results = await response.json();
			autocompleteSuggestions = results;
			showAutocomplete = results.length > 0;
		} catch (error) {
			// Error handled silently
			autocompleteSuggestions = [];
			showAutocomplete = false;
		}
	}

	async function selectLocationFromAutocomplete(location: { lat: string; lon: string; display_name: string }) {
		const lat = parseFloat(location.lat);
		const lng = parseFloat(location.lon);

		// Get Leaflet instance
		const L = (await import('leaflet')).default;

		// Create orange pin icon (SVG data URL)
		const orangePinSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41"><path d="M12.5 0C7 0 2.7 4.3 2.7 9.8c0 7.1 9.8 21 9.8 21s9.8-13.9 9.8-21C22.3 4.3 18 0 12.5 0z" fill="#ff7f00"/><circle cx="12.5" cy="9.8" r="3.5" fill="#ffffff"/></svg>`;
		const orangeIcon = L.icon({
			iconUrl: 'data:image/svg+xml;utf8,' + encodeURIComponent(orangePinSvg),
			iconSize: [25, 41],
			iconAnchor: [12, 41],
			popupAnchor: [1, -34]
		});

		// Create or update marker
		const latlng = L.latLng(lat, lng);
		if (clickMarker) {
			clickMarker.setLatLng(latlng);
			clickMarker.setIcon(orangeIcon);
		} else {
			clickMarker = L.marker(latlng, { icon: orangeIcon, riseOnHover: true }).addTo(map);
		}

		map.setView([lat, lng], 6);
		selectedLocation = { lat, lng };
		// Set loading state and open bottom sheet immediately to show spinner
		isLoading = true;
		if (bottomSheet) {
			bottomSheet.style.transform = '';
		}
		isBottomSheetOpen = true;
		await fetchPrecipitationData(lat, lng);
		searchInput.value = '';
		autocompleteSuggestions = [];
		showAutocomplete = false;
	}

	async function searchLocation(query: string) {
		try {
			// Use OpenStreetMap Nominatim for geocoding
			const response = await fetch(
				`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`
			);
			const results = await response.json();

			if (results.length > 0) {
				const location = results[0];
				await selectLocationFromAutocomplete(location);
			} else {
				alert('Location not found. Please try a different search term.');
			}
		} catch (error) {
			alert('Error searching for location. Please try again.');
		}
	}

	async function shareLocation() {
		if (!selectedLocation) return;

		const url = `${window.location.origin}/${base}/precipitation?lat=${selectedLocation.lat}&lng=${selectedLocation.lng}&climate=${climateChangePeriod}`;
		shareUrl = url;

		// Try to copy to clipboard
		try {
			await navigator.clipboard.writeText(url);
		} catch (error) {
			// Clipboard API might not be available, but we'll still show the modal
			console.error('Failed to copy to clipboard:', error);
		}

		// Show the modal dialog
		showShareModal = true;
	}

	function closeShareModal() {
		showShareModal = false;
	}

	async function copyUrlToClipboard() {
		try {
			await navigator.clipboard.writeText(shareUrl);
		} catch (error) {
			console.error('Failed to copy to clipboard:', error);
		}
	}
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="precipitation-page">
	<!-- Top Search Bar with Location Button and Period Selector -->
	<div class="top-search-container">
		<div class="search-card">
			<input type="text" placeholder="Find a place..." bind:this={searchInput} />
			<svg class="search-icon" viewBox="0 0 24 24" fill="currentColor">
				<path
					d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
				/>
			</svg>
			<button type="button" class="location-btn" id="getLocation" aria-label="Get current location">
				<svg class="icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
					<path
						d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"
					/>
				</svg>
			</button>
			<div class="period-selector">
				<label class="control-card">
					<span>Return Period</span>
					<select bind:this={periodSelect}>
						<option value="10">10</option>
						<option value="20" selected>20</option>
						<option value="30">30</option>
						<option value="50">50</option>
						<option value="100">100</option>
					</select>
				</label>
			</div>
		</div>
		<!-- Autocomplete Dropdown -->
		{#if showAutocomplete && autocompleteSuggestions.length > 0}
			<div class="autocomplete-dropdown">
				{#each autocompleteSuggestions as suggestion}
					<button
						type="button"
						class="autocomplete-item"
						aria-label="Select location: {suggestion.display_name}"
						on:click={() => selectLocationFromAutocomplete(suggestion)}
					>
						<svg class="location-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
							<path
								d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"
							/>
						</svg>
						<span class="autocomplete-text">{suggestion.display_name}</span>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Map Container -->
	<div class="map-container" bind:this={mapContainer}></div>

	<!-- Bottom Sheet -->
	<div class="bottom-sheet" class:open={isBottomSheetOpen} bind:this={bottomSheet}>
		<div class="sheet-handle" bind:this={sheetHandle}></div>
		<div class="sheet-content">
			<!-- Topic Section -->
			<div class="topic-section">
				<h3>Precipitation</h3>
				<p class="description">Expected daily maximum precipitation.</p>
			</div>

			<!-- Graph Section -->
			<div class="graph-section">
				{#if precipitationChart}
					<div use:renderChart={precipitationChart}></div>
				{/if}
				{#if isLoading}
					<div class="loading-spinner">
						<div class="spinner"></div>
					</div>
				{/if}
			</div>

			<!-- Settings Section -->
			<div class="settings-section">
				<div class="setting-item">
					<label>
						<span style="margin-right:10px;">Climate Change Period</span>
						<select bind:this={climatePeriodSelect}>
							<option value="2030">2030</option>
							<option value="2050">2050</option>
							<option value="2090">2090</option>
						</select>
					</label>
				</div>

				<div class="setting-item">
					<label>
						<input type="checkbox" bind:this={uncertaintyCheckbox} />
						<span>Show Uncertainty Range</span>
					</label>
				</div>
			</div>

			<!-- Actions Section -->
			<div class="actions-section">
				<button type="button" class="action-button" on:click={downloadData}>
					<svg class="icon" viewBox="0 0 24 24" fill="currentColor">
						<path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
					</svg>
					<span>Download</span>
				</button>

				<button type="button" class="action-button share-button" on:click={shareLocation}>
					<svg class="icon" viewBox="0 0 24 24" fill="currentColor">
						<path
							d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"
						/>
					</svg>
					<span>Share</span>
					<div class="tooltip">Copied!</div>
				</button>
			</div>
		</div>
	</div>

	<!-- Share Modal -->
	{#if showShareModal}
		<div
			class="modal-overlay"
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
			tabindex="-1"
			on:click={closeShareModal}
			on:keydown={(e) => {
				if (e.key === 'Escape') {
					closeShareModal();
				}
			}}
		>
			<div class="modal-content" on:click|stopPropagation>
				<div class="modal-header">
					<h3 id="modal-title">Share Link</h3>
					<button type="button" class="modal-close" on:click={closeShareModal} aria-label="Close modal">
						<svg viewBox="0 0 24 24" fill="currentColor">
							<path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
						</svg>
					</button>
				</div>
				<div class="modal-body">
					<p class="modal-message">Link copied to clipboard!</p>
					<div class="url-container">
						<input
							type="text"
							readonly
							value={shareUrl}
							class="url-input"
							id="share-url-input"
							bind:this={shareUrlInput}
						/>
						<button type="button" class="copy-button" on:click={copyUrlToClipboard} aria-label="Copy URL">
							<svg viewBox="0 0 24 24" fill="currentColor">
								<path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
							</svg>
						</button>
					</div>
				</div>
				<div class="modal-footer">
					<button type="button" class="modal-button" on:click={closeShareModal}>Close</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style lang="scss">
	.precipitation-page {
		position: relative;
		width: 100%;
		padding-left: 24px;
		padding-right: 24px;
		height: calc(
			100vh - 65px - 80px - 40px
		); /* Subtract topbar (65px), footer (~80px), and extra 40px */
		overflow: hidden;
	}

	.map-container {
		width: 100%;
		height: 100%;
		position: relative;
		border-radius: 16px;
		overflow: hidden;
	}

	.map-controls {
		position: absolute;
		z-index: 1000;
	}

	.period-selector {
		top: 20px;
		left: 20px;
	}

	.top-search-container {
		position: absolute;
		top: 20px;
		left: 24px;
		right: 24px;
		z-index: 1001;
		margin-left: 8px;
		margin-right: 8px;
	}

	.location-button {
		top: 20px;
		right: 20px;
	}

	.search-container {
		top: 80px;
		left: 20px;
		right: 20px;
	}

	.control-card {
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(10px);
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 12px;
		padding: 12px 16px;
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;

		&:hover {
			background: rgba(255, 255, 255, 1);
			transform: translateY(-1px);
			box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		}

		select {
			border: none;
			background: transparent;
			font-size: 14px;
			font-weight: 500;
			outline: none;
			cursor: pointer;
		}

		.icon {
			width: 20px;
			height: 20px;
		}
	}

	.search-card {
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(10px);
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 12px;
		padding: 12px 16px;
		display: flex;
		align-items: center;
		gap: 12px;
		position: relative;
		z-index: 1;

		input {
			flex: 1;
			border: none;
			background: transparent;
			font-size: 14px;
			outline: none;
			color: #000;

			&::placeholder {
				color: #666;
			}
		}

		.search-icon {
			width: 20px;
			height: 20px;
			color: #666;
		}

		.location-btn {
			background: none;
			border: none;
			padding: 8px;
			border-radius: 8px;
			cursor: pointer;
			display: flex;
			align-items: center;
			justify-content: center;
			transition: all 0.2s ease;

			&:hover {
				background: rgba(0, 0, 0, 0.05);
			}

			.icon {
				width: 20px;
				height: 20px;
				color: #3b82f6;
			}
		}

		.period-selector {
			.control-card {
				background: rgba(255, 255, 255, 0.8);
				backdrop-filter: blur(10px);
				border: 1px solid rgba(0, 0, 0, 0.1);
				border-radius: 8px;
				padding: 8px 12px;
				display: flex;
				align-items: center;
				gap: 8px;
				font-size: 13px;
				font-weight: 500;
				cursor: pointer;
				transition: all 0.2s ease;
				margin: 0;

				&:hover {
					background: rgba(255, 255, 255, 1);
					transform: translateY(-1px);
					box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
				}

				span {
					white-space: nowrap;
					color: #374151;
				}

				select {
					border: none;
					background: transparent;
					font-size: 13px;
					font-weight: 500;
					outline: none;
					cursor: pointer;
					color: #000;
					min-width: 50px;
				}
			}
		}
	}

	.autocomplete-dropdown {
		position: absolute;
		top: calc(100% + 8px);
		left: 0;
		right: 0;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(10px);
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 12px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		max-height: 300px;
		overflow-y: auto;
		z-index: 1002;
		margin-top: 4px;

		.autocomplete-item {
			width: 100%;
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 12px 16px;
			border: none;
			background: transparent;
			cursor: pointer;
			text-align: left;
			transition: all 0.2s ease;
			border-bottom: 1px solid rgba(0, 0, 0, 0.05);

			&:last-child {
				border-bottom: none;
			}

			&:hover {
				background: rgba(0, 0, 0, 0.05);
			}

			&:active {
				background: rgba(0, 0, 0, 0.1);
			}

			.location-icon {
				width: 18px;
				height: 18px;
				color: #3b82f6;
				flex-shrink: 0;
			}

			.autocomplete-text {
				font-size: 14px;
				color: #1f2937;
				line-height: 1.4;
				overflow: hidden;
				text-overflow: ellipsis;
				display: -webkit-box;
				-webkit-line-clamp: 2;
				line-clamp: 2;
				-webkit-box-orient: vertical;
			}
		}
	}

	.bottom-sheet {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(20px);
		border-radius: 20px 20px 0 0;
		box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
		z-index: 1000;
		transform: translateY(100%);
		transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		touch-action: pan-y;
		max-width: calc(100% - 48px);
		left: 24px;
		right: 24px;
		overflow: hidden;

		&.open {
			transform: translateY(0);
		}
	}

	@media (max-width: 768px) {
		.bottom-sheet {
			max-width: calc(100% - 24px);
			left: 12px;
			right: 12px;
		}
	}

	@media (max-width: 480px) {
		.bottom-sheet {
			max-width: calc(100% - 8px);
			left: 4px;
			right: 4px;
		}
	}

	.sheet-handle {
		width: 40px;
		height: 4px;
		background: #ddd;
		border-radius: 2px;
		margin: 12px auto;
		cursor: grab;
		user-select: none;

		&:active {
			cursor: grabbing;
		}
	}

	.sheet-content {
		padding: 20px;
		max-height: calc(80vh - 40px);
		overflow-y: auto;
	}

	.topic-section {
		margin-bottom: 20px;

		h3 {
			margin: 0 0 8px 0;
			font-size: 20px;
			font-weight: 600;
			color: #1f2937;
		}

		.description {
			margin: 0;
			font-size: 14px;
			color: #6b7280;
		}
	}

	.graph-section {
		margin-bottom: 20px;
		position: relative;
		min-height: 200px;

		:global(.apexcharts-legend-text) {
			color: #000000 !important;
		}
	}

	.loading-spinner {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);

		.spinner {
			width: 32px;
			height: 32px;
			border: 3px solid #f3f4f6;
			border-top: 3px solid #3b82f6;
			border-radius: 50%;
			animation: spin 1s linear infinite;
		}
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	.settings-section {
		margin-bottom: 20px;
		width: fit-content;
		margin-left: auto;

		.setting-item {
			margin-bottom: 16px;

			label {
				display: flex;
				align-items: center;
				justify-content: space-between;
				font-size: 14px;
				color: #374151;

				span {
					font-weight: 500;
				}

				select {
					border: 1px solid #d1d5db;
					border-radius: 8px;
					padding: 8px 12px;
					font-size: 14px;
					background: white;
					color: #000000;
					outline: none;

					&:focus {
						border-color: #3b82f6;
					}

					option {
						color: #000000;
						background: white;
					}
				}

				input[type='checkbox'] {
					margin-right: 8px;
				}
			}
		}
	}

	.actions-section {
		display: flex;
		gap: 12px;

		.action-button {
			flex: 1;
			background: #3b82f6;
			color: white;
			border: none;
			border-radius: 12px;
			padding: 12px 16px;
			font-size: 14px;
			font-weight: 500;
			display: flex;
			align-items: center;
			justify-content: center;
			gap: 8px;
			cursor: pointer;
			transition: all 0.2s ease;
			position: relative;

			&:hover {
				background: #2563eb;
				transform: translateY(-1px);
			}

			.icon {
				width: 18px;
				height: 18px;
			}

			&.share-button {
				background: #10b981;

				&:hover {
					background: #059669;
				}
			}
		}
	}

	.tooltip {
		position: absolute;
		top: -40px;
		left: 50%;
		transform: translateX(-50%);
		background: #1f2937;
		color: white;
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 12px;
		visibility: hidden;
		opacity: 0;
		transition: all 0.2s ease;

		&::after {
			content: '';
			position: absolute;
			top: 100%;
			left: 50%;
			transform: translateX(-50%);
			border: 4px solid transparent;
			border-top-color: #1f2937;
		}

		&.visible {
			visibility: visible;
			opacity: 1;
		}
	}

	// Dark mode support
	@media (prefers-color-scheme: dark) {
		.control-card,
		.search-card {
			background: rgba(31, 41, 55, 0.9);
			border-color: rgba(255, 255, 255, 0.1);
			color: white;

			&:hover {
				background: rgba(31, 41, 55, 1);
			}

			input,
			select {
				color: white;

				&::placeholder {
					color: #9ca3af;
				}
			}
		}

		.autocomplete-dropdown {
			background: rgba(31, 41, 55, 0.95);
			border-color: rgba(255, 255, 255, 0.1);

			.autocomplete-item {
				border-bottom-color: rgba(255, 255, 255, 0.1);

				&:hover {
					background: rgba(255, 255, 255, 0.1);
				}

				&:active {
					background: rgba(255, 255, 255, 0.15);
				}

				.autocomplete-text {
					color: #d1d5db;
				}
			}
		}

		.details-pane {
			background: rgba(31, 41, 55, 0.95);
			color: white;
		}

		.topic-section h3 {
			color: white;
		}

		.topic-section .description {
			color: #9ca3af;
		}

		.settings-section .setting-item label {
			color: #d1d5db;

			select {
				background: #374151;
				border-color: #4b5563;
				color: white;
			}
		}
	}

	// Responsive design
	@media (max-width: 768px) {
		.precipitation-page {
			padding-left: 12px;
			padding-right: 12px;
			height: calc(
				100vh - 65px - 60px - 40px
			); /* Topbar (65px) + smaller footer (60px) + extra 40px */
		}

		.map-controls {
			.period-selector,
			.location-button {
				top: 10px;
			}

			.period-selector {
				left: 10px;
			}

			.location-button {
				right: 10px;
			}

			.search-container {
				top: 60px;
				left: 10px;
				right: 10px;
			}
		}

		.control-card {
			padding: 8px 12px;
			font-size: 12px;

			.icon {
				width: 16px;
				height: 16px;
			}
		}

		.search-card {
			padding: 8px 12px;

			input {
				font-size: 12px;
			}

			.search-icon {
				width: 16px;
				height: 16px;
			}
		}

		.pane-content {
			padding: 16px;
		}

		.topic-section h3 {
			font-size: 18px;
		}

		.actions-section {
			flex-direction: column;
			gap: 8px;

			.action-button {
				padding: 10px 12px;
				font-size: 12px;

				.icon {
					width: 16px;
					height: 16px;
				}
			}
		}
	}

	@media (max-width: 480px) {
		.precipitation-page {
			padding-left: 4px;
			padding-right: 4px;
			height: calc(
				100vh - 65px - 50px - 40px
			); /* Topbar (65px) + even smaller footer (50px) + extra 40px */
		}

		.map-controls {
			.period-selector,
			.location-button {
				top: 5px;
			}

			.period-selector {
				left: 5px;
			}

			.location-button {
				right: 5px;
			}

			.search-container {
				top: 50px;
				left: 5px;
				right: 5px;
			}
		}

		.control-card {
			padding: 6px 10px;
			font-size: 11px;

			.icon {
				width: 14px;
				height: 14px;
			}
		}

		.search-card {
			padding: 6px 10px;

			input {
				font-size: 11px;
			}

			.search-icon {
				width: 14px;
				height: 14px;
			}
		}
	}

	// Share Modal Styles
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(4px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10000;
		padding: 20px;
		animation: fadeIn 0.2s ease;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.modal-content {
		background: white;
		border-radius: 16px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
		max-width: 500px;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		animation: slideUp 0.3s ease;
		display: flex;
		flex-direction: column;
	}

	@keyframes slideUp {
		from {
			transform: translateY(20px);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 20px 24px;
		border-bottom: 1px solid #e5e7eb;

		h3 {
			margin: 0;
			font-size: 20px;
			font-weight: 600;
			color: #1f2937;
		}

		.modal-close {
			background: none;
			border: none;
			padding: 8px;
			border-radius: 8px;
			cursor: pointer;
			display: flex;
			align-items: center;
			justify-content: center;
			color: #6b7280;
			transition: all 0.2s ease;

			&:hover {
				background: #f3f4f6;
				color: #1f2937;
			}

			svg {
				width: 24px;
				height: 24px;
			}
		}
	}

	.modal-body {
		padding: 24px;
		flex: 1;

		.modal-message {
			margin: 0 0 16px 0;
			font-size: 14px;
			color: #10b981;
			font-weight: 500;
			display: flex;
			align-items: center;
			gap: 8px;

			&::before {
				content: '✓';
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 20px;
				height: 20px;
				background: #10b981;
				color: white;
				border-radius: 50%;
				font-size: 12px;
				font-weight: bold;
			}
		}

		.url-container {
			display: flex;
			gap: 8px;
			align-items: center;

			.url-input {
				flex: 1;
				padding: 12px 16px;
				border: 1px solid #d1d5db;
				border-radius: 8px;
				font-size: 14px;
				font-family: monospace;
				background: #f9fafb;
				color: #1f2937;
				outline: none;
				transition: all 0.2s ease;

				&:focus {
					border-color: #3b82f6;
					background: white;
				}
			}

			.copy-button {
				background: #3b82f6;
				border: none;
				padding: 12px 16px;
				border-radius: 8px;
				cursor: pointer;
				display: flex;
				align-items: center;
				justify-content: center;
				color: white;
				transition: all 0.2s ease;
				flex-shrink: 0;

				&:hover {
					background: #2563eb;
				}

				&:active {
					transform: scale(0.95);
				}

				svg {
					width: 20px;
					height: 20px;
				}
			}
		}
	}

	.modal-footer {
		padding: 16px 24px;
		border-top: 1px solid #e5e7eb;
		display: flex;
		justify-content: flex-end;

		.modal-button {
			background: #3b82f6;
			color: white;
			border: none;
			padding: 10px 20px;
			border-radius: 8px;
			font-size: 14px;
			font-weight: 500;
			cursor: pointer;
			transition: all 0.2s ease;

			&:hover {
				background: #2563eb;
			}
		}
	}

	// Dark mode support for modal
	@media (prefers-color-scheme: dark) {
		.modal-content {
			background: #1f2937;
			color: white;
		}

		.modal-header {
			border-bottom-color: #374151;

			h3 {
				color: white;
			}

			.modal-close {
				color: #9ca3af;

				&:hover {
					background: #374151;
					color: white;
				}
			}
		}

		.modal-body {
			.url-container {
				.url-input {
					background: #374151;
					border-color: #4b5563;
					color: white;

					&:focus {
						border-color: #3b82f6;
						background: #4b5563;
					}
				}
			}
		}

		.modal-footer {
			border-top-color: #374151;
		}
	}

	// Responsive design for modal
	@media (max-width: 768px) {
		.modal-overlay {
			padding: 16px;
		}

		.modal-content {
			max-width: 100%;
		}

		.modal-header,
		.modal-body,
		.modal-footer {
			padding: 16px;
		}

		.modal-body {
			.url-container {
				flex-direction: column;

				.url-input {
					width: 100%;
				}

				.copy-button {
					width: 100%;
				}
			}
		}
	}
</style>
