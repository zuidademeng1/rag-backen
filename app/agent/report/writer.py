from typing import AsyncGenerator

from app.agent.report.base_report_agent import BaseReportAgent


class ReportWriterAgent(BaseReportAgent):
    agent_name = "report_writer"

    """
    写报告agent
    """

    async def run_agent(self, **kwargs) -> AsyncGenerator[str, None]:
        # 1. 获取参数
        query = kwargs.get("query", "")
        task_id = kwargs.get("task_id")
        outline = kwargs.get("outline", "")
        materials = kwargs.get("materials", {})

        # 2. 初始化任务
        self.set_task_id(task_id)
        await self.update_task_status(self.TASK_STATUS_RUNNING)

        # 3. 解析大纲章节
        chapters = self._parse_chapters(outline)
        total = len(chapters)

        # 4. 逐章撰写
        chapter_content = []
        async for chunk in self._write_chapter(chapters, query):
            chapter_content.append(chunk)
            yield chunk

        # 保存章节内容
        # await self.save_task_data(f"chapter_{idx}", {
        #     "title": chapter["title"],
        #     "content": "".join(chapter_content),
        # })

        await self.update_task_status(self.TASK_STATUS_FINISHED)

    """解析大纲 markdown"""
    @staticmethod
    def _parse_chapters(outline: str) -> list[dict]:
        """解析大纲 markdown，提取章节树

        返回递归结构：
        [
          {
            "title": "章节标题",
            "level": 2,
            "children": [
              {"title": "子标题", "level": 3, "children": [...]},
              ...
            ]
          },
          ...
        ]
        以二级标题（##）作为根章节，更深层级递归嵌套。
        若无二级标题则用一级标题（#）作为根。
        """
        if not outline or not outline.strip():
            return []

        # 1. 提取所有标题行
        raw: list[dict] = []
        for line in outline.splitlines():
            line = line.strip()
            if not line or not line.startswith("#"):
                continue
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()
            raw.append({"title": title, "level": level, "children": []})

        if not raw:
            return []

        # 2. 确定根节点级别
        levels = {h["level"] for h in raw}
        root_level = 2 if 2 in levels else (1 if 1 in levels else min(levels))

        # 3. 构建树：将标题按层级插入父节点
        def _build(nodes: list[dict], level: int) -> list[dict]:
            """将 raw 中指定层级的标题构建为树节点，并递归构建子节点"""
            result = []
            i = 0
            while i < len(nodes):
                h = nodes[i]
                if h["level"] != level:
                    i += 1
                    continue
                # 收集此标题下的所有子节点（更深的层级）
                j = i + 1
                children_pool = []
                while j < len(nodes):
                    if nodes[j]["level"] <= level:
                        break
                    children_pool.append(nodes[j])
                    j += 1
                h["children"] = _build(children_pool, level + 1)
                result.append(h)
                i = j
            return result

        return _build(raw, root_level)

    """
    递归撰写章节
        chapters: 整个大纲树
        query: 用户输入
        materials: 查知识库内容
    """
    @staticmethod
    async def _write_chapter(chapters: list[dict], query: str, materials: list | None = None) -> AsyncGenerator[
        str, None]:
        # 递归遍历树，逐节点生成，后文带上前文的 summary 作为上下文
        async def _write_tree(nodes: list[dict], summary: str) -> AsyncGenerator[str, None]:
            for node in nodes:
                # 构建 prompt
                title = node["title"]
                prompt = (
                    f"以下是报告的一部分，请根据标题撰写内容。\n"
                    f"总体需求：{query}\n"
                    f"当前章节：{title}\n"
                )
                if summary:
                    prompt += f"\n上文已写内容摘要：\n{summary}\n"
                if materials:
                    prompt += f"\n参考资料：\n{chr(10).join(str(m) for m in materials)}\n"
                prompt += f"\n请撰写「{title}」部分的完整内容，使用 Markdown 格式。\n"

                messages = [
                    {"role": "system", "content": "你是一个专业的报告撰写助手。"},
                    {"role": "user", "content": prompt},
                ]

                from app.components.llm.async_llm import llm_chat_stream

                section = ""
                async for chunk in llm_chat_stream(messages, temperature=0.5):
                    section += chunk
                    yield chunk

                # 追加到 summary，作为后续章节的上下文
                summary += f"\n\n## {title}\n{section}"

                # 递归处理子节点
                if node.get("children"):
                    async for chunk in _write_tree(node["children"], summary):
                        yield chunk

        async for chunk in _write_tree(chapters, ""):
            yield chunk


if __name__ == '__main__':
    outline = """
    # 2026年第一季度销售业绩报告大纲

## 一、执行摘要  
- 简要概述本季度整体销售表现  
- 关键业绩指标（KPI）达成情况  
- 主要亮点与挑战总结  

## 二、销售目标与实际完成情况对比  
- 年初设定的销售目标（按区域、产品线、客户类型等维度）  
- 实际销售额、销量及达成率  
- 同比（vs. 2025年Q1）与环比（vs. 2025年Q4）分析  

## 三、分维度销售表现分析  
### 3.1 按产品/服务类别  
- 各产品线销售额、毛利率及增长贡献  
- 畅销品与滞销品分析  

### 3.2 按区域/市场  
- 各大区或国家/地区销售数据对比  
- 区域增长驱动因素与瓶颈  

### 3.3 按客户类型  
- 大客户、中小客户、新客户与老客户贡献占比  
- 客户留存率与新增客户数量  

## 四、销售渠道表现  
- 线上 vs. 线下渠道销售对比  
- 直销、分销、电商平台等渠道效能分析  
- 渠道策略调整效果评估  

## 五、市场竞争与外部环境影响  
- 主要竞争对手动态及市场份额变化  
- 宏观经济、政策法规、行业趋势对销售的影响  
- 季节性因素或突发事件（如供应链中断）的应对情况  

## 六、问题与挑战  
- 未达标区域或产品的原因剖析  
- 客户反馈与投诉集中点  
- 内部流程或资源瓶颈  

## 七、改进措施与下一季度行动计划  
- 针对性优化策略（产品、定价、促销、渠道等）  
- 销售团队激励与培训计划  
- Q2销售目标初步设定与关键举措  

## 八、结论  
- 对2026年Q1销售工作的总体评价  
- 对全年销售目标达成的信心与展望
    """
    import asyncio

    chapters = ReportWriterAgent._parse_chapters(outline=outline)

    async def main():
        async for chunk in ReportWriterAgent._write_chapter(
            chapters=chapters,
            query="写一份关于2026年第一季度销售业绩的报告，包含各区域销售数据对比、同比分析、问题总结和改进建议，有些要给出三级标题",
        ):
            print(chunk, end="", flush=True)
        print()

    asyncio.run(main())
