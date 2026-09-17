import asyncio
import os
import time
import re

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.document_dao import DocumentDao
from pypdf import PdfReader

# ---------------------解析pdf文件--------------------------

"""
用pypdf来解析PDF文件
"""
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
    result = _clean_parsed_text(result)
    return result


"""
清洗解析后的文本
"""
def _clean_parsed_text(text: str, rules: list[str] | None = None) -> str:
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
"""
# 判断行是否为页眉页脚
"""
def _is_header_or_footer(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    # 纯数字（页码）
    if stripped.isdigit():
        return True
    # "第 X 页" 或 "Page X" 模式
    if re.match(r'^(第\s*\d+\s*页|Page\s*\d+(\s*of\s*\d+)?|-\s*\d+\s*-)$', stripped, re.IGNORECASE):
        return True
    # 常见页眉页脚关键词
    keywords = ['www.', 'http://', 'https://', '版权所有', 'copyright', '©', 'all rights reserved']
    if any(kw in stripped.lower() for kw in keywords):
        # 网址类或版权信息，且整行不超过 80 字符（长行可能是正文引用）
        if len(stripped) < 10:
            return True
    # 过短的行（< 5 个字符）但排除标点符号
    if len(stripped) < 5 and not all(c in '—–-·、，。！？；：""''『』【】()（）' for c in stripped):
        return True
    return False

"""根据文档ID解析文档内容"""
async def parse_document_by_id(doc_id: str, db: AsyncSession) -> str:

    doc = await DocumentDao.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    ext = doc.file_ext.lower()
    if ext == ".pdf":
        # 把它丢到线程池执行，事件循环继续运行，其他请求不受影响
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, parse_pdf, doc.file_path)
        # return parse_pdf(doc.file_path)
    elif ext in (".docx", ".doc"):
        # TODO: word解析待实现
        raise HTTPException(status_code=501, detail="word文档解析暂未实现")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")


# 解析doc或docx文件
