"""
重生之我是…… - Streamlit前端应用
第二阶段：核心体验版
"""

import streamlit as st
import requests
import json
import time
import os
from typing import Dict, Any, Optional

# 配置
BACKEND_URL = "http://127.0.0.1:8000"  # FastAPI后端地址

# 页面配置
st.set_page_config(
    page_title="重生之我是……",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 函数：载入本地CSS
def local_css(file_name):
    """载入本地CSS文件"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            css_content = f.read()
            print(f"📄 CSS文件大小: {len(css_content)} 字符")  # 调试信息
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            print("✅ CSS已注入到页面")  # 调试信息
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试GBK编码
        with open(file_name, 'r', encoding='gbk') as f:
            css_content = f.read()
            print(f"📄 CSS文件大小(GBK): {len(css_content)} 字符")  # 调试信息
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            print("✅ CSS已注入到页面(GBK)")  # 调试信息
    except Exception as e:
        st.error(f"加载CSS文件失败: {e}")
        print(f"❌ CSS加载失败: {e}")  # 调试信息

# 函数：载入本地JavaScript


# 载入自定义CSS
css_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(css_path):
    local_css(css_path)



# 注意：所有CSS样式现在都在styles.css文件中定义，避免重复和冲突

# 初始化会话状态
def init_session_state():
    """初始化会话状态"""
    if 'game_started' not in st.session_state:
        st.session_state.game_started = False
    if 'story_history' not in st.session_state:
        st.session_state.story_history = []
    if 'current_segment' not in st.session_state:
        st.session_state.current_segment = None
    if 'chapter_count' not in st.session_state:
        st.session_state.chapter_count = 0
    if 'sidebar_visible' not in st.session_state:
        st.session_state.sidebar_visible = True  # 默认为可见
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'node_id' not in st.session_state:
        st.session_state.node_id = None
    # 【新增】在 init_session_state 中也清理一下，确保万无一失
    if 'is_retrying' not in st.session_state:
        st.session_state.is_retrying = False
    if 'retry_target_node_id' not in st.session_state:
        st.session_state.retry_target_node_id = None

def make_api_request(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """发送API请求"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/{endpoint}",
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ 无法连接到后端服务，请确保后端服务正在运行")
        st.stop()
    except requests.exceptions.Timeout:
        st.error("⏰ 请求超时，请稍后重试")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ API请求失败: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ 未知错误: {e}")
        st.stop()

def display_story_segment(segment: Dict[str, Any]):
    """显示故事片段"""
    # 显示图片
    image_url = segment.get('image_url', '')

    if image_url:
        # 直接使用后端返回的URL，构建完整的图片URL
        if image_url.startswith('/static/'):
            # 后端返回的静态文件路径
            full_image_url = f"http://localhost:8000{image_url}"
        elif image_url.startswith('/assets/'):
            # 兼容旧的assets路径，转换为static路径
            image_filename = os.path.basename(image_url)
            full_image_url = f"http://localhost:8000/static/{image_filename}"
        else:
            # 外部URL或其他格式
            full_image_url = image_url

        # 使用纯HTML img标签显示图片，完全避免Streamlit的图片组件
        st.markdown(
            f'<img src="{full_image_url}" class="story-image" alt="故事图片">',
            unsafe_allow_html=True
        )
    else:
        # 没有图片时显示占位符
        st.markdown(
            '<div class="story-image-placeholder">📖 故事继续...</div>',
            unsafe_allow_html=True
        )

    # 显示故事文本（使用新的CSS样式）
    story_text = segment.get('text', '')
    st.markdown(f"""
    <div class="story-text-container">
        {story_text}
    </div>
    """, unsafe_allow_html=True)

def display_choices(choices: list) -> Optional[str]:
    """显示选择按钮并返回用户选择"""
    if not choices:
        return None

    # 创建列布局
    cols = st.columns(len(choices))

    for i, choice in enumerate(choices):
        if cols[i].button(
            choice,
            key=f"choice_{i}_{st.session_state.chapter_count}",
            use_container_width=True
        ):
            return choice

    return None

def start_new_story(wish: str):
    """开始新故事"""
    with st.spinner("🌟 重生之门正在开启，请稍候..."):
        # 添加一些戏剧性的等待时间
        time.sleep(1)

        data = make_api_request("story/start", {"wish": wish})

        # 保存session_id和node_id
        st.session_state.session_id = data['session_id']
        st.session_state.node_id = data['node_id']
        st.session_state.current_segment = data
        st.session_state.story_history.append({
            "role": "assistant",
            "content": data['text']
        })
        st.session_state.game_started = True
        # 【核心修改】完全信任后端返回的章节号
        st.session_state.chapter_count = data.get('metadata', {}).get('chapter_number', 1)
        st.success("✨ 重生成功！你的新生活开始了...")
        time.sleep(1)
        st.rerun()

def continue_story(choice: str):
    """继续故事"""
    with st.spinner("⚡ 命运的齿轮正在转动..."):
        # 添加一些戏剧性的等待时间
        time.sleep(1)

        # 使用新的API格式发送请求
        data = make_api_request("story/continue", {
            "session_id": st.session_state.session_id,
            "node_id": st.session_state.node_id,
            "choice": choice
        })

        # 更新node_id
        st.session_state.node_id = data['node_id']
        st.session_state.current_segment = data
        st.session_state.story_history.append({
            "role": "assistant",
            "content": data['text']
        })
        # 【核心修改】同样，完全信任后端返回的章节号
        st.session_state.chapter_count = data.get('metadata', {}).get('chapter_number', st.session_state.chapter_count)
        st.success(f"📖 第{st.session_state.chapter_count}章展开...")
        time.sleep(1)
        st.rerun()

def reset_game():
    """重置游戏"""
    st.session_state.game_started = False
    st.session_state.story_history = []
    st.session_state.current_segment = None
    st.session_state.chapter_count = 0
    st.session_state.session_id = None
    st.session_state.node_id = None
    st.success("🔄 游戏已重置")
    time.sleep(1)
    st.rerun()

def auto_start_game(wish: str, user_id: str):
    """根据URL参数自动开始游戏"""
    with st.spinner("🚀 正在为您开启重生之旅..."):
        # 添加一些戏剧性的等待时间
        time.sleep(1)

        data = make_api_request("story/start", {"wish": wish, "user_id": user_id})

        # 保存session_id和node_id
        st.session_state.session_id = data['session_id']
        st.session_state.node_id = data['node_id']
        st.session_state.current_segment = data
        st.session_state.story_history.append({
            "role": "assistant",
            "content": data['text']
        })
        st.session_state.game_started = True
        # 【核心修改】完全信任后端返回的章节号
        st.session_state.chapter_count = data.get('metadata', {}).get('chapter_number', 1)
        st.toast(f"🎉 欢迎来到重生世界！您的愿望：{wish}", icon="✨")
        time.sleep(1)
        st.rerun()

# 主应用逻辑
def main():
    """主应用函数"""
    init_session_state()

    # 【核心修改】检查 URL 参数
    query_params = st.query_params
    wish_from_url = query_params.get("wish")
    user_id_from_url = query_params.get("user_id")

    if wish_from_url and user_id_from_url and not st.session_state.game_started:
        # 如果 URL 提供了愿望和用户ID，并且游戏尚未开始，则自动开始游戏
        auto_start_game(wish_from_url, user_id_from_url)

    # 【核心修改】重置编年史页面留下的标志位
    if 'retry_api_called' in st.session_state:
        del st.session_state.retry_api_called

    if st.session_state.get('is_retrying'):
        st.toast(f"已成功回溯到第 {st.session_state.get('chapter_count')} 章！", icon="⏪")
        st.session_state.is_retrying = False
        st.session_state.retry_target_node_id = None

    # 标题
    st.markdown('<h1 class="main-title">🌟 重生之我是…… 🌟</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">一个由AI驱动的互动故事游戏 (核心体验版 V0.2)</p>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        # 新增自己的折叠按钮
        if st.button("⬅️ 收起侧边栏" if st.session_state.sidebar_visible else "➡️ 展开侧边栏", use_container_width=True):
            st.session_state.sidebar_visible = not st.session_state.sidebar_visible
            st.rerun()

        # 只有在 sidebar_visible 为 True 时才渲染侧边栏的其他内容
        if st.session_state.sidebar_visible:
            st.markdown("### 🔧 CSS调试信息")
            st.success("✅ 侧边栏正在显示！")
            st.info("如果你看到这个，说明侧边栏工作正常")
            st.markdown("---")

            st.header("🎮 游戏控制")

            if st.session_state.game_started:
                st.metric("📚 当前章节", st.session_state.chapter_count)
                st.metric("💬 对话轮数", len(st.session_state.story_history))

                if st.button("🔄 重新开始", use_container_width=True):
                    reset_game()

            st.markdown("---")
            st.markdown("### 📖 游戏说明")
            st.markdown("""
            1. 输入你的重生愿望
            2. AI将为你生成独特的故事
            3. 在关键时刻做出选择
            4. 体验不同的人生轨迹
            """)

            st.markdown("---")
            st.markdown("### ⚙️ 技术栈")
            st.markdown("""
            - **后端**: FastAPI + Python
            - **前端**: Streamlit
            - **AI**: OpenAI GPT (可配置)
            - **架构**: 微服务 + RESTful API
            """)
    
    # 主内容区域
    if not st.session_state.game_started:
        # 游戏开始界面
        _, col2, _ = st.columns([1, 2, 1])

        with col2:
            # 显示重生之门图片
            gate_image_filename = "rebirth_gate_placeholder.png"
            gate_image_url = f"http://localhost:8000/static/{gate_image_filename}"

            # 检查图片文件是否存在
            gate_image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "images", gate_image_filename)
            if os.path.exists(gate_image_path):
                st.markdown(
                    f'<img src="{gate_image_url}" class="main-gate-image" alt="重生之门">',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="gate-placeholder">🚪 重生之门即将开启...</div>',
                    unsafe_allow_html=True
                )

            st.markdown("## 🚪 重生之旅开启仪式")
            st.markdown("### ✨ 旅人，你希望重生为...")

            wish = st.text_input(
                "重生愿望",
                placeholder="例如：中世纪骑士、赛博朋克黑客、魔法学院学生...",
                key="wish_input",
                help="发挥你的想象力，描述你想要重生的身份或职业",
                label_visibility="hidden"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🌟 开启重生之旅", use_container_width=True, type="primary"):
                if wish.strip():
                    start_new_story(wish.strip())
                else:
                    st.warning("⚠️ 请输入你的重生愿望！")
        
        # 示例展示
        st.markdown("---")
        st.markdown("### 💡 重生愿望示例")
        
        example_cols = st.columns(3)
        examples = [
            "🗡️ 中世纪骑士",
            "🤖 赛博朋克黑客", 
            "🔮 魔法学院学生",
            "🏴‍☠️ 加勒比海盗",
            "🚀 星际探险家",
            "🕵️ 维多利亚时代侦探"
        ]
        
        for i, example in enumerate(examples):
            with example_cols[i % 3]:
                if st.button(example, key=f"example_{i}"):
                    st.session_state.wish_input = example.split(" ", 1)[1]
                    st.rerun()
    
    else:
        # 游戏进行界面
        segment = st.session_state.current_segment
        
        if segment:
            # 显示当前章节信息
            st.markdown(f"## 📖 第 {st.session_state.chapter_count} 章")
            
            # 显示故事内容
            display_story_segment(segment)
            
            # 显示选择选项
            choices = segment.get('choices', [])
            if choices:
                st.markdown('<div class="choice-container">', unsafe_allow_html=True)
                st.markdown("### 🎯 你的抉择是？")

                selected_choice = display_choices(choices)

                if selected_choice:
                    continue_story(selected_choice)

                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # 故事结束
                st.markdown("---")
                st.markdown("### 🎭 故事完结")
                st.balloons()
                
                _, col2, _ = st.columns([1, 1, 1])
                with col2:
                    if st.button("🔄 开始新的重生", use_container_width=True, type="primary"):
                        reset_game()

if __name__ == "__main__":
    main()
