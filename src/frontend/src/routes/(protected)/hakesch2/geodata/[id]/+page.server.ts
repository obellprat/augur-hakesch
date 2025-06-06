import { getProjectById, updateProject, deleteProject } from '$lib/server/project';
import { error } from '@sveltejs/kit';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { base } from '$app/paths';
import { browser } from '$app/environment';
import { page } from '$app/state';

export const load = async ({ params }) => {
	if (browser) {
		if (!page.data.session?.user?.name) {
			redirect(303, `./login?redirect_url=` + page.url.href + '/hakesch2');
		}
	}

	const { id } = params;
	const project = await getProjectById(id);

	if (!project) {
		error(404, 'Project not found');
	}

	return {
		project
	};
};
