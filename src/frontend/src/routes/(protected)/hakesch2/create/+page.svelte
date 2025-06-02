<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
	import type { ActionData, PageServerData } from './$types';
	import { onMount } from 'svelte';
	import Sidebar from '$lib/page/hakesch2/sidebar.svelte';

	let { data, form }: { data: PageServerData; form: ActionData } = $props();
	$pageTitle = 'HAKESCH 2.0 - Projekt erstellen';

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
					<h3 class="my-0 lh-base">Neues Projekt erstellen</h3>
				</div>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<div class="col-lg-6">
					<form method="post">
						<div class="mb-3">
							<label for="simpleinput" class="form-label">Projekttitel</label>
							<input type="text" name="title" class="form-control" />
						</div>

						<div class="mb-3">
							<label for="example-textarea" class="form-label">Beschreibung</label>
							<textarea class="form-control" name="description" rows="5"></textarea>
						</div>

						<button type="submit" class="btn btn-primary">Erstellen</button>
					</form>
				</div>
				<!-- end col -->
			</div>
			<!-- end row-->
		</div>
	</div>
</div>
