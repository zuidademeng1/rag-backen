import json
import tempfile

from fastapi import HTTPException
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from torch._dynamo import source

from app.components.rag.doc_chunk import chunk_text
from app.components.rag.parser import get_parser
from app.dao.document_chunk_dao import DocumentChunkDao
from app.dao.document_dao import DocumentDao
from app.core.get_milvus import MilvusClient
from app.models.document_chunk import DocumentChunk

from app.components.rag.doc_embedding import embed_texts_hybrid
from app.components.rag.doc_parse import parse_document_by_id
from app.utils.auth_util import CurrentUser
from app.utils.common_util import generate_fast_id
from app.config.config import settings


def _to_text(value) -> str:
    """把解析器返回的字段值统一转成字符串。

    MinerU 的 text 字段有时是字符串、有时是 list（分行文本），
    统一转成 str，避免后续 join 时报 TypeError。
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_to_text(v) for v in value)
    return str(value)


class DocumentChunkService:

    @classmethod
    async def parse_document(cls, db: AsyncSession, doc_id: str, user: CurrentUser) -> dict:
        # 1. 校验文档归属
        doc = await DocumentDao.get_by_id(db, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        if str(doc.uploader_id) != str(user.user_id):
            raise HTTPException(status_code=403, detail="只能操作自己的文档")

        try:
            print("-------文档解析开始------------")
            # 2. 解析文档
            # text = await parse_document_by_id(doc_id, db)
            file_path = doc.file_path
            # 获取文件后缀
            ext = Path(file_path).suffix.lower()

            # 2. 根据文件类型选择解析器
            # 如果是pdf 用MinerU
            if ext == ".pdf":
                parser_type = "mineru"
            # 如果是office 用Docling
            elif ext in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}:
                parser_type = "docling"  # Docling 原生支持 Office
            # MinerU 也支持图片 OCR
            elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
                parser_type = "mineru"
            else:
                parser_type = "mineru"

            # 3. 用 parser 解析，得到结构化 content_list
            parser = get_parser(parser_type)
            # 开发难题 TODO
            content_list = parser.parse_document(
                file_path=file_path,
                output_dir=tempfile.gettempdir(),  # 解析产物的输出目录
                source="local",    # 使用本地模型
                backend="pipeline",  # 使用 pipeline 模式，不需要 VLM 模型
            )

            # 4. 从 content_list 中提取纯文本（忽略图片、表格的二进制内容）
            texts = []
            for item in content_list:
                if item.get("type") == "text":
                    texts.append(_to_text(item.get("text", "")))
                elif item.get("type") == "table":
                    # 表格可以提取 caption + 把表格数据转成文字描述
                    caption = item.get("table_caption", "")
                    body = item.get("table_body", [])
                    if body:
                        texts.append(f"{caption}\n{json.dumps(body, ensure_ascii=False)}")
                    elif caption:
                        texts.append(caption)
                # type == "equation": 通常已有 text 字段
                elif item.get("type") == "equation":
                    texts.append(_to_text(item.get("text", "")))
                # type == "image": 图片本身没有文字，但有 caption
                elif item.get("type") == "image":
                    caption = item.get("image_caption", "") or item.get("image_footnote", "")
                    if caption:
                        texts.append(caption)

            full_text = "\n".join(_to_text(t) for t in texts)
            print(f"{full_text}")
            if not full_text.strip():
                raise HTTPException(status_code=400, detail="文档内容为空，无法切块")
            print("-------文档解析完成------------")

            # 3. 切块
            print("-------切块开始------------")
            chunks = chunk_text(full_text)
            if not chunks:
                raise HTTPException(status_code=400, detail="文档内容为空，无法切块")
            print("-------切块完成------------")
            # 4. 保存切块到数据库
            chunk_records = []
            #enumerate 是 Python 内置函数，遍历列表的同时，自动给你一个递增的下标。它把每个元素变成 (下标, 元素) 的元组，下标从0开始
            for i, content in enumerate(chunks):
                record = DocumentChunk(
                    chunk_id=generate_fast_id(),
                    doc_id=doc_id,
                    chunk_index=i,
                    content=content,
                    char_count=len(content),
                    dept_id=str(user.dept_id) if user.dept_id is not None else None,
                )
                chunk_records.append(record)
            print("-------切块保存到数据库------------")
            await DocumentChunkDao.batch_insert(db, chunk_records)
            print("-------切块保存到数据库------------")
            print("-------开始向量化------------")
            # 5. 向量化（稠密 + 稀疏）
            dense_vectors, sparse_vectors = await embed_texts_hybrid(chunks)
            print("-------向量化完成------------")
            # 6. 存入Milvus
            client = MilvusClient.get_client()
            milvus_data = [
                {
                    "id": chunk_records[i].chunk_id,
                    "kb_id": doc.kb_id,
                    "doc_id": doc_id,
                    "filename":doc.file_name,
                    "content": chunks[i],
                    "chunk_index": i,
                    "dept_id": str(user.dept_id) if user.dept_id is not None else None,
                    "vector": dense_vectors[i],
                    "sparse_vector": sparse_vectors[i],
                }
                for i in range(len(chunks))
            ]
            client.insert(collection_name=settings.milvus_collection, data=milvus_data)

            # 7. 更新文档状态
            doc.chunk_status = "completed"

            return {"doc_id": doc_id, "chunk_count": len(chunks)}

        except HTTPException:
            raise
        except Exception as e:
            doc.chunk_status = "failed"
            raise HTTPException(status_code=500, detail=f"文档解析失败: {e}")
        finally:
            await DocumentDao.update(db, doc)
