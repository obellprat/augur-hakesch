<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';

	import { page } from '$app/state';

	import { currentProject } from '$lib/state.svelte';

	let { children } = $props();

	$pageTitle = 'HydroCalc';

	onMount(async () => {});
</script>

<div class="page-container">
	<div class="d-flex gap-2">
		{@render children()}
	</div>
</div>
<!-- container -->
