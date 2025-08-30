# 🤖 豆包模型配置指南

## 为什么选择豆包？

- ✅ **成本低**：比OpenAI便宜很多
- ✅ **中文优秀**：字节跳动出品，中文原生支持
- ✅ **访问稳定**：国内服务器，无需科学上网
- ✅ **响应快速**：延迟低，用户体验好

## 获取豆包API密钥

### 1. 注册火山引擎账号
1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 注册并完成实名认证
3. 充值一定金额（建议先充值10-20元测试）

### 2. 开通豆包服务
1. 在控制台搜索"豆包"或访问 [豆包大模型](https://console.volcengine.com/ark)
2. 点击"立即使用"开通服务
3. 创建推理接入点

### 3. 创建推理接入点
1. 在豆包控制台点击"推理接入点"
2. 点击"新建接入点"
3. 选择模型：`doubao-seed-1-6-flash-250715`（推荐，速度快成本低）
4. 配置参数（使用默认值即可）
5. 创建完成后记录接入点ID

### 4. 获取API密钥
1. 在控制台左侧菜单找到"API管理"
2. 点击"创建API Key"
3. 复制生成的API密钥（格式类似：`ark-xxx-xxx`）

## 配置项目

### 1. 编辑.env文件
```env
# 豆包API密钥（必填）
DOUBAO_API_KEY="你的豆包API密钥"

# 豆包推理接入点ID（如果与默认不同需要修改）
DOUBAO_MODEL="你的推理接入点ID"

# 其他配置（通常不需要修改）
DOUBAO_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
```

### 2. 示例配置
```env
DOUBAO_API_KEY="ark-xxx-xxxxxxxxxxxxxxxxxxxxxxxxxx"
DOUBAO_MODEL="doubao-seed-1-6-flash-250715"
DOUBAO_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
```

## 测试配置

### 1. 运行系统测试
```bash
python test_system.py
```

### 2. 检查输出
应该看到类似输出：
```
✅ LLM客户端初始化成功 - 模型: doubao-seed-1-6-flash-250715
✅ API地址: https://ark.cn-beijing.volces.com/api/v3
✅ LLM客户端工作正常
```

## 成本估算

### 豆包定价（参考）
- **输入Token**：约 ¥0.0008 / 1K tokens
- **输出Token**：约 ¥0.002 / 1K tokens

### 使用估算
- **每次对话**：约200-500 tokens
- **单次成本**：约 ¥0.0002-0.0005
- **100次对话**：约 ¥0.02-0.05

比OpenAI便宜约5-10倍！

## 故障排除

### 常见错误

**1. API密钥无效**
```
openai.AuthenticationError: Invalid API key
```
**解决**：
- 检查API密钥是否正确复制
- 确认API密钥是否已激活
- 检查账户余额是否充足

**2. 推理接入点不存在**
```
Model not found: doubao-seed-1-6-flash-250715
```
**解决**：
- 检查推理接入点ID是否正确
- 确认推理接入点是否已创建并启用
- 更新.env文件中的DOUBAO_MODEL

**3. 网络连接问题**
```
requests.exceptions.ConnectionError
```
**解决**：
- 检查网络连接
- 确认防火墙设置
- 尝试更换网络环境

**4. 余额不足**
```
Insufficient balance
```
**解决**：
- 登录火山引擎控制台充值
- 检查账户余额和消费限制

### 调试技巧

1. **查看详细日志**：
   ```bash
   # 启动后端时查看控制台输出
   python start_backend.py
   ```

2. **测试API连接**：
   ```bash
   # 运行完整系统测试
   python test_system.py
   ```

3. **手动测试**：
   ```python
   # 在Python中手动测试
   from backend.core.llm_clients import llm_client
   result = llm_client.generate('{"text": "测试", "choices": ["选项1"]}')
   print(result)
   ```

## 模型选择建议

### 推荐模型
- **doubao-seed-1-6-flash-250715**：速度快，成本低，适合开发测试
- **doubao-pro-4k**：质量高，适合生产环境
- **doubao-pro-32k**：支持长文本，适合复杂对话

### 切换模型
只需修改.env文件中的DOUBAO_MODEL即可：
```env
DOUBAO_MODEL="你的新推理接入点ID"
```

## 下一步

配置完成后：
1. 运行 `python test_system.py` 测试
2. 启动项目：`python start_backend.py` 和 `python start_frontend.py`
3. 访问 http://localhost:8501 开始体验
4. 根据使用情况调整模型参数

---

**需要帮助？** 请提供错误信息和配置详情！
