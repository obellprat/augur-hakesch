<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { _ } from 'svelte-i18n'

	export let data;

	$pageTitle = $_('page.discharge.title') + "-" + $_('page.discharge.projects');

	onMount(async () => {});
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="flex-grow-1 card">
	<div class="h-100">
		<div class="card-body py-2">
			<div class="d-flex align-items-center gap-2">
				<button
					type="button"
					class="btn btn-light d-xxl-none d-flex p-1"
					data-bs-toggle="offcanvas"
					data-bs-target="#email-sidebar"
					aria-controls="email-sidebar"
					aria-label="show sidebar"
				>
					<i class="ri-menu-2-line fs-17"></i>
				</button>

				<div class="form-check">
					<input class="form-check-input" type="checkbox" value="" id="flexCheckDefault" />
				</div>

				<div class="d-flex align-items-center">
					<button
						type="button"
						class="btn btn-sm btn-icon btn-ghost-light text-body rounded-circle"
						data-bs-toggle="tooltip"
						data-bs-html="true"
						data-bs-trigger="hover"
						data-bs-placement="top"
						data-bs-title="<span class='fs-12'>Delete</span>"
						aria-label="delete"
					>
						<i class="ri-delete-bin-2-line fs-18"></i>
					</button>
				</div>

				<div class="ms-auto d-xl-flex d-none">
					<!--<div class="app-search">
                        <input type="text" class="form-control rounded-pill" placeholder="Search mail...">
                        <i class="ri-search-line fs-18 app-search-icon text-muted"></i>
                    </div>-->
					<a
						href="{base}/discharge/create"
						type="button"
						class="btn btn-primary bg-gradient rounded-pill">{$_('page.discharge.create.createproject')}</a
					>
				</div>
			</div>
		</div>

		<div class="border-top border-light">
			<div class="table-responsive">
				<table class="table table-hover mail-list mb-0">
					<thead
						><tr>
							<th></th>
							<th>{$_('page.discharge.overview.projectTitle')}</th>
							<th>{$_('page.discharge.overview.description')}</th>
							<th>{$_('page.discharge.overview.easting')}</th>
							<th>{$_('page.discharge.overview.northing')}</th>
						</tr>
					</thead>
					<tbody>
						{#if data.projects && data.projects.length}
							{#each data.projects as project (project.id)}
								<tr class="position-relative">
									<td class="ps-3">
										<input class="form-check-input position-relative z-2" type="checkbox" />
									</td>

									<td>
										<a
											href="{base}/discharge/overview/{project.id}"
											class="link-reset fs-14 fw-medium stretched-link"
										>
											{project.title}
										</a>
									</td>

									<td>
										<div>
											<span class="fs-14 text-muted mb-0">{project.description}</span>
										</div>
									</td>

									<td>
										<div>
											<span class="fs-14 text-muted mb-0">{project.Point.easting}</span>
										</div>
									</td>

									<td>
										<div>
											<span class="fs-14 text-muted mb-0">{project.Point.northing}</span>
										</div>
									</td>

									<td>
										<p class="fs-12 text-muted mb-0 text-end"></p>
									</td>

									<td class="pe-3">
										<iconify-icon
											icon="solar:bolt-circle-bold-duotone"
											class="text-danger fs-16 ms-2 align-middle"
										></iconify-icon>
									</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</div>
	</div>
</div>
