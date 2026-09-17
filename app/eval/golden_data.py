"""RAG 评估黄金数据集（示例）。

每条数据同时服务两个评估层面：
- 检索层：用 query + relevant_chunks（标注相关分块）
- 端到端生成层：用 query + ground_truth（标准答案）

相关分块用 (doc_id, chunk_index) 标注，因为 chunk_id 是 generate_fast_id()
动态生成的、不稳定，而 doc_id + chunk_index 是稳定的。

示例基于已上传的《国家信息化发展报告（2023年）》PDF
（doc_id=e1aa9522ac4a4cbe814181b0c9484add，切成 135 块）。
"""

# 报告文档 ID（示例数据，按需替换）
REPORT_DOC_ID = "e1aa9522ac4a4cbe814181b0c9484add"


def _c(*indexes: int) -> list[dict]:
    """快捷构造多个相关分块标注。"""
    return [{"doc_id": REPORT_DOC_ID, "chunk_index": i} for i in indexes]


GOLDEN_DATA: list[dict] = [
    # ==================== 单/双分块问题（精确事实类） ====================
    # ---- 基础设施 ----
    {
        "query": "截至2023年底，我国建成的5G基站总数是多少？",
        "relevant_chunks": _c(3, 32),
        "ground_truth": "337.7 万个",
    },
    {
        "query": "2023年我国IPv6活跃用户数达到多少？",
        "relevant_chunks": _c(34),
        "ground_truth": "7.78 亿",
    },
    {
        "query": "我国算力总规模达到多少？",
        "relevant_chunks": _c(3),
        "ground_truth": "超过 230EFLOPS",
    },
    # ---- 数据资源 ----
    {
        "query": "2023年我国数据生产总量是多少？",
        "relevant_chunks": _c(3, 37),
        "ground_truth": "32.85ZB",
    },
    # ---- 数字经济 ----
    {
        "query": "2023年我国数字经济核心产业增加值占GDP的比重是多少？",
        "relevant_chunks": _c(4),
        "ground_truth": "10% 左右",
    },
    {
        "query": "2023年我国软件业务收入是多少？",
        "relevant_chunks": _c(4),
        "ground_truth": "12.33 万亿元",
    },
    {
        "query": "2023年我国跨境电商进出口额是多少？",
        "relevant_chunks": _c(44),
        "ground_truth": "2.38 万亿元",
    },
    # ---- 数字生活 ----
    {
        "query": "2023年我国网民规模达到多少人？",
        "relevant_chunks": _c(5),
        "ground_truth": "10.92 亿人",
    },
    {
        "query": "2023年全国电子社保卡领用人数是多少？",
        "relevant_chunks": _c(50),
        "ground_truth": "9.62 亿",
    },
    # ---- 数字教育 / 健康 ----
    {
        "query": "国家智慧教育平台累计注册用户达到多少？",
        "relevant_chunks": _c(46),
        "ground_truth": "突破 1 亿",
    },
    # ---- 网络法治 / 安全 ----
    {
        "query": "针对生成式人工智能，我国发布了哪部管理办法？",
        "relevant_chunks": _c(7, 61),
        "ground_truth": "《生成式人工智能服务管理暂行办法》",
    },
    {
        "query": "2023年发布了多少项网络安全国家标准？",
        "relevant_chunks": _c(8, 65),
        "ground_truth": "47 项",
    },

    # ==================== 跨分块问题（总结类，每个 ≥3 个切块） ====================
    {
        "query": "我国区块链技术发展取得了哪些成效？",
        "relevant_chunks": _c(2, 29, 30),
        "ground_truth": (
            "区块链技术体系不断发展壮大，截至2023年11月区块链领域论文数量全球占比34.4%、"
            "专利申请数量占比57.9%，均居世界前列；完成首批国家区块链创新应用试点终期评估，"
            "覆盖全国近300个场景"
        ),
    },
    {
        "query": "我国数据资源开发利用取得了哪些进展？",
        "relevant_chunks": _c(3, 37, 38, 39),
        "ground_truth": (
            "2023年数据生产总量达32.85ZB，大数据产业规模1.74万亿元；"
            "国资数据集团累计超过20家；地方政府开放有效数据集达34万个，增长22%"
        ),
    },
    {
        "query": "我国网络空间国际合作有哪些进展？",
        "relevant_chunks": _c(9, 69, 70, 71),
        "ground_truth": (
            "习近平主席多次阐述网络空间国际合作的中国主张，世界互联网大会乌镇峰会成功举办，"
            "发布《全球人工智能治理倡议》，参与《数字贸易测度手册》修订，"
            "举办多次数字领域高层对话和合作论坛"
        ),
    },
    {
        "query": "我国电子政务建设取得了哪些成效？",
        "relevant_chunks": _c(6, 56, 57),
        "ground_truth": (
            "全国一体化政务服务平台使用总量超888亿人次，"
            "92.5%的省级行政许可事项实现网上受理和最多跑一次，"
            "形成一网通办、跨省通办的服务模式"
        ),
    },
    {
        "query": "我国5G网络建设取得了哪些成果？",
        "relevant_chunks": _c(3, 32, 52),
        "ground_truth": (
            "5G基站总数达337.7万个，5G移动电话用户8.05亿户，"
            "基本实现乡镇级以上区域和有条件的行政村覆盖"
        ),
    },
]
