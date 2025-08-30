# 🚀 快速启动指南

## 第一次运行项目

### 1. 自动设置（推荐）

```bash
# 运行自动设置脚本
python setup.py
```

这个脚本会：
- ✅ 检查Python版本
- ✅ 安装所有依赖
- ✅ 创建.env配置文件
- ✅ 下载占位符图片
- ✅ 设置前端资源

### 2. 配置API密钥

编辑 `.env` 文件，填入你的OpenAI API密钥：

```env
OPENAI_API_KEY="sk-your-actual-api-key-here"
```

**获取API密钥：**
- 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
- 登录并创建新的API密钥
- 复制密钥到.env文件中

### 3. 测试系统

```bash
# 运行系统测试
python test_system.py
```

确保所有测试通过后再启动服务。

## 启动服务

### 方法一：使用启动脚本（推荐）

**启动后端：**
```bash
python start_backend.py
```

**启动前端：**
```bash
# 新开一个终端窗口
python start_frontend.py
```

### 方法二：手动启动

**启动后端：**
```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**启动前端：**
```bash
cd frontend
streamlit run app.py
```

## 访问应用

- 🎮 **游戏界面**: http://localhost:8501
- 📖 **API文档**: http://localhost:8000/docs
- 🔍 **API健康检查**: http://localhost:8000/story/health

## 故障排除

### 常见问题

**1. 依赖安装失败**
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt
```

**2. 无法连接后端**
- 确保后端服务已启动
- 检查端口8000是否被占用
- 查看后端控制台是否有错误信息

**3. API密钥错误**
- 检查.env文件中的API密钥格式
- 确保API密钥有效且有足够余额
- 查看后端日志中的错误信息

**4. 图片无法显示**
- 确保assets/images目录下有占位符图片
- 运行 `python setup.py` 重新下载图片

### 日志查看

**后端日志：**
- 控制台输出
- `rebirth_game.log` 文件

**前端日志：**
- Streamlit控制台输出
- 浏览器开发者工具

## 开发模式

### 修改代码后

**后端：** 自动重载（使用--reload参数）
**前端：** 刷新浏览器页面

### 调试技巧

1. **启用详细日志：**
   - 在.env中设置 `DEBUG=True`

2. **测试API端点：**
   - 访问 http://localhost:8000/docs
   - 使用Swagger UI测试API

3. **检查数据流：**
   - 查看浏览器网络面板
   - 检查API请求和响应

## 下一步

项目成功运行后，你可以：

1. **体验游戏**：输入重生愿望，体验AI生成的故事
2. **查看代码**：了解项目架构和实现细节
3. **自定义配置**：修改模型参数、提示词等
4. **扩展功能**：添加新的特性和改进

## 需要帮助？

- 📖 查看 `README.md` 了解详细信息
- 🧪 运行 `python test_system.py` 诊断问题
- 🔧 检查配置文件 `config/settings.py`
- 📝 查看日志文件了解错误详情

---

**祝你在重生世界中玩得愉快！** 🌟
