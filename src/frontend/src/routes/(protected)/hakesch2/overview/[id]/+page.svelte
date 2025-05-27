<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
    import type { ActionData, PageServerData } from "./$types";
	import { onMount } from 'svelte';
	import Sidebar from '$lib/page/hakesch2/sidebar.svelte';
	import { currentProject } from "$lib/state.svelte";

    let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HAKESCH 2.0 - Projekt ' + data.project.title;

	currentProject.title = data.project.title;
	currentProject.id = data.project.id;

	onMount(async () => {});
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="flex-grow-1 card">
	<div class="h-100">
		<div class="card-header py-2 px-3 border-bottom">
			<div class="d-flex align-items-center justify-content-between py-1">
				<div class="d-flex align-items-center gap-2">
					<button
						type="button"
						class="btn btn-light d-xxl-none d-flex p-1"
						data-bs-toggle="offcanvas"
						data-bs-target="#email-sidebar"
						aria-controls="email-sidebar"
					>
						<i class="ri-menu-2-line fs-17"></i>
					</button>
					<h3 class="my-0 lh-base">
						{data.project.title}
					</h3>
				</div>
				<div class="d-flex align-items-center gap-2">
					<a
						href="javascript: void(0);"
						class="btn btn-sm btn-icon btn-ghost-danger d-none d-xl-flex"
						data-bs-toggle="modal"
						data-bs-target="#userCall"
						data-bs-placement="top"
						title="Delete"
						aria-label="delete"
					>
						<i class="ti ti-trash fs-20"></i>
					</a>
					<a
						href="javascript: void(0);"
						class="btn btn-sm btn-icon btn-ghost-primary d-none d-xl-flex"
						data-bs-toggle="modal"
						data-bs-target="#userVideoCall"
						data-bs-placement="top"
						title="Export"
						aria-label="export"
					>
						<i class="ti ti-share fs-20"></i>
					</a>
				</div>
			</div>
		</div>
		<div class="card-body">
			<p class="text-muted">Übersicht</p>
			<div class="row">
				<div class="col-lg-6">
					<form method="post">
						<input type="hidden" name="id" value={data.project.id} />
						<div class="mb-3">
							<label for="simpleinput" class="form-label">Projekttitel</label>
							<input type="text" name="title" class="form-control" value={data.project.title} />
						</div>

						<div class="mb-3">
							<label for="example-textarea" class="form-label">Beschreibung</label>
							<textarea class="form-control" name="description" rows="5"></textarea>
						</div>

                        <button type="submit" class="btn btn-primary">Save</button>
					</form>
				</div>
				<!-- end col -->
			</div>
			<!-- end row-->
		</div>
	</div>
</div>
