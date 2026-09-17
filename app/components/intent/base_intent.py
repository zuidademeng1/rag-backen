from abc import ABC, abstractmethod

# 意图处理基类抽象类
class IntentBase(ABC):
    name: str = ""

    """
    判断用户输入是否匹配该意图
    固定输出三种意图：chat / rag_qa / report
    """

    @abstractmethod
    async def intent_recognition(self, query: str) -> str:
        """
        :param query: 用户原始问题
        :return: 固定只能返回三个标签之一
            chat: 普通闲聊
            rag_qa: 知识库RAG问答
            report: 生成报告，材料撰写
        """
        pass
