import { env } from '$env/dynamic/public';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type SupportComment = {
	id: number;
	body: string;
	isInternal: boolean;
	createdAt: string;
	author: {
		email?: string;
		name?: string;
	};
};

type SupportTicket = {
	id: number;
	subject: string;
	message: string;
	status: string;
	priority: string;
	requesterEmail: string;
	requesterName?: string;
	createdAt: string;
	comments: SupportComment[];
};

type FetchResult = { tickets: SupportTicket[]; forbidden?: boolean };

async function fetchTickets(accessToken: string): Promise<FetchResult> {
	const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + '/support/tickets', {
		method: 'GET',
		headers: {
			Authorization: 'Bearer ' + accessToken
		},
		signal: AbortSignal.timeout(4000)
	});
	if (response.status === 403) {
		return { tickets: [], forbidden: true };
	}
	if (!response.ok) {
		return { tickets: [] };
	}
	const tickets = (await response.json()) as SupportTicket[];
	return { tickets };
}

export const load: PageServerLoad = async ({ locals, url }) => {
	const session = await locals.auth();
	const accessToken = (session as any)?.access_token;
	if (!accessToken) {
		throw redirect(303, `/login?redirect_url=${encodeURIComponent(url.href)}`);
	}

	const result = await fetchTickets(accessToken);
	const selectedTicketId = Number(
		url.searchParams.get('ticket') ?? result.tickets[0]?.id ?? 0
	);
	return {
		session,
		tickets: result.tickets,
		forbidden: result.forbidden,
		selectedTicketId
	};
};

export const actions = {
	addComment: async ({ request, locals }) => {
		const session = await locals.auth();
		const accessToken = (session as any)?.access_token;
		if (!accessToken) {
			return fail(401, { success: false });
		}

		const formData = await request.formData();
		const ticketId = Number(formData.get('ticketId'));
		const body = String(formData.get('body') ?? '').trim();
		const isInternal = String(formData.get('isInternal') ?? 'true') === 'true';
		if (!ticketId || body.length < 2) {
			return fail(400, { success: false });
		}

		const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/support/tickets/${ticketId}/comments`, {
			method: 'POST',
			headers: {
				Authorization: 'Bearer ' + accessToken,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ body, isInternal }),
			signal: AbortSignal.timeout(4000)
		});
		if (!response.ok) {
			return fail(response.status, { success: false });
		}
		return { success: true };
	},
	updateStatus: async ({ request, locals }) => {
		const session = await locals.auth();
		const accessToken = (session as any)?.access_token;
		if (!accessToken) {
			return fail(401, { success: false });
		}

		const formData = await request.formData();
		const ticketId = Number(formData.get('ticketId'));
		const status = String(formData.get('status') ?? '').trim();
		if (!ticketId || !status) {
			return fail(400, { success: false });
		}

		const response = await fetch(env.PUBLIC_HAKESCH_API_PATH + `/support/tickets/${ticketId}`, {
			method: 'PATCH',
			headers: {
				Authorization: 'Bearer ' + accessToken,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ status }),
			signal: AbortSignal.timeout(4000)
		});
		if (!response.ok) {
			return fail(response.status, { success: false });
		}
		return { success: true };
	}
} satisfies Actions;
