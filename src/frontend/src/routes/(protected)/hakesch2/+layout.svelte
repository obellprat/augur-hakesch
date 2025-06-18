<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';

	import Sidebar from '$lib/page/hakesch2/sidebar.svelte';
	import { page } from '$app/state';

	import { currentProject } from '$lib/state.svelte';

	let { children } = $props();

	$pageTitle = 'HAKESCH 2.0';

	onMount(async () => {});
</script>

<div class="page-container">
	<div class="d-flex gap-2">
		<Sidebar projectCount={page.data.projects.length} {currentProject} />

		{@render children()}
	</div>
</div>
<!-- container -->
