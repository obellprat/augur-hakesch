<script lang="ts">
	import { page } from '$app/state';
	import { redirect } from '@sveltejs/kit';
	import { browser } from '$app/environment';
	
	import { signIn, signOut } from "@auth/sveltekit/client"
  import { SignIn } from "@auth/sveltekit/components"

	let redirect_url: string | null;
	if (browser) {
		const urlParams = new URLSearchParams(window.location.search);
		redirect_url = urlParams.get('redirect_url');
	}
</script>

<div class="page-container container-fluid d-flex flex-grow-1">
	<div class="container-fluid">
		<div class="row">
			<div class="col-12">
				<div class="card">
					<div class="card-body">
						<h3>Please login for using this tool</h3>
						<button
							class="btn btn-primary bg-gradient rounded-pill"
							id="loginBtn"
							type="button"
							onclick={() => signIn("keycloak",{redirectTo: redirect_url
								? `${decodeURIComponent(redirect_url)}`
								: ``})}>Login</button
						>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
