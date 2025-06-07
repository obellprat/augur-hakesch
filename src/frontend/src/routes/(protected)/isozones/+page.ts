import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load({ data }) {
	if (browser) {
		if (!data.session?.user?.name) {
			redirect(303, `./login?redirect_url=` + page.url.href + 'isozones');
		}
	}
}
