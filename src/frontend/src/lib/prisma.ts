import { PrismaClient } from '../../prisma/src/generated/prisma/client';
import { env } from '$env/dynamic/private';
import { withAccelerate } from '@prisma/extension-accelerate';

const prisma =
	globalThis.prisma ??
	new PrismaClient({
		datasourceUrl: env.DATABASE_URL
	}).$extends(withAccelerate());
if (process.env.NODE_ENV != 'production') globalThis.prisma = prisma;

export { prisma };
