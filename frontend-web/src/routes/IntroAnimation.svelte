<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte'
  import { gsap } from 'gsap'

  const dispatch = createEventDispatcher()

  export let userProfile: any

  let wish = ''
  let showWishInput = false
  let animationContainer: HTMLElement
  let soul: HTMLElement
  let mentor: HTMLElement
  let wishInputContainer: HTMLElement

  onMount(() => {
    startIntroAnimation()
  })

  function startIntroAnimation() {
    const tl = gsap.timeline()

    // 步骤1：近景聚焦灵魂小人面部
    tl.set(soul, { scale: 5, opacity: 1 })
    tl.to(soul, { 
      scale: 1, 
      duration: 3, 
      ease: "power2.out",
      onComplete: () => {
        // 显示旁白
        showNarration(`你，是地球online游戏${userProfile.age || '??'}级用户，你前世是一个${userProfile.identity || '神秘存在'}，现在你在前往重生之门的路上`)
      }
    })

    // 步骤2：镜头拉远，显示电梯和其他灵魂
    tl.to(soul, { 
      x: -200, 
      duration: 2, 
      ease: "power2.inOut" 
    })
    tl.from(".other-souls", { 
      opacity: 0, 
      x: 100, 
      duration: 1.5, 
      stagger: 0.2 
    }, "-=1")

    // 步骤3：导师出现
    tl.from(mentor, { 
      opacity: 0, 
      y: 50, 
      scale: 0.8,
      duration: 2, 
      ease: "back.out(1.7)",
      onComplete: () => {
        showMentorDialog()
      }
    })
  }

  function showNarration(text: string) {
    // 显示旁白文字动画
    const narration = document.querySelector('.narration')
    if (narration) {
      narration.textContent = text
      gsap.from(narration, { opacity: 0, y: 20, duration: 1 })
    }
  }

  function showMentorDialog() {
    showWishInput = true
    gsap.from(wishInputContainer, { 
      opacity: 0, 
      scale: 0.8, 
      duration: 1, 
      ease: "back.out(1.7)" 
    })
  }

  function handleWishSubmit() {
    if (!wish.trim()) return

    // 步骤4：导师回应
    showNarration(`很好，${userProfile.nickname}，请跳下重生之门，开始这次重生之旅吧！`)

    // 步骤5：跳下重生之门动画
    const tl = gsap.timeline()
    
    tl.to(soul, { 
      y: 1000, 
      rotation: 360, 
      scale: 0.5,
      duration: 4, 
      ease: "power2.in" 
    })
    tl.to(mentor, { 
      opacity: 0, 
      duration: 1 
    }, "-=2")
    tl.to(".other-souls", { 
      opacity: 0, 
      duration: 1 
    }, "-=2")

    // 步骤6：黑屏过渡
    tl.to(animationContainer, { 
      opacity: 0, 
      duration: 2,
      onComplete: () => {
        dispatch('animationComplete', { wish })
      }
    })
  }

  function handleRandomWish() {
    const randomWishes = [
      '成为一名拯救世界的英雄',
      '拥有改变命运的魔法力量',
      '在异世界开启全新人生',
      '成为传说中的冒险者',
      '获得不朽的智慧与力量'
    ]
    wish = randomWishes[Math.floor(Math.random() * randomWishes.length)]
    handleWishSubmit()
  }
</script>

<div class="animation-container" bind:this={animationContainer}>
  <!-- 背景 -->
  <div class="background">
    <div class="stars"></div>
    <div class="elevator-path"></div>
  </div>

  <!-- 灵魂小人 -->
  <div class="soul" bind:this={soul}>
    <div class="soul-body"></div>
    <div class="soul-glow"></div>
  </div>

  <!-- 其他灵魂小人 -->
  <div class="other-souls">
    {#each Array(5) as _, i}
      <div class="other-soul" style="animation-delay: {i * 0.5}s"></div>
    {/each}
  </div>

  <!-- 导师 -->
  <div class="mentor" bind:this={mentor}>
    <div class="mentor-body"></div>
    <div class="mentor-aura"></div>
  </div>

  <!-- 重生之门 -->
  <div class="rebirth-gate">
    <div class="gate-frame"></div>
    <div class="gate-portal"></div>
  </div>

  <!-- 旁白 -->
  <div class="narration"></div>

  <!-- 愿望输入 -->
  {#if showWishInput}
    <div class="wish-input-container" bind:this={wishInputContainer}>
      <div class="mentor-dialog">
        <p>{userProfile.nickname}，欢迎你来到重生之门，请说出你希望重生成为什么吧！</p>
      </div>
      
      <div class="wish-form">
        <textarea
          bind:value={wish}
          placeholder="输入你的重生愿望..."
          rows="3"
        ></textarea>
        
        <div class="wish-buttons">
          <button 
            on:click={handleWishSubmit}
            disabled={!wish.trim()}
            class="submit-btn"
          >
            确认愿望
          </button>
          <button 
            on:click={handleRandomWish}
            class="random-btn"
          >
            随机模式
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .animation-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: linear-gradient(180deg, #0a0a2e 0%, #16213e 50%, #1a1a3a 100%);
    overflow: hidden;
    z-index: 1000;
  }

  .background {
    position: absolute;
    width: 100%;
    height: 100%;
  }

  .stars {
    position: absolute;
    width: 100%;
    height: 100%;
    background: radial-gradient(2px 2px at 20px 30px, #eee, transparent),
                radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
                radial-gradient(1px 1px at 90px 40px, #fff, transparent),
                radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
    background-repeat: repeat;
    background-size: 200px 100px;
    animation: twinkle 4s infinite;
  }

  .elevator-path {
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 200px;
    height: 80%;
    background: linear-gradient(to top, 
      rgba(255,255,255,0.1) 0%, 
      rgba(255,255,255,0.05) 50%, 
      transparent 100%);
    border-left: 2px solid rgba(255,255,255,0.2);
    border-right: 2px solid rgba(255,255,255,0.2);
  }

  .soul {
    position: absolute;
    bottom: 20%;
    left: 50%;
    transform: translateX(-50%);
    width: 60px;
    height: 80px;
    z-index: 10;
  }

  .soul-body {
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, #87ceeb 0%, #4682b4 100%);
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    position: relative;
  }

  .soul-body::before {
    content: '';
    position: absolute;
    top: 10%;
    left: 20%;
    width: 60%;
    height: 30%;
    background: radial-gradient(circle, #fff 0%, transparent 70%);
    border-radius: 50%;
    opacity: 0.8;
  }

  .soul-glow {
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    background: radial-gradient(circle, rgba(135,206,235,0.4) 0%, transparent 70%);
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  .other-souls {
    position: absolute;
    bottom: 15%;
    right: 20%;
    display: flex;
    flex-direction: column;
    gap: 30px;
  }

  .other-soul {
    width: 30px;
    height: 40px;
    background: radial-gradient(circle, rgba(135,206,235,0.6) 0%, rgba(70,130,180,0.6) 100%);
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    opacity: 0.7;
    animation: float 3s infinite ease-in-out;
  }

  .mentor {
    position: absolute;
    top: 20%;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 150px;
    opacity: 0;
  }

  .mentor-body {
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, #ffd700 0%, #ff8c00 100%);
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    position: relative;
  }

  .mentor-aura {
    position: absolute;
    top: -20px;
    left: -20px;
    right: -20px;
    bottom: -20px;
    background: radial-gradient(circle, rgba(255,215,0,0.3) 0%, transparent 70%);
    border-radius: 50%;
    animation: pulse 1.5s infinite;
  }

  .rebirth-gate {
    position: absolute;
    top: 10%;
    left: 50%;
    transform: translateX(-50%);
    width: 200px;
    height: 300px;
  }

  .gate-frame {
    width: 100%;
    height: 100%;
    border: 4px solid #ffd700;
    border-radius: 20px;
    background: linear-gradient(45deg, 
      rgba(255,215,0,0.1) 0%, 
      rgba(255,140,0,0.1) 100%);
    box-shadow: 0 0 30px rgba(255,215,0,0.5);
  }

  .gate-portal {
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    bottom: 10px;
    background: radial-gradient(circle, 
      rgba(0,0,0,0.8) 0%, 
      rgba(25,25,112,0.6) 50%, 
      transparent 100%);
    border-radius: 15px;
    animation: portal-swirl 4s infinite linear;
  }

  .narration {
    position: absolute;
    bottom: 10%;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 1rem 2rem;
    border-radius: 10px;
    font-size: 1.1rem;
    text-align: center;
    max-width: 80%;
    backdrop-filter: blur(10px);
  }

  .wish-input-container {
    position: absolute;
    bottom: 20%;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(255,255,255,0.95);
    padding: 2rem;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    max-width: 500px;
    width: 90%;
    backdrop-filter: blur(10px);
  }

  .mentor-dialog {
    margin-bottom: 1.5rem;
    text-align: center;
  }

  .mentor-dialog p {
    color: #333;
    font-size: 1.1rem;
    margin: 0;
  }

  .wish-form textarea {
    width: 100%;
    padding: 1rem;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 1rem;
    resize: vertical;
    margin-bottom: 1rem;
  }

  .wish-form textarea:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
  }

  .wish-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
  }

  .submit-btn, .random-btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s;
  }

  .submit-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .submit-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102,126,234,0.4);
  }

  .submit-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  .random-btn {
    background: linear-gradient(135deg, #ffd700 0%, #ff8c00 100%);
    color: #333;
  }

  .random-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(255,215,0,0.4);
  }

  @keyframes twinkle {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.1); opacity: 1; }
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }

  @keyframes portal-swirl {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style>
