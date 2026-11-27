<script lang="ts">
	import { page } from '$app/state';

	import Navlink from '../../page/discharge/navlink.svelte';
	import { base } from '$app/paths';
	let {
		title,
		icon,
		href,
		projectcount = 0,
		currentproject = null,
		target = '_self',
		submenuId = null,
		submenuOpen = false,
		submenuToggle = true,
		children = null
	} = $props();
	import { _ } from 'svelte-i18n';

	let isExternal = $derived(/^https?:\/\//.test(href));
	let active = $derived(!isExternal && page.url.pathname.includes(href));
	$effect(() => {
		if (page.url.pathname == '/' && href == '/') active = true;
	});

	let url = $derived(isExternal ? href : base + '/' + href);
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
	{:else if submenuId}
		<a
			href={url}
			data-bs-toggle={submenuToggle ? 'collapse' : undefined}
			data-bs-target={submenuToggle ? '#' + submenuId : undefined}
			aria-expanded={submenuOpen}
			aria-controls={submenuId}
			class="side-nav-link"
			data-sveltekit-preload-data="off"
			target={target}
			rel={target === '_blank' ? 'noopener noreferrer' : undefined}
		>
			<span class="menu-icon"><i class={icon}></i></span>
			<span class="menu-text"> {title} </span>
			<span class="menu-arrow"></span>
		</a>
		<div class={['collapse', { show: submenuOpen }]} id={submenuId}>
			<ul class="sub-menu">
				{@render children?.()}
			</ul>
		</div>
	{:else}
		<a
			href={url}
			class="side-nav-link"
			data-sveltekit-preload-data="off"
			target={target}
			rel={target === '_blank' ? 'noopener noreferrer' : undefined}
		>
			<span class="menu-icon"><i class={icon}></i></span>
			<span class="menu-text"> {title} </span>
			{#if isExternal}
				<span class="ms-auto"><i class="ti ti-external-link fs-14" aria-hidden="true"></i></span>
			{/if}
		</a>
	{/if}
</li>
