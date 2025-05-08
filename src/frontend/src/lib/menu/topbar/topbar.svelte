<script lang="ts">
	import pageTitle from '$lib/page/pageTitle';
</script>

<!-- Topbar Start -->
<header class="app-topbar" id="header">
	<div class="page-container topbar-menu">
		<div class="d-flex align-items-center gap-2">
			<!-- Brand Logo -->
			<a href="index.html" class="logo">
				<span class="logo-light">
					<span class="logo-lg"><img src="assets/images/logo.png" alt="logo" /></span>
					<span class="logo-sm"><img src="assets/images/logo-sm.png" alt="small logo" /></span>
				</span>

				<span class="logo-dark">
					<span class="logo-lg"><img src="assets/images/logo-dark.png" alt="dark logo" /></span>
					<span class="logo-sm"><img src="assets/images/logo-sm.png" alt="small logo" /></span>
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
			<!-- Apps Dropdown -->
			<div class="topbar-item d-none d-sm-flex">
				<div class="dropdown">
					<button
						class="topbar-link dropdown-toggle drop-arrow-none"
						data-bs-toggle="dropdown"
						data-bs-offset="0,18"
						type="button"
						aria-haspopup="false"
						aria-expanded="false"
					>
						<i class="ri-apps-2-add-line fs-22"></i>
					</button>
					<div class="dropdown-menu dropdown-menu-end dropdown-menu-lg p-0">
						<div class="p-2">
							<div class="row g-0">
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/slack.svg" alt="slack" />
										<span>Slack</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/gitlab.svg" alt="Github" />
										<span>Gitlab</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/dribbble.svg" alt="dribbble" />
										<span>Dribbble</span>
									</a>
								</div>
							</div>

							<div class="row g-0">
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/bitbucket.svg" alt="bitbucket" />
										<span>Bitbucket</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/dropbox.svg" alt="dropbox" />
										<span>Dropbox</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/google-cloud.svg" alt="G Suite" />
										<span>G Cloud</span>
									</a>
								</div>
							</div>
							<!-- end row-->

							<div class="row g-0">
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/aws.svg" alt="bitbucket" />
										<span>AWS</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/digital-ocean.svg" alt="dropbox" />
										<span>Server</span>
									</a>
								</div>
								<div class="col">
									<a class="dropdown-icon-item" href="#">
										<img src="assets/images/brands/bootstrap.svg" alt="G Suite" />
										<span>Bootstrap</span>
									</a>
								</div>
							</div>
							<!-- end row-->
						</div>
					</div>
				</div>
			</div>

			<!-- Light/Dark Mode Button -->
			<div class="topbar-item d-none d-sm-flex">
				<button class="topbar-link" id="light-dark-mode" type="button">
					<i class="ri-moon-line light-mode-icon fs-22"></i>
					<i class="ri-sun-line dark-mode-icon fs-22"></i>
				</button>
			</div>

			<!-- User Dropdown -->
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
							src="assets/images/users/avatar-1.jpg"
							width="32"
							class="rounded-circle me-lg-2 d-flex"
							alt="user-image"
						/>
						<span class="d-lg-flex flex-column gap-1 d-none">
							<h5 class="my-0">Christoph Suter</h5>
						</span>
						<i class="ri-arrow-down-s-line d-none d-lg-block align-middle ms-1"></i>
					</a>
					<div class="dropdown-menu dropdown-menu-end">
						<!-- item-->
						<div class="dropdown-header noti-title">
							<h6 class="text-overflow m-0">Welcome !</h6>
						</div>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<i class="ri-account-circle-line me-1 fs-16 align-middle"></i>
							<span class="align-middle">My Account</span>
						</a>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<i class="ri-settings-2-line me-1 fs-16 align-middle"></i>
							<span class="align-middle">Settings</span>
						</a>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<i class="ri-question-line me-1 fs-16 align-middle"></i>
							<span class="align-middle">Support</span>
						</a>

						<div class="dropdown-divider"></div>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item active fw-semibold text-danger">
							<i class="ri-logout-box-line me-1 fs-16 align-middle"></i>
							<span class="align-middle">Sign Out</span>
						</a>
					</div>
				</div>
			</div>

			<!-- Language Dropdown -->
			<div class="topbar-item">
				<div class="dropdown">
					<button
						class="topbar-link"
						data-bs-toggle="dropdown"
						data-bs-offset="0,25"
						type="button"
						aria-haspopup="false"
						aria-expanded="false"
					>
						<img
							src="assets/images/flags/us.svg"
							alt="user-image"
							class="w-100 rounded"
							height="18"
							id="selected-language-image"
						/>
					</button>

					<div class="dropdown-menu dropdown-menu-end">
						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item" data-translator-lang="en">
							<img
								src="assets/images/flags/us.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
								data-translator-image
							/> <span class="align-middle">English</span>
						</a>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<img
								src="assets/images/flags/de.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
							/>
							<span class="align-middle">German</span>
						</a>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<img
								src="assets/images/flags/it.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
							/>
							<span class="align-middle">Italian</span>
						</a>

						<!-- item-->
						<a href="javascript:void(0);" class="dropdown-item">
							<img
								src="assets/images/flags/es.svg"
								alt="user-image"
								class="me-1 rounded"
								height="18"
							/>
							<span class="align-middle">Spanish</span>
						</a>
					</div>
				</div>
			</div>
		</div>
	</div>
</header>
<!-- Topbar End -->
