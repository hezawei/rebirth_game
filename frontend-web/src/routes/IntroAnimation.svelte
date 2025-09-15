<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { userStore } from '$lib/stores';
  import { fade } from 'svelte/transition';

  const dispatch = createEventDispatcher();

  let currentStep = 0; // 0: Gateway, 1: Playing Intro, 2: Wish Input, 3: Playing Outro
  let videoSrc = '/开场动画.mp4'; // 恢复原始视频
  let videoPlayer: HTMLVideoElement;
  let showSkipButton = false;
  let wish = ''; // 用于绑定输入框
  let showNarrator = false; // 控制字幕显示

  $: user = $userStore;

  let text1 = '', text2 = '', text3 = '';

  onMount(() => {
    if (user) {
      text1 = `你，是地球online游戏 ${user.age || '未知'} 级用户，你前世是一个 ${user.identity || '未知'}，现在你在前往重生之门的路上`;
      text2 = `${user.nickname || '旅人'}，欢迎你来到重生之门，请说出你希望重生成为什么吧！`;
      text3 = `很好，${user.nickname || '旅人'}，请跳下重生之门，开始这次重生之旅吧！`;
    }
  });

  async function handleStartJourney() {
    currentStep = 1;
    showNarrator = true; // 字幕出现
    // Wait for Svelte to update the DOM and render the video element
    await tick(); 
    try {
      await videoPlayer.play(); // This is now user-initiated, so sound will work
      
      // 5秒后，跳过按钮出现，同时字幕消失
      setTimeout(() => {
        showSkipButton = true;
        showNarrator = false;
      }, 5000);
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
    } else if (currentStep === 3) {
      // 【BUG修复】确保动画正常结束后，也能把wish传递出去
      const finalWish = wish.trim() || '一个随机的冒险者';
      dispatch('complete', { wish: finalWish });
    }
  }

  function handleWishSubmit() {
    if (!wish.trim()) return; // 简单的验证

    currentStep = 3;
    videoSrc = '/穿越动画.mp4';
    // Use a timeout to allow the video src to change before playing
    setTimeout(async () => {
      try {
        await videoPlayer.play();
        setTimeout(() => { showSkipButton = true; }, 5000);
      } catch (err) {
        console.error("Outro video play failed:", err);
        dispatch('complete', { wish });
      }
    }, 100);
  }

  function skipIntro() {
    videoPlayer.pause();
    if (currentStep === 1) {
      // If skipping the first video, go to the wish input screen
      currentStep = 2;
      showSkipButton = false;
    } else if (currentStep === 3) {
      // If skipping the second video, complete the intro
      const finalWish = wish.trim() || '一个随机的冒险者';
      dispatch('complete', { wish: finalWish });
    }
  }
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

  {#if showSkipButton}
    <button class="skip-button" on:click={skipIntro} in:fade>跳过 >></button>
  {/if}

  <div class="overlay">
    {#if currentStep === 1 && showNarrator}
      <p class="narrator" transition:fade={{ duration: 1500 }}>{text1}</p>
    {/if}

    {#if currentStep === 2}
      <div class="dialog-box wish-box" in:fade={{ duration: 1000 }}>
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
          disabled={!wish.trim()}
        >
          开启重生之旅
        </button>
      </div>
    {/if}

    {#if currentStep === 3}
       <p class="narrator" in:fade={{ duration: 1500 }}>{text3}</p>
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
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    /* 垂直居中对齐 */
    align-items: center;
    padding: 2rem;
    box-sizing: border-box;
    pointer-events: none; /* Allow clicks to pass through overlay */
  }

  .overlay > * {
    /* 将内容从底部推上20%的位置，更灵活 */
    margin-top: auto;
    margin-bottom: 30vh;
  }
  
  .dialog-box {
    pointer-events: all; /* But allow interaction with the dialog */
  }

  .narrator {
    color: white;
    font-size: 1.5rem;
    text-align: center;
    background: rgba(0, 0, 0, 0.6);
    padding: 1rem 2rem;
    border-radius: 10px;
    max-width: 80%;
    text-shadow: 2px 2px 4px black;
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
</style>
