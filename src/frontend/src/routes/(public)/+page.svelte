<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { _ } from 'svelte-i18n';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { CLIMAQVA_URL } from '$lib/dischargeMigration';
	import DischargeMigrationNotice from '$lib/components/DischargeMigrationNotice.svelte';

	$pageTitle = $_('page.dashboard.title');
	let dischargeMigrated = $derived(Boolean(page.data.dischargeMigrated));
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<style>
	.card-img-top {
		height: 300px;
		object-fit: cover;
		object-position: center;
	}

	@media (min-width: 1200px) {
		.card-img-top {
			height: 380px;
		}
	}
</style>

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
		<div class="col-sm-6 col-lg-6 d-flex align-items-stretch">
			<!-- Simple card -->
			<div class="card d-flex flex-column w-100">
				<img
					class="card-img-top"
					src="{base}/assets/images/tools/precipitation.png"
					alt={$_('page.dashboard.precipitationtool')}
				/>
				<div class="card-body d-flex flex-column">
					<h3 class="card-title">{$_('page.dashboard.precipitation')}</h3>
					<p class="card-text">
						{$_('page.dashboard.precipitation_card')}
					</p>
					<div class="mt-auto">
						<a href="{base}/precipitation" class="btn btn-primary stretched-link"
							>{$_('page.general.start')}</a
						>
					</div>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->

		<div class="col-sm-6 col-lg-6 d-flex align-items-stretch">
			<!-- Simple card -->
			<div class="card d-flex flex-column w-100">
				<img
					class="card-img-top"
					src="{base}/assets/images/tools/discharge.png"
					alt={$_('page.discharge.nav')}
				/>
				<div class="card-body d-flex flex-column">
					<div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
						<h3 class="card-title mb-0">{$_('page.discharge.nav')}</h3>
						<span
							class={[
								'badge',
								dischargeMigrated
									? 'bg-info-subtle text-info'
									: 'bg-warning-subtle text-warning'
							]}
						>
							{dischargeMigrated
								? $_('page.discharge.migration.badgeAfter')
								: $_('page.discharge.migration.badgeBefore')}
						</span>
					</div>
					<p class="card-text">
						{$_('page.dashboard.dischargedesc')}
					</p>
					<DischargeMigrationNotice
						migrated={dischargeMigrated}
						compact={true}
						showCta={false}
						className="mb-3"
					/>
					<div class="mt-auto d-flex flex-wrap gap-2">
						{#if dischargeMigrated}
							<a href={CLIMAQVA_URL} class="btn btn-primary stretched-link">
								{$_('page.discharge.migration.ctaClimaQva')}
								<i class="ti ti-external-link ms-1" aria-hidden="true"></i>
							</a>
						{:else}
							<a href="{base}/discharge" class="btn btn-primary">{$_('page.general.start')}</a>
							<a
								href={CLIMAQVA_URL}
								class="btn btn-outline-primary"
								target="_blank"
								rel="noopener noreferrer"
							>
								{$_('page.discharge.migration.ctaClimaQva')}
								<i class="ti ti-external-link ms-1" aria-hidden="true"></i>
							</a>
						{/if}
					</div>
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
