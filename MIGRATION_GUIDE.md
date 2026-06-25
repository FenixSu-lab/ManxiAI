# 从OpenAI迁移到DeepSeek指南

本指南将帮助您将ManxiAI项目从OpenAI迁移到DeepSeek，或者配置为支持两者。

## 📋 迁移概述

### 迁移内容
- ✅ 依赖包更新
- ✅ 配置文件修改
- ✅ DeepSeek客户端实现
- ✅ AI服务接口统一
- ✅ 环境变量配置
- ✅ 测试脚本

### 兼容性
- ✅ 保持OpenAI作为备选
- ✅ 支持运行时切换
- ✅ 向后兼容现有代码

## 🚀 快速迁移步骤

### 1. 更新依赖

```bash
# 安装新依赖
pip install httpx==0.24.1 httpx-sse==0.4.0

# 或者重新安装所有依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板：
```bash
cp env.example .env
```

编辑`.env`文件，添加DeepSeek配置：
```env
# DeepSeek配置（新增）
DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# OpenAI配置（保留作为备选）
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 获取DeepSeek API密钥

1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在控制台中创建API密钥
4. 将密钥添加到`.env`文件中

### 4. 测试配置

运行测试脚本验证配置：
```bash
python test_deepseek.py
```

### 5. 重启服务

```bash
# 重启Django服务
python start.py runserver

# 重启Celery（如果使用）
python start.py celery
```

## 🔧 详细配置说明

### DeepSeek模型选择

DeepSeek提供以下模型：

| 模型名称 | 描述 | 适用场景 |
|---------|------|----------|
| `deepseek-chat` | 通用对话模型 | 日常对话、问答 |
| `deepseek-coder` | 编程专用模型 | 代码生成、编程问题 |
| `deepseek-reasoner` | 推理模型 | 复杂推理、逻辑分析 |

配置示例：
```env
# 使用通用对话模型
DEFAULT_LLM_MODEL=deepseek-chat

# 使用编程模型
DEFAULT_LLM_MODEL=deepseek-coder

# 使用推理模型
DEFAULT_LLM_MODEL=deepseek-reasoner
```

### 运行时切换模型

您可以在代码中动态切换模型：

```python
from apps.model_management.ai_service import AIServiceFactory

# 使用DeepSeek
deepseek_service = AIServiceFactory.get_service('deepseek')
response = deepseek_service.generate_response("你好")

# 使用OpenAI
openai_service = AIServiceFactory.get_service('openai')
response = openai_service.generate_response("Hello")
```

### 批量切换配置

如果您想完全切换到DeepSeek，可以修改以下配置：

```env
# 完全切换到DeepSeek
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# 如果不再使用OpenAI，可以清空（可选）
OPENAI_API_KEY=
OPENAI_BASE_URL=
```

## 🔍 功能对比

### API兼容性

| 功能 | OpenAI | DeepSeek | 状态 |
|------|--------|----------|------|
| 文本生成 | ✅ | ✅ | 完全支持 |
| 流式输出 | ✅ | ✅ | 完全支持 |
| 对话历史 | ✅ | ✅ | 完全支持 |
| 文本嵌入 | ✅ | ❌ | 建议保留OpenAI |
| 函数调用 | ✅ | ✅ | 部分支持 |
| 图像理解 | ✅ | ❌ | 建议保留OpenAI |

### 性能对比

| 指标 | OpenAI | DeepSeek | 备注 |
|------|--------|----------|------|
| 响应速度 | 快 | 很快 | DeepSeek通常更快 |
| 成本 | 高 | 低 | DeepSeek成本更低 |
| 中文支持 | 好 | 优秀 | DeepSeek中文更好 |
| 编程能力 | 优秀 | 优秀 | 两者都很强 |

## 🛠️ 故障排除

### 常见问题

#### 1. API密钥错误
```
错误: Authentication failed
解决: 检查DEEPSEEK_API_KEY是否正确配置
```

#### 2. 网络连接问题
```
错误: Connection timeout
解决: 检查网络连接，或配置代理
```

#### 3. 模型不存在
```
错误: Model not found
解决: 检查DEFAULT_LLM_MODEL配置是否正确
```

#### 4. 依赖包问题
```
错误: ModuleNotFoundError: No module named 'httpx'
解决: 运行 pip install httpx httpx-sse
```

### 调试步骤

1. **检查配置**：
   ```bash
   python test_deepseek.py
   ```

2. **查看日志**：
   ```bash
   tail -f logs/django.log
   ```

3. **测试网络**：
   ```bash
   curl -H "Authorization: Bearer your-api-key" https://api.deepseek.com/models
   ```

4. **验证环境变量**：
   ```python
   from django.conf import settings
   print(settings.DEEPSEEK_API_KEY)
   ```

## 🔄 回滚步骤

如果需要回滚到OpenAI：

1. **修改环境变量**：
   ```env
   DEFAULT_LLM_PROVIDER=openai
   DEFAULT_LLM_MODEL=gpt-3.5-turbo
   ```

2. **重启服务**：
   ```bash
   python start.py runserver
   ```

3. **验证回滚**：
   ```bash
   python test_deepseek.py
   ```

## 📊 迁移检查清单

### 迁移前准备
- [ ] 备份现有配置
- [ ] 获取DeepSeek API密钥
- [ ] 了解DeepSeek模型特性
- [ ] 准备测试数据

### 迁移过程
- [ ] 更新依赖包
- [ ] 配置环境变量
- [ ] 运行测试脚本
- [ ] 验证基础功能
- [ ] 测试关键业务流程

### 迁移后验证
- [ ] 对话功能正常
- [ ] 流式输出正常
- [ ] 错误处理正常
- [ ] 性能满足要求
- [ ] 日志记录正常

## 🎯 最佳实践

### 1. 渐进式迁移
建议先在测试环境验证，再逐步迁移生产环境。

### 2. 双重备份
保持OpenAI配置作为备选，以防DeepSeek服务不可用。

### 3. 监控告警
设置监控告警，及时发现API调用异常。

### 4. 成本优化
根据使用场景选择合适的模型，平衡性能和成本。

### 5. 定期更新
定期检查DeepSeek的新模型和功能更新。

## 📞 支持与帮助

如果在迁移过程中遇到问题：

1. 查看本指南的故障排除部分
2. 运行测试脚本进行诊断
3. 查看项目日志文件
4. 提交GitHub Issue

---

**注意**：本迁移指南基于当前版本编写，DeepSeek API可能会有更新，请参考官方文档获取最新信息。 