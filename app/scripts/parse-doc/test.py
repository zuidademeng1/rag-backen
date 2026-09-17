import os
import time
import re

from pypdf import PdfReader
from typing import List

# 用pypdf来解析PDF文件
def parse_pdf(file_path: str) -> str:
    # 开始解析
    start = time.time()
    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text)
    result = "\n".join(texts)
    elapsed = time.time() - start
    print(f"解析完成，耗时: {elapsed:.3f}秒")
    # 清洗文本
    result = clean_parsed_text(result)
    return result

# 清洗解析后的文本
def clean_parsed_text(text: str, rules: list[str] | None = None) -> str:
    """高级清理：解析后按需调用"""
    if rules is None:
        rules = ["page_number", "special_chars", "excessive_whitespace"]

    if "header_footer" in rules:
        # 去除页眉页脚（根据业务规则）
        lines = text.split("\n")
        lines = [l for l in lines if not _is_header_or_footer(l)]
        text = "\n".join(lines)

    if "page_number" in rules:
        # 去除页码
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)

    if "special_chars" in rules:
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    if "excessive_whitespace" in rules:
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'(?:[ \t]*\n){3,}', '\n\n', text)
        text = text.strip()

    return text


# 
# 按照段落切块 并设置overloap
def chunk_by_paragraph(
    text: str,
    chunk_overlap: int = 128,
) -> List[dict]:
    """按段落切块，支持块间重叠

    以连续空行（\n\n+）作为段落分隔符，
    每个段落作为一个独立的块。
    当 chunk_overlap > 0 时，相邻块之间会包含重叠内容。

    Args:
        text: 输入文本
        chunk_overlap: 相邻块之间的重叠字符数，0 表示不重叠

    Returns:
        [{"chunk_index": 0, "content": "...", "char_count": 123}, ...]
    """
    if not text or not text.strip():
        return []

    paragraphs = re.split(r'\n{2,}', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    if chunk_overlap <= 0:
        result = []
        for i, para in enumerate(paragraphs):
            result.append({
                "chunk_index": i,
                "content": para,
                "char_count": len(para),
            })
        return result

    result = []
    for i, para in enumerate(paragraphs):
        overlap_parts = []
        accumulated = 0
        for j in range(i - 1, -1, -1):
            prev = paragraphs[j]
            needed = chunk_overlap - accumulated
            if needed <= 0:
                break
            if len(prev) <= needed:
                overlap_parts.insert(0, prev)
                accumulated += len(prev)
            else:
                overlap_parts.insert(0, prev[-needed:])
                accumulated += needed
                break

        if overlap_parts:
            overlap_text = '\n\n'.join(overlap_parts)
            content = overlap_text + '\n\n' + para
        else:
            content = para

        result.append({
            "chunk_index": i,
            "content": content,
            "char_count": len(content),
        })

    return result

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "docx", "中华人民共和国环境保护行业标准.pdf")
    print(f"文件路径: {pdf_path}")
    
    text = parse_pdf(pdf_path)
    chunks = []
    chunkes = chunk_by_paragraph(text=text)
    print(f"----------------------切块后-------------------------------")
    for i, chunk in enumerate(chunkes):
        print(f"第{i}个段落: ")
        print(f"{chunk['content']}")
        print(f"==================================================================")

