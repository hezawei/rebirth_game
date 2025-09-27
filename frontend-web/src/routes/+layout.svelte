<script lang="ts">
    import { onMount } from 'svelte';
    import { afterNavigate, goto } from '$app/navigation';
    import { userStore, authReady } from '$lib/stores';
    import { isProtectedPath } from '$lib/routeGuard';
    import { get } from 'svelte/store';

    let { children } = $props();

    function enforceGuard() {
        if (typeof window === 'undefined') return;
        const path = window.location.pathname;
        const ready = get(authReady);
        const user = get(userStore);
        if (!ready) return; // wait for cookie-based hydration to finish
        if (isProtectedPath(path) && !user) {
            goto('/', { replaceState: true, noScroll: true });
        }
    }

    onMount(() => {
        enforceGuard();
    });

    afterNavigate(() => {
        enforceGuard();
    });
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
</svelte:head>

{@render children?.()}
