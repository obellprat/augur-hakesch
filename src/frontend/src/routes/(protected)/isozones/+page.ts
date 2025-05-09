
import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load({ parent }) {
		if (browser) {
            console.log("iso page load");
			console.log(page.data.keycloak);
			await page.data.keycloakPromise;

			if (page.data.keycloak!=null && !page.data.keycloak.authenticated) {
				redirect(307,"/login?redirect_url="+page.url.origin+"/isozones");
			}
			else if (page.data.keycloak===null) {
				console.log("not initialized");
			}
        }
}
