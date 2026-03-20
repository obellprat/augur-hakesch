<script lang="ts">
	import { _ } from 'svelte-i18n';
	import pageTitle from '$lib/page/pageTitle';
	import { base } from '$app/paths';

	$pageTitle = $_('page.support.boardTitle');

	let { data, form } = $props();
	const statuses = ['open', 'in_progress', 'resolved', 'closed'];

const selectedTicket = $derived(
	data.tickets.find((ticket: any) => ticket.id === data.selectedTicketId) ?? data.tickets[0]
);
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row">
		<div class="col-lg-4">
			<div class="card mb-3">
				<div class="card-body">
					<h4 class="card-title">{$_('page.support.heading')}</h4>
					<p class="text-muted">{$_('page.support.description')}</p>

					{#if form?.createTicketSuccess}
						<div class="alert alert-success" role="alert">
							{$_('page.support.success', { values: { id: form.createTicketId } })}
						</div>
					{:else if form?.createTicketError}
						<div class="alert alert-danger" role="alert">
							{$_('page.support.error')}
						</div>
					{/if}

					<form method="POST" action="?/createTicket">
						<div class="mb-3">
							<label class="form-label" for="requesterName">{$_('page.support.requesterName')}</label>
							<input
								class="form-control"
								id="requesterName"
								name="requesterName"
								type="text"
								value={form?.createTicketValues?.requesterName ?? ''}
								maxlength="120"
							/>
						</div>
						<div class="mb-3">
							<label class="form-label" for="requesterEmail">{$_('page.support.requesterEmail')}</label>
							<input
								class="form-control"
								id="requesterEmail"
								name="requesterEmail"
								type="email"
								value={form?.createTicketValues?.requesterEmail ?? ''}
								required
							/>
						</div>
						<div class="mb-3">
							<label class="form-label" for="subject">{$_('page.support.subject')}</label>
							<input
								class="form-control"
								id="subject"
								name="subject"
								type="text"
								value={form?.createTicketValues?.subject ?? ''}
								required
								minlength="3"
								maxlength="200"
							/>
						</div>
						<div class="mb-3">
							<label class="form-label" for="message">{$_('page.support.message')}</label>
							<textarea
								class="form-control"
								id="message"
								name="message"
								rows="6"
								required
								minlength="10"
								maxlength="5000"
							>{form?.createTicketValues?.message ?? ''}</textarea>
						</div>
						<button type="submit" class="btn btn-primary">{$_('page.support.submit')}</button>
					</form>
				</div>
			</div>

			<div class="card">
				<div class="card-body">
					<h4 class="card-title">{$_('page.support.boardTitle')}</h4>
					{#if data.forbidden}
						<div class="alert alert-warning mb-0" role="alert">
							{$_('page.support.forbidden')}
						</div>
					{:else if data.tickets.length === 0}
						<p class="text-muted mb-0">{$_('page.support.noTickets')}</p>
					{:else}
						<div class="list-group">
							{#each data.tickets as ticket}
								<a
									href={`${base}/support/tickets?ticket=${ticket.id}`}
									class={`list-group-item list-group-item-action ${selectedTicket?.id === ticket.id ? 'active' : ''}`}
								>
									<div class="fw-semibold">#{ticket.id} - {ticket.subject}</div>
									<div class="small text-muted">{ticket.requesterEmail}</div>
									<div class="small">{ticket.status}</div>
								</a>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
		<div class="col-lg-8">
			{#if selectedTicket}
				<div class="card mb-3">
					<div class="card-body">
						<h4 class="card-title">#{selectedTicket.id} - {selectedTicket.subject}</h4>
						<p class="mb-1"><strong>{$_('page.support.requesterEmail')}:</strong> {selectedTicket.requesterEmail}</p>
						<p class="mb-3"><strong>{$_('page.support.status')}:</strong> {selectedTicket.status}</p>
						<p>{selectedTicket.message}</p>

						<form method="POST" action="?/updateStatus" class="d-flex gap-2 align-items-end">
							<input type="hidden" name="ticketId" value={selectedTicket.id} />
							<div>
								<label class="form-label" for="status">{$_('page.support.changeStatus')}</label>
								<select class="form-select" id="status" name="status">
									{#each statuses as status}
										<option selected={status === selectedTicket.status} value={status}>{status}</option>
									{/each}
								</select>
							</div>
							<button type="submit" class="btn btn-outline-primary">{$_('page.general.save')}</button>
						</form>
					</div>
				</div>

				<div class="card mb-3">
					<div class="card-body">
						<h5 class="card-title">{$_('page.support.thread')}</h5>
						{#if selectedTicket.comments?.length === 0}
							<p class="text-muted mb-0">{$_('page.support.noComments')}</p>
						{:else}
							{#each selectedTicket.comments as comment}
								<div class="border rounded p-2 mb-2">
									<div class="small text-muted mb-1">
										{comment.author?.name || comment.author?.email || 'Unknown'} - {comment.createdAt}
									</div>
									<div>{comment.body}</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>

				<div class="card">
					<div class="card-body">
						<h5 class="card-title">{$_('page.support.reply')}</h5>
						<form method="POST" action="?/addComment">
							<input type="hidden" name="ticketId" value={selectedTicket.id} />
							<input type="hidden" name="isInternal" value="true" />
							<div class="mb-3">
								<label class="form-label" for="body">{$_('page.support.message')}</label>
								<textarea class="form-control" id="body" name="body" rows="4" required minlength="2"></textarea>
							</div>
							<button type="submit" class="btn btn-primary">{$_('page.support.sendReply')}</button>
						</form>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
