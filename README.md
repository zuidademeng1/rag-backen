# RAG 知识库问答系统（RuoYi-AI）

基于 FastAPI 的企业级 RAG（检索增强生成）智能知识库问答后端，实现从文档上传到智能问答的完整闭环。

## 技术栈

| 类别 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn（异步） |
| 关系数据库 | PostgreSQL（SQLAlchemy 异步 ORM） |
| 缓存 / 队列 | Redis（任务队列、会话记忆） |
| 向量数据库 | Milvus（稠密 + 稀疏向量） |
| 嵌入模型 | BGE-M3（独立嵌入服务） |
| 文档解析 | MinerU（PDF）/ Docling（Office） |
| 大模型 | 通义千问 Qwen3-max（OpenAI 兼容协议） |
| 权限体系 | 若依 RBAC（用户 / 角色 / 菜单 / 五级数据权限） |

## 核心功能

- **文档全链路入库**：上传 → 异步解析 → 切块 → 稠密+稀疏双向量化 → 存入 Milvus，Redis 队列 + 后台 worker 异步解耦
- **混合检索**：稠密向量（语义）+ 稀疏向量（关键词）双路召回，RRF 融合排序
- **流式问答**：SSE 逐 token 输出，支持普通对话与 RAG 问答两种模式
- **数据隔离**：五级数据权限（data_scope）+ 部门隔离（dept_id）
- **多智能体报告生成**：Planner → Writer 流水线，大纲解析成章节树递归撰写
- **意图路由**：关键词快速匹配 + LLM 兜底分类，分流到闲聊 / 问答 / 报告三条链路
- **评估闭环**：检索层指标（Recall / Precision / MRR）+ 端到端 LLM Judge（忠实度 / 相关性）双层评估

## 项目结构

```
rag-backend/
├── app/
│   ├── main.py                 # FastAPI 入口，lifespan 生命周期管理
│   ├── config/                 # 统一配置中心（pydantic-settings）
│   ├── api/                    # 接口层（auth/chat/doc/knowledge_base/session/system）
│   ├── services/               # 业务层（对话/文档/解析/会话/后台 worker）
│   ├── dao/                    # 数据访问层
│   ├── models/                 # ORM 模型
│   ├── schemas/                # Pydantic DTO
│   ├── core/                   # 基础设施（数据库/权限/Milvus/Redis/异常处理）
│   ├── components/             # 业务组件（llm/rag/intent/memory/context/tool）
│   ├── agent/                  # 多智能体（报告生成流水线）
│   ├── eval/                   # 评估模块（检索层 + 端到端）
│   └── sql/                    # 数据库初始化脚本
├── .env.example                # 环境变量模板
└── requirements.txt            # 依赖清单
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
# 激活虚拟环境后
pip install -r requirements.txt
```

> 若需 PDF 高精度解析，另安装 MinerU 及其模型（`pip install mineru`，模型单独下载）。

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入数据库密码、LLM API Key 等真实配置
```

### 3. 启动依赖服务

需要先启动以下中间件：

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| PostgreSQL | 5432 | 业务数据 |
| Redis | 6379 | 任务队列 |
| Milvus | 19530 | 向量库（Docker） |
| BGE-M3 嵌入服务 | 9003 | 向量化 |

### 4. 初始化数据库

执行 `app/sql/public.sql` 建表，并插入初始用户数据。

### 5. 启动后端

```bash
python -m app.main
```

服务启动于 `http://127.0.0.1:9090`，API 文档见 `/docs`。

## 数据流

```
文档入库：上传 → 落盘 → 存库 → 推 Redis 队列 → worker 解析 → 切块 → 向量化 → 存 Milvus
检索问答：提问 → 向量化 → Milvus 混合检索（RRF）→ 召回 top_k → 拼 prompt → LLM 流式回答
```

## 评估

```bash
python -m app.eval.run_eval
```

- **检索层**：Hit@k / Recall / Precision / MRR
- **端到端**：LLM Judge 评估忠实度（Faithfulness）与相关性（Relevance）

## 许可证

MIT
