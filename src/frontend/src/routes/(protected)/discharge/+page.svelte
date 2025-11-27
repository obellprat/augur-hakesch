<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { _ } from 'svelte-i18n';
	import type { PageServerData } from './$types';

	let { data }: { data: PageServerData } = $props();

	$pageTitle = $_('page.discharge.title') + '-' + $_('page.discharge.projects');

	let selectedProjects = $state<string[]>([]);
	let selectAll = $state(false);

	function toggleSelectAll() {
		if (selectAll) {
			selectedProjects = data.projects?.map((p: { id: string }) => p.id) || [];
		} else {
			selectedProjects = [];
		}
	}

	function toggleProject(projectId: string) {
		const index = selectedProjects.indexOf(projectId);
		if (index > -1) {
			selectedProjects = selectedProjects.filter((id) => id !== projectId);
		} else {
			selectedProjects = [...selectedProjects, projectId];
		}
		// Update select all checkbox state
		selectAll = selectedProjects.length === (data.projects?.length || 0) && selectedProjects.length > 0;
	}

	$effect(() => {
		// Update select all when projects change
		selectAll = selectedProjects.length === (data.projects?.length || 0) && selectedProjects.length > 0;
	});

	function showDeleteModal() {
		if (selectedProjects.length === 0) {
			return;
		}
		// Use Bootstrap modal API (compatible with jQuery if available)
		const modalElement = document.getElementById('delete-projects-modal');
		if (modalElement) {
			// Check if Bootstrap 5 is available
			if ((window as any).bootstrap) {
				const modal = new (window as any).bootstrap.Modal(modalElement);
				modal.show();
			} else if ((globalThis as any).$) {
				// Fallback to jQuery if available
				(globalThis as any).$('#delete-projects-modal').modal('show');
			}
		}
	}

	onMount(async () => {});
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="flex-grow-1 card">
	<div class="h-100">
		<div class="card-body py-2">
			<div class="d-flex align-items-center gap-2">
				<div class="form-check">
					<input
						class="form-check-input"
						type="checkbox"
						value=""
						id="flexCheckDefault"
						checked={selectAll}
						onchange={() => {
							selectAll = !selectAll;
							toggleSelectAll();
						}}
					/>
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
						disabled={selectedProjects.length === 0}
						onclick={showDeleteModal}
					>
						<i class="ri-delete-bin-2-line fs-18"></i>
					</button>
				</div>

				<div class="ms-auto">
					<!--<div class="app-search">
                        <input type="text" class="form-control rounded-pill" placeholder="Search mail...">
                        <i class="ri-search-line fs-18 app-search-icon text-muted"></i>
                    </div>-->
					<a
						href="{base}/discharge/create"
						type="button"
						class="btn btn-primary bg-gradient rounded-pill"
						>{$_('page.discharge.create.createproject')}</a
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
										<input
											class="form-check-input position-relative z-2"
											type="checkbox"
											checked={selectedProjects.includes(project.id)}
											onchange={() => toggleProject(project.id)}
										/>
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

<!-- Delete Projects Modal -->
<div
	id="delete-projects-modal"
	class="modal fade"
	tabindex="-1"
	role="dialog"
	aria-labelledby="warning-header-modalLabel"
	aria-hidden="true"
>
	<div class="modal-dialog">
		<div class="modal-content">
			<div class="modal-header text-bg-warning border-0">
				<h4 class="modal-title" id="warning-header-modalLabel">
					{$_('page.discharge.overview.deleteProject')}
				</h4>
				<button
					type="button"
					class="btn-close btn-close-white"
					data-bs-dismiss="modal"
					aria-label="Close"
				></button>
			</div>
			<div class="modal-body">
				<p>
					{#if selectedProjects.length === 1}
						{$_('page.discharge.overview.shoulddeleteproject', {
							values: {
								title:
									data.projects?.find((p: { id: string }) => p.id === selectedProjects[0])?.title ||
									''
							}
						})}
					{:else}
						Sollen {selectedProjects.length} Projekte gelöscht werden?
					{/if}
				</p>
			</div>
			<div class="modal-footer">
				<button type="button" class="btn btn-light" data-bs-dismiss="modal"
					>{$_('page.general.cancel')}</button
				>
				<form method="POST" action="?/delete">
					{#each selectedProjects as projectId}
						<input type="hidden" name="ids[]" value={projectId} />
					{/each}
					<input type="hidden" name="userid" value={data.session?.myuser.id} />
					<button type="submit" class="btn btn-warning">{$_('page.general.delete')}</button>
				</form>
			</div>
		</div>
		<!-- /.modal-content -->
	</div>
	<!-- /.modal-dialog -->
</div>
<!-- /.modal -->
