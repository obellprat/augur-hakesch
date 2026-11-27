<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import DischargeMigrationNotice from '$lib/components/DischargeMigrationNotice.svelte';

	let { children } = $props();
	let dischargeMigrated = $derived(Boolean(page.data.dischargeMigrated));

	$pageTitle = 'HydroCalc';

	onMount(async () => {});
</script>

<div class="page-container">
	<DischargeMigrationNotice migrated={dischargeMigrated} className="mb-3" />
	<div class="d-flex gap-2">
		{@render children()}
	</div>
</div>
<!-- container -->
