import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load({data}) {
		if (browser) {
			console.log(data.session);
			if (!data.session?.user?.name) {
				redirect(303, `./login?redirect_url=` + page.url.href + 'isozones');
			}
		}
	
}
