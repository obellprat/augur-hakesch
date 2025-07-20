<script lang="ts">
	import { _ } from 'svelte-i18n';
</script>

<!-- Footer Start -->
<footer class="footer">
	<div class="page-container">
		<div class="row">
			<div class="col-md-6 text-center text-md-start">
				<script>
					document.write(new Date().getFullYear());
				</script> © AUGUR
			</div>
			<div class="col-md-6">
				<div class="text-md-end footer-links d-none d-md-block">
					<a href="/about">{$_('page.nav.aboutAugur')}</a>
					<a href="/support">{$_('page.nav.support')}</a>
					<a href="/contact">{$_('page.nav.contact')}</a>
				</div>
			</div>
		</div>
	</div>
</footer>
<!-- end Footer -->
