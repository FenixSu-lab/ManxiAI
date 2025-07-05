# ManxiAI 部署指南

## 📋 项目框架已完成

✅ **已完成的功能模块**：
1. **项目配置** - Django配置、URL路由、Celery配置
2. **核心模块** - 基础模型类、通用工具
3. **用户管理** - 完整的用户、团队、API密钥管理
4. **知识库管理** - 完整的知识库CRUD、分享、标签、设置功能
5. **基础应用结构** - 文档、对话、向量化、管道、工作流、模型管理应用框架

## 🚀 快速启动流程

### 1. 安装依赖
```bash
cd ManxiAI
pip install -r requirements.txt
```

### 2. 配置数据库
```bash
# 创建PostgreSQL数据库
createdb manxiai

# 启用pgvector扩展
psql -d manxiai -c "CREATE EXTENSION vector;"
```

### 3. 环境变量
创建 `.env` 文件：
```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=manxiai
DB_USER=postgres
DB_PASSWORD=postgres
OPENAI_API_KEY=your-openai-key
```

### 4. 初始化数据库
```bash
python start.py migrate
python start.py createsuperuser
```

### 5. 启动服务
```bash
python start.py runserver 8000
```

## 📁 当前项目结构

```
ManxiAI/
├── config/                    # ✅ 项目配置
│   ├── settings.py           # ✅ Django设置
│   ├── urls.py               # ✅ URL路由
│   ├── wsgi.py               # ✅ WSGI配置
│   └── celery.py             # ✅ Celery配置
├── apps/
│   ├── core/                 # ✅ 核心工具模块
│   │   ├── models.py         # ✅ 基础模型类
│   │   └── apps.py           # ✅ 应用配置
│   ├── users/                # ✅ 用户管理 (完整实现)
│   │   ├── models.py         # ✅ 用户、团队、API密钥模型
│   │   ├── serializers.py    # ✅ 序列化器
│   │   ├── views.py          # ✅ 视图集
│   │   └── urls.py           # ✅ URL配置
│   ├── knowledge_base/       # ✅ 知识库管理 (完整实现)
│   │   ├── models.py         # ✅ 知识库、分享、标签、设置模型
│   │   ├── serializers.py    # ✅ 序列化器
│   │   ├── views.py          # ✅ 视图集
│   │   └── urls.py           # ✅ URL配置
│   ├── document/             # 🔄 文档管理 (基础框架)
│   ├── chat/                 # 🔄 对话管理 (基础框架)
│   ├── embedding/            # 🔄 向量化处理 (基础框架)
│   ├── pipeline/             # 🔄 RAG管道 (基础框架)
│   ├── workflow/             # 🔄 工作流编排 (基础框架)
│   └── model_management/     # 🔄 模型管理 (基础框架)
├── requirements.txt          # ✅ 依赖包
├── manage.py                 # ✅ Django管理工具
├── start.py                  # ✅ 启动脚本
└── README.md                 # ✅ 项目说明
```

## 🔧 下一步开发计划

### 第一阶段：核心RAG功能 (2-3周)
1. **文档管理模块** (apps/document)
   - 文档上传、解析、存储
   - 支持PDF、Word、PPT、TXT等格式
   - 文档版本控制

2. **向量化处理模块** (apps/embedding)
   - 文本分块处理
   - 向量化存储
   - 相似度计算

3. **对话管理模块** (apps/chat)
   - 对话会话管理
   - 消息历史记录
   - 用户反馈系统

4. **RAG管道模块** (apps/pipeline)
   - 检索增强生成流程
   - 多阶段处理管道
   - 结果排序优化

### 第二阶段：增强功能 (3-4周)
1. **异步任务处理**
   - 文档处理任务
   - 向量化任务
   - 定时清理任务

2. **文档解析优化**
   - OCR图片识别
   - 表格提取
   - 多语言支持

3. **检索优化**
   - 混合检索模式
   - 重排序算法
   - 查询扩展

### 第三阶段：高级特性 (4-5周)
1. **工作流编排** (apps/workflow)
   - 可视化工作流设计
   - 条件分支处理
   - 自定义节点

2. **模型管理** (apps/model_management)
   - 多模型支持
   - 模型切换
   - 性能监控

## 🔍 API接口设计

### 已实现的API
- **用户管理**: `/api/v1/auth/`
  - 用户注册、登录、个人信息
  - 团队管理、成员邀请
  - API密钥管理

- **知识库管理**: `/api/v1/knowledge-base/`
  - 知识库CRUD操作
  - 分享与权限管理
  - 标签与设置管理

### 待实现的API
- **文档管理**: `/api/v1/document/`
- **对话管理**: `/api/v1/chat/`
- **向量化处理**: `/api/v1/embedding/`
- **RAG管道**: `/api/v1/pipeline/`

## 📊 数据库设计

### 已实现的表
- `users` - 用户信息
- `user_profiles` - 用户详细信息
- `teams` - 团队信息
- `team_members` - 团队成员关系
- `api_keys` - API密钥
- `knowledge_bases` - 知识库
- `knowledge_base_shares` - 知识库分享
- `knowledge_base_tags` - 知识库标签
- `knowledge_base_settings` - 知识库设置

### 待实现的表
- `documents` - 文档信息
- `document_chunks` - 文档分块
- `embeddings` - 向量数据
- `chat_sessions` - 对话会话
- `chat_messages` - 对话消息
- `workflows` - 工作流定义
- `workflow_executions` - 工作流执行记录

## 🧪 测试与验证

### 当前可测试的功能
1. 启动项目: `python start.py runserver`
2. 访问API文档: http://localhost:8000/swagger/
3. 用户注册登录
4. 知识库创建管理

### 建议的测试流程
1. 创建用户账号
2. 创建知识库
3. 设置知识库参数
4. 添加知识库标签
5. 分享知识库给其他用户

## 🔗 有用的链接

- **Swagger API文档**: http://localhost:8000/swagger/
- **ReDoc API文档**: http://localhost:8000/redoc/
- **Django Admin**: http://localhost:8000/admin/

这个框架为您提供了一个完整的企业级AI知识库系统的基础架构，您可以在此基础上逐步实现各个功能模块。 