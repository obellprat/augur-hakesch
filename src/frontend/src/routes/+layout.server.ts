import { env } from '$env/dynamic/public';
import { env as env_priv } from '$env/dynamic/private';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	try {
		const response = await fetch(env_priv.ORIGIN + env.PUBLIC_HAKESCH_API_PATH + '/version/', {
			method: 'GET',
			signal: AbortSignal.timeout(200)
		});

		const versionObject = await response.json();

		return {
			apiversion: versionObject.version, // This will include the version from the API response
			version: '0.5.0-dev.1', // This is dynamically set in the build process
			session: await event.locals.auth()
		};
	} catch (error) {
		console.error(`Error in load function for /: ${error}`);
	}

	return {
		apiversion: 'undefined', // Fallback in case of error
		version: '0.3.0.dev1', // This is dynamically set in the build process
		session: await event.locals.auth()
	};
};
