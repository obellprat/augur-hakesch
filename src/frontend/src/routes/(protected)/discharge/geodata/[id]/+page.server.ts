import { getProjectById } from '$lib/server/project';
import { error } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { page } from '$app/state';

export const load = async ({ params }) => {
	if (browser) {
		if (!page.data.session?.user?.name) {
			redirect(303, `./login?redirect_url=` + page.url.href + '/discharge');
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
