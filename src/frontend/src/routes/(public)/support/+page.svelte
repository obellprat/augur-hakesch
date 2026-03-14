<script lang="ts">
	import { _ } from 'svelte-i18n';
	import pageTitle from '$lib/page/pageTitle';

	$pageTitle = $_('page.support.title');

	let { form } = $props();
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row justify-content-center">
		<div class="col-lg-8">
			<div class="card">
				<div class="card-body">
					<h2 class="card-title mb-3">{$_('page.support.heading')}</h2>
					<p class="text-muted">{$_('page.support.description')}</p>

					{#if form?.success}
						<div class="alert alert-success" role="alert">
							{$_('page.support.success', { values: { id: form.ticketId } })}
						</div>
					{:else if form?.error}
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
								value={form?.values?.requesterName ?? ''}
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
								value={form?.values?.requesterEmail ?? ''}
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
								value={form?.values?.subject ?? ''}
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
							>{form?.values?.message ?? ''}</textarea>
						</div>
						<button type="submit" class="btn btn-primary">{$_('page.support.submit')}</button>
					</form>
				</div>
			</div>
		</div>
	</div>
</div>
