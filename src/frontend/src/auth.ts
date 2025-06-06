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
					console.log("jwt");
					console.log(token);
					console.log(account)
					return { ...token,
          access_token: account.access_token,
          expires_at: account.expires_at,
          refresh_token: account.refresh_token, };
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
				session.access_token = token.access_token;
				session.refresh_token = token.refresh_token;
				session.expoires_at = token.expires_at
				
				console.log("token.......");
				console.log(token);
				console.log(".....");
				console.log(session);
				console.log(Date.now())
				if (Date.now() > token.expires_at * 1000) {
					console.log("refresh token");
					const response  = await fetch(`${AUTH_KEYCLOAK_ISSUER}/protocol/openid-connect/token`, {
						method: 'POST',
						headers: {
						'content-type': 'application/x-www-form-urlencoded'
						},
						body: new URLSearchParams({
						grant_type: 'refresh_token',
						refresh_token: token.refresh_token,
						client_id: AUTH_KEYCLOAK_ID,
						client_secret: AUTH_KEYCLOAK_SECRET,
						})
					});
					
					const tokensOrError = await response.json()
			
					if (!response.ok) throw tokensOrError
			
					const newTokens = tokensOrError as {
						access_token: string
						expires_in: number
						refresh_token?: string
					}

					session.access_token = newTokens.access_token;
					session.refresh_token = newTokens.refresh_token;
					session.expoires_at = Math.floor(Date.now() / 1000 + newTokens.expires_in);					
				}
					
				return session;
			}
		}
	};
	return authOptions;
});
