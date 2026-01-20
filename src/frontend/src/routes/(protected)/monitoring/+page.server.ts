import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load() {
	if (browser) {
		if (!page.data.session?.user?.name) {
			redirect(303, './login?redirect_url=' + page.url.href);
		}
	}

	return {};
}
