import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (events) => {
	const session = await events.locals.auth();
	return {
		session
	};
};
