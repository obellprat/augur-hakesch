<script lang="ts">
	import { _ } from 'svelte-i18n';
	import { CLIMAQVA_URL, WSL_URL } from '$lib/dischargeMigration';

	let {
		migrated = false,
		compact = false,
		showCta = true,
		className = ''
	}: {
		migrated?: boolean;
		compact?: boolean;
		showCta?: boolean;
		className?: string;
	} = $props();
</script>

{#if compact && migrated}
	<div
		class={['alert alert-info d-flex align-items-center gap-2 py-2 px-3 small', className]}
		role="alert"
	>
		<i class="ti ti-info-circle fs-18 flex-shrink-0" aria-hidden="true"></i>
		<span>
			{$_('page.discharge.migration.shortAfterPrefix')}<a
				href={CLIMAQVA_URL}
				class="alert-link text-decoration-underline position-relative z-2"
				>{$_('page.discharge.migration.climaqvaShortLabel')}</a
			>{$_('page.discharge.migration.shortAfterMiddle')}<a
				href={WSL_URL}
				class="alert-link text-decoration-underline position-relative z-2"
				target="_blank"
				rel="noopener noreferrer">{$_('page.discharge.migration.wslShortLabel')}</a
			>{$_('page.discharge.migration.shortAfterSuffix')}
		</span>
	</div>
{:else}
	<div
		class={[
			'alert d-flex align-items-start',
			compact ? 'gap-2 p-3' : 'gap-3',
			migrated ? 'alert-info' : 'alert-warning',
			className
		]}
		role="alert"
	>
		<i
			class={[
				'flex-shrink-0',
				compact ? 'fs-20' : 'fs-22 mt-1',
				migrated ? 'ti ti-info-circle' : 'ti ti-alert-triangle'
			]}
			aria-hidden="true"
		></i>
		<div class="flex-grow-1">
			{#if compact}
				<div class="fw-semibold mb-1">
					{migrated
						? $_('page.discharge.migration.titleAfter')
						: $_('page.discharge.migration.titleBefore')}
				</div>
			{:else}
				<h5 class="alert-heading fw-semibold mb-1">
					{migrated
						? $_('page.discharge.migration.titleAfter')
						: $_('page.discharge.migration.titleBefore')}
				</h5>
			{/if}
			<p class={['mb-0', compact && 'small']}>
				{#if migrated}
					{$_('page.discharge.migration.bodyAfterPrefix')}<a
						href={CLIMAQVA_URL}
						class="alert-link text-decoration-underline position-relative z-2"
						target="_blank"
						rel="noopener noreferrer">{$_('page.discharge.migration.climaqvaLabel')}</a
					>{$_('page.discharge.migration.bodyAfterMiddle')}<a
						href={WSL_URL}
						class="alert-link text-decoration-underline position-relative z-2"
						target="_blank"
						rel="noopener noreferrer">{$_('page.discharge.migration.wslLabel')}</a
					>{$_('page.discharge.migration.bodyAfterSuffix')}
				{:else}
					{$_('page.discharge.migration.bodyBeforePrefix')}<a
						href={CLIMAQVA_URL}
						class="alert-link text-decoration-underline position-relative z-2"
						target="_blank"
						rel="noopener noreferrer">{$_('page.discharge.migration.climaqvaLabel')}</a
					>{$_('page.discharge.migration.bodyBeforeMiddle')}<a
						href={WSL_URL}
						class="alert-link text-decoration-underline position-relative z-2"
						target="_blank"
						rel="noopener noreferrer">{$_('page.discharge.migration.wslLabel')}</a
					>{$_('page.discharge.migration.bodyBeforeSuffix')}
				{/if}
			</p>
			{#if showCta}
				<div class="mt-2">
					<a
						href={CLIMAQVA_URL}
						class={['btn btn-sm position-relative z-2', migrated ? 'btn-info' : 'btn-warning']}
						target={migrated ? '_self' : '_blank'}
						rel={migrated ? undefined : 'noopener noreferrer'}
					>
						{$_('page.discharge.migration.ctaClimaQva')}
						<i class="ti ti-external-link ms-1" aria-hidden="true"></i>
					</a>
				</div>
			{/if}
		</div>
	</div>
{/if}
