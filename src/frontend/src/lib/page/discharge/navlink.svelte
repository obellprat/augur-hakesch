<script lang="ts">
	import { page } from '$app/state';

	import { base } from '$app/paths';
	let { title, href, tool } = $props();

	let active = $derived(page.url.pathname.includes(tool));
	$effect(() => {
		if (page.url.pathname == '/' && href == '/') active = true;
	});
	function closeOffcanvas() {
		let closeCanvas = document.querySelector('[data-bs-dismiss="offcanvas"]');
		if (closeCanvas) closeCanvas.click();
	}

	let url = base + '/' + href;
</script>

<a
	href="{href}"
	onclick={closeOffcanvas}
	class="{active?'active':''}"
>
	<iconify-icon icon="solar:mailbox-outline" class="me-2 fs-18 text-muted"
	></iconify-icon>
	<span>{title}</span>
</a>
