/*export async function handle({ event, resolve }) {
	if (event.url.href.includes('#')) {
		console.log('path hat isozones');
	} else {
		return await resolve(event);
	}
}*/

import { type Handle } from '@sveltejs/kit';
import { handle as authenticationHandle } from './auth';
import { sequence } from '@sveltejs/kit/hooks';

async function authorizationHandle({ event, resolve }) {
	// If the request is still here, just proceed as normally
	return resolve(event);
}

// First handle authentication, then authorization
// Each function acts as a middleware, receiving the request handle
// And returning a handle which gets passed to the next function
export const handle: Handle = sequence(authenticationHandle, authorizationHandle);
