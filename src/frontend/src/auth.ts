import { SvelteKitAuth } from '@auth/sveltekit';
import keycloak from '@auth/sveltekit/providers/keycloak';

import {
	AUTH_KEYCLOAK_ID,
	AUTH_KEYCLOAK_ISSUER,
	AUTH_KEYCLOAK_SECRET,
	AUTH_SECRET
} from '$env/static/private';

export const { handle, signIn, signOut } = SvelteKitAuth(async () => {
	const authOptions = {
		providers: [
			keycloak({
				clientId: AUTH_KEYCLOAK_ID,
				clientSecret: AUTH_KEYCLOAK_SECRET,
				issuer: AUTH_KEYCLOAK_ISSUER
			})
		],
		secret: AUTH_SECRET,
		trustHost: true,
		debug: true
	};
	return authOptions;
});
