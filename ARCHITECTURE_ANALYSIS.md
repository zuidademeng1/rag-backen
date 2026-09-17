# RAG-Backend 项目架构分析报告

## 1. 项目概述

项目名称：**智慧办公系统（RuoYi-AI）**  
技术定位：基于 FastAPI 的 RAG（检索增强生成）智能知识库问答后端服务  
数据库：RuoYi-Vue 经典 RBAC 表结构（sys_user / sys_role / sys_menu 等）+ AI 业务表（ai_*）  
向量引擎：Milvus 混合检索（稠密 BGE-M3 + 稀疏 BM25）  
LLM：通义千问 Qwen3-max（OpenAI 兼容 API）  
文档解析：MinerU（PDF/图片OCR）+ Docling（Office 文档）

---

## 2. 项目目录结构与模块职责

```
rag-backend/
├── app/
│   ├── main.py                    # FastAPI 应用入口，lifespan 生命周期管理
│   ├── config/
│   │   └── config.py              # 统一配置中心（pydantic-settings）
│   ├── api/                       # 接口层 — HTTP 路由 & 参数校验
│   │   ├── auth.py                # 认证接口：登录/JWT、用户信息、路由菜单树
│   │   ├── chat.py                # 对话接口：/chat/stream（纯LLM）、/chat/rag-stream（RAG）
│   │   ├── doc.py                 # 文档接口：上传/分块上传、解析、列表、删除、预览
│   │   ├── knowledge_base.py      # 知识库接口：CRUD、个人/公共分页
│   │   ├── session.py             # 会话接口：CRUD + 对话记录管理
│   │   └── system.py              # 系统管理：用户/角色/菜单/部门/日志/字典 CRUD
│   ├── services/                  # 服务层 — 核心业务逻辑编排
│   │   ├── chat_service.py        # 对话服务：流式对话、RAG对话、历史记录管理
│   │   ├── document_service.py    # 文档服务：上传（含分块上传）、合并、推入解析队列
│   │   ├── document_chunk_service.py # 文档解析+切块+向量化+存入Milvus
│   │   ├── knowledge_base_service.py # 知识库CRUD服务
│   │   ├── session_service.py     # 会话&记录 CRUD
│   │   └── task_worker.py         # 后台Worker：Redis队列消费解析任务
│   ├── dao/                       # 数据访问层 — 纯SQL操作
│   │   ├── document_dao.py        # ai_document 表 CRUD + 分页 + scope查询
│   │   ├── document_chunk_dao.py  # ai_document_chunk 表批量插入
│   │   ├── knowledge_base_dao.py  # ai_knowledge_base 表 CRUD + 分页
│   │   ├── session_dao.py         # ai_session 表 CRUD
│   │   └── session_record_dao.py  # ai_session_record 表 CRUD
│   ├── models/                    # ORM 模型层 — SQLAlchemy Mapped
│   │   ├── document.py            # 文档表 ai_document
│   │   ├── document_chunk.py      # 文档分块表 ai_document_chunk
│   │   ├── knowledge_base.py      # 知识库表 ai_knowledge_base
│   │   ├── session.py             # 会话表 ai_session
│   │   ├── session_record.py      # 会话记录表 ai_session_record
│   │   └── system.py              # RuoYi 系统表：sys_user/role/menu/dept
│   ├── schemas/                   # Pydantic Schema — 请求/响应 DTO
│   │   ├── auth.py                # 登录请求/响应、用户信息、路由树
│   │   ├── chat.py                # ChatRequest、RagChatRequest
│   │   ├── document.py            # DocumentEntity
│   │   ├── document_chunk.py      # —（空）
│   │   ├── knowledge_base.py      # KnowledgeBaseCreateRequest/Entity
│   │   ├── session.py             # Session/Record CreateRequest/Entity
│   │   └── system.py              # 系统管理各种 Entity/Query/Create
│   ├── core/                      # 核心基础设施
│   │   ├── database.py            # 异步引擎、会话工厂、慢SQL监控
│   │   ├── auth.py                # JWT Token 验证函数
│   │   ├── permission.py          # RequirePermission / RequireRole 依赖注入
│   │   ├── exception_handler.py   # 全局异常处理（Service/HTTP/Validation/500）
│   │   ├── data_scope.py          # RuoYi 数据权限 SQL 构建器
│   │   ├── get_milvus.py          # Milvus 客户端封装（单例模式）
│   │   └── get_redis.py           # Redis 客户端封装（连接池 + 全类型操作）
│   ├── components/                # 业务组件 — 可复用的领域模块
│   │   ├── llm/
│   │   │   └── async_llm.py       # OpenAI 兼容异步 LLM 调用（流式+非流式+错误处理）
│   │   ├── rag/
│   │   │   ├── rag_retrieval.py   # 语义检索：vector_only / hybrid（RRF融合）
│   │   │   ├── doc_embedding.py   # BGE-M3 向量化：稠密+稀疏批量调用
│   │   │   ├── doc_chunk.py       # 文本切块：固定大小 + 句子边界优化
│   │   │   ├── doc_parse.py       # 简单PDF解析（pypdf备选方案）
│   │   │   ├── parser.py          # 解析器注册表：MinerU + Docling + PaddleOCR
│   │   │   └── asset_urls.py      # 媒体URL处理
│   │   ├── context/
│   │   │   └── compressor.py      # 上下文压缩：truncate/summarize/hybrid
│   │   ├── memory/
│   │   │   └── memory.py          # 短时记忆组件（Redis List/Hash）
│   │   ├── intent/
│   │   │   ├── base_intent.py     # 意图识别基类（chat / rag_qa / report）
│   │   │   └── keyword_llm_intent.py
│   │   └── tool/
│   │       ├── tools.py           # 动态工具注册 & 调用
│   │       └── types.py           # ToolDef / ToolResult 类型
│   ├── utils/                     # 工具类
│   │   ├── auth_util.py           # CurrentUser 数据类 + JWT 解析 + DB补全
│   │   ├── common_util.py         # UUID 生成
│   │   └── response_util.py       # 统一响应封装（success/error/paginate）
│   └── agent/                     # Agent 智能体模块（报告中用）
│       ├── base_agent.py          # Agent 基类
│       ├── single_agent.py        # 单轮 Agent
│       └── report/                # 报告生成 Agent
│           ├── base_report_agent.py
│           ├── graph.py           # LangGraph 工作流
│           ├── planner.py         # 计划制定
│           └── writer.py          # 报告撰写
```

---

## 3. 模块分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  auth.py  chat.py  doc.py  kb.py  session.py  system.py     │
│     路由定义 · 参数校验 · 依赖注入 · 权限检查                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                   Service Layer (业务逻辑)                    │
│  ChatWithLLMService  DocumentService  SessionService        │
│  DocumentChunkService  KnowledgeBaseService  task_worker     │
│     业务编排 · 事务边界 · 流程控制                             │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────┘
   │          │          │          │          │
┌──▼──┐  ┌───▼───┐  ┌──▼──┐  ┌───▼───┐  ┌──▼───────────────┐
│ DAO │  │Comp-  │  │Core │  │Models │  │   External APIs   │
│Layer│  │onents │  │Infra│  │Schemas│  │ LLM · Embedding   │
│     │  │       │  │     │  │       │  │ Milvus · Redis    │
│ ORM │  │ RAG   │  │ DB  │  │ORM Map│  │ MinrU · Docling   │
│CRUD │  │ LLM   │  │Auth │  │Pydantic│ └───────────────────┘
│     │  │Memory │  │Perm │  │       │
│     │  │Intent │  │Scope│  │       │
│     │  │Tool   │  │Redis│  │       │
└─────┘  └───────┘  └─────┘  └───────┘
```

### 各层依赖关系（箭头 = 依赖方向）：

```
api ──► services ──► dao ──► models ──► core/database
  │         │          │
  │         ├──────────► components/rag ──► core/get_milvus
  │         ├──────────► components/llm
  │         ├──────────► components/context
  │         ├──────────► components/memory
  │         │
  ├─────────► core/permission ──► utils/auth_util
  ├─────────► core/exception_handler ──► utils/response_util
  ├─────────► schemas/*
  │
  └─────────► utils/response_util
```

---

## 4. /chat/stream 接口完整调用链路

```
1. 请求进入
   POST /chat/stream
   Body: { session_id, content }
   Header: Authorization: Bearer <JWT>

2. API 层 [api/chat.py:20-41]
   ├─ Depends(get_db)              → 创建/获取异步数据库会话
   ├─ Depends(RequirePermission("ai:chat:talk"))
   │   ├─ AuthUtil.get_current_user(request)
   │   │   ├─ 从 Header 提取 JWT
   │   │   ├─ jwt.decode(token, secret, HS256)
   │   │   ├─ 若 payload 信息不全 → async DB查询补全用户/角色/权限
   │   │   └─ return CurrentUser(user_id, roles, permissions, dept_id...)
   │   └─ 检查 perm in user.permissions 或 is_admin
   ├─ SessionDao.get_by_id(db, session_id) → 校验会话存在
   └─ return StreamingResponse(event_stream())

3. Service 层 [services/chat_service.py:22-71]
   ChatWithLLMService.chat_stream(db, session_id, content, user)
   │
   ├─ [Step 1] 保存用户消息
   │   SessionService.add_record(db, user_req, user)
   │   ├─ SessionDao.get_by_id → 校验会话
   │   ├─ SessionRecordDao.get_next_msg_index → 计算消息序号
   │   ├─ SessionRecord(record_id, session_id, role="user", content, msg_index)
   │   └─ SessionRecordDao.add → INSERT ai_session_record
   │
   ├─ [Step 2] 加载历史记录
   │   SessionService.get_records(db, session_id)
   │   ├─ SessionRecordDao.get_list_by_session → ORDER BY msg_index ASC
   │   └─ return [RecordEntity...] 列表
   │
   ├─ [Step 3] 组装 messages
   │   messages = [system_prompt] + [历史对话]
   │
   ├─ [Step 4] 调用 LLM 流式输出
   │   llm_chat_stream(messages) [components/llm/async_llm.py:36-71]
   │   ├─ _get_client() → AsyncOpenAI(base_url=DashScope, api_key)
   │   ├─ client.chat.completions.create(model=qwen3-max, stream=True)
   │   ├─ yield delta.content (每个 token)
   │   └─ 错误处理：APITimeoutError / APIStatusError → yield error event
   │
   ├─ [Step 5] 保存助手回复
   │   SessionService.add_record(db, assistant_req, user)
   │
   └─ [Step 6] 发送结束标记
       yield {done: True}
```

### RAG 对话额外链路 [services/chat_service.py:78-148]

```
chat_rag_stream() 在 Step 3 之前插入：

├─ [Step 3-RAG] 语义检索
│   rag_research(query, dept_id, top_k=5, mode="hybrid")
│   ├─ 调用 Embedding 服务 http://127.0.0.1:9003/embed/sparse
│   │   → 获取 稠密向量 + 稀疏向量
│   ├─ MilvusClient.hybrid_search()
│   │   ├─ AnnSearchRequest(稠密, field="vector", COSINE)
│   │   ├─ AnnSearchRequest(稀疏, field="sparse_vector", IP)
│   │   └─ RRFRanker(k=60) → 融合排序
│   └─ 按 dept_id 做数据隔离过滤
│
├─ [Step 4-RAG] 增强用户消息
│   rag_context = "\n\n".join(chunk["content"])
│   user_augmented = "资料：\n{rag_context}\n\n用户问题：{content}"
│
└─ 后续同普通对话流程
```

---

## 5. 文档上传→解析→检索 数据流

```
用户上传 PDF
  │
  ▼
[api/doc.py] POST /doc/upload
  ├─ 校验扩展名 .pdf/.doc/.docx
  ├─ 校验知识库归属
  └─ DocumentService.upload_file()
      ├─ 单文件：直接保存到 uploads/YYYYMMDD/{doc_id}.pdf
      ├─ 分块：保存到 uploads/chunks/{file_hash}/chunk_{N}
      │   └─ 收齐后 merge → uploads/YYYYMMDD/{doc_id}.pdf
      └─ INSERT ai_document (chunk_status="pending")

用户点击解析
  │
  ▼
[api/doc.py] POST /doc/parse
  └─ DocumentService.enqueue_parse_task(doc_id, user)
      └─ Redis Rpush → "doc:parse:queue"

后台 Worker [services/task_worker.py]
  │
  ▼
Redis BLpop → 获取任务
  └─ DocumentChunkService.parse_document(doc_id, user)
      │
      ├─ 1. 校验文档归属
      ├─ 2. 选择解析器
      │     .pdf → MineruParser (调用 mineru -p xxx.pdf 命令行)
      │     .doc/.docx → DoclingParser (Python API)
      │
      ├─ 3. 执行解析 → content_list [{type, text/image_caption/table_body...}]
      ├─ 4. 提取纯文本
      ├─ 5. chunk_text(full_text, 500, 50) → 文本切片
      │
      ├─ 6. INSERT ai_document_chunk (批量)
      │
      ├─ 7. embed_texts_hybrid(chunks)
      │     └─ POST http://127.0.0.1:9003/embed/sparse
      │         └─ BGE-M3 生成 稠密向量(1024d) + 稀疏向量
      │
      ├─ 8. Milvus.insert(collection="ai_embeddings", data=[
      │       {id, kb_id, doc_id, content, dept_id, vector, sparse_vector}
      │    ])
      │
      └─ 9. UPDATE ai_document SET chunk_status="completed" / "failed"
```

---

## 6. 数据库表关系

```
sys_user ──┬── sys_user_role ──── sys_role ──┬── sys_role_menu ──── sys_menu
           │                                 │
           │                                 └── sys_role_dept
           │
           └── sys_dept

ai_knowledge_base ──── ai_document ──── ai_document_chunk
       │                   │                    │
       │ (kb_id)           │ (doc_id)           │ (chunk_id)
       │                   │                    │
       └── Milvus (kb_id, doc_id, chunk_id, vector, dept_id)

ai_session ──── ai_session_record
    │                │
    (session_id)     (session_id, msg_index)

数据权限隔离字段：dept_id（部门隔离）+ user_id / uploader_id（个人隔离）
```

---

## 7. 核心业务逻辑分析

### 7.1 流式对话服务 (ChatWithLLMService)
- **设计模式**：类方法模式（`@classmethod`），无状态服务
- **核心流程**：用户消息入库 → 加载历史 → 组装 Prompt → LLM 流式 → 助手回复入库
- **RAG 变体**：在普通对话基础上插入检索环节，将检索结果注入用户消息
- **断连处理**：捕获 `GeneratorExit`，确保 LLM 流被关闭

### 7.2 文档处理管道 (DocumentChunkService)
- **解析器选择**：PDF→MinerU，Office→Docling，图片→MinerU OCR
- **文本提取**：从结构化 content_list 中提取 text/table/image/equation
- **切片策略**：固定大小 500 字符 + 句子边界优化 + 50 字符重叠
- **混合向量化**：BGE-M3 同时生成稠密和稀疏向量
- **事务保证**：所有操作在一个 DB 事务中

### 7.3 RAG 混合检索 (rag_retrieval.py)
- **vector_only 模式**：纯稠密向量 ANN（COSINE 距离）
- **hybrid 模式**：稠密 ANN + 稀疏 ANN → RRF 融合（k=60）
- **数据隔离**：通过 Milvus expr filter 按 dept_id 过滤

### 7.4 认证授权体系
- **JWT**：HS256 签名，包含 user_id/roles/permissions/dept_id/data_scope
- **RBAC**：RuoYi 经典五表（用户-角色-菜单）
- **数据权限**：支持 5 级（全部/自定义/本部门/本部门及以下/仅本人）
- **权限校验**：`RequirePermission(perm_string)` 依赖注入

---

## 8. 可优化点

### 8.1 架构层面

| 问题 | 位置 | 建议 |
|------|------|------|
| **API 层直接操作 DAO** | [api/chat.py:25](app/api/chat.py#L25)、[api/doc.py:104](app/api/doc.py#L104)、[api/knowledge_base.py:34](app/api/knowledge_base.py#L34) | API 层应只调用 Service 层，不应直接调用 DAO。如 chat.py 中 `SessionDao.get_by_id` 应封装到 SessionService |
| **Service 层全是 @classmethod** | 所有 Service 文件 | 改用实例方法 + FastAPI DI 注入，提高可测试性和扩展性；当前无状态但不利于 mock |
| **缺少 Service 接口/抽象** | 全局 | 引入 Protocol/ABC 定义接口契约，便于 mock 测试和服务降级切换 |
| **DAO 层滥用 `**filters` 动态属性** | [dao/document_dao.py:24-37](app/dao/document_dao.py#L24-L37) | `hasattr + getattr` 动态过滤存在安全风险（任意属性注入）和维护隐患，建议改为显式参数 |
| **system.py API 中混用 ORM 和原生 SQL** | [api/auth.py:24-65](app/api/auth.py#L24-L65)、[api/system.py](app/api/system.py) | auth 和 system 模块使用 `text()` 原生 SQL 拼接，应统一迁移到 SQLAlchemy ORM 或至少使用参数化查询 + DAO 封装 |

### 8.2 性能优化

| 问题 | 位置 | 建议 |
|------|------|------|
| **chunk 数量用 `len(scalars().all())` 计数** | [dao/document_dao.py:119](app/dao/document_dao.py#L119)、[dao/knowledge_base_dao.py:131](app/dao/knowledge_base_dao.py#L131) | COUNT 应使用 `func.count()`，当前实现会把全部结果加载到内存 |
| **历史记录与用户消息串行写入** | [services/chat_service.py:30-31](app/services/chat_service.py#L30-L31) | 保存用户消息和加载历史两者可并行（先 save 再 load 是正确顺序，但 load 可用缓存） |
| **Token 估算粗糙** | [services/chat_service.py:151-155](app/services/chat_service.py#L151-L155) | `len(text)//2` 对中英文混合场景不准确，建议接入 tiktoken 或实际 tokenizer |
| **LLM 客户端全局单例无连接池** | [components/llm/async_llm.py:5-17](app/components/llm/async_llm.py#L5-L17) | `AsyncOpenAI` 单例在高并发下可能成为瓶颈，httpx 自带连接池但建议配置 limits |
| **RedisClient 每次操作创建新连接** | [core/get_redis.py:33-36](app/core/get_redis.py#L33-L36) | `get_client()` 调用 `Redis.from_pool(pool)` 每次新建连接对象（底层共享连接池，但对象创建开销存在）。建议复用单个 Redis 实例 |
| **Milvus connect 标 async 但内部是同步调用** | [core/get_milvus.py:23-40](app/core/get_milvus.py#L23-L40) | `pymilvus.MilvusClient` 是同步客户端，在 async 上下文中调用可能阻塞事件循环。应使用 `run_in_executor` 或异步 Milvus 客户端 |

### 8.3 代码质量

| 问题 | 位置 | 建议 |
|------|------|------|
| **print() 用于调试** | [services/chat_service.py:103-104](app/services/chat_service.py#L103-L104)、[services/chat_service.py:115-116](app/services/chat_service.py#L115-L116)、[document_chunk_service.py](app/services/document_chunk_service.py) 多处 | 应替换为 `logger.debug()` |
| **重复代码：流式输出逻辑** | [services/chat_service.py:42-71](app/services/chat_service.py#L42-L71) 和 [services/chat_service.py:118-148](app/services/chat_service.py#L118-L148) | `chat_stream` 和 `chat_rag_stream` 的 LLM 流式调用 + 保存助手回复逻辑几乎完全相同，应提取为公共方法 |
| **魔法字符串** | [services/chat_service.py:14](app/services/chat_service.py#L14) 等 | `"你是一个AI助手"` 等 system prompt 硬编码，应配置化 |
| **RAG 检索后 records[:-1] 逻辑脆弱** | [services/chat_service.py:111](app/services/chat_service.py#L111) | 依赖最后一条是用户消息的假设隐式成立，若消息列表顺序出错会导致检索结果丢失 |
| **doc_parse.py 中注释掉的代码** | [components/rag/doc_parse.py:99-101](app/components/rag/doc_parse.py#L99-L101) | 应删除 |
| **parser.py 文件巨大（2696行）** | [components/rag/parser.py](app/components/rag/parser.py) | 单一文件包含 Parser 基类 + MineruParser + DoclingParser + PaddleOCRParser，应拆分为独立文件 |
| **异常处理吞掉错误** | [services/document_chunk_service.py:141-145](app/services/document_chunk_service.py#L141-L145) | `except HTTPException: raise; except Exception: ...` 捕获范围过大，应具体化 |
| **异步函数内同步 I/O** | [services/document_chunk_service.py:56-63](app/services/document_chunk_service.py#L56-L63) | `parser.parse_document()` 内部调用了子进程和同步 I/O，未用 `run_in_executor` 包装 |
| **/chat/stop 端点未实现** | [api/chat.py:72-78](app/api/chat.py#L72-L78) | 仅有 `pass`，需实现真正的流中断逻辑（可以使用 asyncio.Event 或 cancel token） |

### 8.4 安全层面

| 问题 | 位置 | 建议 |
|------|------|------|
| **JWT Secret 硬编码** | [config/config.py:21](app/config/config.py#L21) | 应仅从环境变量注入，移除代码中的默认值 |
| **数据库密码默认值 `123456`** | [config/config.py:30](app/config/config.py#L30) | 同上，移除硬编码默认密码 |
| **CORS allow_origins=["*"]** | [main.py:69](app/main.py#L69) | 生产环境应限制为具体域名 |
| **upload 路径未限制访问** | [api/doc.py:123-177](app/api/doc.py#L123-L177) | `/doc/view/{doc_id}` 中自行解析 JWT 的实现与 Depends 重复，应复用 `AuthUtil` |
| **SQL 拼接使用 f-string** | [api/system.py:47](app/api/system.py#L47) 等多处 | `text(f"SELECT ... WHERE {where}")` 已有 `:param` 绑定但 WHERE 条件动态拼接，确保了参数化但拼接字符串增加了代码复杂度 |

---

## 9. 依赖关系总结图

```
                    ┌──────────────┐
                    │   main.py    │
                    │ (App入口)     │
                    └──┬────────┬──┘
                       │        │
              ┌────────▼──┐ ┌──▼──────────┐
              │  config   │ │  core/db     │
              │ (Settings) │ │ (asyncpg)    │
              └───────────┘ └──┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐   ┌────────▼────────┐   ┌───────▼───────┐
   │ api/ (6个)  │   │  services/ (6个) │   │  dao/ (5个)   │
   │ 路由+校验   │──►│  业务编排       │──►│ 纯SQL操作     │
   └─────────────┘   └────────┬────────┘   └───────┬───────┘
                              │                    │
              ┌───────────────┼────────────────────┤
              │               │                    │
     ┌────────▼──────┐  ┌────▼─────┐     ┌────────▼──────┐
     │ components/   │  │ models/  │     │   core/       │
     │  llm  rag     │  │ (ORM)    │     │  auth perm    │
     │  memory       │  │          │     │  redis milvus │
     │  context      │  │schemas/  │     │  exception    │
     │  intent tool  │  │(DTO)     │     │  data_scope   │
     └───────────────┘  └──────────┘     └───────────────┘
```

---

## 10. 综合评价

### 优势
1. **清晰的分层架构**：api → services → dao → models 职责分明
2. **完整的 RAG 管道**：上传→解析→切片→向量化→混合检索→LLM 生成，链路完整
3. **混合检索方案**：稠密(BGE-M3) + 稀疏(BM25) + RRF 融合，检索质量较好
4. **数据权限隔离**：支持 RuoYi 五级数据权限 + Milvus 级别过滤
5. **异步支持全面**：FastAPI async + SQLAlchemy async + httpx async + Redis async
6. **可扩展的解析器**：注册表模式支持多种解析引擎

### 待改进
1. **Service 全静态方法** + **API 直调 DAO** 破坏了分层纯粹性
2. **高并发下潜在瓶颈**：同步 Milvus 调用、无连接池管理
3. **代码重复**：流式对话的两个方法大量重复
4. **配置安全**：敏感信息有默认值
5. **测试缺失**：未见单元测试或集成测试代码
6. **/chat/stop 端点未实现**：无法中断正在进行的流式输出
