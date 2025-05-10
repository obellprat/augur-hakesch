import { browser } from '$app/environment';
import { page } from '$app/state';
import { redirect } from '@sveltejs/kit';

export async function load(events) {
	const session = await events.locals.auth();

	return { session };
}
