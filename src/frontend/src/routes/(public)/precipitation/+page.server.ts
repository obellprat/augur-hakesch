import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const lat = url.searchParams.get('lat');
	const lng = url.searchParams.get('lng');

	return {
		initialLocation: lat && lng ? { lat: parseFloat(lat), lng: parseFloat(lng) } : null
	};
}; 