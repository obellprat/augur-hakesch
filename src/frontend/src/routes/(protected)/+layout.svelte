<script lang="ts">
	import { browser } from '$app/environment';

	import { redirect } from '@sveltejs/kit';

	import { page } from '$app/state';
	import { onMount } from 'svelte';
	let { children } = $props();
	//let current = $derived(page.url.href);
	//if (page.data.keycloak && browser && !page.data.keycloak.authenticated) {
	//	redirect(307, '/login');
	//}

	onMount(() => {
		/*console.log(page);
		if (page.data.keycloak!=null && !page.data.keycloak.authenticated) {
				redirect(307,"/login?redirect_url="+page.url.href);
			}*/
	});
</script>

{@render children()}
