<script lang="ts">
	import { page } from '$app/state';
	import { redirect } from '@sveltejs/kit';
	import { browser } from '$app/environment';
	import { base } from '$app/paths';

	import { signIn } from '@auth/sveltekit/client';
	import { _ } from 'svelte-i18n';

	let redirect_url: string | null = null;
	if (browser) {
		const urlParams = new URLSearchParams(window.location.search);
		redirect_url = urlParams.get('redirect_url');
	}

	function login() {
		signIn('keycloak', {
			redirectTo: redirect_url ? `${decodeURIComponent(redirect_url)}` : `${base}/`
		});
	}

	function register() {
		// Hint the provider to show account creation
		signIn('keycloak', null, { prompt: 'create' });
	}
</script>

<div class="page-container container-fluid d-flex flex-grow-1">
	<div class="container-fluid">
		<div class="row">
			<div class="col-12">
				<div class="card">
					<div class="card-body">
						<h1 class="card-title">{$_('page.login.title')}</h1>

						<h4 class="mt-4">{$_('page.login.why_heading')}</h4>
						<p class="card-text">{$_('page.login.why_p1')}</p>
						<p class="card-text">{$_('page.login.why_p2')}</p>

						<h4 class="mt-4">{$_('page.login.free_heading')}</h4>
						<p class="card-text">{$_('page.login.free_p1')}</p>
						<p class="text-muted small">{$_('page.login.privacy_note')}</p>

						<div class="d-flex gap-2 mt-3">
							<button class="btn btn-primary" id="loginBtn" type="button" onclick={login}>
								{$_('page.login.btn_login')}
							</button>
							<button class="btn btn-outline-primary" type="button" onclick={register}>
								{$_('page.login.btn_register')}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
