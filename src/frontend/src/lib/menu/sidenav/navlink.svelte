<script lang="ts">
	import { page } from '$app/state';

	import { base } from '$app/paths';
	let { title, icon, href } = $props();

	let active = $derived(page.url.pathname.includes(href));
	$effect(() => {
		if (page.url.pathname == '/' && href == '/') active = true;
	});

	let url = base + '/' + href;
</script>

<li class={['side-nav-item', { active }]}>
	<a href={url} class="side-nav-link" data-sveltekit-preload-data="off">
		<span class="menu-icon"><i class={icon}></i></span>
		<span class="menu-text"> {title} </span>
	</a>
</li>
