<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/apiService';
  import { userStore, gameStateStore, lastSessionStore } from '../lib/stores';
  import { get } from 'svelte/store';

  export let session: any;
  export let wish: string = ''; // New prop from intro animation
  export let initialState: any = null; // New prop for restoring state from chronicle

  // Initialize state variables to their default "empty" state.
  let storyHistory: { role: string; content: string }[] = [];
  let currentSegment: any = null;
  let chapterCount = 0;
  let sessionId: number | null = null;
  let nodeId: number | null = null;
  let loading = false;
  let error = '';

  onMount(() => {
    // 【终极修正】All instance-specific initialization logic now lives in onMount.
    
    // Priority 1: Check for state passed directly as a prop (from chronicle retry).
    if (initialState) {
      currentSegment = initialState;
      storyHistory = [{ role: 'assistant', content: initialState.text }];
      chapterCount = initialState.metadata?.chapter_number || 0;
      sessionId = initialState.session_id;
      nodeId = initialState.node_id;
      
      // The restored session is now the "last active" one.
      lastSessionStore.set(sessionId);
      return; // Stop further execution
    }

    // Priority 2: Check for state from the store (from WelcomeBack page).
    const restoredState = get(gameStateStore);
    if (restoredState) {
      currentSegment = restoredState;
      storyHistory = [{ role: 'assistant', content: restoredState.text }];
      chapterCount = restoredState.metadata?.chapter_number || 0;
      sessionId = restoredState.session_id;
      nodeId = restoredState.node_id;
      
      // Important: Clear the store AFTER using the data.
      gameStateStore.set(null);
      return; // Stop further execution
    }

    // Priority 3: If no restored state, check for a wish from the intro animation.
    if (wish && !currentSegment) {
      startNewStory();
    }
  });

  const exampleWishes = [
    "🗡️ 中世纪骑士",
    "🤖 赛博朋克黑客", 
    "🔮 魔法学院学生",
    "🏴‍☠️ 加勒比海盗",
    "🚀 星际探险家",
    "🕵️ 维多利亚时代侦探"
  ];

  function selectExampleWish(example: string) {
    wish = example.split(" ", 2)[1];
  }

  async function startNewStory() {
    loading = true;
    error = '';
    try {
      const data = await api.startStory(wish);
      sessionId = data.session_id;
      nodeId = data.node_id;
      currentSegment = data;
      storyHistory = [{ role: 'assistant', content: data.text }];
      chapterCount = data.metadata?.chapter_number || 1;
      lastSessionStore.set(sessionId); // Save the new session ID
    } catch (err: any) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function continueStory(choice: string) {
    if (!sessionId || !nodeId) return;
    loading = true;
    error = '';
    try {
      const data = await api.continueStory(sessionId, nodeId, choice);
      nodeId = data.node_id;
      currentSegment = data;
      storyHistory = [...storyHistory, { role: 'assistant', content: data.text }];
      chapterCount = data.metadata?.chapter_number || chapterCount;
    } catch (err: any) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function resetGame() {
    wish = '';
    storyHistory = [];
    currentSegment = null;
    chapterCount = 0;
    sessionId = null;
    nodeId = null;
    error = '';
    lastSessionStore.set(null); // Also clear the last session
  }
</script>

<div class="page-container">
  <main class="main-content">
    <div class="user-header">
      <span>欢迎, {session.nickname || session.email}</span>
      <a href="/chronicle" class="chronicle-link">📜 编年史</a>
      <button class="logout-button" on:click={userStore.logout}>登出</button>
    </div>

    {#if error}
      <div class="error-box">
        <p>发生了一个错误:</p>
        <p><strong>{error}</strong></p>
        <button on:click={() => (error = '')}>关闭</button>
      </div>
    {/if}

    {#if !currentSegment}
      <!-- GAME START SCREEN -->
      {#if loading}
        <div class="loading-screen">
          <h1 class="main-title">⏳</h1>
          <p class="sub-title">AI正在为你构建新的世界，请稍候...</p>
        </div>
      {:else}
        <div class="start-screen">
          <h1 class="main-title">🌟 重生之我是…… 🌟</h1>
          <p class="sub-title">一个由AI驱动的互动故事游戏</p>
          
          <img src="/rebirth_gate_placeholder.png" alt="重生之门" class="main-gate-image" />

          <h2>🚪 重生之旅开启仪式</h2>
          <p>✨ 旅人，你希望重生为...</p>

          <input 
            type="text" 
            bind:value={wish} 
            placeholder="发挥你的想象力，描述你想要重生的身份或职业" 
          />
          
          <button class="primary-button" on:click={startNewStory} disabled={loading || !wish.trim()}>
            {loading ? '开启中...' : '🌟 开启重生之旅'}
          </button>

          <div class="divider"></div>
          <h3>💡 或者试试这些？</h3>
          <div class="example-wishes">
            {#each exampleWishes as example}
              <button class="secondary-button" on:click={() => selectExampleWish(example)}>
                {example}
              </button>
            {/each}
          </div>
        </div>
      {/if}
    {:else}
      <!-- IN-GAME SCREEN -->
      <div class="in-game-screen">
        <h2>📖 第 {chapterCount} 章</h2>
        
        <div class="story-display">
          <img src={currentSegment.image_url} alt="故事场景" class="story-image" />
          <div class="story-text-container">
            <p>{currentSegment.text}</p>
          </div>
        </div>

        {#if currentSegment.choices && currentSegment.choices.length > 0}
          <div class="choices-section">
            <h3>🎯 你的抉择是？</h3>
            <div class="choices-grid">
              {#each currentSegment.choices as choice}
                <button class="choice-button" on:click={() => continueStory(choice)} disabled={loading}>
                  {choice}
                </button>
              {/each}
            </div>
          </div>
        {:else}
          <div class="story-end">
            <h3>🎭 故事完结</h3>
            <button class="primary-button" on:click={resetGame}>🔄 开始新的重生</button>
          </div>
        {/if}
      </div>
    {/if}
  </main>
</div>

<style>
  :global(body) {
    background-color: #0E1117;
    color: white;
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }

  .page-container {
    min-height: 100vh;
    background-color: #0E1117;
  }

  .main-content {
    height: 100vh;
    overflow-y: auto;
    padding: 2rem 4rem;
    position: relative;
  }

  .user-header {
    position: absolute;
    top: 1.5rem;
    right: 2rem;
    background: rgba(0, 0, 0, 0.7);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.9rem;
    z-index: 10;
  }

  .logout-button {
    background: #e53e3e;
    color: white;
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    cursor: pointer;
    font-size: 0.8rem;
  }
  .logout-button:hover {
    background: #c53030;
  }

  .chronicle-link {
    color: white;
    text-decoration: none;
    font-weight: bold;
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.2);
    transition: background 0.3s;
  }
  .chronicle-link:hover {
    background: rgba(255, 255, 255, 0.4);
  }

  .loading-screen {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 80vh;
  }

  .start-screen, .in-game-screen {
    max-width: 800px;
    margin: 0 auto;
    text-align: center;
  }

  .main-title {
    text-align: center;
    color: #6C63FF;
    font-size: 3rem;
    margin-bottom: 0.5rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
  }

  .sub-title {
    text-align: center;
    color: rgba(255, 255, 255, 0.8);
    font-size: 1.2rem;
    margin-bottom: 2rem;
  }

  .main-gate-image {
    width: 100%;
    max-width: 500px;
    height: auto;
    border-radius: 15px;
    margin: 20px auto;
    box-shadow: 0 8px 32px rgba(108, 99, 255, 0.3);
  }

  input {
    width: 100%;
    padding: 0.75rem;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.5);
    color: white;
    border-radius: 10px;
    font-size: 1rem;
    margin: 1rem 0;
  }
  input:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 10px rgba(108, 99, 255, 0.3);
  }

  button {
    cursor: pointer;
    transition: all 0.3s ease;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .primary-button {
    width: 100%;
    padding: 0.75rem;
    background-color: rgba(108, 99, 255, 0.8);
    color: white;
    border: 1px solid rgba(108, 99, 255, 1);
    border-radius: 25px;
    font-weight: bold;
  }
  .primary-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 1);
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(108, 99, 255, 0.3);
  }

  .divider {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin: 2rem 0;
  }

  .example-wishes {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
  }

  .secondary-button {
    padding: 0.75rem;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.8);
    color: white;
    border-radius: 25px;
    font-weight: bold;
  }
  .secondary-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 0.8);
  }

  .story-display {
    margin-top: 2rem;
  }

  .story-image {
    width: 100%;
    height: auto;
    max-height: 50vh;
    object-fit: cover;
    border-radius: 10px;
    display: block;
    margin: 0 auto;
  }

  .story-text-container {
    background-color: rgba(0, 0, 0, 0.7);
    padding: 2rem;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: -60px;
    position: relative;
    z-index: 1;
    font-size: 1.1rem;
    line-height: 1.6;
    text-align: left;
  }

  .choices-section {
    margin-top: 2rem;
  }

  .choices-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .choice-button {
    padding: 0.75rem;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.8);
    color: white;
    border-radius: 25px;
    font-weight: bold;
  }
  .choice-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 0.8);
  }

  .story-end {
    margin-top: 2rem;
  }

  .error-box {
    background: #c53030;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
  }
</style>
