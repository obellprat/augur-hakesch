export const CLIMAQVA_URL = 'https://www.climaqva.ch';
export const WSL_URL = 'https://wsl.ch';

/**
 * Cutover date for migrating the Discharge ("Abfluss") section to ClimaQva:
 * 1 December 2026, 00:00:00 Europe/Zurich (CET, UTC+1).
 */
export const DISCHARGE_MIGRATION_DATE_ISO = '2026-12-01T00:00:00+01:00';
export const DISCHARGE_MIGRATION_TIMESTAMP = Date.parse(DISCHARGE_MIGRATION_DATE_ISO);

/**
 * Resolves the effective migration timestamp in milliseconds since Unix epoch.
 * Accepts an optional ISO-8601 date string override (useful for testing/staging).
 */
export function getDischargeMigrationTimestamp(overrideIso?: string): number {
	if (overrideIso) {
		const parsed = Date.parse(overrideIso);
		if (!Number.isNaN(parsed)) {
			return parsed;
		}
	}
	return DISCHARGE_MIGRATION_TIMESTAMP;
}

/**
 * Returns true once the Discharge ("Abfluss") section has moved to ClimaQva
 * (from 1 December 2026 00:00 CET onwards).
 */
export function isDischargeMigrated(now: Date = new Date(), overrideIso?: string): boolean {
	return now.getTime() >= getDischargeMigrationTimestamp(overrideIso);
}
