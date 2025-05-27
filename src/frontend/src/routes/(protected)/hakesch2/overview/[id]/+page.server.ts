	
import { getProjectById, updateProject } from "$lib/server/project";
import { error } from "@sveltejs/kit";
import { fail, redirect } from "@sveltejs/kit";
import type { Actions } from './$types';
import { base } from '$app/paths';

export const load = async ({ params }) => {
  const { id } = params;
  const project = await getProjectById(id);

  if (!project) {
    error(404, "Project not found");
  }

  return {
    project,
  };
};

export const actions = {
  default: async ({ request }) => {
    const formData = Object.fromEntries(await request.formData());
    const { title, id, description } = formData as unknown as {
      title: string | undefined;
      id: string | undefined;
      description: string|undefined;
    };
    if (!title || !id) {
      return fail(400, { message: "Missing required fields" });
    }

    const updatedPost = await updateProject(id, {
      title,
      description
    });

    redirect(302, `${base}/hakesch2/overview/${updatedPost.id}`);
  },
} satisfies Actions;
