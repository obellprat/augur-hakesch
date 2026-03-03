<script lang="ts">
	import '../scss/app.scss';
	import '../scss/icons.scss';

	import { base } from '$app/paths';
	import { env } from '$env/dynamic/public';

	import { SvelteToast } from '@zerodevx/svelte-toast';

	import { Footer, Menu, LoadingOverlay } from '$lib/index';

	import { loadScript } from '$lib/page/loadscript';
	import { onMount } from 'svelte';
	import { _, locale } from 'svelte-i18n';

	import { UmamiAnalytics, trackSession, status } from '@lukulent/svelte-umami';
	import { page } from '$app/state';

	let { children } = $props();
	let sessionTracked = false;
	let dismissImportantNews = $state(false);

	onMount(async () => {
		await loadScript(`${base}/assets/js/app.js`);
	});

	$effect(() => {
		if (!sessionTracked && $status === 'loaded' && page.data.session) {
			sessionTracked = true;
			const trackedUserId = (page.data.session as any).myuser?.id?.toString() ?? '0';
			trackSession(trackedUserId, {
				email: page.data.session.user?.email ?? '',
				name: page.data.session.user?.name ?? ''
			} as any);
		}
	});

	const getLocalizedValue = (
		news: {
			titleDe: string;
			titleEn: string;
			titleFr: string;
			contentDe: string;
			contentEn: string;
			contentFr: string;
		},
		field: 'title' | 'content'
	) => {
		const currentLocale = ($locale || 'en').toLowerCase();
		const language = currentLocale.startsWith('de')
			? 'de'
			: currentLocale.startsWith('fr')
				? 'fr'
				: 'en';

		if (field === 'title') {
			if (language === 'de') return news.titleDe || news.titleEn || news.titleFr;
			if (language === 'fr') return news.titleFr || news.titleEn || news.titleDe;
			return news.titleEn || news.titleDe || news.titleFr;
		}

		if (language === 'de') return news.contentDe || news.contentEn || news.contentFr;
		if (language === 'fr') return news.contentFr || news.contentEn || news.contentDe;
		return news.contentEn || news.contentDe || news.contentFr;
	};

	const markImportantNewsAsRead = async () => {
		if (!page.data.importantNews) return;

		const accessToken = (page.data.session as any)?.access_token;
		if (!accessToken) return;

		try {
			const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/news/${page.data.importantNews.id}/read`, {
				method: 'POST',
				headers: {
					Authorization: 'Bearer ' + accessToken
				}
			});

			if (response.ok) {
				dismissImportantNews = true;
			}
		} catch (error) {
			console.error(`Error while marking important news as read: ${error}`);
		}
	};
</script>

<UmamiAnalytics websiteID="a38a9cf9-a9dd-4b4a-bc94-5d1612de34b3" srcURL="https://umami.geotools.ch/script.js" />

<svelte:head>
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
	<style>
		html, body, :root {
			font-family: 'Inter', sans-serif !important;
		}
	</style>
	<script src="{base}/assets/vendor/jquery/jquery.min.js"></script>
	<script src="{base}/assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
</svelte:head>
<!-- Begin page -->
<div class="wrapper">
	<Menu />

	<!-- ============================================================== -->
	<!-- Start Page Content here -->
	<!-- ============================================================== -->
	<div class="page-content">
		{@render children()}
		<Footer />
	</div>
	<LoadingOverlay />
	<SvelteToast />
	{#if page.data.session && page.data.importantNews && !dismissImportantNews}
		<div
			class="modal fade show d-block"
			tabindex="-1"
			aria-modal="true"
			role="dialog"
			style="background: rgba(0, 0, 0, 0.5);"
		>
			<div class="modal-dialog modal-dialog-centered">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">{$_('page.news.importantModalTitle')}</h5>
					</div>
					<div class="modal-body">
						<h6 class="fw-semibold">{getLocalizedValue(page.data.importantNews, 'title')}</h6>
						<p class="mb-0">{getLocalizedValue(page.data.importantNews, 'content')}</p>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-primary" onclick={markImportantNewsAsRead}>
							{$_('page.news.markAsRead')}
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
	<!-- ============================================================== -->
	<!-- End Page content -->
	<!-- ============================================================== -->
</div>
<!-- END wrapper -->
