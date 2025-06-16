<script lang="ts">
	import '../scss/app.scss';
	import '../scss/icons.scss';

	import { base } from '$app/paths';
	
  	import { SvelteToast } from '@zerodevx/svelte-toast'

	import { Footer, Menu } from '$lib/index';

	import { loadScript } from '$lib/page/loadscript';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(async () => {
		await loadScript(`${base}/assets/js/app.js`);
	});
</script>

<svelte:head>
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
	<SvelteToast />
	<!-- ============================================================== -->
	<!-- End Page content -->
	<!-- ============================================================== -->
</div>
<!-- END wrapper -->
