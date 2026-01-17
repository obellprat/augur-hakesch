import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const lat = url.searchParams.get('lat');
	const lng = url.searchParams.get('lng');
	const climatePeriod = url.searchParams.get('climate') || '2030';

	return {
		initialLocation: lat && lng ? { lat: parseFloat(lat), lng: parseFloat(lng) } : null,
		initialClimatePeriod: ['2030', '2050', '2090'].includes(climatePeriod) ? climatePeriod : '2030'
	};
};
