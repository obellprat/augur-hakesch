<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { PageServerData } from './$types';
	import { onMount, onDestroy } from 'svelte';
	import { env } from '$env/dynamic/public';
	import { _ } from 'svelte-i18n';

	let { data }: { data: PageServerData } = $props();
	$pageTitle = 'Server Monitoring';

	interface MonitoringSummary {
		timestamp: string;
		cpu: {
			percent: number;
			free_percent: number;
		};
		memory: {
			used_percent: number;
			free_percent: number;
			used_gb: number;
			free_gb: number;
			total_gb: number;
		};
		disk: {
			used_percent: number;
			free_percent: number;
			used_gb: number;
			free_gb: number;
			total_gb: number;
		};
		uptime_seconds: number;
		uptime_formatted: string;
	}

	interface SystemInfo {
		platform: string;
		system: string;
		release: string;
		version: string;
		machine: string;
		processor: string;
		python_version: string;
		boot_time: string;
		uptime_seconds: number;
		uptime_formatted: string;
		hostname: string;
		cpu_count_physical: number;
		cpu_count_logical: number;
	}

	interface CpuInfo {
		cpu_percent_overall: number;
		cpu_percent_per_core: number[];
		cpu_freq: {
			current: number | null;
			min: number | null;
			max: number | null;
		};
		load_average: number[] | null;
	}

	interface MemoryInfo {
		virtual_memory: {
			total_gb: number;
			available_gb: number;
			used_gb: number;
			free_gb: number;
			percent: number;
		};
		swap_memory: {
			total_gb: number;
			used_gb: number;
			free_gb: number;
			percent: number;
		};
	}

	interface DiskInfo {
		root: {
			total_gb: number;
			used_gb: number;
			free_gb: number;
			percent: number;
		};
		partitions: Array<{
			device: string;
			mountpoint: string;
			total_gb: number;
			used_gb: number;
			free_gb: number;
			percent: number;
		}>;
		data_directories?: Array<{
			name: string;
			path: string;
			size_gb: number;
			size_mb: number;
			size_bytes: number;
		}>;
	}

	interface NetworkInfo {
		io_counters: {
			bytes_sent_gb: number;
			bytes_recv_gb: number;
			packets_sent: number;
			packets_recv: number;
		} | null;
		connections_count: number;
		interfaces: Array<{
			name: string;
			is_up: boolean | null;
			speed: number | null;
		}>;
	}

	interface ProcessInfo {
		processes: Array<{
			pid: number;
			name: string;
			username: string;
			cpu_percent: number | null;
			memory_percent: number | null;
			status: string;
		}>;
		total_processes: number;
	}

	interface LogInfo {
		logs: string[];
		total_lines: number;
		returned_lines: number;
		log_file: string;
		available_logs: string[];
	}

	let summary = $state<MonitoringSummary | null>(null);
	let systemInfo = $state<SystemInfo | null>(null);
	let cpuInfo = $state<CpuInfo | null>(null);
	let memoryInfo = $state<MemoryInfo | null>(null);
	let diskInfo = $state<DiskInfo | null>(null);
	let networkInfo = $state<NetworkInfo | null>(null);
	let processInfo = $state<ProcessInfo | null>(null);
	let logInfo = $state<LogInfo | null>(null);
	let selectedLogFile = $state<string>('celery.log');
	let logLines = $state<number>(100);
	let error = $state<string | null>(null);
	let loading = $state<boolean>(true);
	let autoRefresh = $state<boolean>(true);
	let refreshInterval = $state<number>(5000); // 5 seconds default
	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	let activeTab = $state<string>('summary');

	async function fetchMonitoringData() {
		try {
			error = null;
			const headers = {
				Authorization: 'Bearer ' + data.session.access_token
			};

			// Fetch summary
			const summaryRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/summary', {
				headers
			});
			if (summaryRes.ok) {
				summary = await summaryRes.json();
			}

			// Fetch system info
			const systemRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/system', {
				headers
			});
			if (systemRes.ok) {
				systemInfo = await systemRes.json();
			}

			// Fetch CPU info
			const cpuRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/cpu', {
				headers
			});
			if (cpuRes.ok) {
				cpuInfo = await cpuRes.json();
			}

			// Fetch memory info
			const memoryRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/memory', {
				headers
			});
			if (memoryRes.ok) {
				memoryInfo = await memoryRes.json();
			}

			// Fetch disk info
			const diskRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/disk', {
				headers
			});
			if (diskRes.ok) {
				diskInfo = await diskRes.json();
			}

			// Fetch network info
			const networkRes = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/monitoring/network', {
				headers
			});
			if (networkRes.ok) {
				networkInfo = await networkRes.json();
			}

			// Fetch processes info
			const processesRes = await fetch(
				env.PUBLIC_HAKESCH_API_PATH + '/monitoring/processes?limit=20',
				{ headers }
			);
			if (processesRes.ok) {
				processInfo = await processesRes.json();
			}

			loading = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch monitoring data';
			loading = false;
		}
	}

	async function fetchLogs() {
		try {
			const headers = {
				Authorization: 'Bearer ' + data.session.access_token
			};
			const res = await fetch(
				env.PUBLIC_HAKESCH_API_PATH +
					`/monitoring/logs?lines=${logLines}&log_file=${selectedLogFile}`,
				{ headers }
			);
			if (res.ok) {
				logInfo = await res.json();
			} else {
				error = `Failed to fetch logs: ${res.status}`;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch logs';
		}
	}

	function formatBytes(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
	}

	function formatUptime(seconds: number): string {
		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = seconds % 60;
		return `${days}d ${hours}h ${minutes}m ${secs}s`;
	}

	function getStatusColor(percent: number): string {
		if (percent < 50) return 'success';
		if (percent < 80) return 'warning';
		return 'danger';
	}

	function startAutoRefresh() {
		if (refreshTimer) clearInterval(refreshTimer);
		if (autoRefresh) {
			refreshTimer = setInterval(() => {
				fetchMonitoringData();
				if (activeTab === 'logs') {
					fetchLogs();
				}
			}, refreshInterval);
		}
	}

	function stopAutoRefresh() {
		if (refreshTimer) {
			clearInterval(refreshTimer);
			refreshTimer = null;
		}
	}

	onMount(() => {
		fetchMonitoringData();
		fetchLogs();
		startAutoRefresh();
	});

	onDestroy(() => {
		stopAutoRefresh();
	});

	$effect(() => {
		if (autoRefresh) {
			startAutoRefresh();
		} else {
			stopAutoRefresh();
		}
	});

	$effect(() => {
		if (activeTab === 'logs') {
			fetchLogs();
		}
	});
</script>

<div class="container-fluid mt-4">
	<div class="d-flex justify-content-between align-items-center mb-4">
		<h1>Server Monitoring</h1>
		<div class="d-flex align-items-center gap-3">
			<div class="form-check form-switch">
				<input
					class="form-check-input"
					type="checkbox"
					id="autoRefresh"
					bind:checked={autoRefresh}
				/>
				<label class="form-check-label" for="autoRefresh">Auto Refresh</label>
			</div>
			<div class="input-group" style="width: 200px">
				<span class="input-group-text">Interval (ms)</span>
				<input
					type="number"
					class="form-control"
					bind:value={refreshInterval}
					min="1000"
					step="1000"
				/>
			</div>
			<button class="btn btn-primary" onclick={fetchMonitoringData}>Refresh Now</button>
		</div>
	</div>

	{#if error}
		<div class="alert alert-danger" role="alert">{error}</div>
	{/if}

	{#if loading && !summary}
		<div class="text-center">
			<div class="spinner-border" role="status">
				<span class="visually-hidden">Loading...</span>
			</div>
		</div>
	{:else if summary}
		<!-- Summary Cards -->
		<div class="row mb-4">
			<div class="col-md-3">
				<div class="card">
					<div class="card-body">
						<h5 class="card-title">CPU Usage</h5>
						<h2 class="text-{getStatusColor(summary.cpu.percent)}">
							{summary.cpu.percent.toFixed(1)}%
						</h2>
						<p class="text-muted mb-0">Free: {summary.cpu.free_percent.toFixed(1)}%</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body">
						<h5 class="card-title">Memory Usage</h5>
						<h2 class="text-{getStatusColor(summary.memory.used_percent)}">
							{summary.memory.used_percent.toFixed(1)}%
						</h2>
						<p class="text-muted mb-0">
							{summary.memory.used_gb.toFixed(2)} GB / {summary.memory.total_gb.toFixed(2)} GB
						</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body">
						<h5 class="card-title">Disk Usage</h5>
						<h2 class="text-{getStatusColor(summary.disk.used_percent)}">
							{summary.disk.used_percent.toFixed(1)}%
						</h2>
						<p class="text-muted mb-0">
							{summary.disk.used_gb.toFixed(2)} GB / {summary.disk.total_gb.toFixed(2)} GB
						</p>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card">
					<div class="card-body">
						<h5 class="card-title">Uptime</h5>
						<h2 class="text-info">{summary.uptime_formatted}</h2>
						<p class="text-muted mb-0">
							{formatUptime(summary.uptime_seconds)}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Tabs -->
		<ul class="nav nav-tabs mb-3" role="tablist">
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'summary'}
					onclick={() => (activeTab = 'summary')}
				>
					Summary
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'system'}
					onclick={() => (activeTab = 'system')}
				>
					System Info
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'cpu'}
					onclick={() => (activeTab = 'cpu')}
				>
					CPU
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'memory'}
					onclick={() => (activeTab = 'memory')}
				>
					Memory
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'disk'}
					onclick={() => (activeTab = 'disk')}
				>
					Disk
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'network'}
					onclick={() => (activeTab = 'network')}
				>
					Network
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'processes'}
					onclick={() => (activeTab = 'processes')}
				>
					Processes
				</button>
			</li>
			<li class="nav-item">
				<button
					class="nav-link"
					class:active={activeTab === 'logs'}
					onclick={() => (activeTab = 'logs')}
				>
					Logs
				</button>
			</li>
		</ul>

		<!-- Tab Content -->
		<div class="tab-content">
			<!-- Summary Tab -->
			{#if activeTab === 'summary'}
				<div class="row">
					<div class="col-md-6">
						<div class="card mb-3">
							<div class="card-header">CPU Details</div>
							<div class="card-body">
								{#if cpuInfo}
									<p><strong>Overall Usage:</strong> {cpuInfo.cpu_percent_overall.toFixed(1)}%</p>
									{#if cpuInfo.cpu_percent_per_core && cpuInfo.cpu_percent_per_core.length > 0}
										<p><strong>Per Core:</strong></p>
										<div class="d-flex flex-wrap gap-2">
											{#each cpuInfo.cpu_percent_per_core as core, i}
												<span class="badge bg-secondary">Core {i + 1}: {core.toFixed(1)}%</span>
											{/each}
										</div>
									{/if}
									{#if cpuInfo.cpu_freq?.current}
										<p><strong>Frequency:</strong> {cpuInfo.cpu_freq.current.toFixed(0)} MHz</p>
									{/if}
									{#if cpuInfo.load_average}
										<p><strong>Load Average:</strong> {cpuInfo.load_average.map((l) => l.toFixed(2)).join(', ')}</p>
									{/if}
								{/if}
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<div class="card mb-3">
							<div class="card-header">Memory Details</div>
							<div class="card-body">
								{#if memoryInfo}
									<p><strong>Virtual Memory:</strong></p>
									<p class="mb-1">
										Used: {memoryInfo.virtual_memory.used_gb.toFixed(2)} GB ({memoryInfo.virtual_memory.percent.toFixed(1)}%)
									</p>
									<p class="mb-1">
										Free: {memoryInfo.virtual_memory.free_gb.toFixed(2)} GB
									</p>
									<p class="mb-3">
										Total: {memoryInfo.virtual_memory.total_gb.toFixed(2)} GB
									</p>
									<p><strong>Swap Memory:</strong></p>
									<p class="mb-1">
										Used: {memoryInfo.swap_memory.used_gb.toFixed(2)} GB ({memoryInfo.swap_memory.percent.toFixed(1)}%)
									</p>
									<p class="mb-0">
										Total: {memoryInfo.swap_memory.total_gb.toFixed(2)} GB
									</p>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- System Info Tab -->
			{#if activeTab === 'system' && systemInfo}
				<div class="card">
					<div class="card-body">
						<table class="table table-striped">
							<tbody>
								<tr>
									<th>Platform</th>
									<td>{systemInfo.platform}</td>
								</tr>
								<tr>
									<th>System</th>
									<td>{systemInfo.system}</td>
								</tr>
								<tr>
									<th>Release</th>
									<td>{systemInfo.release}</td>
								</tr>
								<tr>
									<th>Version</th>
									<td>{systemInfo.version}</td>
								</tr>
								<tr>
									<th>Machine</th>
									<td>{systemInfo.machine}</td>
								</tr>
								<tr>
									<th>Processor</th>
									<td>{systemInfo.processor}</td>
								</tr>
								<tr>
									<th>Hostname</th>
									<td>{systemInfo.hostname}</td>
								</tr>
								<tr>
									<th>Python Version</th>
									<td>{systemInfo.python_version}</td>
								</tr>
								<tr>
									<th>CPU Cores (Physical)</th>
									<td>{systemInfo.cpu_count_physical}</td>
								</tr>
								<tr>
									<th>CPU Cores (Logical)</th>
									<td>{systemInfo.cpu_count_logical}</td>
								</tr>
								<tr>
									<th>Boot Time</th>
									<td>{new Date(systemInfo.boot_time).toLocaleString()}</td>
								</tr>
								<tr>
									<th>Uptime</th>
									<td>{formatUptime(systemInfo.uptime_seconds)}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			{/if}

			<!-- CPU Tab -->
			{#if activeTab === 'cpu' && cpuInfo}
				<div class="card">
					<div class="card-body">
						<h5>CPU Usage: {cpuInfo.cpu_percent_overall.toFixed(1)}%</h5>
						<div class="progress mb-3" style="height: 30px">
							<div
								class="progress-bar bg-{getStatusColor(cpuInfo.cpu_percent_overall)}"
								role="progressbar"
								style="width: {cpuInfo.cpu_percent_overall}%"
							>
								{cpuInfo.cpu_percent_overall.toFixed(1)}%
							</div>
						</div>
						{#if cpuInfo.cpu_percent_per_core && cpuInfo.cpu_percent_per_core.length > 0}
							<h6>Per Core Usage</h6>
							<div class="row">
								{#each cpuInfo.cpu_percent_per_core as core, i}
									<div class="col-md-3 mb-2">
										<label>Core {i + 1}</label>
										<div class="progress" style="height: 20px">
											<div
												class="progress-bar bg-{getStatusColor(core)}"
												role="progressbar"
												style="width: {core}%"
											>
												{core.toFixed(1)}%
											</div>
										</div>
									</div>
								{/each}
							</div>
						{/if}
						{#if cpuInfo.cpu_freq?.current}
							<p><strong>Frequency:</strong> {cpuInfo.cpu_freq.current.toFixed(0)} MHz</p>
						{/if}
						{#if cpuInfo.load_average}
							<p><strong>Load Average:</strong> {cpuInfo.load_average.map((l) => l.toFixed(2)).join(', ')}</p>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Memory Tab -->
			{#if activeTab === 'memory' && memoryInfo}
				<div class="row">
					<div class="col-md-6">
						<div class="card">
							<div class="card-header">Virtual Memory</div>
							<div class="card-body">
								<h5>Usage: {memoryInfo.virtual_memory.percent.toFixed(1)}%</h5>
								<div class="progress mb-3" style="height: 30px">
									<div
										class="progress-bar bg-{getStatusColor(memoryInfo.virtual_memory.percent)}"
										role="progressbar"
										style="width: {memoryInfo.virtual_memory.percent}%"
									>
										{memoryInfo.virtual_memory.percent.toFixed(1)}%
									</div>
								</div>
								<p><strong>Used:</strong> {memoryInfo.virtual_memory.used_gb.toFixed(2)} GB</p>
								<p><strong>Free:</strong> {memoryInfo.virtual_memory.free_gb.toFixed(2)} GB</p>
								<p><strong>Total:</strong> {memoryInfo.virtual_memory.total_gb.toFixed(2)} GB</p>
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<div class="card">
							<div class="card-header">Swap Memory</div>
							<div class="card-body">
								<h5>Usage: {memoryInfo.swap_memory.percent.toFixed(1)}%</h5>
								<div class="progress mb-3" style="height: 30px">
									<div
										class="progress-bar bg-{getStatusColor(memoryInfo.swap_memory.percent)}"
										role="progressbar"
										style="width: {memoryInfo.swap_memory.percent}%"
									>
										{memoryInfo.swap_memory.percent.toFixed(1)}%
									</div>
								</div>
								<p><strong>Used:</strong> {memoryInfo.swap_memory.used_gb.toFixed(2)} GB</p>
								<p><strong>Free:</strong> {memoryInfo.swap_memory.free_gb.toFixed(2)} GB</p>
								<p><strong>Total:</strong> {memoryInfo.swap_memory.total_gb.toFixed(2)} GB</p>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Disk Tab -->
			{#if activeTab === 'disk' && diskInfo}
				<div class="card mb-3">
					<div class="card-header">Root Filesystem</div>
					<div class="card-body">
						<h5>Usage: {diskInfo.root.percent.toFixed(1)}%</h5>
						<div class="progress mb-3" style="height: 30px">
							<div
								class="progress-bar bg-{getStatusColor(diskInfo.root.percent)}"
								role="progressbar"
								style="width: {diskInfo.root.percent}%"
							>
								{diskInfo.root.percent.toFixed(1)}%
							</div>
						</div>
						<p><strong>Used:</strong> {diskInfo.root.used_gb.toFixed(2)} GB</p>
						<p><strong>Free:</strong> {diskInfo.root.free_gb.toFixed(2)} GB</p>
						<p><strong>Total:</strong> {diskInfo.root.total_gb.toFixed(2)} GB</p>
					</div>
				</div>
				{#if diskInfo.data_directories && diskInfo.data_directories.length > 0}
					<div class="card mb-3">
						<div class="card-header">Data Directories</div>
						<div class="card-body">
							<table class="table table-striped">
								<thead>
									<tr>
										<th>Directory</th>
										<th>Path</th>
										<th>Size</th>
									</tr>
								</thead>
								<tbody>
									{#each diskInfo.data_directories as dir}
										<tr>
											<td><strong>{dir.name}</strong></td>
											<td><code>{dir.path}</code></td>
											<td>
												{dir.size_gb.toFixed(2)} GB
												<span class="text-muted">({dir.size_mb.toFixed(0)} MB)</span>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
				{#if diskInfo.partitions && diskInfo.partitions.length > 0}
					<div class="card">
						<div class="card-header">All Partitions</div>
						<div class="card-body">
							<table class="table table-striped">
								<thead>
									<tr>
										<th>Device</th>
										<th>Mountpoint</th>
										<th>Used</th>
										<th>Free</th>
										<th>Total</th>
										<th>Usage %</th>
									</tr>
								</thead>
								<tbody>
									{#each diskInfo.partitions as partition}
										<tr>
											<td>{partition.device}</td>
											<td>{partition.mountpoint}</td>
											<td>{partition.used_gb.toFixed(2)} GB</td>
											<td>{partition.free_gb.toFixed(2)} GB</td>
											<td>{partition.total_gb.toFixed(2)} GB</td>
											<td>
												<span class="badge bg-{getStatusColor(partition.percent)}">
													{partition.percent.toFixed(1)}%
												</span>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			{/if}

			<!-- Network Tab -->
			{#if activeTab === 'network' && networkInfo}
				<div class="card">
					<div class="card-body">
						{#if networkInfo.io_counters}
							<h5>Network I/O</h5>
							<p><strong>Bytes Sent:</strong> {networkInfo.io_counters.bytes_sent_gb.toFixed(2)} GB</p>
							<p><strong>Bytes Received:</strong> {networkInfo.io_counters.bytes_recv_gb.toFixed(2)} GB</p>
							<p><strong>Packets Sent:</strong> {networkInfo.io_counters.packets_sent.toLocaleString()}</p>
							<p><strong>Packets Received:</strong> {networkInfo.io_counters.packets_recv.toLocaleString()}</p>
							<hr />
						{/if}
						<p><strong>Active Connections:</strong> {networkInfo.connections_count}</p>
						{#if networkInfo.interfaces && networkInfo.interfaces.length > 0}
							<h5>Network Interfaces</h5>
							<table class="table table-striped">
								<thead>
									<tr>
										<th>Name</th>
										<th>Status</th>
										<th>Speed</th>
									</tr>
								</thead>
								<tbody>
									{#each networkInfo.interfaces as iface}
										<tr>
											<td>{iface.name}</td>
											<td>
												{#if iface.is_up === true}
													<span class="badge bg-success">UP</span>
												{:else if iface.is_up === false}
													<span class="badge bg-danger">DOWN</span>
												{:else}
													<span class="badge bg-secondary">Unknown</span>
												{/if}
											</td>
											<td>
												{#if iface.speed}
													{iface.speed} Mbps
												{:else}
													N/A
												{/if}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Processes Tab -->
			{#if activeTab === 'processes' && processInfo}
				<div class="card">
					<div class="card-body">
						<p><strong>Total Processes:</strong> {processInfo.total_processes}</p>
						<table class="table table-striped">
							<thead>
								<tr>
									<th>PID</th>
									<th>Name</th>
									<th>User</th>
									<th>CPU %</th>
									<th>Memory %</th>
									<th>Status</th>
								</tr>
							</thead>
							<tbody>
								{#each processInfo.processes as proc}
									<tr>
										<td>{proc.pid}</td>
										<td>{proc.name}</td>
										<td>{proc.username}</td>
										<td>{(proc.cpu_percent || 0).toFixed(1)}</td>
										<td>{(proc.memory_percent || 0).toFixed(1)}</td>
										<td>
											<span class="badge bg-secondary">{proc.status}</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}

			<!-- Logs Tab -->
			{#if activeTab === 'logs'}
				<div class="card mb-3">
					<div class="card-header d-flex justify-content-between align-items-center">
						<span>Application Logs</span>
						<div class="d-flex gap-2">
							{#if logInfo}
								<select class="form-select form-select-sm" style="width: auto" bind:value={selectedLogFile}>
									{#each logInfo.available_logs as logFile}
										<option value={logFile}>{logFile}</option>
									{/each}
								</select>
							{/if}
							<input
								type="number"
								class="form-control form-control-sm"
								style="width: 100px"
								bind:value={logLines}
								min="10"
								max="1000"
								step="10"
							/>
							<button class="btn btn-sm btn-primary" onclick={fetchLogs}>Refresh</button>
						</div>
					</div>
					<div class="card-body">
						{#if logInfo}
							<p class="text-muted">
								Showing last {logInfo.returned_lines} of {logInfo.total_lines} lines from {logInfo.log_file}
							</p>
							<pre class="bg-dark text-light p-3" style="max-height: 600px; overflow-y: auto"><code>{logInfo.logs.join('')}</code></pre>
						{:else}
							<p>No logs available</p>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.progress-bar {
		transition: width 0.3s ease;
	}
	.card {
		margin-bottom: 1rem;
	}
	pre {
		font-size: 0.85rem;
		line-height: 1.4;
	}
</style>
