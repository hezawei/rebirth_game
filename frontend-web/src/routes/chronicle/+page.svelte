<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/apiService';
  import { goto } from '$app/navigation';
  import { gameStateStore, userStore } from '$lib/stores';
  import { getSessionScoped, removeSessionScoped, CHRONICLE_SNAPSHOT_KEY, CHRONICLE_RETURN_TO_KEY } from '$lib/sessionScope';
  import { get } from 'svelte/store';

  let sessions: any[] = [];
  let loading = true;
  let error = '';
  
  let expandedSessionId: number | null = null;
  let sessionDetails: any = null;
  let detailsLoading = false;
  let canReturn = false;

  let saves: any[] = [];
  let savesLoading = true;
  let saveError = '';
  let selectedSave: any = null;
  let saveDetailLoading = false;
  let saveStatusFilter: string = 'active';

  // 统一的提示框（成功/错误）
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

  onMount(async () => {
    // determine if we can return (only when snapshot and return_to recorded for current user)
    try {
      const uid = get(userStore)?.id;
      if (typeof window !== 'undefined' && uid) {
        const hasSnap = !!getSessionScoped(uid, CHRONICLE_SNAPSHOT_KEY);
        const hasRet = !!getSessionScoped(uid, CHRONICLE_RETURN_TO_KEY);
        canReturn = hasSnap && hasRet;
      }
    } catch {}

    await Promise.all([loadSessions(), loadSaves(saveStatusFilter)]);
  });

  async function loadSessions() {
    loading = true;
    error = '';
    try {
      sessions = await api.getSessions();
    } catch (err: any) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function loadSaves(status?: string) {
    savesLoading = true;
    saveError = '';
    try {
      saves = await api.listSaves(status);
    } catch (err: any) {
      saveError = err.message;
      showToast(`加载存档失败：${saveError}`, 'error');
    } finally {
      savesLoading = false;
    }
  }

  async function toggleSessionDetails(sessionId: number) {
    if (expandedSessionId === sessionId) {
      expandedSessionId = null;
      sessionDetails = null;
      return;
    }

    detailsLoading = true;
    error = '';
    try {
      sessionDetails = await api.getSessionDetails(sessionId);
      expandedSessionId = sessionId;
    } catch (err: any) {
      error = err.message;
    } finally {
      detailsLoading = false;
    }
  }

  async function handleRetry(nodeId: number) {
    try {
      const gameState = await api.retryFromNode(nodeId);
      gameStateStore.set(gameState);
      goto('/');
    } catch (err: any) {
      error = `时光回溯失败: ${err.message}`;
    }
  }

  async function showSaveDetail(saveId: number) {
    saveDetailLoading = true;
    saveError = '';
    try {
      selectedSave = await api.getSaveDetail(saveId);
    } catch (err: any) {
      saveError = err.message;
    } finally {
      saveDetailLoading = false;
    }
  }

  async function resumeSave(saveId: number) {
    try {
      showToast('正在从存档恢复到游戏…', 'success', 1500);
      const detail = await api.getSaveDetail(saveId);
      if (!detail?.node) {
        saveError = '存档内容缺失，无法继续';
        showToast(saveError, 'error');
        return;
      }
      gameStateStore.set(detail.node);
      // 刷新存档列表，确保状态最新
      await loadSaves(saveStatusFilter);
      await goto('/');
    } catch (err: any) {
      saveError = err.message || '存档恢复失败';
      showToast(saveError, 'error');
    }
  }

  async function deleteSave(saveId: number) {
    if (!confirm('确定要删除这个存档吗？')) return;
    try {
      await api.deleteSave(saveId);
      if (selectedSave?.id === saveId) {
        selectedSave = null;
      }
      await loadSaves(saveStatusFilter);
      showToast('已删除存档', 'success');
    } catch (err: any) {
      saveError = err.message || '删除存档失败';
      showToast(saveError, 'error');
    }
  }

  function acknowledgeError() {
    if (error && error.includes('登录状态已失效')) {
      userStore.logout();
      error = '';
      goto('/');
      return;
    }
    error = '';
  }

  async function goBack() {
    try {
      const uid = get(userStore)?.id;
      if (!uid || typeof window === 'undefined') {
        error = '无法恢复返回目标，请从首页重新进入';
        return;
      }
      const snapStr = getSessionScoped(uid, CHRONICLE_SNAPSHOT_KEY);
      const retTo = getSessionScoped(uid, CHRONICLE_RETURN_TO_KEY);
      if (!snapStr || !retTo) {
        error = '无法恢复返回目标，请从首页重新进入';
        return;
      }
      const snapshot = JSON.parse(snapStr);
      console.debug('[Chronicle] restoring snapshot and returning to', retTo);
      gameStateStore.set(snapshot);
      // one-time consume
      removeSessionScoped(uid, CHRONICLE_SNAPSHOT_KEY);
      removeSessionScoped(uid, CHRONICLE_RETURN_TO_KEY);
      await goto(retTo, { replaceState: true });
    } catch (e: any) {
      error = e?.message || '返回失败';
    }
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleString('zh-CN');
  }
</script>

<div class="page-container">
  <header>
    {#if canReturn}
      <button class="back-link" on:click={goBack}>← 返回游戏</button>
    {:else}
      <a href="/" class="back-link">← 回到首页</a>
    {/if}
    <h1>📜 重生编年史</h1>
  </header>

  <!-- 顶部提示 -->
  {#if toast}
    <div class="toast-container">
      <div class={`toast ${toast.type}`}>{toast.message}</div>
    </div>
  {/if}

  <section class="content-grid">
    <div class="sessions-column">
      <div class="column-header">
        <h2>🧭 历史旅程</h2>
        <button class="refresh" on:click={loadSessions}>刷新</button>
      </div>
      {#if loading}
        <p>正在加载历史记录...</p>
      {:else if error}
        <div class="error-box">
          <p>{error}</p>
          <button class="retry-button" on:click={acknowledgeError}>确定</button>
        </div>
      {:else if sessions.length === 0}
        <div class="empty-state">
          <div class="icon">🗺️</div>
          <h3>还没有编年史</h3>
          <p>去首页开启一段新的重生之旅吧！你的每一次抉择都会被记录在这里。</p>
          <a class="cta" href="/">开始游戏</a>
        </div>
      {:else}
        <div class="sessions-list">
          {#each sessions as session}
            <div class="session-item">
              <button class="session-header" on:click={() => toggleSessionDetails(session.id)}>
                <span class="wish-title">{session.wish}</span>
                <span class="date">{formatDate(session.created_at)}</span>
                <span class="arrow">{expandedSessionId === session.id ? '▲' : '▼'}</span>
              </button>

              {#if expandedSessionId === session.id}
                <div class="session-details">
                  {#if detailsLoading}
                    <p>正在加载详细历史...</p>
                  {:else if sessionDetails}
                    {#each sessionDetails.nodes as node, i}
                      <div class="node-item">
                        <div class="node-header">
                          <h3>📜 第 {node.chapter_number} 章</h3>
                          {#if node.choices.length > 0}
                            <button class="retry-button" on:click={() => handleRetry(node.id)}>
                              ⏪ 从这里重来
                            </button>
                          {/if}
                        </div>
                        <div class="node-content">
                          <div class="node-image">
                            <img src={node.image_url} alt="场景图 {i + 1}" />
                          </div>
                          <div class="node-text">
                            <p>{node.story_text}</p>
                            {#if node.user_choice}
                              <p class="user-choice"><strong>你的选择:</strong> {node.user_choice}</p>
                            {/if}
                          </div>
                        </div>
                      </div>
                    {/each}
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="saves-column">
      <div class="column-header">
        <h2>💾 存档管理</h2>
        <select bind:value={saveStatusFilter} on:change={() => loadSaves(saveStatusFilter)}>
          <option value="">全部</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">已失败</option>
        </select>
      </div>

      {#if savesLoading}
        <p>正在加载存档...</p>
      {:else if saveError}
        <div class="error-box">
          <p>{saveError}</p>
          <button class="retry-button" on:click={() => loadSaves(saveStatusFilter)}>重试</button>
        </div>
      {:else if saves.length === 0}
        <div class="empty-state">
          <div class="icon">💾</div>
          <h3>还没有存档</h3>
          <p>在游戏中点击“存档”按钮即可在此查看与管理。</p>
          <a class="cta" href="/">返回游戏</a>
        </div>
      {:else}
        <div class="saves-list">
          {#each saves as save}
            <button
              type="button"
              class={`save-item ${selectedSave?.id === save.id ? 'active' : ''}`}
              on:click={() => showSaveDetail(save.id)}
            >
              <div class="save-header">
                <span class="save-title">{save.title}</span>
                <span class={`status-badge status-${save.status}`}>{save.status}</span>
              </div>
              <div class="save-meta">
                <span>会话 #{save.session_id}</span>
                <span>节点 #{save.node_id}</span>
              </div>
              <div class="save-date">创建: {formatDate(save.created_at)}</div>
            </button>
          {/each}
        </div>
      {/if}

      {#if selectedSave}
        <div class="save-detail">
          <div class="detail-header">
            <h3>{selectedSave.title}</h3>
            <div class="actions">
              <button on:click={() => resumeSave(selectedSave.id)}>▶ 继续</button>
              <button class="danger" on:click={() => deleteSave(selectedSave.id)}>🗑 删除</button>
            </div>
          </div>
          <p><strong>状态：</strong>{selectedSave.status}</p>
          <p><strong>会话：</strong>#{selectedSave.session_id}</p>
          <p><strong>节点：</strong>#{selectedSave.node_id}</p>
          <p><strong>创建时间：</strong>{formatDate(selectedSave.created_at)}</p>
          <p><strong>更新时间：</strong>{formatDate(selectedSave.updated_at)}</p>

          {#if saveDetailLoading}
            <p>正在加载存档详情...</p>
          {:else if selectedSave.node}
            <div class="save-node">
              <img src={selectedSave.node.image_url} alt="存档场景" />
              <div>
                <p>{selectedSave.node.text}</p>
                {#if selectedSave.node.metadata?.chapter_number}
                  <p>章节：第 {selectedSave.node.metadata.chapter_number} 章</p>
                {/if}
                {#if selectedSave.node.success_rate !== null}
                  <p>成功率：{selectedSave.node.success_rate}%</p>
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </section>
</div>

<style>
  .page-container {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    color: white;
    font-family: sans-serif;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 1rem;
  }

  .back-link {
    color: #6C63FF;
    text-decoration: none;
    font-weight: bold;
  }

  h1 {
    color: #FFD700;
    text-align: center;
    flex-grow: 1;
  }

  /* 响应式栅格布局 */
  .content-grid {
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 1.5rem;
  }
  @media (max-width: 960px) {
    .content-grid {
      grid-template-columns: 1fr;
    }
  }

  .sessions-column, .saves-column {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 1rem;
  }

  .column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }
  .column-header .refresh {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.8);
    color: #fff;
    padding: 0.4rem 0.75rem;
    border-radius: 8px;
  }

  .sessions-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .session-item {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .session-header {
    width: 100%;
    background: transparent;
    border: none;
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    color: white;
    font-size: 1.1rem;
  }
  .session-header:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .wish-title {
    font-weight: bold;
  }

  .date {
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.6);
  }

  .arrow {
    font-size: 1.2rem;
  }

  .session-details {
    padding: 0 1.5rem 1.5rem 1.5rem;
  }

  .node-item {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 1.5rem;
    margin-top: 1.5rem;
  }
  .node-item:first-child {
    border-top: none;
    margin-top: 0;
    padding-top: 0;
  }

  .node-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .node-header h3 {
    margin: 0;
    color: #6C63FF;
  }

  .retry-button {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid #6C63FF;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    cursor: pointer;
  }
  .retry-button:hover {
    background: #6C63FF;
  }

  .node-content {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 1.5rem;
    align-items: flex-start;
  }

  .node-image img {
    width: 100%;
    border-radius: 8px;
  }

  .user-choice {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px dashed rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.7);
  }

  .error-box {
    background: #c53030;
    padding: 1rem;
    border-radius: 10px;
  }

  /* 顶部提示（Toast） */
  .toast-container {
    position: sticky;
    top: 0.5rem;
    z-index: 10;
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
  }
  .toast {
    padding: 0.6rem 1rem;
    border-radius: 10px;
    border: 1px solid transparent;
    font-size: 0.95rem;
  }
  .toast.success {
    background: rgba(72, 187, 120, 0.15);
    border-color: rgba(72, 187, 120, 0.6);
    color: #68d391;
  }
  .toast.error {
    background: rgba(229, 62, 62, 0.15);
    border-color: rgba(229, 62, 62, 0.6);
    color: #fc8181;
  }

  /* 空状态 */
  .empty-state {
    text-align: center;
    padding: 2rem 1rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px dashed rgba(255, 255, 255, 0.2);
    border-radius: 10px;
  }
  .empty-state .icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }
  .empty-state .cta {
    margin-top: 0.75rem;
    display: inline-block;
    color: #fff;
    background: rgba(108, 99, 255, 0.85);
    border: 1px solid rgba(108, 99, 255, 1);
    padding: 0.5rem 0.9rem;
    border-radius: 10px;
    text-decoration: none;
  }
</style>
