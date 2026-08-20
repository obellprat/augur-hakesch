import { base } from '$app/paths';

function postToAuth(path: string, callbackUrl: string) {
	const form = document.createElement('form');
	form.method = 'POST';
	form.action = `${base}/auth/${path}`;
	form.style.display = 'none';

	const callback = document.createElement('input');
	callback.type = 'hidden';
	callback.name = 'callbackUrl';
	callback.value = callbackUrl;
	form.appendChild(callback);

	document.body.appendChild(form);
	form.submit();
}

/** Full-page POST so Set-Cookie is applied on the 302 to Keycloak. */
export function startKeycloakLogin(redirectTo = `${base}/`, prompt?: string) {
	const qs = prompt ? `?${new URLSearchParams({ prompt })}` : '';
	postToAuth(`signin/keycloak${qs}`, redirectTo);
}

export function startKeycloakLogout(redirectTo = `${base}/`) {
	postToAuth('signout', redirectTo);
}
