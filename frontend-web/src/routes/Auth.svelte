<script lang="ts">
  import { supabase } from '$lib/supabase' // 【核心修正】从中央配置文件导入
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher()

  let email = ''
  let password = ''
  let isLogin = true
  let loading = false
  let error = ''
  let showResendEmail = false
  let devMode = true // 开发模式

  async function resendConfirmation() {
    loading = true
    try {
      const { error: resendError } = await supabase.auth.resend({
        type: 'signup',
        email: email
      })
      if (resendError) throw resendError
      error = '验证邮件已重新发送，请检查您的邮箱。'
    } catch (err: any) {
      error = `重发邮件失败: ${err.message}`
    } finally {
      loading = false
    }
  }

  async function handleAuth() {
    loading = true
    error = ''

    try {
      if (isLogin) {
        const { data, error: authError } = await supabase.auth.signInWithPassword({
          email,
          password
        })
        if (authError) throw authError
        if (data.user) {
          dispatch('authenticated', { user: data.user })
        }
      } else {
        const { data, error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin
          }
        })
        if (authError) throw authError

        if (data.user) {
          if (data.user.email_confirmed_at) {
            // 邮箱已验证，直接登录
            dispatch('authenticated', { user: data.user })
          } else {
            // 邮箱未验证，显示提示信息
            error = '注册成功！请检查您的邮箱并点击验证链接完成注册。'
            // 3秒后自动切换到登录模式
            setTimeout(() => {
              isLogin = true
              error = ''
            }, 3000)
          }
        }
      }
    } catch (err: any) {
      if (err.message === 'Email not confirmed') {
        if (devMode) {
          // 开发模式：创建一个临时用户对象
          const tempUser = {
            id: 'dev-user-' + Date.now(),
            email: email,
            email_confirmed_at: new Date().toISOString()
          }
          dispatch('authenticated', { user: tempUser })
          return
        } else {
          error = '邮箱未验证。请检查您的邮箱并点击验证链接。'
          showResendEmail = true
        }
      } else {
        error = err.message
        showResendEmail = false
      }
    } finally {
      loading = false
    }
  }
</script>

<div class="auth-container">
  <div class="auth-card">
    <h2>{isLogin ? '登录' : '注册'}</h2>

    {#if devMode}
      <div class="dev-notice">
        🚧 开发模式：邮箱验证已跳过
      </div>
    {/if}
    
    {#if error}
      <div class="error">{error}</div>
      {#if showResendEmail}
        <button
          type="button"
          class="resend-button"
          on:click={resendConfirmation}
          disabled={loading}
        >
          重新发送验证邮件
        </button>
      {/if}
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

  .resend-button {
    width: 100%;
    padding: 0.5rem;
    background: #f8f9fa;
    color: #667eea;
    border: 1px solid #667eea;
    border-radius: 5px;
    font-size: 0.9rem;
    cursor: pointer;
    margin-top: 0.5rem;
    transition: all 0.3s;
  }

  .resend-button:hover:not(:disabled) {
    background: #667eea;
    color: white;
  }

  .resend-button:disabled {
    background: #f5f5f5;
    color: #ccc;
    border-color: #ddd;
    cursor: not-allowed;
  }

  .error {
    background: #fee;
    color: #c33;
    padding: 0.75rem;
    border-radius: 5px;
    margin-bottom: 1rem;
    border: 1px solid #fcc;
  }

  .dev-notice {
    background: #fff3cd;
    color: #856404;
    padding: 0.5rem;
    border-radius: 5px;
    margin-bottom: 1rem;
    border: 1px solid #ffeaa7;
    text-align: center;
    font-size: 0.9rem;
  }

  p {
    text-align: center;
    margin-top: 1rem;
    color: #666;
  }
</style>
