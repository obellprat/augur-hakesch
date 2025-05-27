import { SvelteKitAuth } from '@auth/sveltekit';
import keycloak from '@auth/sveltekit/providers/keycloak';
import { prisma } from '$lib/prisma';

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
		debug: true,
		callbacks: {
			async jwt({ token, account }) {
				if (account) {
					return { ...token, accessToken: account.access_token };
				}
				return token;
			},
			async session({ session, token }) {
				const users = await prisma.user.findMany({});
				let myuser = users.find((t) => t.email == session.user.email);
				if (myuser) {
					if (myuser.name != session.user.name) {
						myuser = await prisma.user.update({
							where: { id: myuser.id },
							data: { name: session.user.name }
						});
					}
				} else {
					myuser = await prisma.user.create({
						data: {
							email: session.user.email,
							name: session.user.name
						}
					});
				}
				session.myuser = myuser;
				session.accessToken = token.accessToken;
				return session;
			}
		}
	};
	return authOptions;
});
