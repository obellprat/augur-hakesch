import { browser } from '$app/environment';

/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Module/App: Theme Config Js
 */
declare global {
	interface Window {
		defaultConfig: object;
		config: object;
	}
}
if (browser) {
	const savedConfig = sessionStorage.getItem('__ARCLON_CONFIG__');

	let html = document.getElementsByTagName('html')[0];

	//  Default Config Value
	const defaultConfig = {
		theme: 'dark',

		layout: {
			mode: 'fluid'
		},

		topbar: {
			color: 'light'
		},

		menu: {
			color: 'light'
		},

		// This option for only vertical (left Sidebar) layout
		sidenav: {
			size: 'default'
		}
	};

	html = document.getElementsByTagName('html')[0];

	let config = Object.assign(JSON.parse(JSON.stringify(defaultConfig)), {});

	const layoutColor = html.getAttribute('data-bs-theme');
	config['theme'] = layoutColor !== null ? layoutColor : defaultConfig.theme;

	const layoutSize = html.getAttribute('data-layout-mode');
	config['layout']['mode'] = layoutSize !== null ? layoutSize : defaultConfig.layout.mode;

	const topbarColor = html.getAttribute('data-topbar-color');
	config['topbar']['color'] = topbarColor != null ? topbarColor : defaultConfig.topbar.color;

	const leftbarSize = html.getAttribute('data-sidenav-size');
	config['sidenav']['size'] = leftbarSize !== null ? leftbarSize : defaultConfig.sidenav.size;

	const menuColor = html.getAttribute('data-menu-color');
	config['menu']['color'] = menuColor !== null ? menuColor : defaultConfig.menu.color;

	window.defaultConfig = JSON.parse(JSON.stringify(config));

	if (savedConfig !== null) {
		config = JSON.parse(savedConfig);
	}

	window.config = config;

	if (config) {
		if (window.innerWidth <= 1140) {
			html.setAttribute('data-sidenav-size', 'full');
			html.setAttribute('data-layout-mode', 'default');
		} else {
			html.setAttribute('data-layout-mode', config.layout.mode);
			html.setAttribute('data-sidenav-size', config.sidenav.size);
		}

		html.setAttribute('data-bs-theme', config.theme);
		html.setAttribute('data-menu-color', config.menu.color);
		html.setAttribute('data-topbar-color', config.topbar.color);
	}
}
