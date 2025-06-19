<script lang="ts">
	import { base } from '$app/paths';
	import Navlink from './navlink.svelte';
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
			<li class="side-nav-title">Tools</li>

			<Navlink title="Dashboard" href="./" icon="ti ti-home" />

			<Navlink title="Precipitation" href="precipitation" icon="ti ti-cloud-rain" />

			<Navlink title="HydroCalc" href="hydrocalc" icon="ti ti-chart-histogram" />

			<!--<Navlink title="Isozones" href="isozones" icon="ti ti-stopwatch" />-->

			<li class="side-nav-title mt-2">About</li>

			<Navlink title="Science" href="science" icon="ti ti-school" />

			<Navlink title="About AUGUR" href="about" icon="ti ti-info-circle" />
		</ul>

		<!-- dDonate Box -->
		<div class="help-box text-center">
			<h5 class="fw-semibold fs-16">Donate</h5>
			<p class="mb-3 text-muted">Help support us. Please donate!</p>
			<a href="javascript: void(0);" class="btn btn-danger btn-sm">Donate</a>
		</div>

		<div class="clearfix"></div>
	</div>
</div>
<!-- Sidenav Menu End -->
