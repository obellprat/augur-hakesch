<script lang="ts">
	import { page } from '$app/state';
	let { title, icon, href } = $props();

	let active = $derived(page.url.pathname === '/' + href);
	$effect(() => {
		if (page.url.pathname == '/' && href == '/') active = true;
	});
</script>

<li class={['side-nav-item', { active }]}>
	<a {href} class="side-nav-link" data-sveltekit-preload-data="off">
		<span class="menu-icon"><i class={icon}></i></span>
		<span class="menu-text"> {title} </span>
	</a>
</li>
