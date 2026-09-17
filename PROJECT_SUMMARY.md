# Agent应用开发 多智能体客服系统 | ReAct 范式 · 大模型路由 · 记忆沙箱 · Python

## 项目定位

基于 FastAPI 构建的企业级 RAG 智能问答与多智能体后端：文档解析（MinerU / Docling / PaddleOCR）→ 混合向量检索（Milvus 稠密 + 稀疏 RRF）→ 意图路由 → LLM 流式问答与报告生成；以 RuoYi RBAC 权限体系提供部门级数据隔离。技术栈为 Python / FastAPI / SQLAlchemy / Redis / Milvus / BGE-M3 / Qwen3-max。

## 1. 多智能体路由与工具链路

### 总结

- 以 `IntentBase` 抽象定义意图识别契约，`KeywordLlmIntent` 实现"关键词优先、LLM 兜底"的混合路由：关键词命中直接短路，未命中时以 `temperature=0.1` 的低随机性交给 LLM 分类，固定输出 `chat / rag_qa / report` 三路标签，实现精准分流。
- 对话服务按意图进入不同链路：普通流式问答 `/chat/stream`、RAG 检索增强问答 `/chat/rag-stream`、报告 Agent 管线，路由结果与执行链路解耦。
- 工具层以 `ToolDef / ToolResult` 定义统一契约，`register_tool / get_tool / list_tools / call_tool` 构成轻量 ToolManager：动态注册、按名查找、统一调度、异常兜底，`knowledge_retrieval` 已将 RAG 检索封装为可调用工具。
- 企业级链路约束：JWT + RBAC 权限校验 + `dept_id` 数据隔离贯穿 API、检索与工具调用。

### 闪光点

- "快慢结合"路由：关键词短路是 O(1) 成本，LLM 兜底保证覆盖，避免每轮都付出一次大模型路由开销，兼顾延迟与准确率。
- 工具调用统一收口：`call_tool` 捕获异常并返回 `ToolResult(success=False)`，为本地容灾降级预留了挂载点；新工具只需注册，不侵入对话主流程。
- ReAct 循环骨架已就位：`BaseAgent` 抽象 + `SingleAgent` 骨架 + 工具返回值注入，构成"观察（检索结果）→ 行动（工具调用）→ 推理（LLM）"的最小闭环，显式 thought/action 编排可在骨架内直接补齐。

## 2. 技能编排与按需加载

### 总结

- 报告生成以 `ReportGraph` 编排多 Agent 流水线：`planner → retrieve → writer → polish → revise`，其中大纲规划与正文撰写已实现，素材检索、润色、修订为扩展位。
- 每个 Agent 继承 `BaseAgent`，具备任务状态（RUNNING / FINISHED）与步骤进度上报，前端可实时看到执行阶段。
- `ReportWriterAgent` 将大纲解析为章节树并递归逐章撰写，后续章节携带"上文摘要"接力，实现长报告的结构化、增量式生成。
- 按模板的 Anthropic Agent Skills 思路，SKILL.md 的"发现 → 激活 → 执行"三段式可作为技能挂载机制补充到 agent 模块，与现有流水线一一对应。

### 闪光点

- 把"技能"落成可编排的 Agent 流水线而非单个 Prompt：规划、检索、写作、润色、修订各环节可独立替换与扩展，是工程化程度更高的技能编排形态。
- 章节树递归撰写解决了长文生成的结构一致性问题，且天然支持按章节按需加载素材与技能。
- 任务状态 + 步骤进度让多智能体执行过程可观测，为沙箱评测埋点打下基础。

## 3. 解决长上下文记忆遗忘

### 总结

- 双层记忆隔离：短期记忆（STM）用 Redis List 保存会话消息，上限 50 条并 `ltrim` 截断；长期记忆（LTM）预留用户画像 / 偏好存储，会话状态以 Redis Hash 维护。
- 上下文压缩组件提供 `truncate / summarize / hybrid` 三种策略，默认超过 4000 token 阈值触发；hybrid 策略将早期历史压缩为 LLM 摘要，最近 10 条原文保留。
- 渐进式累积压缩：摘要持久化到 `ctx:session:{id}:summary`（TTL 24 小时），下次会话直接 `load_summary()` 加载，不再重放全部原始历史。
- 压缩发生在"读时变换"，不修改 Memory 原始数据，会话记录仍完整落库。

### 闪光点

- 摘要"只写一次、反复复用"，把多轮对话的历史重放成本从随轮数增长的 O(n) 压到"摘要 + 固定窗口"的 O(1) 量级，是长会话成本可控的关键设计。
- 原始记录（数据库）与压缩摘要（Redis）分层隔离，策略可热切换，数据不互相污染。
- "早期信息进摘要、近期细节原样保留"的 hybrid 设计，兼顾长期事实连续性与短期细节精度。

## 4. 落地 Agentic RAG 与幻觉抑制

### 总结

- 完整文档链路：上传（支持分块）→ Redis 异步队列 → 解析器注册表选择（PDF/MinerU、Office/Docling、图片 OCR）→ 500 字符 + 句子边界 + 50 重叠切块 → BGE-M3 稠密 + 稀疏向量化 → Milvus 入库。
- 检索支持 `vector_only` 与 `hybrid` 两种模式，hybrid 以 `RRFRanker(k=60)` 融合稠密 ANN（COSINE）与稀疏 ANN（IP）。
- 检索结果强绑定来源字段：`id / score / doc_id / filename / chunk_index / kb_id / dept_id` 随命中片段一并返回，并被注入"请基于以下资料回答问题"的增强消息，答案可溯源。
- 检索即工具：`knowledge_retrieval` 以统一 `ToolResult` 注入 Agent，使 RAG 成为 Agent 可调度的能力而非旁路。

### 闪光点

- 混合召回 + RRF 融合比单一稠密向量检索更稳，稀疏向量兜底长尾术语与编号类查询。
- 来源标注与工具返回值强绑定：模型、日志、前端都能看到"答案来自哪个文档第几块"，是幻觉抑制和事实核查的工程基础。
- 企业级约束前置：`dept_id` 检索过滤 + `kb_id / doc_id` 归属校验，知识库不是"全量可查"，检索天然带权限边界。

## 5. 构建端到端沙箱评估闭环

### 总结

- 已保留可复现评估素材：`app/test` 下有文档切块样例（`1.json / 2.json`）与检索命中样例（`3.jsonl`），`test_rag_evaluate.py` 为评估入口，解析器模块配套 pytest 单测。
- 报告 Agent 自带 `__main__` 可执行用例，可独立回放大纲生成与章节撰写流程。
- 模板中的 Sandbox 测试底座、过程指标（耗时 / 路由匹配）、结果指标（意图覆盖）与 LLM Judge（幻觉核查）作为评估闭环的演进目标，可在现有结构化输入输出上直接埋点。

### 闪光点

- "可评测性"已埋入工程结构：路由、检索、生成三层均输出结构化结果（意图标签、检索 hit、流式事件），天然适合指标采集与问题归因。
- 保留黄金样例与自测入口，后续接入 Judge 后可直接回放，实现"开发构建 → 沙箱评测 → 数据归因 → 持续迭代"的闭环。

## 模板能力与项目现状对照

| 模板能力 | 项目现状 |
| --- | --- |
| 售前 / 售后 / 投诉三路分流 | 已实现 `chat / rag_qa / report` 三路路由，标签可按客服场景直接映射 |
| MCP 协议标准化接入业务 API | 当前为内部 `ToolDef / register_tool` 机制，MCP 为扩展点 |
| ToolManager 统一调度与本地容灾降级 | 统一 `call_tool` 与异常兜底已实现，本地降级策略可继续扩展 |
| SKILL.md 发现 → 激活 → 执行 | 技能编排已体现为报告 Agent 流水线，SKILL.md 挂载机制待落地 |
| STM / LTM 双层 + O(1) Token | STM 已实现，LTM 预留；摘要压缩已实现有界上下文（O(1) 级窗口） |
| Numpy / Chroma 双后端知识库 | 当前为 Milvus 混合检索生产后端，Numpy/Chroma 可作为本地降级后端扩展 |
| Sandbox 评测 + LLM Judge | 测试样例与评估入口已备，双层指标与 Judge 闭环待完善 |

## 一句话总结

这是一个从企业知识库到多智能体能力的完整 RAG 后端：以"意图路由 + 动态工具 + 分层记忆 + 混合检索 + 报告流水线"构建客服/办公智能体底座，工程分层清晰、可评测性已预埋，具备向 MCP 技能化、双后端降级与沙箱评测闭环继续演进的完整条件。
