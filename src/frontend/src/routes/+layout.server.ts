import { env as publicEnv } from '$env/dynamic/public';
import { env as privateEnv } from '$env/dynamic/private';
import type { LayoutServerLoad } from './$types';

const getApiBaseUrl = (): string | undefined =>
	privateEnv.HAKESCH_API_PATH || publicEnv.PUBLIC_HAKESCH_API_PATH;

const buildApiUrl = (path: string): string | null => {
	const baseUrl = getApiBaseUrl();
	if (!baseUrl) {
		console.error(
			'Layout API base URL is not configured. Set HAKESCH_API_PATH or PUBLIC_HAKESCH_API_PATH.'
		);
		return null;
	}

	try {
		const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
		return new URL(path, normalizedBase).toString();
	} catch (error) {
		console.error(`Invalid Layout API base URL "${baseUrl}": ${error}`);
		return null;
	}
};

export const load: LayoutServerLoad = async (event) => {
	const session = await event.locals.auth();
	const sessionWithToken = session as any;
	const unreadImportantNewsUrl = buildApiUrl('/news/important/unread');
	const versionUrl = buildApiUrl('/version/');
	let importantNews: {
		id: number;
		titleDe: string;
		titleEn: string;
		titleFr: string;
		contentDe: string;
		contentEn: string;
		contentFr: string;
	} | null = null;

	if (sessionWithToken?.access_token && unreadImportantNewsUrl) {
		try {
			const newsResponse = await fetch(unreadImportantNewsUrl, {
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

	if (!versionUrl) {
		return {
			apiversion: 'undefined',
			version: '0.3.0.dev1',
			session,
			importantNews
		};
	}

	try {
		const response = await fetch(versionUrl, {
			method: 'GET',
			signal: AbortSignal.timeout(200)
		});

		const versionObject = await response.json();

		return {
			apiversion: versionObject.version, // This will include the version from the API response
			version: '1.3.0', // This is dynamically set in the build process
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
