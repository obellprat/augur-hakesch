	
import { createNewProject} from "$lib/server/project";
import { fail, redirect } from "@sveltejs/kit";
import type { Actions } from './$types';
import { base } from '$app/paths';

export const actions = {
  default: async ({ request, locals }) => {
    const auth = await locals.auth();
    console.log(auth.myuser);
    const formData = Object.fromEntries(await request.formData());
    const { title, description } = formData as unknown as {
      title: string | undefined;
      description: string;
    };
    if (!title) {
      return fail(400, { message: "Missing required fields" });
    }

    const createdProject = await createNewProject({
      title: title,
      description: description,
      user: {connect
        : {id:auth.myuser.id}
      }, 
      Point: {
        create: {
          northing: 2600000,
          easting: 1200000
        }        
      }
    });

    redirect(302, `${base}/hakesch2/overview/${createdProject.id}`);
  },
} satisfies Actions;
