import { browser } from '$app/environment';
import { init, register, locale } from 'svelte-i18n';

const defaultLocale = 'en';
const LOCALE_STORAGE_KEY = 'locale';

export const supportedLocales = ['en', 'de', 'fr'] as const;
export type SupportedLocale = (typeof supportedLocales)[number];

export function normalizeLocale(value: string | null | undefined): SupportedLocale {
	const lang = (value || defaultLocale).toLowerCase().split('-')[0];
	if (lang === 'de' || lang === 'fr') return lang;
	return defaultLocale;
}

export function getStoredLocale(): SupportedLocale | null {
	if (!browser) return null;
	const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
	return stored ? normalizeLocale(stored) : null;
}

export function resolveInitialLocale(): SupportedLocale {
	return getStoredLocale() ?? normalizeLocale(browser ? window.navigator.language : defaultLocale);
}

export function setAppLocale(code: string) {
	const normalized = normalizeLocale(code);
	locale.set(normalized);
	if (browser) {
		localStorage.setItem(LOCALE_STORAGE_KEY, normalized);
	}
}

register('en', () => import('./locales/en.json'));
register('de', () => import('./locales/de.json'));
register('fr', () => import('./locales/fr.json'));
init({
	fallbackLocale: defaultLocale,
	initialLocale: resolveInitialLocale()
});
