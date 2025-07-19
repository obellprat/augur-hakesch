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
import { locale } from 'svelte-i18n';

async function authorizationHandle({ event, resolve }) {
	// If the request is still here, just proceed as normally
	return resolve(event);
}

async function localizeHandle({ event, resolve }) {
	const lang = event.request.headers.get('accept-language')?.split(',')[0];
	if (lang) {
		locale.set(lang);
	}
	return resolve(event);
}

// First handle authentication, then authorization
// Each function acts as a middleware, receiving the request handle
// And returning a handle which gets passed to the next function
export const handle: Handle = sequence(authenticationHandle, authorizationHandle, localizeHandle);
