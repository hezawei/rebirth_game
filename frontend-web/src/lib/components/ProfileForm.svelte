<script lang="ts">
  import { createEventDispatcher } from 'svelte'

  export let user: any
  const dispatch = createEventDispatcher()

  let nickname = ''
  let age: number | null = null
  let identity = ''
  let photoFile: File | null = null
  let loading = false
  let error = ''

  async function handleSubmit() {
    if (!nickname.trim()) {
      error = '请输入昵称'
      return
    }

    loading = true
    error = ''

    try {
      let photoUrl = ''

      // 暂时跳过照片上传功能，直接使用空字符串
      // TODO: 需要在Supabase中创建avatars bucket后再启用
      if (photoFile) {
        console.log('照片上传功能暂时禁用，等待Supabase bucket配置')
        photoUrl = '' // 暂时设为空
      }

      // 暂时跳过后端API调用，直接使用本地数据
      // TODO: 修复JWT验证后再启用后端API
      const userData = {
        id: user.id,
        nickname: nickname.trim(),
        age: age,
        identity: identity.trim() || null,
        photo_url: photoUrl || null,
        created_at: new Date().toISOString()
      }

      console.log('用户资料（暂存本地）:', userData)
      dispatch('profileCreated', { user: userData })

    } catch (err: any) {
      error = err.message
    } finally {
      loading = false
    }
  }

  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement
    if (target.files && target.files[0]) {
      photoFile = target.files[0]
    }
  }
</script>

<div class="profile-container">
  <div class="profile-card">
    <h2>完善个人资料</h2>
    <p class="subtitle">请填写您的基本信息，开始重生之旅</p>

    {#if error}
      <div class="error">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="nickname">昵称 *</label>
        <input
          id="nickname"
          type="text"
          bind:value={nickname}
          placeholder="请输入您的昵称"
          required
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="age">年龄</label>
        <input
          id="age"
          type="number"
          bind:value={age}
          placeholder="请输入您的年龄"
          min="1"
          max="150"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="identity">身份</label>
        <input
          id="identity"
          type="text"
          bind:value={identity}
          placeholder="例如：学生、程序员、设计师等"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="photo">个人照片</label>
        <input
          id="photo"
          type="file"
          accept="image/*"
          on:change={handleFileChange}
          disabled={loading}
        />
        <small>支持 JPG、PNG 格式，文件大小不超过 5MB</small>
      </div>

      <button type="submit" disabled={loading || !nickname.trim()}>
        {loading ? '创建中...' : '开始重生之旅'}
      </button>
    </form>
  </div>
</div>

<style>
  .profile-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
  }

  .profile-card {
    background: white;
    padding: 2rem;
    border-radius: 15px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    width: 100%;
    max-width: 500px;
  }

  h2 {
    text-align: center;
    margin-bottom: 0.5rem;
    color: #333;
    font-size: 1.8rem;
  }

  .subtitle {
    text-align: center;
    color: #666;
    margin-bottom: 2rem;
    font-size: 0.9rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
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
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.3s, box-shadow 0.3s;
  }

  input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  input[type="file"] {
    padding: 0.5rem;
  }

  small {
    display: block;
    margin-top: 0.25rem;
    color: #888;
    font-size: 0.8rem;
  }

  button[type="submit"] {
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  button[type="submit"]:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
  }

  button[type="submit"]:disabled {
    background: #ccc;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }

  .error {
    background: #fee;
    color: #c33;
    padding: 0.75rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border: 1px solid #fcc;
    text-align: center;
  }
</style>
