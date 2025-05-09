export async function handle({ event, resolve }) {
	if (event.url.href.includes('#')) {
		console.log('path hat isozones');
	} else {
		return await resolve(event);
	}
}
