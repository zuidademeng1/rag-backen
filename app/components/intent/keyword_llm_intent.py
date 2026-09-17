from app.components.intent.base_intent import IntentBase
from app.components.llm.async_llm import llm_chat

# 闲聊类关键词（问候 / 情绪 / 客套）
_chat_keywords: list[str] = [
    "你好", "您好", "哈喽", "嗨", "hello", "hi", "在吗", "在不在",
    "谢谢", "感谢", "再见", "拜拜", "晚安", "早安", "午安",
    "早上好", "中午好", "晚上好", "你是谁", "你叫什么",
    "哈哈", "嘿嘿", "聊天", "聊聊", "无聊", "爱你",
]

# 知识问答类关键词（政策 / 制度 / 流程 / 疑问词）
_rag_keywords: list[str] = [
    "政策", "规定", "制度", "流程", "标准", "要求", "条件",
    "报销", "请假", "加班", "工资", "福利", "假期", "年假",
    "依据", "规范", "办法", "条例", "条款", "定义", "含义",
    "区别", "对比", "是什么", "为什么", "有哪些", "多少钱",
    "查询", "资料", "文档", "文件",
]

# 报告生成类关键词（产出物 / 写作动作）
_report_keywords: list[str] = [
    "报告", "总结", "方案", "公文", "汇报", "计划", "规划",
    "演讲稿", "发言稿", "述职", "起草", "撰写",
    "帮我写", "写一份", "写一篇", "写个", "写一个", "写一份材料",
]

"""基于关键词和LLM的混合意图识别，先关键词匹配，匹配不出来再用llm进行意图识别"""
class KeywordLlmIntent(IntentBase):
    name = "keyword_llm"
    """
    关键词和LLM的混合意图识别实现方法
    """
    async def intent_recognition(self, query: str) -> str:
        # 1. 关键词匹配
        for kw in _chat_keywords:
            if kw in query:
                return "chat"
        for kw in _rag_keywords:
            if kw in query:
                return "rag_qa"
        for kw in _report_keywords:
            if kw in query:
                return "report"

        # 2. LLM 兜底分类
        prompt = f"""判断以下用户问题的意图，只返回一个词：chat、rag_qa 或 report。
        chat：问候、闲聊、情感交流
        rag_qa：询问知识、政策、数据、概念等需要查文档的问题
        report：撰写报告、工作总结、材料、公文等
        问题：{query}
        意图："""
        messages = [
            {"role": "system", "content": "你是一个意图分类器，只输出一个词。"},
            {"role": "user", "content": prompt},
        ]
        # 温度设置最低
        result = (await llm_chat(messages, temperature=0.1)).strip().lower()
        if result in ("chat", "rag_qa", "report"):
            return result
        return "rag_qa"  # 兜底
