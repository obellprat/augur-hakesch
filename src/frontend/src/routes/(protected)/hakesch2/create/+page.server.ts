import { createNewProject } from '$lib/server/project';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { base } from '$app/paths';

export const actions = {
	default: async ({ request, locals }) => {
		const auth = await locals.auth();
		const formData = Object.fromEntries(await request.formData());
		const { title, description, easting, northing } = formData as unknown as {
			title: string | undefined;
			description: string | undefined;
			easting: number | undefined;
			northing: number | undefined;
		};
		if (!title) {
			return fail(400, { message: 'Missing required fields' });
		}

		const createdProject = await createNewProject({
			title: title,
			description: description!,
			user: { connect: { id: auth.myuser.id } },
			Point: {
				create: {
					northing: Number(northing),
					easting: Number(easting)
				}
			}
		});

		redirect(302, `${base}/hakesch2/overview/${createdProject.id}`);
	}
} satisfies Actions;
