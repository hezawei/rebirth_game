<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { lastSessionStore } from '../lib/stores';
  import { api } from '../lib/apiService';
  import { gameStateStore } from '../lib/stores';

  const dispatch = createEventDispatcher();

  let loading = false;

  async function continueLastGame() {
    const sessionId = $lastSessionStore;
    if (!sessionId) return;

    loading = true;
    try {
      // This API endpoint might need to be created.
      // It should fetch the latest node of a given session.
      const lastState = await api.getLatestStoryNode(sessionId);
      gameStateStore.set(lastState);
      // The parent component (+page.svelte) will react to gameStateStore changing
      // and will render the Game component.
    } catch (error) {
      console.error("Failed to continue last game:", error);
      // If it fails, maybe the session is invalid, so we start a new game.
      startNewGame();
    } finally {
      loading = false;
    }
  }

  function startNewGame() {
    lastSessionStore.set(null);
    // Dispatch an event to tell the parent to proceed to the intro animation
    dispatch('newgame');
  }
</script>

<div class="welcome-container">
  <h1 class="main-title">👋 欢迎回来！</h1>
  <img src="/rebirth_gate_placeholder.png" alt="重生之门" class="main-gate-image" />
  
  <p class="sub-title">我们为你保存了上一次的旅程，<br/>你想...</p>

  <div class="button-group">
    <button class="primary-button" on:click={continueLastGame} disabled={loading}>
      {loading ? '加载中...' : '▷ 继续上一次的旅程'}
    </button>
    <button class="secondary-button" on:click={startNewGame} disabled={loading}>
      + 开启一次新的重生
    </button>
  </div>
</div>

<style>
  .welcome-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100vh;
    text-align: center;
    background-color: #0E1117;
  }

  .main-title {
    color: #6C63FF;
    font-size: 3rem;
    margin-bottom: 0.5rem;
  }

  .sub-title {
    color: rgba(255, 255, 255, 0.8);
    font-size: 1.2rem;
    margin-bottom: 2rem;
    line-height: 1.6;
  }

  .main-gate-image {
    width: 100%;
    max-width: 400px;
    height: auto;
    border-radius: 15px;
    margin: 20px auto;
    box-shadow: 0 8px 32px rgba(108, 99, 255, 0.3);
  }

  .button-group {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
    max-width: 400px;
  }

  button {
    padding: 0.75rem;
    border-radius: 25px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .primary-button {
    background-color: rgba(108, 99, 255, 0.8);
    color: white;
    border: 1px solid rgba(108, 99, 255, 1);
  }
  .primary-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 1);
  }

  .secondary-button {
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.8);
    color: white;
  }
  .secondary-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 0.8);
  }
</style>
