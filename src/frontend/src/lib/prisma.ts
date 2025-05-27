import { PrismaClient } from '../../prisma/src/generated/prisma/client';
import { DATABASE_URL } from '$env/static/private';
import { withAccelerate } from '@prisma/extension-accelerate';

const prisma =
	globalThis.prisma ??
	new PrismaClient({
		datasourceUrl: DATABASE_URL
	}).$extends(withAccelerate());
console.log('Hoi');
if (process.env.NODE_ENV != 'production') globalThis.prisma = prisma;

export { prisma };
