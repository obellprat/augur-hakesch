import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { cjsInterop } from 'vite-plugin-cjs-interop';

export default defineConfig({
	plugins: [
		sveltekit(),
		cjsInterop({
			// List of CJS dependencies that require interop
			dependencies: ['cupertino-pane']
		})
	]
});
