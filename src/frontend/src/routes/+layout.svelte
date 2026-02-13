<script lang="ts">
	import '../scss/app.scss';
	import '../scss/icons.scss';

	import { base } from '$app/paths';

	import { SvelteToast } from '@zerodevx/svelte-toast';

	import { Footer, Menu, LoadingOverlay } from '$lib/index';

	import { loadScript } from '$lib/page/loadscript';
	import { onMount } from 'svelte';

	import { UmamiAnalytics } from '@lukulent/svelte-umami';

	let { children } = $props();

	onMount(async () => {
		await loadScript(`${base}/assets/js/app.js`);
	});
</script>

<UmamiAnalytics websiteID="a38a9cf9-a9dd-4b4a-bc94-5d1612de34b3" srcURL="https://umami.geotools.ch/script.js" />

<svelte:head>
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
	<style>
		html, body, :root {
			font-family: 'Inter', sans-serif !important;
		}
	</style>
	<script src="{base}/assets/vendor/jquery/jquery.min.js"></script>
	<script src="{base}/assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
</svelte:head>
<!-- Begin page -->
<div class="wrapper">
	<Menu />

	<!-- ============================================================== -->
	<!-- Start Page Content here -->
	<!-- ============================================================== -->
	<div class="page-content">
		{@render children()}
		<Footer />
	</div>
	<LoadingOverlay />
	<SvelteToast />
	<!-- ============================================================== -->
	<!-- End Page content -->
	<!-- ============================================================== -->
</div>
<!-- END wrapper -->
