<script lang="ts">
  import Auth from './Auth.svelte';
  import Game from './Game.svelte';
  import ProfileForm from './ProfileForm.svelte';
  import IntroAnimation from './IntroAnimation.svelte';
  import WelcomeBack from './WelcomeBack.svelte';
  import { userStore, gameStateStore, lastSessionStore, lastSessionOwnerStore } from '../lib/stores';
  

  let introComplete = false;
  let initialWish = ''; // To store the wish from the animation
  let initialLevelMeta: any = null;
  let forceNewGame = false; // Flag from WelcomeBack component
  let restoredGameState: any = null; // 本地持有一次性状态，避免受 store 清空影响

  // 改为响应式使用 $gameStateStore，让 WelcomeBack 设置的状态能驱动渲染切换
  $: if ($gameStateStore && !restoredGameState) {
    console.debug('[+page] detected gameStateStore update, capturing into local state');
    restoredGameState = $gameStateStore;
    try { gameStateStore.set(null); } catch {}
  }

  // 观察关键状态用于调试分支切换
  $: console.debug('[+page] state snapshot', {
    hasUser: !!$userStore,
    hasNickname: !!($userStore && $userStore.nickname),
    lastSessionId: $lastSessionStore,
    lastSessionOwner: $lastSessionOwnerStore,
    currentUserId: $userStore?.id,
    forceNewGame,
    introComplete,
    restoredGameStatePresent: !!restoredGameState,
  });

  function handleIntroComplete(event: CustomEvent) {
    initialWish = event.detail.wish;
    initialLevelMeta = event.detail.level || null;
    introComplete = true;
    // Intro 完成即视为用户明确开始新游戏，防止随后再弹出“欢迎回来”
    forceNewGame = true;
  }

  // Subscribe to userStore to reset state on logout
  userStore.subscribe(user => {
    if (!user) {
      introComplete = false;
      initialWish = '';
      forceNewGame = false; // Also reset this flag
      restoredGameState = null; // 清理本地状态
    }
  });

</script>

<main>
  {#if restoredGameState}
    <!-- Priority 1: Restoring from WelcomeBack/chronicle via local captured state -->
    <Game session={$userStore} initialState={restoredGameState} />
  {:else if $userStore}
    {#if $userStore.nickname}
      {#if !introComplete}
        <!-- Priority: 登录后始终先播放第一段开场动画（不可跳过） -->
        <IntroAnimation on:complete={handleIntroComplete} />
      {:else if $lastSessionStore && $lastSessionOwnerStore === $userStore.id && !forceNewGame}
        <!-- Intro 完成后如仍需“欢迎回来”，此分支理论上不会触发（forceNewGame 在 Intro 完成时被置为 true） -->
        <WelcomeBack 
          on:newgame={() => { console.debug('[+page] newgame event received'); forceNewGame = true; }}
          on:continue={(e) => { console.debug('[+page] continue event received', e.detail); restoredGameState = e.detail; }}
        />
      {:else}
        <!-- Intro 完成，开始游戏（新局或从外部指定的 wish） -->
        <Game session={$userStore} wish={initialWish} initialLevel={initialLevelMeta} />
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
