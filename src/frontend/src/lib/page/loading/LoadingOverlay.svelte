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
    <div class="spinner" />
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

  .spinner {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 3px solid rgba(255, 255, 255, 0.25);
    border-top-color: #fff;
    animation: spin 0.9s linear infinite;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.04) inset;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation: none;
      border-top-color: rgba(255, 255, 255, 0.85);
    }
  }
</style>

