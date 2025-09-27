<script lang="ts">
  import { userStore } from '$lib/stores';
  import { api } from '$lib/apiService';

  let nickname = '';
  let age: number | undefined = undefined;
  let identity = '';

  let loading = false;
  let error = '';
  let success = '';

  async function handleSubmit() {
    loading = true;
    error = '';
    success = '';

    // Basic validation
    if (!nickname || !age || !identity) {
      error = '所有字段都必须填写';
      loading = false;
      return;
    }

    try {
      const updatedProfile = await api.updateProfile({ nickname, age, identity });
      userStore.update(updatedProfile);
      success = '个人资料更新成功！游戏即将开始...';
      // The parent page (+page.svelte) will detect the updated user store
      // and automatically transition to the next step (the animation).
    } catch (err: any) {
      error = err.message;
    } finally {
      loading = false;
    }
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

<div class="profile-form-container">
  <div class="form-box">
    <h1 class="main-title">📝 完善你的灵魂档案</h1>
    <p class="sub-title">在开始重生之前，我们需要了解你的过去</p>

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="nickname">你的昵称是？</label>
        <input id="nickname" type="text" bind:value={nickname} placeholder="例如：探险家" />
      </div>
      <div class="form-group">
        <label for="age">你在地球OL的等级？(年龄)</label>
        <input id="age" type="number" bind:value={age} placeholder="例如：25" />
      </div>
      <div class="form-group">
        <label for="identity">你的前世身份是？</label>
        <input id="identity" type="text" bind:value={identity} placeholder="例如：一位程序员" />
      </div>

      <button type="submit" class="primary-button" disabled={loading}>
        {loading ? '正在存档...' : '✔️ 确认档案并继续'}
      </button>
    </form>

    {#if error}
      <div class="error-box">
        <p>{error}</p>
        <button class="primary-button" on:click={acknowledgeError}>确定</button>
      </div>
    {/if}
    {#if success}
      <div class="success-box">{success}</div>
    {/if}
  </div>
</div>

<style>
  .profile-form-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background-color: #0E1117;
    color: white;
    font-family: sans-serif;
  }

  .form-box {
    background: rgba(0, 0, 0, 0.5);
    padding: 2rem 3rem;
    border-radius: 15px;
    border: 1px solid rgba(108, 99, 255, 0.3);
    width: 100%;
    max-width: 500px;
    text-align: center;
  }

  .main-title {
    color: #6C63FF;
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }

  .sub-title {
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 2rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
    text-align: left;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: rgba(255, 255, 255, 0.9);
  }

  input {
    width: 100%;
    padding: 0.75rem;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.5);
    color: white;
    border-radius: 10px;
    font-size: 1rem;
  }
  input:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 10px rgba(108, 99, 255, 0.3);
  }

  .primary-button {
    width: 100%;
    padding: 0.75rem;
    background-color: rgba(108, 99, 255, 0.8);
    color: white;
    border: 1px solid rgba(108, 99, 255, 1);
    border-radius: 25px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  .primary-button:hover:not(:disabled) {
    background-color: rgba(108, 99, 255, 1);
  }
  .primary-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-box, .success-box {
    margin-top: 1rem;
    padding: 0.75rem;
    border-radius: 8px;
  }

  .error-box {
    background-color: rgba(224, 49, 49, 0.2);
    border: 1px solid #e03131;
  }

  .success-box {
    background-color: rgba(34, 139, 230, 0.2);
    border: 1px solid #228be6;
  }
</style>
