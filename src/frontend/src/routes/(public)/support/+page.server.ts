import { env } from '$env/dynamic/public';
import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	const session = await locals.auth();
	return { session };
};

export const actions = {
	createTicket: async ({ request, locals }) => {
		const session = await locals.auth();
		const accessToken = (session as any)?.access_token;
		const formData = await request.formData();

		const subject = String(formData.get('subject') ?? '').trim();
		const message = String(formData.get('message') ?? '').trim();
		const requesterName = String(formData.get('requesterName') ?? '').trim();
		const requesterEmail = String(formData.get('requesterEmail') ?? '').trim();

		if (subject.length < 3 || message.length < 10 || requesterEmail.length < 3) {
			return fail(400, {
				success: false,
				error: 'validation',
				values: { subject, message, requesterName, requesterEmail }
			});
		}

		try {
			const headers: Record<string, string> = {
				'Content-Type': 'application/json'
			};
			if (accessToken) {
				headers.Authorization = 'Bearer ' + accessToken;
			}

			const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/support/tickets', {
				method: 'POST',
				headers,
				body: JSON.stringify({
					subject,
					message,
					requesterName,
					requesterEmail
				}),
				signal: AbortSignal.timeout(4000)
			});

			if (!response.ok) {
				return fail(response.status, {
					success: false,
					error: 'api',
					values: { subject, message, requesterName, requesterEmail }
				});
			}

			const ticket = await response.json();
			return {
				success: true,
				ticketId: ticket.id
			};
		} catch (error) {
			console.error(`Error creating support ticket: ${error}`);
			return fail(500, {
				success: false,
				error: 'network',
				values: { subject, message, requesterName, requesterEmail }
			});
		}
	}
} satisfies Actions;
