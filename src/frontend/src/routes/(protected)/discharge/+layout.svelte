<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';

	import Sidebar from '$lib/page/discharge/sidebar.svelte';
	import { page } from '$app/state';

	import { currentProject } from '$lib/state.svelte';

	let { children } = $props();

	$pageTitle = 'HydroCalc';

	onMount(async () => {});
</script>

<div class="page-container">
	<div class="d-flex gap-2">
		<Sidebar projectCount={page.data.projects.length} {currentProject} />

		{@render children()}
	</div>
</div>
<!-- container -->
