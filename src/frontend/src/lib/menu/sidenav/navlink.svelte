<script lang="ts">
	import { page } from '$app/state';

	import Navlink from '../../page/discharge/navlink.svelte';
	import { base } from '$app/paths';
	let { title, icon, href, projectcount = 0, currentproject = null } = $props();
	import { _ } from 'svelte-i18n';

	let active = $derived(page.url.pathname.includes(href));
	$effect(() => {
		if (page.url.pathname == '/' && href == '/') active = true;
	});

	let url = base + '/' + href;
</script>

<li class={['side-nav-item', { active }]}>
	{#if href == 'discharge' && projectcount > 0}
		<a
			data-bs-toggle="collapse"
			href="#dischargeSubmenu"
			aria-expanded="true"
			aria-controls="dischargeSubmenu"
			class="side-nav-link"
		>
			<span class="menu-icon"><i class={icon}></i></span>
			<span class="menu-text"> {title} </span>
			<span class="menu-arrow"></span>
		</a>
		<div class="collapse show" id="dischargeSubmenu" style="">
			<ul class="sub-menu">
				<li class="side-nav-item">
					<a href={url} class="side-nav-link">
						<span class="menu-text">{$_('page.discharge.projects')}</span>
						<span class="badge bg-danger rounded-pill">{projectcount}</span>
					</a>
				</li>
				{#if currentproject != null}
					<li class="side-nav-item">
						<a
							data-bs-toggle="collapse"
							href="#sidebarProject"
							aria-expanded="true"
							aria-controls="sidebarProject"
							class="side-nav-link"
						>
							<span class="menu-text"> {currentproject.title} </span>
							<span class="menu-arrow"></span>
						</a>
						<div class="collapse show" id="sidebarProject" style="">
							<ul class="sub-menu">
								<Navlink
									title={$_('page.discharge.overviewText')}
									href="{base}/discharge/overview/{currentproject.id}"
									tool="overview"
								/>
								<Navlink
									title={$_('page.discharge.calculate')}
									href="{base}/discharge/calculation/{currentproject.id}"
									tool="calculation"
								/>
							</ul>
						</div>
					</li>
				{/if}
			</ul>
		</div>
	{:else}
		<a href={url} class="side-nav-link" data-sveltekit-preload-data="off">
			<span class="menu-icon"><i class={icon}></i></span>
			<span class="menu-text"> {title} </span>
		</a>
	{/if}
</li>
