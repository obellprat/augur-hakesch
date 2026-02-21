<script lang="ts">
	import { base } from '$app/paths';
	import Navlink from './navlink.svelte';
	import { _ } from 'svelte-i18n';
	import { page } from '$app/state';

	let props = $props();
</script>

<!-- Sidenav Menu Start -->
<div class="sidenav-menu">
	<!-- Brand Logo -->
	<a href="./" class="logo">
		<span class="logo-light">
			<span class="logo-lg"><img src="{base}/assets/images/logo.png" alt="logo" /></span>
			<span class="logo-sm"><img src="{base}/assets/images/logo-sm.png" alt="small logo" /></span>
		</span>

		<span class="logo-dark">
			<span class="logo-lg"><img src="{base}/assets/images/logo-dark.png" alt="dark logo" /></span>
			<span class="logo-sm"><img src="{base}/assets/images/logo-sm.png" alt="small logo" /></span>
		</span>
	</a>

	<!-- Sidebar Hover Menu Toggle Button -->
	<button class="button-sm-hover">
		<i class="ri-circle-line align-middle"></i>
	</button>

	<!-- Full Sidebar Menu Close Button -->
	<button class="button-close-fullsidebar">
		<i class="ti ti-x align-middle"></i>
	</button>

	<div data-simplebar>
		<!--- Sidenav Menu -->
		<ul class="side-nav">
			<li class="side-nav-title">{$_('page.nav.tools')}</li>

			<Navlink title={$_('page.dashboard.nav')} href="./" icon="ti ti-home" />

			<Navlink title={$_('page.precipitation.nav')} href="precipitation" icon="ti ti-cloud-rain" />

			<Navlink
				title={$_('page.discharge.nav')}
				href="discharge"
				icon="ti ti-chart-histogram"
				projectcount={page.data.projects?.length}
				currentproject={page.data.project}
			/>

			<!--<Navlink title="Isozones" href="isozones" icon="ti ti-stopwatch" />-->

			<li class="side-nav-title mt-2">{$_('page.nav.about')}</li>

			<!--<Navlink title={$_('page.nav.science')} href="science" icon="ti ti-school" />-->

			<Navlink title={$_('page.nav.aboutAugur')} href="about" icon="ti ti-info-circle" />
			<Navlink title={$_('page.nav.technicalDocumentation')} href="assets/documents/AUGUR_Dokumentation_2026-02-20.pdf" icon="ti ti-file-type-pdf" target="_blank" />
		</ul>

		<!-- dDonate Box -->
		<!--
		<div class="help-box text-center">
			<h5 class="fw-semibold fs-16">{$_('page.nav.donate')}</h5>
			<p class="mb-3 text-muted">{$_('page.nav.helpSupportUs')}</p>
			<a href="javascript: void(0);" class="btn btn-danger btn-sm">{$_('page.nav.donateNow')}</a>
		</div>
		-->

		<div class="clearfix"></div>
		<div class="help-box mt-1">
			<h5 class="fw-semibold fs-16 text-center pb-2">{$_('page.nav.version')}</h5>
			<p class="text-muted">
				{$_('page.nav.frontend')}: {page.data.version}
				<br />
				{$_('page.nav.backend')}: {page.data.apiversion}
			</p>
		</div>
	</div>
</div>
<!-- Sidenav Menu End -->
