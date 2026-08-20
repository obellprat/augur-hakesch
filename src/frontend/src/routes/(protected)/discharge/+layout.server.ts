import type { PageServerLoad } from './$types';
import { getAllProjects } from '$lib/server/project';
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const load: PageServerLoad = async (events) => {
	const session = await events.locals.auth();
	if (session?.myuser?.id) {
		const projects = await getAllProjects(session.myuser.id);

		return {
			session,
			projects
		};
	}
	redirect(303, base + `/login?redirect_url=` + base + '/discharge');
};
