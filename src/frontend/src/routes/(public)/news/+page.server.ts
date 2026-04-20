import { fail } from '@sveltejs/kit';
import { env as publicEnv } from '$env/dynamic/public';
import { env as privateEnv } from '$env/dynamic/private';
import type { Actions, PageServerLoad } from './$types';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { marked } from 'marked';

type NewsItem = {
	id: number;
	titleDe: string;
	titleEn: string;
	titleFr: string;
	contentDe: string;
	contentEn: string;
	contentFr: string;
	isImportant: boolean;
	isRead: boolean;
	createdAt: string;
};

const getApiBaseUrl = (): string | undefined =>
	privateEnv.HAKESCH_API_PATH || publicEnv.PUBLIC_HAKESCH_API_PATH;

const buildApiUrl = (path: string): string | null => {
	const baseUrl = getApiBaseUrl();
	if (!baseUrl) {
		console.error(
			'News API base URL is not configured. Set HAKESCH_API_PATH or PUBLIC_HAKESCH_API_PATH.'
		);
		return null;
	}

	try {
		const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
		return new URL(path, normalizedBase).toString();
	} catch (error) {
		console.error(`Invalid News API base URL "${baseUrl}": ${error}`);
		return null;
	}
};

export const load: PageServerLoad = async ({ locals }) => {
	const session = await locals.auth();
	const accessToken = (session as any)?.access_token;
	let changelogHtml = '';
	const newsUrl = buildApiUrl('/news/');

	try {
		const changelogMarkdown = await readFile(join(process.cwd(), 'CHANGELOG.md'), 'utf8');
		changelogHtml = await marked.parse(changelogMarkdown);
	} catch (error) {
		console.error(`Error while loading changelog: ${error}`);
	}

	if (!newsUrl) {
		return {
			session,
			news: [] as NewsItem[],
			changelogHtml
		};
	}

	try {
		const headers: Record<string, string> = {};
		if (accessToken) {
			headers.Authorization = 'Bearer ' + accessToken;
		}

		const response = await fetch(newsUrl, {
			method: 'GET',
			headers,
			signal: AbortSignal.timeout(2000)
		});

		if (!response.ok) {
			return {
				session,
				news: [] as NewsItem[],
				changelogHtml
			};
		}

		const news = (await response.json()) as NewsItem[];
		return {
			session,
			news,
			changelogHtml
		};
	} catch (error) {
		console.error(`Error while loading news page: ${error}`);
		return {
			session,
			news: [] as NewsItem[],
			changelogHtml
		};
	}
};

export const actions = {
	markRead: async ({ request, locals }) => {
		const session = await locals.auth();
		const accessToken = (session as any)?.access_token;
		if (!accessToken) {
			return fail(401, {
				success: false
			});
		}

		const formData = await request.formData();
		const newsId = Number(formData.get('newsId'));
		if (!newsId) {
			return fail(400, {
				success: false
			});
		}

		const markReadUrl = buildApiUrl(`/news/${newsId}/read`);
		if (!markReadUrl) {
			return fail(500, {
				success: false
			});
		}

		try {
			const response = await fetch(markReadUrl, {
				method: 'POST',
				headers: {
					Authorization: 'Bearer ' + accessToken
				},
				signal: AbortSignal.timeout(2000)
			});

			if (!response.ok) {
				return fail(response.status, {
					success: false
				});
			}
		} catch (error) {
			console.error(`Error while marking news ${newsId} as read: ${error}`);
			return fail(500, {
				success: false
			});
		}

		return {
			success: true
		};
	}
} satisfies Actions;
