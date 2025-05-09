import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load({ parent }) {
	/*await parent().then(async(data) => {
		if (browser) {
			console.log(data.keycloak);
			await data.keycloakPromise;

			if (data.keycloak!=null && !data.keycloak.authenticated) {
				redirect(307,"/login?redirect_url="+page.url.pathname);
			}
			else if (data.keycloak===null) {
				console.log("not initialized");
			}
		}

	});*/
}
