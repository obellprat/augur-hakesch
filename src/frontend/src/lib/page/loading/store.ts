import { derived, writable } from 'svelte/store';

// Counts concurrent app-level operations (saves, long tasks)
const counter = writable(0);

export const appLoading = derived(counter, (n) => n > 0);

export function beginLoading() {
  counter.update((n) => n + 1);
}

export function endLoading() {
  counter.update((n) => (n > 0 ? n - 1 : 0));
}

