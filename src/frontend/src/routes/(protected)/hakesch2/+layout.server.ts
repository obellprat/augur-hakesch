import type { PageServerLoad } from './$types';
import { getAllProjects } from '$lib/server/project';
import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const load: PageServerLoad = async (events) => {
	if (browser) {
		if (!data.session?.user) {
			redirect(303, `./login?redirect_url=` + '{base}/hakesch2');
		}
	}

	const session = await events.locals.auth();
	if (session) {
		const projects = await getAllProjects(session.myuser.id);

		return {
			session,
			projects
		};
	}
	else redirect(303, base+`/login?redirect_url=` + base + '/hakesch2');
};
