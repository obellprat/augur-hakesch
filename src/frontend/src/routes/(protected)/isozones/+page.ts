import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

<<<<<<< HEAD
export async function load() {
	if (browser) {
		await page.data.keycloakPromise;

		if (page.data.keycloak != null && !page.data.keycloak.authenticated) {
			redirect(307, '/login?redirect_url=' + page.url.origin + '/isozones');
		} else if (page.data.keycloak === null) {
			console.log('not initialized');
=======
export async function load({data}) {
		if (browser) {
			console.log(data.session);
			if (!data.session?.user?.name) {
				redirect(303, `./login?redirect_url=` + page.url.href + 'isozones');
			}
>>>>>>> d662451 (replace keycloak-js with auth.js)
		}
	
}
