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

export const actions = {
	update: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { title, id, description, easting, northing } = formData as unknown as {
			title: string | undefined;
			id: string | undefined;
			description: string | undefined;
			easting: number | undefined;
			northing: number | undefined;
		};
		if (!title || !id) {
			return fail(400, { message: 'Missing required fields' });
		}

		const updatedProject = await updateProject(id, {
			title,
			description,
			Point: {
				update: {
					easting: Number(easting),
					northing: Number(northing)
				}
			}
		});

		redirect(302, `${base}/hakesch2/overview/${updatedProject.id}`);
	},
	delete: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: string | undefined;
		};

		await deleteProject(id!, page.data.session?.myuser.id);
		redirect(302, `${base}/hakesch2`);
	}
} satisfies Actions;
