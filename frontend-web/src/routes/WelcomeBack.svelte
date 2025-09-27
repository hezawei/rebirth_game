<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { goto } from '$app/navigation';
  import { lastSessionStore, lastSessionOwnerStore, userStore } from '../lib/stores';
  import { api } from '../lib/apiService';
  import { gameStateStore } from '../lib/stores';

  const dispatch = createEventDispatcher();

  let loading = false;
  let error: string = '';

  async function continueLastGame() {
    loading = true;
    try {
      const sessionId = $lastSessionStore;
      console.log('[WelcomeBack] continueLastGame clicked, lastSessionId(from store)=', sessionId);
      // 严格按“上次最近一次”的会话继续，不再使用全局最深
      if (!sessionId) {
        throw new Error('无可用的历史进度');
      }
      const lastState = await api.getLatestStoryNode(sessionId);
      console.log('[WelcomeBack] latest node fetched:', lastState);
      gameStateStore.set(lastState);
      console.log('[WelcomeBack] gameStateStore set.');
      // 同步 last session 归属，避免之后再提示不属于当前用户
      try {
        lastSessionStore.set(lastState.session_id);
        lastSessionOwnerStore.set($userStore?.id ?? null);
      } catch {}
      // 额外：向父组件显式派发一个 continue 事件，传递状态
      dispatch('continue', lastState);
      console.log('[WelcomeBack] dispatched continue event with state.');
      // 父组件 (+page.svelte) 会通过 gameStateStore 的变化来切换渲染
      // 无需强制 goto 触发重渲染
    } catch (error) {
      console.error("Failed to continue last game:", error);
      const msg = (error as any)?.message || '';
      if (msg.includes('登录状态已失效')) {
        // prompt user and redirect to login
        error = msg;
      } else {
        // 其他错误：提示用户明确问题，不自动新开以避免误操作
        error = msg || '无法继续上次进度，请前往编年史查看历史记录';
      }
    } finally {
      loading = false;
    }
  }

  function startNewGame() {
    lastSessionStore.set(null);
    // Dispatch an event to tell the parent to proceed to the intro animation
    dispatch('newgame');
  }

  function acknowledgeError() {
    if (error && error.includes('登录状态已失效')) {
      userStore.logout();
      error = '';
      return;
    }
    error = '';
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
