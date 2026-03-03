import { fail } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
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

export const load: PageServerLoad = async ({ locals }) => {
	const session = await locals.auth();
	const accessToken = (session as any)?.access_token;
	let changelogHtml = '';

	try {
		const changelogMarkdown = await readFile(join(process.cwd(), 'CHANGELOG.md'), 'utf8');
		changelogHtml = await marked.parse(changelogMarkdown);
	} catch (error) {
		console.error(`Error while loading changelog: ${error}`);
	}

	try {
		const headers: Record<string, string> = {};
		if (accessToken) {
			headers.Authorization = 'Bearer ' + accessToken;
		}

		const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/news/', {
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

		try {
			const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/news/${newsId}/read`, {
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
