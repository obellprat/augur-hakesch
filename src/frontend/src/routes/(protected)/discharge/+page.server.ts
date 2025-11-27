import type { PageServerLoad, Actions } from './$types';
import { getAllProjects, deleteProject } from '$lib/server/project';
import { fail, redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const load: PageServerLoad = async (events) => {
	const session = await events.locals.auth();
	const projects = await getAllProjects(session.myuser.id);

	return {
		session,
		projects
	};
};

export const actions = {
	delete: async ({ request }) => {
		const formData = await request.formData();
		const ids = formData.getAll('ids[]') as string[];
		const userid = formData.get('userid') as string;

		if (!ids || ids.length === 0 || !userid) {
			return fail(400, { message: 'Missing required fields' });
		}

		// Delete all selected projects
		for (const id of ids) {
			await deleteProject(id, parseInt(userid));
		}

		redirect(302, `${base}/discharge`);
	}
} satisfies Actions;
