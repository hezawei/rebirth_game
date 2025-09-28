<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { api } from '../lib/apiService';
  import { userStore, gameStateStore, lastSessionStore, lastSessionOwnerStore } from '../lib/stores';
  import { setSessionScoped, CHRONICLE_SNAPSHOT_KEY, CHRONICLE_RETURN_TO_KEY } from '$lib/sessionScope';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';

  export let session: any;
  export let wish: string = ''; // New prop from intro animation
  export let initialState: any = null; // New prop for restoring state from chronicle
  export let initialLevel: any = null; // New prop for pre-generated level metadata

  // Initialize state variables to their default "empty" state.
  let storyHistory: { role: string; content: string }[] = [];
  let currentSegment: any = null;
  let chapterCount = 0;
  let sessionId: number | null = null;
  let nodeId: number | null = null;
  let loading = false;
  let error = '';
  // 二阶段启动相关状态
  let preStartLoading = false;
  let wishError: string = '';
  let levelInfo: {
    level_title: string;
    background: string;
    main_quest: string;
    metadata?: any;
  } | null = null;
  let saveLoading = false;
  // 分阶段状态（避免用户误以为“卡在校验”）
  let gameStage: 'idle' | 'validating' | 'animating' | 'preparing' = 'idle';

  type ToastType = 'success' | 'error';
  let toast: { type: ToastType; message: string } | null = null;
  let toastTimer: any = null;

  function showToast(message: string, type: ToastType = 'success', duration = 2500) {
    if (toastTimer) clearTimeout(toastTimer);
    toast = { type, message };
    toastTimer = setTimeout(() => {
      toast = null;
      toastTimer = null;
    }, duration);
  }

  // Navigate to Chronicle after saving a snapshot and return target (per-user scoped)
  async function toChronicle(event?: Event) {
    try {
      if (event) event.preventDefault();
      if (typeof window !== 'undefined') {
        try {
          const uid = get(userStore)?.id;
          if (uid) {
            // Persist the last visible segment as a one-time snapshot for return.
            if (currentSegment) {
              const snapshot = { ...currentSegment };
              setSessionScoped(uid, CHRONICLE_SNAPSHOT_KEY, JSON.stringify(snapshot));
            } else {
              setSessionScoped(uid, CHRONICLE_SNAPSHOT_KEY, ''); // clear via empty
            }
            // Record the exact current URL (path+query+hash) as return target
            const retTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
            setSessionScoped(uid, CHRONICLE_RETURN_TO_KEY, retTo || '/');
          }
        } catch (e) {
          console.error('[Game] failed to persist chronicle return snapshot', e);
        }
      }
      await goto('/chronicle');
    } catch (e) {
      console.error('[Game] failed to navigate to chronicle', e);
    }
  }

  $: currentSuccessRate = typeof currentSegment?.success_rate === 'number' ? currentSegment.success_rate : null;
  function acknowledgeError() {
    if (error && error.includes('登录状态已失效')) {
      // Token invalidated (e.g., logged in elsewhere) -> log out and route to Auth page
      userStore.logout();
      error = '';
      return;
    }
    // Generic errors: just close the message
    error = '';
  }

  onMount(() => {
    // 【终极修正】All instance-specific initialization logic now lives in onMount.
    console.debug('[Game] onMount, initialState present?', !!initialState);
    
    // Priority 1: Check for state passed directly as a prop (from chronicle retry).
    if (initialState) {
      console.debug('[Game] using initialState from props', initialState);
      currentSegment = initialState;
      storyHistory = [{ role: 'assistant', content: initialState.text }];
      chapterCount = initialState.metadata?.chapter_number || 0;
      sessionId = initialState.session_id;
      nodeId = initialState.node_id;
      
      // The restored session is now the "last active" one.
      lastSessionStore.set(sessionId);
      lastSessionOwnerStore.set(get(userStore)?.id ?? null);
      // 清理一次性状态，避免顶层路由持续认为有初始状态
      try { gameStateStore.set(null); } catch {}
      return; // Stop further execution
    }

    // Priority 2: Check for state from the store (from WelcomeBack page).
    const restoredState = get(gameStateStore);
    if (restoredState) {
      console.debug('[Game] using restoredState from store', restoredState);
      currentSegment = restoredState;
      storyHistory = [{ role: 'assistant', content: restoredState.text }];
      chapterCount = restoredState.metadata?.chapter_number || 0;
      sessionId = restoredState.session_id;
      nodeId = restoredState.node_id;
      
      // Important: Clear the store AFTER using the data.
      gameStateStore.set(null);
      lastSessionOwnerStore.set(get(userStore)?.id ?? null);
      return; // Stop further execution
    }

    // Priority 3: If no restored state, check for a wish from the intro animation.
    if (initialLevel && !currentSegment) {
      console.debug('[Game] using initialLevel from intro', initialLevel);
      levelInfo = {
        level_title: initialLevel.level_title,
        background: initialLevel.background,
        main_quest: initialLevel.main_quest,
        metadata: initialLevel.metadata ?? null,
      };
      return;
    }

    if (wish && !currentSegment) {
      console.debug('[Game] pre-start flow with wish', wish);
      beginPreStartFlow();
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

  async function beginPreStartFlow() {
    preStartLoading = true;
    gameStage = 'validating';
    wishError = '';
    levelInfo = null;
    try {
      console.debug('[Game] Phase1 校验愿望 /story/check_wish', { wish });
      const chk = await api.checkWish(wish);
      if (!chk.ok) {
        wishError = chk.reason || '不能满足这个重生愿望哦，换一个吧';
        return;
      }
      // 展示一个简短的通过动画，避免用户误以为还在“校验”
      gameStage = 'animating';
      await tick(); // 强制UI更新
      await new Promise((r) => setTimeout(r, 800));

      // 第二阶段：生成故事概要
      gameStage = 'preparing';
      console.debug('[Game] Phase2 概要生成 /story/prepare_start', { wish });
      const prep = await api.prepareStart(wish);
      levelInfo = {
        level_title: prep.level_title,
        background: prep.background,
        main_quest: prep.main_quest,
        metadata: prep.metadata ?? null,
      };
    } catch (err: any) {
      error = err.message || '关卡准备失败，请稍后重试';
    } finally {
      preStartLoading = false;
      gameStage = 'idle';
    }
  }

  async function confirmStart() {
    loading = true;
    error = '';
    try {
      console.debug('[Game] POST /story/start (confirm)', { wish });
      const data = await api.startStory(wish);
      sessionId = data.session_id;
      nodeId = data.node_id;
      currentSegment = data;
      storyHistory = [{ role: 'assistant', content: data.text }];
      chapterCount = data.metadata?.chapter_number || 1;
      // 仅在确认开始后写入最近一次会话ID
      lastSessionStore.set(sessionId);
      lastSessionOwnerStore.set(get(userStore)?.id ?? null);
      levelInfo = null; // 清理预备信息
      initialLevel = null;
    } catch (err: any) {
      error = err.message || '开始重生失败，请稍后重试';
    } finally {
      loading = false;
    }
  }

  async function continueStory(choice: string) {
    if (!sessionId || !nodeId) return;
    loading = true;
    error = '';
    try {
      console.debug('[Game] POST /story/continue', { sessionId, nodeId, choice });
      const data = await api.continueStory(sessionId, nodeId, choice);
      console.debug('[Game] continueStory response', data);
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

  async function createSave() {
    if (!sessionId || !nodeId) {
      showToast('当前没有进行中的关卡，无法存档', 'error');
      return;
    }
    saveLoading = true;
    const title = `第${chapterCount}章存档 - ${new Date().toLocaleString('zh-CN')}`;
    try {
      const payload = await api.createSave(sessionId, nodeId, title);
      showToast(`存档成功：「${payload.title}」`, 'success');
    } catch (err: any) {
      showToast(err?.message || '存档失败，请稍后再试', 'error');
    } finally {
      saveLoading = false;
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
    lastSessionOwnerStore.set(null);
    levelInfo = null;
    wishError = '';
    initialLevel = null;
    toast = null;
  }
</script>

<div class="page-container">
  <main class="main-content">
    <div class="user-header">
      <span>欢迎, {(session && (session.nickname || session.email)) || ''}</span>
      <a href="/chronicle" class="chronicle-link" on:click|preventDefault={toChronicle}>📜 编年史</a>
      <button class="save-button" on:click={createSave} disabled={saveLoading}>💾 存档</button>
      <button class="logout-button" on:click={userStore.logout}>登出</button>
    </div>

    {#if error}
      <div class="error-box">
        <p>发生了一个错误:</p>
        <p><strong>{error}</strong></p>
        <button on:click={acknowledgeError}>确定</button>
      </div>
    {/if}

    {#if toast}
      <div class="toast-container">
        <div class={`toast ${toast.type}`}>
          <span class="toast-glow"></span>
          <span>{toast.message}</span>
        </div>
      </div>
    {/if}

    {#if !currentSegment}
      <!-- GAME START / PREPARE SCREEN -->
      {#if loading}
        <!-- 启动故事骨架屏 -->
        <div class="loading-screen">
          <div class="loading-card">
            <div class="loading-icon">🧠</div>
            <h2>世界构建中</h2>
            <p class="loading-desc">AI 正在为你构建新的世界，请稍等片刻。</p>
            <div class="skeleton-image"></div>
            <div class="skeleton-text">
              <div class="skeleton-line short"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line long"></div>
            </div>
            <div class="loading-tip">小提示：每次抉择都会塑造全新的剧情走向。</div>
          </div>
        </div>
      {:else if preStartLoading}
        <!-- 分阶段预启动骨架屏：校验 -> 过渡动画 -> 概要生成 -->
        <div class="loading-screen">
          <div class="loading-card">
            {#if gameStage === 'validating'}
              <div class="loading-icon">⚡</div>
              <h2>愿望校验中</h2>
              <p class="loading-desc">正在快速检查你的愿望是否合适…</p>
              <div class="skeleton-image"></div>
              <div class="skeleton-text">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line long"></div>
              </div>
              <div class="loading-tip">这一步通常仅需片刻</div>
            {:else if gameStage === 'animating'}
              <div class="loading-icon">✅</div>
              <h2>校验通过</h2>
              <p class="loading-desc">正在为你准备世界观与任务概要…</p>
              <div class="skeleton-image"></div>
              <div class="skeleton-text">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line long"></div>
              </div>
              <div class="loading-tip">即将进入关卡设定生成</div>
            {:else}
              <!-- preparing -->
              <div class="loading-icon">🧭</div>
              <h2>关卡设定生成中</h2>
              <p class="loading-desc">正在分析你的愿望，为你量身打造第一关的背景与使命。</p>
              <div class="skeleton-image"></div>
              <div class="skeleton-text">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line long"></div>
              </div>
              <div class="loading-tip">🚀 后台已开始预生成第一节故事</div>
            {/if}
          </div>
        </div>
      {:else if levelInfo}
        <div class="start-screen">
          <h1 class="main-title">🎯 第一关概要</h1>
          <p class="sub-title">请确认是否开始本次重生任务</p>
          <div class="story-display">
            <div class="story-text-container">
              <p><strong>标题：</strong>{levelInfo.level_title}</p>
              <p><strong>背景：</strong>{levelInfo.background}</p>
              <p><strong>主线任务：</strong>{levelInfo.main_quest}</p>
              {#if levelInfo.metadata?.history_profile}
                <div class="history-context">
                  <p><strong>身份：</strong>{levelInfo.metadata.history_profile.name}</p>
                  <p><strong>时代：</strong>{levelInfo.metadata.history_profile.era}</p>
                  <p><strong>人物特质：</strong>{levelInfo.metadata.history_profile.personas?.join('，')}</p>
                </div>
              {/if}
            </div>
          </div>
          <button class="primary-button" on:click={confirmStart} disabled={loading}>立即开始</button>
          <div class="divider"></div>
          <button class="secondary-button" on:click={() => { levelInfo = null; }}>返回修改愿望</button>
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
          {#if wishError}
            <div class="error-box"><p>{wishError}</p></div>
          {/if}
          
          <button class="primary-button" on:click={beginPreStartFlow} disabled={preStartLoading || !wish.trim()}>
            {preStartLoading ? '生成设定中...' : '🌟 开启重生之旅'}
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
        {#if currentSuccessRate !== null}
          <div class="success-rate">
            <div class="success-label">主线成功率</div>
            <div class="success-bar">
              <div class="success-bar-fill" style={`width: ${currentSuccessRate}%`}></div>
            </div>
            <div class="success-value">{currentSuccessRate}%</div>
          </div>
        {/if}

        <div class="story-display">
          <img src={currentSegment.image_url} alt="故事场景" class="story-image" />
          <div class="story-text-container">
            <p>{currentSegment.text}</p>
          </div>
        </div>

        {#if loading}
          <!-- Loading overlay shown during /story/continue to provide instant feedback -->
          <div class="loading-overlay">
            <div class="skeleton-image"></div>
            <div class="skeleton-text">
              <div class="skeleton-line short"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line long"></div>
            </div>
          </div>
        {/if}

        {#if currentSegment.choices && currentSegment.choices.length > 0}
          <div class="choices-section">
            <h3>🎯 你的抉择是？</h3>
            <div class="choices-grid">
              {#each currentSegment.choices as choice}
                <button class="choice-button" on:click={() => continueStory(choice.option)} disabled={loading}>
                  <div class="choice-header">
                    <span class="choice-title">{choice.option}</span>
                    {#if typeof choice.success_rate_delta === 'number'}
                      <span class={`choice-delta ${choice.success_rate_delta >= 0 ? 'positive' : 'negative'}`}>
                        {choice.success_rate_delta >= 0 ? '+' : ''}{choice.success_rate_delta}%
                      </span>
                    {/if}
                  </div>
                  <div class="choice-summary">{choice.summary}</div>
                  <div class="choice-meta">
                    {#if choice.risk_level}
                      <span class={`risk-badge risk-${choice.risk_level}`}>{choice.risk_level}</span>
                    {/if}
                    {#if choice.tags?.length}
                      <span class="choice-tags">{choice.tags.join(' / ')}</span>
                    {/if}
                  </div>
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

  .save-button {
    background: rgba(108, 99, 255, 0.8);
    color: white;
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 15px;
    cursor: pointer;
    font-size: 0.8rem;
  }
  .save-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .save-button:not(:disabled):hover {
    background: rgba(108, 99, 255, 1);
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
    justify-content: center;
    align-items: center;
    min-height: 70vh;
  }

  .loading-card {
    width: min(540px, 90vw);
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 2rem 2.5rem;
    text-align: center;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(6px);
  }

  .loading-card h2 {
    margin: 0.5rem 0 0.75rem;
    font-size: 1.8rem;
    color: #FFD700;
  }

  .loading-desc {
    color: rgba(255,255,255,0.85);
    font-size: 1rem;
    margin-bottom: 1.5rem;
  }

  .loading-icon {
    font-size: 2.2rem;
    animation: float 3s ease-in-out infinite;
  }

  .loading-tip {
    margin-top: 1.5rem;
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.65);
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }

  .save-feedback {
    margin: 1rem 0;
    padding: 0.75rem 1rem;
    border-radius: 10px;
    text-align: center;
    font-size: 0.95rem;
  }
  .save-feedback.success {
    background: rgba(72, 187, 120, 0.15);
    border: 1px solid rgba(72, 187, 120, 0.6);
    color: #68d391;
  }
  .save-feedback.error {
    background: rgba(229, 62, 62, 0.15);
    border: 1px solid rgba(229, 62, 62, 0.6);
    color: #fc8181;
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

  /* 骨架屏样式（可用于预启动与启动故事加载） */
  .skeleton-image {
    width: 100%;
    height: 40vh;
    max-height: 360px;
    border-radius: 10px;
    background: linear-gradient(90deg, rgba(255,255,255,0.08) 25%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.08) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.6s infinite;
  }
  .skeleton-text {
    background-color: rgba(0, 0, 0, 0.7);
    padding: 1.25rem;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: -40px;
    position: relative;
    z-index: 1;
  }
  .skeleton-line {
    height: 14px;
    margin: 10px 0;
    border-radius: 6px;
    background: linear-gradient(90deg, rgba(255,255,255,0.08) 25%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.08) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.6s infinite;
  }
  .skeleton-line.short { width: 45%; }
  .skeleton-line.long { width: 90%; }
  .skeleton-line:not(.short):not(.long) { width: 70%; }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .error-box {
    background: #c53030;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
  }
</style>
