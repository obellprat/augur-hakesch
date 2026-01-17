import { json } from '@sveltejs/kit';
import Database from 'better-sqlite3';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

export async function GET({ url }) {
	const lat = Number(url.searchParams.get('lat') ?? '0');
	const lng = Number(url.searchParams.get('lng') ?? '0');
	const dbResult = await selectLocation(lat, lng);
	// const parsedResult = JSON.parse(dbResult.data);
	console.log(dbResult);

	return json(dbResult);
}

/**
 * Select location entry from local database
 * @param  {number} lat latitude of location
 * @param  {number} lng longitude of location
 */
async function selectLocation(lat: number, lng: number) {
	try {
		// Construct path to SQLite database
		// Path is relative to the project root: src/frontend/static/assets/precip_db/augur.sqlite
		// Try multiple possible paths to handle different execution contexts
		const possiblePaths = [
			join(process.cwd(), 'src/frontend/static/assets/precip_db/augur.sqlite'), // From project root
			join(process.cwd(), 'static/assets/precip_db/augur.sqlite'), // If cwd is src/frontend
			join(dirname(fileURLToPath(import.meta.url)), '../../../../static/assets/precip_db/augur.sqlite') // Relative to this file
		];

		let dbPath: string | null = null;
		for (const path of possiblePaths) {
			if (existsSync(path)) {
				dbPath = path;
				break;
			}
		}

		if (!dbPath) {
			throw new Error(
				`Database file not found. Tried paths: ${possiblePaths.join(', ')}. Current working directory: ${process.cwd()}`
			);
		}

		const db = new Database(dbPath, { readonly: true });

		// Find closest latitude and longitude
		const closestLat = db
			.prepare('SELECT lat FROM latitude ORDER BY ABS(lat - ?) LIMIT 1')
			.get(lat) as { lat: number } | undefined;

		const closestLng = db
			.prepare('SELECT lon FROM longitude ORDER BY ABS(lon - ?) LIMIT 1')
			.get(lng) as { lon: number } | undefined;

		if (!closestLat || !closestLng) {
			db.close();
			throw new Error('Could not find closest location in database');
		}

		// Query precipitation data for the closest location
		const result = db
			.prepare('SELECT * FROM data WHERE lat = ? AND lon = ?')
			.get(closestLat.lat, closestLng.lon) as Record<string, unknown>;

		db.close();

		if (!result) {
			throw new Error('No precipitation data found for the closest location');
		}

		const years: number[] = [2030, 2050, 2090];
		const periods: number[] = [10, 20, 30, 50, 100];

		const data = {
			period: years.reduce((acc: Record<number, unknown>, year) => {
				acc[year] = {
					years: periods.reduce((pAcc: Record<number, unknown>, period) => {
						pAcc[period] = {
							present: result[`year${period}`],
							climate_change: result[`year${period}_cchange${year}`]
						};
						return pAcc;
					}, {})
				};
				return acc;
			}, {})
		};

		return data;
	} catch (error) {
		console.error('Error selecting location from database:', error);
		throw error;
	}
}
