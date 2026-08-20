import { SvelteKitAuth, type SvelteKitAuthConfig } from '@auth/sveltekit';
import keycloak from '@auth/sveltekit/providers/keycloak';
import { prisma } from '$lib/prisma';

import { env } from '$env/dynamic/private';

export const { handle, signIn, signOut } = SvelteKitAuth(async () => {
	const authOptions = {
		providers: [
			keycloak({
				clientId: env.AUTH_KEYCLOAK_ID,
				clientSecret: env.AUTH_KEYCLOAK_SECRET,
				issuer: env.AUTH_KEYCLOAK_ISSUER
			})
		],
		secret: env.AUTH_SECRET,
		trustHost: true,
		// Behind a TLS-terminating proxy Node sees HTTP, so Auth.js must not prefix
		// cookies with __Secure- (it would then ignore them on the callback).
		// The cookies themselves still need Secure=true because the browser is on HTTPS.
		useSecureCookies: false,
		cookies: {
			sessionToken: {
				name: 'abfluss.session-token',
				options: { httpOnly: true, sameSite: 'lax', path: '/abfluss', secure: true }
			},
			callbackUrl: {
				name: 'abfluss.callback-url',
				options: { httpOnly: true, sameSite: 'lax', path: '/abfluss', secure: true }
			},
			csrfToken: {
				name: 'abfluss.csrf-token',
				options: { httpOnly: true, sameSite: 'lax', path: '/abfluss', secure: true }
			},
			pkceCodeVerifier: {
				name: 'abfluss.pkce.code_verifier',
				options: {
					httpOnly: true,
					sameSite: 'lax',
					path: '/abfluss',
					secure: true,
					maxAge: 60 * 15
				}
			},
			state: {
				name: 'abfluss.state',
				options: {
					httpOnly: true,
					sameSite: 'lax',
					path: '/abfluss',
					secure: true,
					maxAge: 60 * 15
				}
			},
			nonce: {
				name: 'abfluss.nonce',
				options: {
					httpOnly: true,
					sameSite: 'lax',
					path: '/abfluss',
					secure: true,
					maxAge: 60 * 15
				}
			}
		},
		debug: env.AUTH_DEBUG === 'true',
		callbacks: {
			async jwt({ token, account }: { token: any; account?: any }) {
				if (account) {
					return {
						...token,
						access_token: account.access_token,
						expires_at: account.expires_at,
						refresh_token: account.refresh_token
					};
				}
				return token;
			},
			async session({ session, token }: { session: any; token: any }) {
				const users = await prisma.user.findMany({});
				let myuser = users.find((t: { email?: string | null }) => t.email == session.user.email);
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
				session.expires_at = token.expires_at;

				if (Date.now() > token.expires_at * 1000) {
					const response = await fetch(
						`${env.AUTH_KEYCLOAK_ISSUER}/protocol/openid-connect/token`,
						{
							method: 'POST',
							headers: {
								'content-type': 'application/x-www-form-urlencoded'
							},
							body: new URLSearchParams({
								grant_type: 'refresh_token',
								refresh_token: token.refresh_token,
								client_id: env.AUTH_KEYCLOAK_ID,
								client_secret: env.AUTH_KEYCLOAK_SECRET
							})
						}
					);

					const tokensOrError = await response.json();

					if (!response.ok) throw tokensOrError;

					const newTokens = tokensOrError as {
						access_token: string;
						expires_in: number;
						refresh_token?: string;
					};

					session.access_token = newTokens.access_token;
					session.refresh_token = newTokens.refresh_token;
					session.expoires_at = Math.floor(Date.now() / 1000 + newTokens.expires_in);
				}

				return session;
			}
		}
	};
	return authOptions as SvelteKitAuthConfig;
});
