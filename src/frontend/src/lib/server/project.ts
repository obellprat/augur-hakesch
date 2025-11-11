import type { Prisma } from '../../../prisma/src/generated/prisma/client';
import { prisma } from '$lib/prisma';

const createNewProject = async (project: Prisma.ProjectCreateInput) => {
	// Get all annualities (2.3, 20, 100)
	const annualities = await prisma.Annualities.findMany({
		where: {
			number: {
				in: [2.3, 20, 100]
			}
		}
	});

	// If annualities don't exist, create them
	if (annualities.length === 0) {
		await prisma.Annualities.createMany({
			data: [
				{ number: 2.3, description: 'HQ 2.3' },
				{ number: 20, description: 'HQ 20' },
				{ number: 100, description: 'HQ 100' }
			],
			skipDuplicates: true
		});
		// Fetch again after creation
		const newAnnualities = await prisma.Annualities.findMany({
			where: {
				number: {
					in: [2.3, 20, 100]
				}
			}
		});
		annualities.push(...newAnnualities);
	}

	// Create the project with default scenarios for all hydrological calculations
	// Each scenario consists of 3 entries (one per annuality)
	const createdProject = await prisma.project.create({
		data: {
			...project,
			// Create Mod. Fliesszeitverfahren for all 3 annualities (1 scenario)
			Mod_Fliesszeit: {
				create: annualities.map((annuality: { id: number }) => ({
					x: annuality.id,
					Vo20: 0,
					psi: 0
				}))
			},
			// Create Koella for all 3 annualities (1 scenario)
			Koella: {
				create: annualities.map((annuality: { id: number }) => ({
					x: annuality.id,
					Vo20: 0,
					glacier_area: 0
				}))
			},
			// Create Clark-WSL for all 3 annualities (1 scenario)
			ClarkWSL: {
				create: annualities.map((annuality: { id: number }) => ({
					x: annuality.id
				}))
			},
			// Create NAM for all 3 annualities (1 scenario)
			NAM: {
				create: annualities.map((annuality: { id: number }) => ({
					x: annuality.id,
					precipitation_factor: 0.7,
					water_balance_mode: 'cumulative'
				}))
			}
		}
	});

	return createdProject;
};

const getProjectById = async (id: string) => {
	return await prisma.project.findUnique({
		where: {
			id
		},
		include: {
			Point: true,
			IDF_Parameters: true,
			Mod_Fliesszeit: {
				orderBy: {
					id: 'asc'
				},
				include: {
					Annuality: true,
					Mod_Fliesszeit_Result: true,
					Mod_Fliesszeit_Result_1_5: true,
					Mod_Fliesszeit_Result_2: true,
					Mod_Fliesszeit_Result_3: true,
					Mod_Fliesszeit_Result_4: true
				}
			},
			Koella: {
				orderBy: {
					id: 'asc'
				},
				include: {
					Annuality: true,
					Koella_Result: true,
					Koella_Result_1_5: true,
					Koella_Result_2: true,
					Koella_Result_3: true,
					Koella_Result_4: true
				}
			},
			ClarkWSL: {
				orderBy: {
					id: 'asc'
				},
				include: {
					Annuality: true,
					ClarkWSL_Result: true,
					ClarkWSL_Result_1_5: true,
					ClarkWSL_Result_2: true,
					ClarkWSL_Result_3: true,
					ClarkWSL_Result_4: true,
					Fractions: true
				}
			},
			NAM: {
				orderBy: {
					id: 'asc'
				},
				include: {
					Annuality: true,
					NAM_Result: true,
					NAM_Result_1_5: true,
					NAM_Result_2: true,
					NAM_Result_3: true,
					NAM_Result_4: true,
				}
			}
		}
	});
};

const updateProject = async (projectId: string, project: Prisma.ProjectUpdateInput) => {
	return await prisma.project.update({
		where: { id: projectId },
		data: project
	});
};

const getAllProjects = async (userId: number) => {
	return await prisma.project.findMany({
		where: {
			user: { id: userId }
		},
		include: {
			Point: true
		},
		orderBy: {
			lastModified: 'desc'
		}
	});
};

const getAllZones = async () => {
	return await prisma.ZoneParameter.findMany({});
};

const deleteProject = async (projectId: string, userId: number) => {
	return await prisma.project.delete({
		where: {
			user: { id: userId },
			id: projectId
		}
	});
};

export {
	createNewProject,
	getProjectById,
	updateProject,
	getAllProjects,
	deleteProject,
	getAllZones
};
