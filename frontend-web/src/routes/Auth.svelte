<script lang="ts">
  import { userStore } from '../lib/stores';

  let email = '';
  let password = '';
  let isLogin = true;
  let loading = false;
  let error = '';
  let successMessage = '';

  async function handleAuth() {
    loading = true;
    error = '';
    successMessage = '';

    try {
      if (isLogin) {
        // --- Login Logic ---
        await userStore.login(email, password);
        // The userStore will update, and the main +page.svelte will reactively
        // switch to the Game component. No need to dispatch events.
      } else {
        // --- Registration Logic ---
        await userStore.register(email, password);
        successMessage = '注册成功！请使用您的新账户登录。';
        // Switch to login view after successful registration
        isLogin = true;
      }
    } catch (err: any) {
      error = err.message || '发生未知错误';
    } finally {
      loading = false;
    }
  }
</script>

<div class="auth-container">
  <div class="auth-card">
    <h2>{isLogin ? '登录' : '注册'}</h2>

    {#if successMessage}
      <div class="success">{successMessage}</div>
    {/if}
    {#if error}
      <div class="error">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleAuth}>
      <div class="form-group">
        <label for="email">邮箱</label>
        <input
          id="email"
          type="email"
          bind:value={email}
          required
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="password">密码</label>
        <input
          id="password"
          type="password"
          bind:value={password}
          required
          disabled={loading}
        />
      </div>

      <button type="submit" disabled={loading}>
        {loading ? '处理中...' : (isLogin ? '登录' : '注册')}
      </button>
    </form>

    <p>
      {isLogin ? '还没有账号？' : '已有账号？'}
      <button type="button" on:click={() => isLogin = !isLogin}>
        {isLogin ? '注册' : '登录'}
      </button>
    </p>
  </div>
</div>

<style>
  .auth-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .auth-card {
    background: white;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    width: 100%;
    max-width: 400px;
  }

  h2 {
    text-align: center;
    margin-bottom: 1.5rem;
    color: #333;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: #555;
    font-weight: 500;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 1rem;
  }

  input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
  }

  button[type="submit"] {
    width: 100%;
    padding: 0.75rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 5px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.3s;
  }

  button[type="submit"]:hover:not(:disabled) {
    background: #5a6fd8;
  }

  button[type="submit"]:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  button[type="button"] {
    background: none;
    border: none;
    color: #667eea;
    cursor: pointer;
    text-decoration: underline;
  }

  .error {
    background: #fee;
    color: #c33;
    padding: 0.75rem;
    border-radius: 5px;
    margin-bottom: 1rem;
    border: 1px solid #fcc;
  }

  .success {
    background: #e6fffa;
    color: #00bfa5;
    padding: 0.75rem;
    border-radius: 5px;
    margin-bottom: 1rem;
    border: 1px solid #a7f3d0;
  }

  p {
    text-align: center;
    margin-top: 1rem;
    color: #666;
  }
</style>
