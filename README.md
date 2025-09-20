# 重生之我是…… (Rebirth Game) 

一个基于AI的互动故事生成游戏，让用户体验不同的重生人生。

## 🌟 项目简介

"重生之我是……"是一个创新的AI驱动互动故事游戏。用户可以输入自己的重生愿望（如"中世纪骑士"、"赛博朋克黑客"等），AI将为用户生成独特的故事情节，并在关键时刻提供选择选项，让用户体验不同的人生轨迹。

## 🚀 当前版本：阶段一 - 核心链路验证版 (v0.1)

### 功能特性

- ✅ 基于用户愿望的故事生成
- ✅ 互动式分支选择系统
- ✅ 流畅的前后端通信
- ✅ 错误处理和恢复机制
- ✅ 响应式Web界面
- ✅ 模块化架构设计

### 技术栈

**后端**
- FastAPI - 现代、快速的Web框架
- Pydantic - 数据验证和设置管理
- OpenAI API - 大语言模型服务
- Uvicorn - ASGI服务器

**前端**
- Streamlit - 快速Web应用开发框架
- Requests - HTTP客户端库

**架构**
- RESTful API设计
- 微服务架构
- 模块化代码组织

## 📁 项目结构

```
rebirth_game/
├── backend/                 # 后端服务
│   ├── api/                # API路由
│   │   └── story.py        # 故事相关端点
│   ├── core/               # 核心业务逻辑
│   │   ├── llm_clients.py  # LLM客户端封装
│   │   ├── prompt_templates.py # Prompt模板
│   │   └── story_engine.py # 故事生成引擎
│   ├── schemas/            # 数据模型
│   │   └── story.py        # 故事相关数据结构
│   └── main.py             # FastAPI应用入口
├── frontend/               # 前端应用
│   └── app.py              # Streamlit应用
├── assets/                 # 静态资源
│   └── images/             # 图片资源
├── config/                 # 配置文件
│   └── settings.py         # 应用设置
├── .env                    # 环境变量
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 🛠️ 安装和运行

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd rebirth_game

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥（必须）

编辑 `.env` 文件，填入你的API密钥：

**推荐使用豆包（便宜且中文效果好）：**
```env
DOUBAO_API_KEY="你的豆包API密钥"
```

**或者使用OpenAI：**
```env
OPENAI_API_KEY="sk-your-actual-api-key-here"
```

**⚠️ 重要：必须配置至少一个真实的API密钥，否则程序无法运行！**

📖 **详细配置指南**：
- 豆包配置：查看 `DOUBAO_SETUP.md`
- 其他模型：查看 `MODEL_SETUP.md`

### 3. 准备图片资源

在 `assets/images/` 目录下放置以下图片：
- `placeholder_01.png`
- `placeholder_02.png`
- `placeholder_03.png`

### 4. 启动服务

**启动后端服务：**
```bash
cd backend
python main.py
# 或使用 uvicorn
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**启动前端应用：**
```bash
cd frontend
streamlit run app.py
```

### 5. 访问应用

- 前端界面：http://localhost:8501
- 后端API文档：http://localhost:8000/docs

## 🎮 使用指南

1. **开始游戏**：在首页输入你的重生愿望
2. **阅读故事**：AI将生成独特的开场故事
3. **做出选择**：在关键时刻选择你的行动
4. **继续冒险**：根据你的选择，故事将继续发展
5. **重新开始**：随时可以开始新的重生之旅

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | 必填 |
| `DEBUG` | 调试模式 | `True` |
| `BACKEND_HOST` | 后端主机地址 | `127.0.0.1` |
| `BACKEND_PORT` | 后端端口 | `8000` |

### LLM配置

可在 `config/settings.py` 中调整：
- `default_model`: 使用的模型（默认：gpt-4o-mini）
- `max_tokens`: 最大token数（默认：1000）
- `temperature`: 创造性参数（默认：0.8）

## 🚧 开发计划

### 阶段二：核心体验版
- [ ] 精美的UI设计
- [ ] 预制高质量图片库
- [ ] 改进的故事生成算法
- [ ] 用户体验优化

### 阶段三：技术探索版
- [ ] 实时图片生成
- [ ] 故事存档功能
- [ ] 多模型支持
- [ ] 性能优化

### 未来版本
- [ ] 用户账户系统
- [ ] 故事分享功能
- [ ] 多语言支持
- [ ] 移动端适配

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🙏 致谢

- OpenAI - 提供强大的语言模型
- Streamlit - 简化前端开发
- FastAPI - 现代化的API框架

---

**注意**：这是项目的第一个版本，主要用于验证核心技术链路。后续版本将持续优化用户体验和功能完善。
