<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { _, locale } from 'svelte-i18n';

	let { data } = $props();
	$pageTitle = $_('page.news.title');

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
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row">
		<div class="col-12">
			<div class="d-flex align-items-center justify-content-between mb-3">
				<h4 class="mb-0">{$_('page.news.title')}</h4>
			</div>
		</div>
	</div>

	{#if data.news.length === 0}
		<div class="row">
			<div class="col-12">
				<div class="alert alert-info mb-0">{$_('page.news.noNews')}</div>
			</div>
		</div>
	{:else}
		<div class="row">
			{#each data.news as news}
				<div class="col-12 mb-3">
					<div class="card">
						<div class="card-body">
							<div class="d-flex justify-content-between align-items-center mb-2">
								<h5 class="card-title mb-0">{getLocalizedValue(news, 'title')}</h5>
								<div class="d-flex gap-2">
									{#if news.isImportant}
										<span class="badge bg-danger">{$_('page.news.important')}</span>
									{/if}
									{#if news.isRead}
										<span class="badge bg-success">{$_('page.news.read')}</span>
									{/if}
								</div>
							</div>
							<p class="text-muted small mb-2">
								{new Date(news.createdAt).toLocaleString()}
							</p>
							<p class="mb-3">{getLocalizedValue(news, 'content')}</p>
							{#if data.session && !news.isRead}
								<form method="POST" action="?/markRead">
									<input type="hidden" name="newsId" value={news.id} />
									<button type="submit" class="btn btn-outline-primary btn-sm">
										{$_('page.news.markAsRead')}
									</button>
								</form>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="row mt-4">
		<div class="col-12">
			<div class="d-flex align-items-center justify-content-between mb-3">
				<h4 class="card-title mb-3">{$_('page.news.changelog')}</h4>
			</div>
		</div>
	</div>
	<div class="row">
		<div class="col-12">
			<div class="card">
				<div class="card-body">
					<div class="changelog-content">
						{@html data.changelogHtml}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.changelog-content :global(h1),
	.changelog-content :global(h2),
	.changelog-content :global(h3),
	.changelog-content :global(h4) {
		margin-top: 1.25rem;
		margin-bottom: 0.75rem;
		font-weight: 600;
	}

	.changelog-content :global(p) {
		margin-bottom: 0.75rem;
		line-height: 1.6;
	}

	.changelog-content :global(ul),
	.changelog-content :global(ol) {
		margin-bottom: 0.75rem;
		padding-left: 1.25rem;
	}

	.changelog-content :global(code) {
		background: rgba(128, 128, 128, 0.15);
		padding: 0.1rem 0.35rem;
		border-radius: 4px;
	}

	.changelog-content :global(pre) {
		padding: 0.75rem;
		border-radius: 6px;
		background: rgba(128, 128, 128, 0.12);
		overflow: auto;
	}
</style>
