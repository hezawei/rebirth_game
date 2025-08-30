<script lang="ts">
  import { onMount } from 'svelte'
  import { createClient, type AuthChangeEvent, type Session } from '@supabase/supabase-js'
  import Auth from './Auth.svelte'
  import ProfileForm from './ProfileForm.svelte'
  import IntroAnimation from './IntroAnimation.svelte'

  // Initialize Supabase client
  const supabaseUrl = 'https://wfvgicshdseqdtycofvl.supabase.co'
  const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmdmdpY3NoZHNlcWR0eWNvZnZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU3MDAzMDcsImV4cCI6MjA3MTI1NjMwN30.7oY3rhXDMSNZGKmgkU_nQ3h0Bw2hUbYEaXh4F-D8MaA'
  const supabase = createClient(supabaseUrl, supabaseAnonKey)

  const API_HOST = import.meta.env.VITE_PUBLIC_API_HOST;
  const API_BASE_URL = API_HOST ? `https://${API_HOST}` : 'http://localhost:8000';

  let currentUser: any = null
  let userProfile: any = null
  let showAnimation = false
  let loading = true

  onMount(async () => {
    // 检查当前用户状态
    const { data: { session } } = await supabase.auth.getSession()

    if (session?.user) {
      currentUser = session.user
      await checkUserProfile()
    }

    loading = false

    // 监听认证状态变化
    supabase.auth.onAuthStateChange(async (event: AuthChangeEvent, session: Session | null) => {
      if (event === 'SIGNED_IN' && session?.user) {
        currentUser = session.user
        await checkUserProfile()
      } else if (event === 'SIGNED_OUT') {
        currentUser = null
        userProfile = null
        showAnimation = false
      }
    })
  })

  async function checkUserProfile() {
    if (!currentUser) return

    // 开发模式：检查本地存储中是否有用户资料
    const savedProfile = localStorage.getItem(`profile_${currentUser.id}`)
    if (savedProfile) {
      userProfile = JSON.parse(savedProfile)
      return
    }

    try {
      const { data: session } = await supabase.auth.getSession()
      const token = session.session?.access_token

      if (!token) {
        // 如果没有token，为开发模式创建默认资料
        createDefaultProfile()
        return
      }

      const response = await fetch(`${API_BASE_URL}/users/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        userProfile = await response.json()
      } else {
        // 如果后端请求失败，为开发模式创建默认资料
        createDefaultProfile()
      }
    } catch (error) {
      console.error('获取用户资料失败:', error)
      // 为开发模式创建默认资料
      createDefaultProfile()
    }
  }

  function createDefaultProfile() {
    // 检查用户邮箱是否以dev-user开头（我们的开发模式用户）
    if (currentUser.id.startsWith('dev-user') || currentUser.email) {
      userProfile = {
        id: currentUser.id,
        nickname: currentUser.email.split('@')[0] || '神秘旅人',
        age: 25,
        identity: '重生者',
        photo_url: null,
        created_at: new Date().toISOString()
      }
      // 保存到本地存储
      localStorage.setItem(`profile_${currentUser.id}`, JSON.stringify(userProfile))
    }
  }

  function handleAuthenticated(event: CustomEvent) {
    currentUser = event.detail.user
    checkUserProfile()
  }

  function handleProfileCreated(event: CustomEvent) {
    userProfile = event.detail.user
    // 保存到本地存储
    localStorage.setItem(`profile_${currentUser.id}`, JSON.stringify(userProfile))
  }

  function handleStartAnimation() {
    showAnimation = true
  }

  function handleAnimationComplete(event: CustomEvent) {
    const wish = event.detail.wish
    // 跳转到Streamlit游戏界面
    window.location.href = `http://localhost:8501/?wish=${encodeURIComponent(wish)}&user_id=${currentUser.id}`
  }
</script>

{#if loading}
  <div class="loading">
    <div class="spinner"></div>
    <p>加载中...</p>
  </div>
{:else if showAnimation}
  <IntroAnimation
    {userProfile}
    on:animationComplete={handleAnimationComplete}
  />
{:else if !currentUser}
  <Auth on:authenticated={handleAuthenticated} />
{:else if !userProfile}
  <ProfileForm
    user={currentUser}
    on:profileCreated={handleProfileCreated}
  />
{:else}
  <div class="welcome-container">
    <div class="welcome-card">
      <h1>欢迎回来，{userProfile.nickname}！</h1>
      <p>准备好开始新的重生之旅了吗？</p>

      <div class="user-info">
        {#if userProfile.photo_url}
          <img src={userProfile.photo_url} alt="头像" class="avatar" />
        {/if}
        <div class="info">
          <p><strong>年龄：</strong>{userProfile.age || '未设置'}</p>
          <p><strong>身份：</strong>{userProfile.identity || '神秘存在'}</p>
        </div>
      </div>

      <button class="start-btn" on:click={handleStartAnimation}>
        开始重生之旅
      </button>

      <div class="button-group">
        <button
          class="reset-btn"
          on:click={() => {
            localStorage.removeItem(`profile_${currentUser.id}`)
            userProfile = null
          }}
        >
          🔄 重置资料
        </button>

        <button
          class="logout-btn"
          on:click={() => {
            // 清理本地存储
            localStorage.removeItem(`profile_${currentUser.id}`)
            supabase.auth.signOut()
          }}
        >
          退出登录
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .loading {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255,255,255,0.3);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  .welcome-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
  }

  .welcome-card {
    background: white;
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    text-align: center;
    max-width: 500px;
    width: 100%;
  }

  h1 {
    color: #333;
    margin-bottom: 1rem;
    font-size: 2rem;
  }

  .user-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin: 2rem 0;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 10px;
  }

  .avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid #667eea;
  }

  .info {
    text-align: left;
  }

  .info p {
    margin: 0.5rem 0;
    color: #555;
  }

  .start-btn {
    width: 100%;
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1.2rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    margin-bottom: 1rem;
  }

  .start-btn:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 25px rgba(102,126,234,0.4);
  }

  .logout-btn {
    background: none;
    border: 1px solid #ddd;
    color: #666;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.3s;
  }

  .logout-btn:hover {
    background: #f5f5f5;
    border-color: #999;
  }

  .button-group {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
  }

  .reset-btn {
    background: #ffc107;
    border: none;
    color: #212529;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 0.9rem;
  }

  .reset-btn:hover {
    background: #e0a800;
    transform: translateY(-1px);
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>
