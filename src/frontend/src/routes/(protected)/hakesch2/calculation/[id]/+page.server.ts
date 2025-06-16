import { getProjectById, updateProject, deleteProject } from '$lib/server/project';
import { error } from '@sveltejs/kit';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { base } from '$app/paths';
import { browser } from '$app/environment';
import { page } from '$app/state';
import { prisma } from '$lib/prisma';
import { NULL } from 'sass';

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
	updatefnp: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, idf_id, P_low_1h, P_high_1h, P_low_24h, P_high_24h, rp_low, rp_high} = formData as unknown as {
			id: string | undefined;
			idf_id: number | undefined;
			P_low_1h: number | undefined;
			P_high_1h: number | undefined;
			P_low_24h: number | undefined;
			P_high_24h: number | undefined;
			rp_low: number | undefined;
			rp_high: number | undefined;
		};
		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}

		const idf = await prisma.IDF_Parameters.upsert({
			where: {id : Number(idf_id) || 0},
			update: {
				P_low_1h: Number(P_low_1h) || 0,
				P_high_1h: Number(P_high_1h) || 0,
				P_low_24h: Number(P_low_24h) || 0,
				P_high_24h: Number(P_high_24h) || 0,
				rp_low: Number(rp_low) || 0,
				rp_high: Number(rp_high) || 0
			},
			create: {
				P_low_1h: Number(P_low_1h) || 0,
				P_high_1h: Number(P_high_1h) || 0,
				P_low_24h: Number(P_low_24h) || 0,
				P_high_24h: Number(P_high_24h) || 0,
				rp_low: Number(rp_low) || 0,
				rp_high: Number(rp_high) || 0
			}
		})

		await prisma.project.update({
			where: { id: id!},
			data: {
				IDF_Parameters: {
					connect: {
							id: idf.id,
					}
				}
			}
		});

		redirect(302, `${base}/hakesch2/calculation/${id}`);
	},

	updatemfzv: async ({ request }) => {
		const formData = Object.fromEntries(await request.formData());
		const { id, mfzv_id, x, Vo20, psi} = formData as unknown as {
			id: string | undefined;
			mfzv_id: number | undefined;
			x: number | undefined;
			Vo20: number | undefined;
			psi: number | undefined;
		};
		
		if (!id) {
			return fail(400, { message: 'Missing required fields' });
		}
		const annuality = await prisma.Annualities.findUnique({
			where: {
				number: Number(x) || 0
			}
		})
		console.log("Da noch");
		const mfzv = await prisma.Mod_Fliesszeit.upsert({
			where: {
				id : Number(mfzv_id) || 0				
			},
			update: {
				Annuality: {
					connect : {
						id: annuality.id
					}	
				},
				Vo20: Number(Vo20) || 0,
				psi: Number(psi) || 0
			},
			create: {
				Annuality: {
					connect : {
						number: Number(x) || 0
					}	
				},
				Vo20: Number(Vo20) || 0,
				psi: Number(psi) || 0,
				Project: {
					connect: {
						id: id
					}
				}
			}
		})
		
		console.log("Da noch immer");
		const project = await prisma.project.update({
			where: { id: id!},
			data: {
				Mod_Fliesszeit: {
					connect: {
							id: mfzv.id,
					}
				}
			},
			include: {
				Point: true,
				IDF_Parameters: true,
				Mod_Fliesszeit: {
					orderBy: {
						id: "asc",
					},
					include: {
						Annuality: true,
						Mod_Fliesszeit_Result: true
					}
				}
			}
		});
		return project;
		//redirect(302, `${base}/hakesch2/calculation/${id}`);
	},

	delete: async({request}) => {
		const formData = Object.fromEntries(await request.formData());
		const { id } = formData as unknown as {
			id: number | undefined;
		};

		await await prisma.Mod_Fliesszeit.delete({
			where : {
				id: Number(id)
			}
		});
	}
} satisfies Actions;
