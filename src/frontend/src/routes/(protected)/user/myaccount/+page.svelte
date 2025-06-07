<script lang="ts">
	import { page } from '$app/state';
	import pageTitle from '$lib/page/pageTitle';

	$pageTitle = 'My Account';
</script>

<svelte:head>
	<title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
	<div class="row row-cols-xxl-1 row-cols-md-1 row-cols-1">
		<div class="col">
			<div class="card d-block">
				<div class="card-body">
					<div class="card-header border-bottom border-dashed d-flex align-items-center">
						<h4 class="header-title">My Account</h4>
					</div>
					<div class="card-body">
						<form class="form-horizontal">
							<div class="row mb-3">
								<label for="inputEmail3" class="col-3 col-form-label">Name</label>
								<div class="col-9">
									<input
										type="email"
										class="form-control"
										id="inputEmail3"
										value={page.data.session?.user?.name}
										disabled
									/>
								</div>
							</div>
							<div class="row mb-3">
								<label for="inputEmail3" class="col-3 col-form-label">Email</label>
								<div class="col-9">
									<input
										type="email"
										class="form-control"
										id="inputEmail3"
										value={page.data.session?.user?.email}
										disabled
									/>
								</div>
							</div>
							<div class="row mb-3">
								<label for="inputPassword3" class="col-3 col-form-label">API Token</label>
								<div class="col-9">
									<textarea class="form-control" style="height: 300px;"
										>{page.data.session?.accessToken}</textarea
									>
								</div>
							</div>
						</form>
					</div>
				</div>
				<!-- end card-body-->
			</div>
			<!-- end card-->
		</div>
		<!-- end col -->
	</div>
	<!-- end row -->
</div>
<!-- container -->
