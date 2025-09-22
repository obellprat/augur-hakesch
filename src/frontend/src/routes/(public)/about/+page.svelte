<script lang="ts">
	import { onMount } from 'svelte';
	import pageTitle from '$lib/page/pageTitle';
	import { _ } from 'svelte-i18n';
	import { base } from '$app/paths';

	$pageTitle = $_('page.about.title');
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row row-cols-xxl-1 row-cols-md-1 row-cols-1">
		<div class="col">
			<div class="card d-block">
				<div class="card-body">
					<h3 class="mt-3">{$_('page.about.intro.heading')}</h3>
					<p class="card-text">{$_('page.about.intro.p1')}</p>
					<p class="card-text">{$_('page.about.intro.p2')}</p>

					<h3 class="mt-4">{$_('page.about.idea.heading')}</h3>
					<p class="card-text">{$_('page.about.idea.p1')}</p>
					<p class="card-text">{$_('page.about.idea.p2')}</p>

					<div class="my-4 p-0 d-flex justify-content-start" style="margin: 0;">
						<img
							src="{base}/assets/images/AUGUR-process-Ilustration.png"
							alt="AUGUR process illustration"
							class="img-fluid"
							style="max-width: 60%; height: auto; display: block; margin: 0 auto; border: none; padding: 0;"
						/>
					</div>

					<h3 class="mt-4">{$_('page.about.technology.heading')}</h3>
					<p class="card-text">{$_('page.about.technology.p1')}</p>
					<p class="card-text">{$_('page.about.technology.p2')}</p>
					<p class="card-text">{$_('page.about.technology.p3')}</p>
					<div class="my-4 p-0" style="margin: 0;">
						<img
							src="{base}/assets/images/AUGUR-concept.png"
							alt="AUGUR process illustration"
							class="img-fluid"
							style="max-width: 60%; height: auto; display: block; margin: 0 auto; border: none; padding: 0;"
						/>
					</div>

					<h3 class="mt-4">{$_('page.about.getting_started.heading')}</h3>
					<p class="card-text">{$_('page.about.getting_started.p1')}</p>
					<div class="d-flex gap-2">
						<a class="btn btn-primary" href="{base}/precipitation"
							>{$_('page.about.getting_started.open_precip')}</a
						>
						<a class="btn btn-outline-primary" href="{base}/discharge"
							>{$_('page.about.getting_started.open_discharge')}</a
						>
					</div>

					<h3 class="mt-4">{$_('page.about.credits.heading')}</h3>
					<p class="card-text">{$_('page.about.credits.p1')}</p>
					<p class="card-text">{$_('page.about.credits.p2')}</p>
					<div class="my-4 p-0" style="margin: 0;">
						<div class="d-flex justify-content-center align-items-center gap-4">
							<img
								src="{base}/assets/images/logo-deza.png"
								alt="DEZA logo"
								class="img-fluid"
								style="max-width: 20%; height: auto; border: none; padding: 0;"
							/>
							<img
								src="{base}/assets/images/logo-bern.png"
								alt="Bern logo"
								class="img-fluid"
								style="max-width: 20%; height: auto; border: none; padding: 0;"
							/>
							<img
								src="{base}/assets/images/logo-srk.png"
								alt="SRK logo"
								class="img-fluid"
								style="max-width: 20%; height: auto; border: none; padding: 0;"
							/>
						</div>
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
