import type { Prisma } from '../../../prisma/src/generated/prisma/client';
import { prisma } from '$lib/prisma';

const createNewProject = async (project: Prisma.ProjectCreateInput) => {
	return await prisma.project.create({
		data: project
	});
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
					Mod_Fliesszeit_Result: true
				}
			},
			Koella: {
				orderBy: {
					id: 'asc'
				},
				include: {
					Annuality: true,
					Koella_Result: true
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

const deleteProject = async (projectId: string, userId: number) => {
	return await prisma.project.delete({
		where: {
			user: { id: userId },
			id: projectId
		}
	});
};

export { createNewProject, getProjectById, updateProject, getAllProjects, deleteProject };
