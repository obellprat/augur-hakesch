import { env as privateEnv } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import { redirect } from '@sveltejs/kit';
import { CLIMAQVA_URL, isDischargeMigrated } from '$lib/dischargeMigration';

/**
 * Server-side migration check supporting an optional DISCHARGE_MIGRATION_DATE
 * (or PUBLIC_DISCHARGE_MIGRATION_DATE) ISO-8601 override for testing/staging.
 */
export function isDischargeMigratedServer(now: Date = new Date()): boolean {
	const overrideIso =
		privateEnv.DISCHARGE_MIGRATION_DATE || publicEnv.PUBLIC_DISCHARGE_MIGRATION_DATE;
	return isDischargeMigrated(now, overrideIso);
}

/**
 * Redirects requests for the Discharge ("Abfluss") section to ClimaQva
 * once the migration cutover date has been reached.
 */
export function redirectIfDischargeMigrated(): void {
	if (isDischargeMigratedServer()) {
		redirect(302, CLIMAQVA_URL);
	}
}
