<script lang="ts">
	import { onMount } from 'svelte';
	import pageTitle from '$lib/page/pageTitle';
	import { _ } from 'svelte-i18n'

	$pageTitle = $_('page.dashboard.title');
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row row-cols-xxl-1 row-cols-md-1 row-cols-1">
		<div class="col">
			<div class="card d-block">
				<div class="card-body">
					<h1 class="card-title">{$_('page.dashboard.welcome')}</h1>
					<p class="card-text">
						{$_('page.dashboard.welcome_text')}
					</p>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->
	</div>
	<!-- end row -->

	<div class="row">
		<div class="col-sm-6 col-lg-3 d-flex align-items-stretch">
			<!-- Simple card -->
			<div class="card d-block">
				<img
					class="card-img-top"
					src="assets/images/tools/precipitation.png"
					alt="{$_('page.dashboard.precipitationtool')}"
				/>
				<div class="card-body">
					<h3 class="card-title">{$_('page.dashboard.precipitation')}</h3>
					<p class="card-text">
						{$_('page.dashboard.precipitation_card')}
					</p>
					<a href="precipitation" class="btn btn-primary stretched-link">{$_('page.general.start')}</a>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->

		<div class="col-sm-6 col-lg-3 d-flex align-items-stretch">
			<!-- Simple card -->
			<div class="card d-block" >
				<img
					class="card-img-top"
					src="assets/images/tools/hydrocalc.png"
					alt="{$_('page.hydrocalc.nav')}"
				/>
				<div class="card-body">
					<h3 class="card-title">{$_('page.hydrocalc.nav')}</h3>
					<p class="card-text">
						{$_('page.dashboard.hydrocalcdesc')}
					</p>
					<a href="hydrocalc" class="btn btn-primary stretched-link">{$_('page.general.start')}</a>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->
	</div>
	<!-- end row -->
</div>
<!-- container -->
