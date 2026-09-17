import re
from typing import List

"""
切块
"""
# def chunk_by_paragraph(text: str, chunk_overlap: int = 50) -> list[str]:
#     """
#     按段落切块，支持块间重叠
#     """
#     if not text or not text.strip():
#         return []
#
#     # 预处理：将连续非空行合并为段落（解决PDF单\n换行问题）
#     lines = text.split('\n')
#     paras = []
#     buf = []
#     for line in lines:
#         if line.strip():
#             buf.append(line.strip())
#         else:
#             if buf:
#                 paras.append(''.join(buf))
#                 buf = []
#     if buf:
#         paras.append(''.join(buf))
#
#     paragraphs = [p for p in paras if p.strip()]
#
#     if not paragraphs:
#         return []
#
#     if chunk_overlap <= 0:
#         return list(paragraphs)
#
#     result = []
#     for i, para in enumerate(paragraphs):
#         overlap_parts = []
#         accumulated = 0
#         for j in range(i - 1, -1, -1):
#             prev = paragraphs[j]
#             needed = chunk_overlap - accumulated
#             if needed <= 0:
#                 break
#             if len(prev) <= needed:
#                 overlap_parts.insert(0, prev)
#                 accumulated += len(prev)
#             else:
#                 overlap_parts.insert(0, prev[-needed:])
#                 accumulated += needed
#                 break
#
#         if overlap_parts:
#             overlap_text = '\n\n'.join(overlap_parts)
#             content = overlap_text + '\n\n' + para
#         else:
#             content = para
#         result.append(content)
#     return result


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    将文本切分成块
    Args:
        text: 原始文本
        chunk_size: 每块大小
        overlap: 重叠大小
    Returns:
        文本块列表
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size#先按固定长度切
        chunk = text[start:end]

        # 尝试在句子边界切分
        #保证每个分块语义完整，不跨句子
        if end < len(text):
            for sep in ['。', '！', '？', '.', '!   ', '?', '\n']:
                last_sep = chunk.rfind(sep)#在块里找最后一个句子符号
                if last_sep > chunk_size // 2:#这个符号要在块的后半段
                    chunk = chunk[:last_sep + 1]#从块头切到这个符号
                    end = start + last_sep + 1
                    break

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap

    return chunks


