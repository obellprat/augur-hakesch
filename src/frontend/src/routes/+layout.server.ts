import { env } from '$env/dynamic/public';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	const session = await event.locals.auth();
	const sessionWithToken = session as any;
	let importantNews: {
		id: number;
		titleDe: string;
		titleEn: string;
		titleFr: string;
		contentDe: string;
		contentEn: string;
		contentFr: string;
	} | null = null;

	if (sessionWithToken?.access_token) {
		try {
			const newsResponse = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/news/important/unread', {
				method: 'GET',
				headers: {
					Authorization: 'Bearer ' + sessionWithToken.access_token
				},
				signal: AbortSignal.timeout(1000)
			});

			if (newsResponse.ok) {
				importantNews = await newsResponse.json();
			}
		} catch (error) {
			console.error(`Error loading important news: ${error}`);
		}
	}

	try {
		const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/version/', {
			method: 'GET',
			signal: AbortSignal.timeout(200)
		});

		const versionObject = await response.json();

		return {
			apiversion: versionObject.version, // This will include the version from the API response
			version: '1.3.0-rc.1', // This is dynamically set in the build process
			session,
			importantNews
		};
	} catch (error) {
		console.error(`Error in load function for /: ${error}`);
	}

	return {
		apiversion: 'undefined', // Fallback in case of error
		version: '0.3.0.dev1', // This is dynamically set in the build process
		session,
		importantNews
	};
};
