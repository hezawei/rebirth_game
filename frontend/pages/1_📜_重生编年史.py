# frontend/pages/1_📜_重生编年史.py
import streamlit as st
import requests
from datetime import datetime
import os  # 【<<< 新增这一行导入】
import time  # 【新增】用于时间延迟

# 【新增】从主应用复制 BACKEND_URL，避免硬编码
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# 【修改】缩短缓存时间，并添加版本控制
@st.cache_data(ttl=10)  # 缓存10秒，更快响应数据变化
def get_session_details(session_id: int, cache_version: int = 0):
    """获取并缓存单个游戏的详细历史"""
    detail_res = requests.get(f"{BACKEND_URL}/story/sessions/{session_id}")
    detail_res.raise_for_status()
    return detail_res.json()

st.set_page_config(page_title="重生编年史", layout="wide")

# 页面标题和刷新按钮
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("📜 重生编年史")
with col_refresh:
    if st.button("🔄 刷新数据", use_container_width=True):
        # 清除缓存并更新版本
        get_session_details.clear()
        if 'cache_version' not in st.session_state:
            st.session_state.cache_version = 0
        st.session_state.cache_version += 1
        st.success("✅ 数据已刷新")
        st.rerun()

st.markdown("---")

# 【新增】一个统一的状态更新函数，这是本次修复的关键
def update_game_state_from_segment(segment_data: dict):
    """从后端返回的 segment 数据，原子性地更新所有相关的 session_state"""
    st.session_state.game_started = True
    st.session_state.session_id = segment_data['session_id']
    st.session_state.node_id = segment_data['node_id']
    st.session_state.current_segment = segment_data
    st.session_state.chapter_count = segment_data.get('metadata', {}).get('chapter_number', 1)

    # 非常重要：重置故事历史，只保留当前这一段，因为历史将从后端重新构建
    st.session_state.story_history = [{"role": "assistant", "content": segment_data['text']}]

# 【核心修改】handle_retry 函数的 info 提示
def handle_retry(node_id: int, session_id: int, chapter_num: int):
    """处理 '从这里重来' 的点击事件"""
    try:
        st.info(f"🚀 正在准备时光机，返回到第 {chapter_num} 章...")  # 使用章节号提示用户

        st.session_state.is_retrying = True
        st.session_state.retry_target_node_id = node_id
        st.rerun()

    except Exception as e:
        st.error(f"页面重绘失败: {e}")

# 【新增】初始化缓存版本
if 'cache_version' not in st.session_state:
    st.session_state.cache_version = 0

try:
    response = requests.get(f"{BACKEND_URL}/story/sessions")
    response.raise_for_status()
    sessions = response.json()

    if not sessions:
        st.info("暂无历史记录，快去开启一段新的人生吧！")
    else:
        for session in sessions:
            # 【优化】解析日期并格式化
            created_time = datetime.fromisoformat(session['created_at']).strftime('%Y-%m-%d %H:%M')
            with st.expander(f"**{session['wish']}** - *开始于: {created_time}*"):
                try:
                    # 【修复】使用缓存版本控制，确保数据同步
                    nodes = get_session_details(session['id'], st.session_state.cache_version)
                    # 【优化】使用 st.container 增加视觉分隔
                    for node in nodes:
                        with st.container():
                            chapter_num = node.get('chapter_number', '未知')

                            col_header, col_button = st.columns([4, 1])
                            with col_header:
                                st.markdown(f"#### 📜 第 {chapter_num} 章")

                            # 【核心修改】现在任何章节都可以重来，因为是停留在本章
                            with col_button:
                                is_retrying_this_node = st.session_state.get('is_retrying', False) and \
                                                        st.session_state.get('retry_target_node_id') == node['id']

                                # 将文案改回更有感觉的 "从这里重来"
                                retry_button_text = "⏪ 从这里重来"

                                if is_retrying_this_node:
                                    st.button(
                                        "⏳ 时光回溯中...",
                                        key=f"retry_{node['id']}",
                                        use_container_width=True,
                                        disabled=True
                                    )
                                else:
                                    if st.button(
                                        retry_button_text,
                                        key=f"retry_{node['id']}",
                                        use_container_width=True,
                                        # 如果一个章节没有选项（即结局），则不允许重来
                                        disabled=not node.get('choices', [])
                                    ):
                                        handle_retry(node['id'], session['id'], chapter_num)

                            # 显示图片和文字的 col1, col2 逻辑
                            col1, col2 = st.columns([1, 2])

                            with col1:
                                image_url = node.get('image_url')
                                if image_url and image_url.startswith('/static/'):
                                    full_image_url = f"{BACKEND_URL}{image_url}"
                                    st.image(full_image_url, caption=f"场景图 #{chapter_num}", use_container_width=True)
                                else:
                                    # 如果没有图片或URL格式不对，显示一个占位符
                                    st.markdown('<div class="chronicle-image-placeholder">🖼️</div>', unsafe_allow_html=True)

                            with col2:
                                st.markdown(f'<div class="chronicle-text">{node["text"]}</div>', unsafe_allow_html=True)

                            # 显示用户选择
                            if node.get('user_choice'):
                                st.caption(f"你的选择: {node['user_choice']}")

                            st.markdown("---")
                except requests.exceptions.RequestException as e:
                    st.error(f"加载详细历史失败: {e}")

except requests.exceptions.RequestException as e:
    st.error(f"无法连接后端服务加载历史记录: {e}")

# 【新增】在文件的末尾，增加一个检查块来执行API请求
# 这是为了确保在UI更新后再执行耗时操作，体验更好
if st.session_state.get('is_retrying') and 'retry_api_called' not in st.session_state:
    node_id = st.session_state.retry_target_node_id
    try:
        response = requests.post(f"{BACKEND_URL}/story/retry", json={"node_id": node_id})
        response.raise_for_status()

        # 【核心修改】现在返回的是目标节点本身，而不是父节点
        target_node_data = response.json()

        # 清理缓存
        get_session_details.clear()
        st.session_state.cache_version += 1

        # 使用我们的原子函数来更新状态
        update_game_state_from_segment(target_node_data)

        st.session_state.retry_api_called = True  # 标记API已调用
        st.success("✅ 时空道标锁定！正在跳转...")
        time.sleep(1)  # 让用户看到成功提示
        st.switch_page("app.py")

    except requests.exceptions.RequestException as e:
        st.error(f"时空回溯失败: {e}")
        st.session_state.is_retrying = False
        st.session_state.retry_target_node_id = None
