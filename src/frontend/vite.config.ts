import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { cjsInterop } from 'vite-plugin-cjs-interop';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		sveltekit(),
		cjsInterop({
			// List of CJS dependencies that require interop
			dependencies: ['cupertino-pane'],
			apply: 'serve'
		}),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/bootstrap/dist/**/*',
					dest: 'assets/vendor/bootstrap'
				},
				{
					src: 'node_modules/jquery/dist/**/*',
					dest: 'assets/vendor/jquery'
				}
			]
		})
	]
});
