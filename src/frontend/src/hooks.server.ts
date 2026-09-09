/*export async function handle({ event, resolve }) {
	if (event.url.href.includes('#')) {
		console.log('path hat isozones');
	} else {
		return await resolve(event);
	}
}*/

import { redirect, type Handle } from '@sveltejs/kit';
import { handle as authenticationHandle } from './auth';
import { sequence } from '@sveltejs/kit/hooks';
import { locale } from 'svelte-i18n';
import { base } from '$app/paths';

const authRelativeAssetPrefix = `${base}/auth/_app/`;
const appAssetPrefix = `${base}/_app/`;

/** Browser resolved `_app` relative to `/abfluss/auth/...`; send those requests to the real assets. */
const fixAuthRelativeAssets: Handle = async ({ event, resolve }) => {
	if (event.url.pathname.startsWith(authRelativeAssetPrefix)) {
		throw redirect(
			301,
			appAssetPrefix + event.url.pathname.slice(authRelativeAssetPrefix.length) + event.url.search
		);
	}
	return resolve(event);
};

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
export const handle: Handle = sequence(
	fixAuthRelativeAssets,
	authenticationHandle,
	authorizationHandle,
	localizeHandle
);
