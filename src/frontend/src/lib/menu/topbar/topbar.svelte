<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';

	import { locale, locales } from 'svelte-i18n'
	import { _ } from 'svelte-i18n'
	import { page } from '$app/state';

	import { signIn, signOut } from '@auth/sveltekit/client';

	import { base } from '$app/paths';
	function changeLanguage(code: string) {
		locale.set(code);
	}

</script>

<!-- Topbar Start -->
<header class="app-topbar" id="header">
	<div class="page-container topbar-menu">
		<div class="d-flex align-items-center gap-2">
			<!-- Brand Logo -->
			<a href="index.html" class="logo">
				<span class="logo-light">
					<span class="logo-lg"><img src="{base}/assets/images/logo.png" alt="logo" /></span>
					<span class="logo-sm"
						><img src="{base}/assets/images/logo-sm.png" alt="small logo" /></span
					>
				</span>

				<span class="logo-dark">
					<span class="logo-lg"
						><img src="{base}/assets/images/logo-dark.png" alt="dark logo" /></span
					>
					<span class="logo-sm"
						><img src="{base}/assets/images/logo-sm.png" alt="small logo" /></span
					>
				</span>
			</a>

			<!-- Sidebar Menu Toggle Button -->
			<button class="sidenav-toggle-button">
				<i class="ri-menu-5-line fs-24"></i>
			</button>

			<!-- Horizontal Menu Toggle Button -->
			<button
				class="topnav-toggle-button px-2"
				data-bs-toggle="collapse"
				data-bs-target="#topnav-menu-content"
			>
				<i class="ri-menu-5-line fs-24"></i>
			</button>

			<!-- Topbar Page Title -->
			<div class="topbar-item d-none d-md-flex px-2">
				<div>
					<h4 class="page-title fs-20 fw-semibold mb-0">{$pageTitle}</h4>
				</div>
			</div>
		</div>

		<div class="d-flex align-items-center gap-2">
			<!-- Light/Dark Mode Button -->
			<div class="topbar-item d-none d-sm-flex">
				<button class="topbar-link" id="light-dark-mode" type="button">
					<i class="ri-moon-line light-mode-icon fs-22"></i>
					<i class="ri-sun-line dark-mode-icon fs-22"></i>
				</button>
			</div>
			<!-- User Dropdown -->
			{#if page.data.session}
				<div class="topbar-item nav-user">
					<div class="dropdown">
						<a
							class="topbar-link dropdown-toggle drop-arrow-none px-2"
							data-bs-toggle="dropdown"
							data-bs-offset="0,19"
							type="button"
							aria-haspopup="false"
							aria-expanded="false"
						>
							<img
								src="{base}/assets/images/users/avatar-1.jpg"
								width="32"
								class="rounded-circle me-lg-2 d-flex"
								alt="user-image"
							/>
							<span class="d-lg-flex flex-column gap-1 d-none">
								<h5 class="my-0">{page.data.session.user?.name}</h5>
							</span>
							<i class="ri-arrow-down-s-line d-none d-lg-block align-middle ms-1"></i>
						</a>
						<div class="dropdown-menu dropdown-menu-end">
							<!-- item-->
							<div class="dropdown-header noti-title">
								<h6 class="text-overflow m-0">{$_('page.nav.welcome')}</h6>
							</div>

							<!-- item-->
							<a
								href="{base}/user/myaccount"
								data-sveltekit-preload-data="off"
								class="dropdown-item"
							>
								<i class="ri-account-circle-line me-1 fs-16 align-middle"></i>
								<span class="align-middle">{$_('page.nav.my-account')}</span>
							</a>

							<!-- item-->
							<a href="javascript:void(0);" class="dropdown-item">
								<i class="ri-settings-2-line me-1 fs-16 align-middle"></i>
								<span class="align-middle">{$_('page.nav.settings')}</span>
							</a>

							<!-- item-->
							<a href="javascript:void(0);" class="dropdown-item">
								<i class="ri-question-line me-1 fs-16 align-middle"></i>
								<span class="align-middle">{$_('page.nav.support')}</span>
							</a>

							<div class="dropdown-divider"></div>

							<!-- item-->
							<a
								href="javascript:void(0);"
								class="dropdown-item active fw-semibold text-danger"
								onclick={() => signOut()}
							>
								<i class="ri-logout-box-line me-1 fs-16 align-middle"></i>
								<span class="align-middle">{$_('page.nav.sign-out')}</span>
							</a>
						</div>
					</div>
				</div>
			{:else}
				<div class="" id="loginbuttonbar">
					<button
						class="topbar-link btn btn-primary bg-gradient rounded-pill"
						id="loginBtn"
						type="button"
						onclick={() => signIn('keycloak')}>{$_('page.nav.login')}</button
					>
				</div>
				<div class="" id="loginbuttonbar">
					<button
						class="topbar-link btn btn-outline-primary rounded-pill"
						id="loginBtn"
						type="button"
						onclick={() => signIn('keycloak', null, { prompt: 'create' })}>{$_('page.nav.signup')}</button
					>
				</div>
			{/if}
			<!-- Language Dropdown -->
			<div class="topbar-item" style="padding-right:10px;">
				<div class="dropdown">
					<span
						class="topbar-link light-mode-icon fs-18"
						data-bs-toggle="dropdown"
						data-bs-offset="0,25"
						aria-haspopup="false"
						aria-expanded="false"
					>
						{$locale?.toLocaleLowerCase() === 'de-de' || $locale?.toLocaleLowerCase() === 'de' ? 'DE' : 'EN'}
					</span>

					<div class="dropdown-menu dropdown-menu-end">
						<!-- item-->
						<button onclick={() => changeLanguage('en')} class="dropdown-item" data-translator-lang="en">
							<img
								src="{base}/assets/images/flags/gb.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
								data-translator-image
							/> <span class="align-middle">{$_('page.nav.english')}</span>
						</button>

						<!-- item-->
						<button onclick={() => changeLanguage('de')} class="dropdown-item">
							<img
								src="{base}/assets/images/flags/de.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
							/>
							<span class="align-middle">{$_('page.nav.german')}</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</header>
<!-- Topbar End -->
