<script lang="ts">
    import { onMount } from 'svelte';
    import pageTitle from '$lib/page/pageTitle';
    import { _ } from 'svelte-i18n';
    import { base } from '$app/paths';

    // set translated page title
    $pageTitle = $_('page.science.title');

    let isDark = false;
    onMount(() => {
        const checkTheme = () => {
            isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        };
        checkTheme();
        const observer = new MutationObserver(checkTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });
        return () => observer.disconnect();
    });
</script>

<svelte:head>
    <title>{$pageTitle} | AUGUR</title>
</svelte:head>

<div class="page-container">
    <div class="row row-cols-xxl-1 row-cols-md-1 row-cols-1">
        <div class="col">
            <div class="card d-block">
                <div class="card-body">
                    <h1 class="card-title">{$_('page.science.title')}</h1>

                    <h3 class="mt-3">{$_('page.science.heading')}</h3>
                    <p class="card-text">{$_('page.science.p1')}</p>
                </div>
            </div>
        </div>
    </div>
</div>