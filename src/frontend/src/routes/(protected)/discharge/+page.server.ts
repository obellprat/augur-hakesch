import type { PageServerLoad } from './$types';
import { getAllProjects } from '$lib/server/project';

export const load: PageServerLoad = async (events) => {
	const session = await events.locals.auth();
	const projects = await getAllProjects(session.myuser.id);

	return {
		session,
		projects
	};
};
