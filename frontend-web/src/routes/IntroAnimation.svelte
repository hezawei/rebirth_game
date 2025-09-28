<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { userStore } from '$lib/stores';
  import { api } from '$lib/apiService';
  import { fade } from 'svelte/transition';

  const dispatch = createEventDispatcher();

  let currentStep = 0; // 0: Gateway, 1: Playing Intro, 2: Wish Input, 3: Playing Outro
  let videoSrc = '/starting.webm'; // 使用webm格式
  let videoPlayer: HTMLVideoElement;
  let showSkipButton = false;
  let wish = ''; // 用于绑定输入框
  let wishChecking = false; // 愿望校验中
  let wishError: string = '';
  let wishBoxEl: HTMLDivElement;
  let wishVisible = false;
  let preparedLevel: any = null;

  $: user = $userStore;

  let text2 = '';

  onMount(() => {
    if (user) {
      text2 = `${user.nickname || '旅人'}，欢迎你来到重生之门，请说出你希望重生成为什么吧！`;
    }
  });

  async function handleStartJourney() {
    preparedLevel = null;
    wishError = '';
    currentStep = 1;
    // Wait for Svelte to update the DOM and render the video element
    await tick(); 
    try {
      await videoPlayer.play(); // This is now user-initiated, so sound will work
      // 1秒后允许跳过第一段
      setTimeout(() => { showSkipButton = true; }, 1000);
    } catch (err) {
      console.error("Video play failed:", err);
      // If play fails, skip the animation
      dispatch('complete', { wish: '一个随机的冒险者' });
    }
  }

  function handleVideoEnd() {
    if (currentStep === 1) {
      currentStep = 2;
      showSkipButton = false; // Hide skip button for the next phase
      wishVisible = false;
      // defer visibility until layout is stable to avoid flicker
      measurePositions('enter step 2');
      requestAnimationFrame(() => {
        console.debug('[Intro] showing wish box after RAF');
        wishVisible = true;
      });
    } else if (currentStep === 3) {
      // 【BUG修复】确保动画正常结束后，也能把wish传递出去
      const finalWish = wish.trim() || '一个随机的冒险者';
      dispatch('complete', { wish: finalWish, level: preparedLevel });
    }
  }

  async function handleWishSubmit() {
    const trimmed = wish.trim();
    if (!trimmed || wishChecking) return;

    wishError = '';
    preparedLevel = null;
    wishChecking = true;

    let prep: any = null;
    try {
      prep = await api.prepareStart(trimmed);
    } catch (err: any) {
      wishError = err?.message || '关卡生成失败，请换一个愿望试试';
    } finally {
      wishChecking = false;
    }

    if (!prep) {
      return;
    }

    preparedLevel = prep;

    currentStep = 3;
    videoSrc = '/interact_1.webm';
    showSkipButton = false;
    setTimeout(async () => {
      try {
        await videoPlayer.play();
      } catch (err) {
        console.error("Outro video play failed:", err);
        dispatch('complete', { wish });
      }
    }, 100);
  }

  function skipIntro() {
    videoPlayer.pause();
    // 第一段：跳过后直接进入愿望输入阶段
    if (currentStep === 1) {
      currentStep = 2;
      showSkipButton = false;
      wishVisible = false;
      measurePositions('skip to step 2');
      requestAnimationFrame(() => {
        console.debug('[Intro] showing wish box after RAF (skip)');
        wishVisible = true;
      });
      return;
    }
    // 第三段（穿越动画）：跳过后完成并将愿望传递给父组件
    if (currentStep === 3) {
      const finalWish = wish.trim() || '一个随机的冒险者';
      dispatch('complete', { wish: finalWish, level: preparedLevel });
    }
  }

  function logRect(label: string, el?: Element | null) {
    try {
      if (!el) return console.debug(`[Intro][rect] ${label}: <null>`);
      const r = (el as HTMLElement).getBoundingClientRect();
      console.debug(`[Intro][rect] ${label}:`, { x: r.x, y: r.y, left: r.left, top: r.top, width: r.width, height: r.height });
    } catch (e) {
      console.debug(`[Intro][rect] ${label}: error`, e);
    }
  }

  async function measurePositions(tag: string) {
    await tick();
    requestAnimationFrame(() => {
      console.debug(`[Intro][measure RAF] ${tag}`);
      logRect('video', videoPlayer);
      logRect('wishBox', wishBoxEl);
    });
  }

  $: if (currentStep === 1) { measurePositions('step=1'); }
  $: if (currentStep === 2) { measurePositions('step=2'); }
  $: if (currentStep === 3) { measurePositions('step=3'); }
</script>

<div class="animation-container">
  {#if currentStep === 0}
    <div class="gateway" in:fade>
      <img src="/rebirth_gate_placeholder.png" alt="重生之门" class="gateway-image" />
      <button class="gateway-button" on:click={handleStartJourney}>▷ 开启你的重生之旅</button>
    </div>
  {/if}

  {#if currentStep > 0}
    <!-- svelte-ignore a11y-media-has-caption -->
    <video 
      bind:this={videoPlayer}
      src={videoSrc} 
      on:ended={handleVideoEnd}
      playsinline
    ></video>
  {/if}

  {#if showSkipButton && currentStep === 1}
    <button class="skip-button" on:click={skipIntro} in:fade>跳过 >></button>
  {/if}

  <div class="overlay">
    {#if currentStep === 2}
      {#if wishVisible}
      <div class="dialog-box wish-box wish-pos" bind:this={wishBoxEl}>
        <p>{text2}</p>
        <input 
          type="text" 
          bind:value={wish} 
          placeholder="输入你的愿望..." 
          class="wish-input"
        />
        <button 
          on:click={handleWishSubmit} 
          class="wish-submit-button"
          disabled={!wish.trim() || wishChecking}
        >
          {wishChecking ? '正在校验...' : '开启重生之旅'}
        </button>
        {#if wishError}
          <div class="wish-error">{wishError}</div>
        {/if}
        <div class="links-row">
          <a href="/chronicle" class="history-link">📜 历史重生记录</a>
        </div>
      </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .animation-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: black;
    z-index: 100;
    /* 通过内边距在垂直方向上压缩视频容器，从而露出视频的硬字幕 */
    box-sizing: border-box;
    padding: 5vh 0; /* 上下各留出5%的黑边 */
  }

  .gateway {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: #0E1117;
  }

  .gateway-image {
    width: 100%;
    max-width: 500px;
    height: auto;
    border-radius: 15px;
    box-shadow: 0 8px 32px rgba(108, 99, 255, 0.3);
  }

  .gateway-button {
    margin-top: 2rem;
    padding: 1rem 2.5rem;
    font-size: 1.5rem;
    background-color: rgba(108, 99, 255, 0.8);
    color: white;
    border: 1px solid #6C63FF;
    border-radius: 50px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-shadow: 1px 1px 2px black;
  }
  .gateway-button:hover {
    background-color: #6C63FF;
    transform: scale(1.05);
  }

  video {
    /* 移除绝对定位和object-fit，让视频在有内边距的父容器中自适应 */
    width: 100%;
    height: 100%;
    object-fit: contain; /* 保持视频的宽高比，自动产生黑边 */
  }

  .skip-button {
    position: absolute;
    top: 2rem;
    right: 2rem;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.5);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    cursor: pointer;
    z-index: 110;
  }
  .skip-button:hover {
    background: rgba(0, 0, 0, 0.8);
  }

  .overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    padding: 2rem;
    box-sizing: border-box;
    pointer-events: none; /* Allow clicks to pass through overlay */
  }

  .wish-pos {
    position: absolute;
    left: 50%;
    transform: translate3d(-50%, 0, 0);
    bottom: 30vh;
    width: calc(100% - 4rem);
    max-width: 600px;
    will-change: transform;
  }
  
  .dialog-box {
    pointer-events: all; /* But allow interaction with the dialog */
  }

  .dialog-box {
    color: white;
    font-size: 1.5rem;
    text-align: center;
    background: rgba(0, 0, 0, 0.7);
    padding: 2rem;
    border-radius: 15px;
    border: 1px solid rgba(108, 99, 255, 0.5);
    max-width: 600px;
  }

  .wish-box {
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
  }

  .wish-input {
    width: 100%;
    padding: 0.75rem;
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(108, 99, 255, 0.5);
    color: white;
    border-radius: 10px;
    font-size: 1rem;
    margin: 1rem 0;
    box-sizing: border-box;
  }

  .wish-submit-button {
    width: 100%;
    padding: 0.75rem;
    font-size: 1.1rem;
    background-color: rgba(108, 99, 255, 0.8);
    color: white;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    transition: background-color 0.3s;
  }
  .wish-submit-button:hover:not(:disabled) {
    background-color: #6C63FF;
  }
  .wish-submit-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .links-row {
    margin-top: 1rem;
    display: flex;
    justify-content: center;
  }
  .history-link {
    color: #FFD700;
    text-decoration: none;
    font-weight: bold;
  }
  .wish-error {
    margin-top: 0.5rem;
    color: #ff6b6b;
    font-size: 0.95rem;
  }
</style>
