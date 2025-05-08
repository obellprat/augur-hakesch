<script lang="ts">
    import '../scss/app.scss';
    import '../scss/icons.scss';
        
    import bootstrapSrc from '../../node_modules/bootstrap/dist/js/bootstrap.bundle?url';
    import jquerySrc from '../../node_modules/jquery/dist/jquery?url';

    import {Footer, Menu} from '$lib/index'
    
    import { loadScript } from '$lib/page/loadscript';
    import { onMount } from 'svelte';

	let { children } = $props();

    
    onMount(async () => {
        await loadScript('/assets/js/app.js');
    });
</script>
<svelte:head>
    <script src={jquerySrc}></script>
    <script src={bootstrapSrc}></script>
</svelte:head>
<!-- Begin page -->
<div class="wrapper">

    <Menu />

    <!-- ============================================================== -->
    <!-- Start Page Content here -->
    <!-- ============================================================== -->
    <div class="page-content">
        <div class="page-container">
            {@render children()}
        </div> <!-- container -->
        <Footer />
    </div>
    <!-- ============================================================== -->
    <!-- End Page content -->
    <!-- ============================================================== -->

</div>
<!-- END wrapper -->
