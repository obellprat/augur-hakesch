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
					<h1 class="card-title">{$_('page.about.title')}</h1>

					<h4 class="mt-3">{$_('page.about.intro.heading')}</h4>
					<p class="card-text">{$_('page.about.intro.p1')}</p>
					<p class="card-text">{$_('page.about.intro.p2')}</p>

					<h4 class="mt-4">{$_('page.about.idea.heading')}</h4>
					<p class="card-text">{$_('page.about.idea.p1')}</p>
					<p class="card-text">{$_('page.about.idea.p2')}</p>

					<h4 class="mt-4">{$_('page.about.technology.heading')}</h4>
					<p class="card-text">{$_('page.about.technology.p1')}</p>
					<ul>
						<li>{$_('page.about.technology.list.svelte')}</li>
						<li>{$_('page.about.technology.list.fastapi')}</li>
						<li>{$_('page.about.technology.list.prisma')}</li>
						<li>{$_('page.about.technology.list.celery')}</li>
						<li>{$_('page.about.technology.list.redis')}</li>
						<li>{$_('page.about.technology.list.docker')}</li>
					</ul>

					<h4 class="mt-4">{$_('page.about.getting_started.heading')}</h4>
					<p class="card-text">{$_('page.about.getting_started.p1')}</p>
					<div class="d-flex gap-2">
						<a class="btn btn-primary" href="{base}/precipitation">{$_('page.about.getting_started.open_precip')}</a>
						<a class="btn btn-outline-primary" href="{base}/discharge">{$_('page.about.getting_started.open_discharge')}</a>
					</div>

					<h4 class="mt-4">{$_('page.about.credits.heading')}</h4>
					<p class="card-text">{$_('page.about.credits.p1')}</p>
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
