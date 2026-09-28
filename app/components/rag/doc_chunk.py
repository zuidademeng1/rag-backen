import re

"""
切块：条款优先切分

制度文件通常有「第X章」「第X条」结构，按条款切分能让检索更精准、
并且能追溯到具体条款号（section）。无条款结构的文档回退固定长度切分。
"""

# 条款/章节边界：第X条 / 第X章 / 第X节（X 为中文或阿拉伯数字）
_BOUNDARY_RE = re.compile(r'第([一二三四五六七八九十百千万零〇\d]+)([章节条])')

# 固定长度切分时找句子边界的结束符
_SENTENCE_ENDS = ['。', '！', '？', '.', '!', '?', '\n']


def _fixed_chunk(text: str, chunk_size: int, overlap: int) -> list[str]:
    """固定长度切分（作为无条款结构/超长条款时的回退）"""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            for sep in _SENTENCE_ENDS:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    chunk = chunk[:last_sep + 1]
                    end = start + last_sep + 1
                    break
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def _emit(body: str, section: str, chunk_size: int, overlap: int) -> list[dict]:
    """把一段正文按长度切成块，并附上 section 标签"""
    if not body:
        return []
    if len(body) <= chunk_size:
        return [{"content": body, "section": section}]
    return [{"content": c, "section": section} for c in _fixed_chunk(body, chunk_size, overlap)]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """将文本按「条款优先」切分成块。

    Returns:
        list[dict]: 每项 {"content": str, "section": str}
        section 形如「第一章 第一条」，无条款结构时为 ""
    """
    if not text or not text.strip():
        return []

    boundaries = list(_BOUNDARY_RE.finditer(text))
    if not boundaries:
        # 无条款结构，回退固定长度切分
        return [{"content": c, "section": ""} for c in _fixed_chunk(text, chunk_size, overlap)]

    result = []
    current_chapter = ""

    for i, m in enumerate(boundaries):
        start = m.start()
        end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(text)
        seg = text[start:end].strip()
        if not seg:
            continue

        heading = f"第{m.group(1)}{m.group(2)}"
        kind = m.group(2)

        if kind in ("章", "节"):
            # 章节标题段：只更新当前章节标记；若标题后还跟了实质内容，也切出来
            current_chapter = heading
            if len(seg) > 20:
                result.extend(_emit(seg, heading, chunk_size, overlap))
            continue

        # 条款（条）
        section = f"{current_chapter} {heading}".strip() if current_chapter else heading
        result.extend(_emit(seg, section, chunk_size, overlap))

    return result
