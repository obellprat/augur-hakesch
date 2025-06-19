<script lang="ts">
	import { base } from '$app/paths';
	import { currentProject } from '$lib/state.svelte';
	import Navlink from './navlink.svelte'

	let props = $props();
	// Function to close the offcanvas menu
	function closeOffcanvas() {
		let closeCanvas = document.querySelector('[data-bs-dismiss="offcanvas"]');
		if (closeCanvas) closeCanvas.click();
	}
</script>

<div class="card email-sidebar">
	<div
		class="offcanvas-xxl offcanvas-start"
		tabindex="-1"
		id="email-sidebar"
		aria-labelledby="email-sidebarLabel"
	>
		<div class="h-100" data-simplebar="init">
			<div class="simplebar-wrapper" style="margin: 0px;">
				<div class="simplebar-height-auto-observer-wrapper">
					<div class="simplebar-height-auto-observer"></div>
				</div>
				<div class="simplebar-mask">
					<div class="simplebar-offset" style="right: 0px; bottom: 0px;">
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<div
							class="simplebar-content-wrapper"
							tabindex="0"
							role="region"
							aria-label="scrollable content"
							style="height: 100%; overflow: hidden;"
						>
							<div class="simplebar-content" style="padding: 0px;">
								<div class="card-body">
									<div class="d-flex justify-content-between gap-2 align-items-center mb-2">
										<button
											type="button"
											class="btn btn-sm btn-icon btn-soft-danger ms-auto d-xl-none"
											data-bs-dismiss="offcanvas"
											data-bs-target="#email-sidebar"
											aria-label="Close"
										>
											<i class="ri-close-line"></i>
										</button>
									</div>

									<div class="email-menu-list d-flex flex-column">
										<a href="{base}/hydrocalc" class="active" onclick={closeOffcanvas}>
											<iconify-icon icon="solar:inbox-outline" class="me-2 fs-18 text-muted"
											></iconify-icon>
											<span>Projekte</span>
											<span class="badge bg-info-subtle fs-12 text-info ms-auto"
												>{props.projectCount}</span
											>
										</a>
										
									</div>
								</div>
								{#if props.currentProject.id != ''}
									<div class="card-body border-top border-light">
										<a
											href="#"
											class="btn-link d-flex align-items-center text-muted fw-bold fs-12 text-uppercase mb-0"
											data-bs-toggle="collapse"
											data-bs-target="#other"
											aria-expanded="false"
											aria-controls="other"
											>Projekt: {currentProject.title}
											<i class="ri-arrow-down-s-line ms-auto"></i></a
										>
										<div id="other" class="collapse show">
											<div class="email-menu-list d-flex flex-column mt-2">
												<Navlink title="Übersicht" href="{base}/hydrocalc/overview/{props.currentProject.id}" tool="overview" />
												<Navlink title="Geodaten" href="{base}/hydrocalc/geodata/{props.currentProject.id}" tool="geodata" />
												<Navlink title="Berechnen" href="{base}/hydrocalc/calculation/{props.currentProject.id}" tool="calculation" />
											</div>
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
				<div class="simplebar-placeholder" style="width: 266px; height: 698px;"></div>
			</div>
			<div class="simplebar-track simplebar-horizontal" style="visibility: hidden;">
				<div class="simplebar-scrollbar" style="width: 0px; display: none;"></div>
			</div>
			<div class="simplebar-track simplebar-vertical" style="visibility: hidden;">
				<div class="simplebar-scrollbar" style="height: 0px; display: none;"></div>
			</div>
		</div>
	</div>
</div>
