<script lang="ts">
  import Auth from './Auth.svelte';
  import Game from './Game.svelte';
  import ProfileForm from './ProfileForm.svelte';
  import IntroAnimation from './IntroAnimation.svelte';
  import WelcomeBack from './WelcomeBack.svelte';
  import { userStore, gameStateStore, lastSessionStore } from '../lib/stores';
  import { get } from 'svelte/store';

  let introComplete = false;
  let initialWish = ''; // To store the wish from the animation
  let forceNewGame = false; // Flag from WelcomeBack component

  // Consume the one-time state from chronicle/retry before rendering.
  let restoredGameState = get(gameStateStore);
  if (restoredGameState) {
    // Clear the store immediately so it's not used again on refresh.
    gameStateStore.set(null);
  }

  function handleIntroComplete(event: CustomEvent) {
    initialWish = event.detail.wish;
    introComplete = true;
  }

  // Subscribe to userStore to reset state on logout
  userStore.subscribe(user => {
    if (!user) {
      introComplete = false;
      initialWish = '';
      forceNewGame = false; // Also reset this flag
      restoredGameState = null; // Clear restored state on logout
    }
  });

</script>

<main>
  {#if restoredGameState}
    <!-- Priority 1: Restoring from chronicle, passing state as a prop -->
    <Game session={$userStore} initialState={restoredGameState} />
  {:else if $userStore}
    {#if $userStore.nickname}
      {#if $lastSessionStore && !forceNewGame}
        <!-- Priority 2: User has a last session and hasn't chosen to start a new one -->
        <WelcomeBack on:newgame={() => forceNewGame = true} />
      {:else if !introComplete}
        <!-- Priority 3: No last session, or user chose new game -> play intro -->
        <IntroAnimation on:complete={handleIntroComplete} />
      {:else}
        <!-- Priority 4: Intro is complete, play the game -->
        <Game session={$userStore} wish={initialWish} />
      {/if}
    {:else}
      <!-- If user profile is NOT complete, show the profile form -->
      <ProfileForm />
    {/if}
  {:else}
    <!-- Otherwise, show the Auth component -->
    <Auth />
  {/if}
</main>

<style>
  main {
    width: 100%;
    height: 100%;
  }
</style>
