<script lang="ts">
	import { navigating } from '$app/stores';
	import { onDestroy } from 'svelte';

	let show = false;
	let startTimer: ReturnType<typeof setTimeout> | null = null;
	let stopTimer: ReturnType<typeof setTimeout> | null = null;

	// Delay showing to avoid flicker on fast navigations
	// Keep visible briefly to avoid instant hide flash
	$: {
		if ($navigating) {
			if (stopTimer) {
				clearTimeout(stopTimer);
				stopTimer = null;
			}
			if (!startTimer) {
				startTimer = setTimeout(() => {
					show = true;
					startTimer = null;
				}, 150);
			}
		} else {
			if (startTimer) {
				clearTimeout(startTimer);
				startTimer = null;
			}
			if (show && !stopTimer) {
				stopTimer = setTimeout(() => {
					show = false;
					stopTimer = null;
				}, 150);
			} else if (!show) {
				show = false;
			}
		}
	}

	onDestroy(() => {
		if (startTimer) clearTimeout(startTimer);
		if (stopTimer) clearTimeout(stopTimer);
	});
</script>

{#if show}
	<div class="loading-overlay" role="status" aria-live="polite" aria-label="Loading">
		<div class="loading-container">
			<svg width="50" height="50" viewBox="0 0 24 24">
				<path
				fill="currentColor"
				d="M12 2A10 10 0 1 0 22 12A10 10 0 0 0 12 2Zm0 18a8 8 0 1 1 8-8A8 8 0 0 1 12 20Z"
				opacity=".5"/><path fill="currentColor" d="M20 12h2A10 10 0 0 0 12 2V4A8 8 0 0 1 20 12Z"
				><animateTransform
					attributeName="transform"
					dur="1s"
					from="0 12 12"
					repeatCount="indefinite"
					to="360 12 12"
					type="rotate"
				/></path>
			</svg>
		</div>
	</div>
{/if}

<style>
	.loading-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.35);
		backdrop-filter: blur(1px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 2000; /* above app chrome */
	}

</style>
