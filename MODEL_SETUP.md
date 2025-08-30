# 🤖 大模型配置指南

## 当前项目使用的AI功能

### 📝 故事文本生成
- **功能**：根据用户的重生愿望和选择生成故事情节
- **输入**：用户愿望 + 历史对话
- **输出**：JSON格式的故事文本和选择选项
- **要求**：支持中文，创意性强，响应速度快

### 🖼️ 图片生成
- **当前状态**：使用占位符图片
- **未来计划**：集成AI图片生成（如DALL-E、Midjourney等）

## 推荐的模型选择

### 1. OpenAI GPT-4o-mini（推荐）
**优势：**
- ✅ 性价比极高（比GPT-4便宜很多）
- ✅ 响应速度快
- ✅ 中文效果优秀
- ✅ JSON格式输出稳定
- ✅ 国际通用，文档完善

**获取方式：**
1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 注册账号并绑定支付方式
3. 创建API密钥
4. 复制密钥到 `.env` 文件

**配置示例：**
```env
OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 2. 豆包（字节跳动）
**优势：**
- ✅ 国内访问稳定
- ✅ 中文原生支持
- ✅ 价格相对便宜
- ✅ 无需科学上网

**获取方式：**
1. 访问 [豆包开放平台](https://www.volcengine.com/product/doubao)
2. 注册火山引擎账号
3. 开通豆包服务
4. 获取API密钥

**需要修改的代码：**
- `backend/core/llm_clients.py` - 添加豆包客户端
- `config/settings.py` - 添加豆包配置

### 3. Google Gemini
**优势：**
- ✅ Google最新技术
- ✅ 多模态能力强
- ✅ 免费额度较高

**获取方式：**
1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建API密钥

**需要修改的代码：**
- `backend/core/llm_clients.py` - 添加Gemini客户端
- `config/settings.py` - 添加Gemini配置

## 当前配置状态

### 已配置支持
- ✅ **OpenAI GPT系列**（完整支持）

### 需要开发支持
- ⏳ **豆包**（需要添加客户端代码）
- ⏳ **Gemini**（需要添加客户端代码）
- ⏳ **其他模型**（如Claude、文心一言等）

## 快速开始

### 使用OpenAI（推荐）
1. 获取OpenAI API密钥
2. 编辑 `.env` 文件：
   ```env
   OPENAI_API_KEY="你的密钥"
   ```
3. 运行项目即可

### 使用其他模型
如果你想使用豆包、Gemini或其他模型，请告诉我：
1. 你选择的模型
2. 你的API密钥
3. 我会为你添加相应的客户端代码

## 成本估算

### OpenAI GPT-4o-mini
- **输入**：$0.15 / 1M tokens
- **输出**：$0.60 / 1M tokens
- **估算**：每次对话约200-500 tokens，成本约 $0.0001-0.0003

### 豆包
- **价格**：约 ¥0.0008 / 1K tokens
- **估算**：每次对话成本约 ¥0.0002-0.0005

## 故障排除

### 常见错误

**1. API密钥无效**
```
openai.AuthenticationError: Incorrect API key provided
```
**解决**：检查API密钥是否正确，是否有足够余额

**2. 配置文件错误**
```
pydantic.ValidationError: 1 validation error for Settings
```
**解决**：确保 `.env` 文件格式正确

**3. 网络连接问题**
```
requests.exceptions.ConnectionError
```
**解决**：检查网络连接，如使用OpenAI可能需要科学上网

### 调试技巧

1. **查看详细错误**：
   - 检查后端控制台输出
   - 查看 `rebirth_game.log` 文件

2. **测试API连接**：
   ```bash
   python test_system.py
   ```

3. **手动测试API**：
   - 访问 http://localhost:8000/docs
   - 使用Swagger UI测试接口

## 下一步

配置好模型后，你可以：
1. 运行 `python test_system.py` 测试连接
2. 启动项目开始体验
3. 根据需要调整模型参数（temperature、max_tokens等）

---

**需要帮助？** 请告诉我你选择的模型和遇到的问题！
