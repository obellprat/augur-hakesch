// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
import { PrismaClient } from '../../prisma/src/generated/prisma/client';

declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
	let prisma: PrismaClient;
}

export {};
