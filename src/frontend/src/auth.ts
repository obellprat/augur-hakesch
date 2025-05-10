/*import { SvelteKitAuth } from "@auth/sveltekit"
import Keycloak from "@auth/sveltekit/providers/keycloak"
 
export const { handle, signIn } = SvelteKitAuth({
  providers: [Keycloak({
    clientId:"4459369d-435f-4451-adf6-1328de26631a",
    clientSecret:"6ve4dVJjoDCnW0qxNVXcf4MbdjyQdvKQ",
    issuer:"https:/id.boccadileone.ch/auth/realms/augur"
  })],
}) */


import { SvelteKitAuth } from "@auth/sveltekit"
import keycloak from "@auth/sveltekit/providers/keycloak"
 
import { AUTH_KEYCLOAK_ID, AUTH_KEYCLOAK_ISSUER, AUTH_KEYCLOAK_SECRET, AUTH_SECRET } from '$env/static/private';

export const { handle, signIn, signOut } = SvelteKitAuth(async (event) => {
  const authOptions = {
    providers: [
        keycloak({
            clientId:AUTH_KEYCLOAK_ID,
            clientSecret:AUTH_KEYCLOAK_SECRET,
            issuer:AUTH_KEYCLOAK_ISSUER
          }),
    ],
    secret: AUTH_SECRET,
    trustHost: true,
    debug: true
  }
  return authOptions
})