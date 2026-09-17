import json
import os
import shutil#python标准库的文件操作模块
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.get_redis import RedisClient
from app.dao.document_dao import DocumentDao
from app.schemas.document import DocumentEntity
from app.dao.knowledge_base_dao import KnowledgeBaseDao
from app.models.document import Document
from app.utils.auth_util import CurrentUser
from app.utils.common_util import generate_fast_id
from app.schemas.document import DocumentEntity
from app.config.config import settings


ALLOWED_EXTENSIONS = {ext.lower() for ext in settings.allowed_extensions}


class DocumentService:

    @classmethod
    async def upload_file(
        cls,
        db: AsyncSession,
        file: UploadFile,
        kb_id: str,
        user: CurrentUser,
        chunk_number: int | None = None,
        total_chunks: int | None = None,
        file_hash: str | None = None,
    ) -> dict:
        """上传文件（支持单文件和分块上传）"""
        # 1. 校验文件扩展名
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

        # 2. 校验知识库归属
        kb = await KnowledgeBaseDao.get_by_id(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if str(kb.user_id) != str(user.user_id):
            raise HTTPException(status_code=403, detail="只能上传到自己的知识库")

        # 3. 准备公共字段
        doc_id = generate_fast_id()
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        save_dir = Path(settings.upload_dir) / today

        # 单文件上传
        if chunk_number is None or total_chunks is None or total_chunks == 1:
            save_dir.mkdir(parents=True, exist_ok=True)
            file_path = str(save_dir / f"{doc_id}{ext}")
            meta = await cls._save_single_file(db, file, save_dir, doc_id, ext)
            return await cls.save_document_record(db, doc_id, meta["file_name"], meta["file_size"], file_path, ext, kb_id, user)

        # 分块上传
        meta_or_progress = await cls._save_chunk(db, file, ext, chunk_number, total_chunks, file_hash, save_dir, doc_id)
        if meta_or_progress.get("status") == "continue":
            return meta_or_progress
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(save_dir / f"{doc_id}{ext}")
        return await cls.save_document_record(db, doc_id, meta_or_progress["file_name"], meta_or_progress["file_size"], file_path, ext, kb_id, user)

    """
    单文件上传 
    """
    @classmethod
    async def _save_single_file(
        cls, db: AsyncSession, file: UploadFile, save_dir: Path, doc_id: str, ext: str
    ) -> dict:
        content = await file.read()
        file_size = len(content)

        (save_dir / f"{doc_id}{ext}").write_bytes(content)

        return {"file_name": file.filename, "file_size": file_size}

    """
    分块上传
    """
    #这个函数是分块上传的单块处理器——每次接收一块，存进以 file_hash 命名的目录（文件名 chunk_N 记录顺序），
    # 然后检查已收块数是否等于总块数。收齐了就调 _merge_chunks 合并成完整文件；没齐就返回"继续"，前端接着传下一块。
    @classmethod
    async def _save_chunk(
        cls, db: AsyncSession, file: UploadFile, ext: str,
        chunk_number: int, total_chunks: int, file_hash: str | None,
        save_dir: Path, doc_id: str,
    ) -> dict:
        if not file_hash:#file_hash 是文件的 MD5 指纹，用来唯一标识"这些块属于同一个文件"。
            raise HTTPException(status_code=400, detail="分块上传必须提供 file_hash")

        chunk_dir = Path(settings.chunk_dir) / file_hash#用 file_hash 作为目录名，同一个文件的chunk在一个目录下
        chunk_dir.mkdir(parents=True, exist_ok=True)

        content = await file.read()#读这一块的内容
        chunk_path = chunk_dir / f"chunk_{chunk_number}"#如：chunk_1, chunk_2, ...
        chunk_path.write_bytes(content)#写这一块的内容到文件

        # 判断是否所有分块都上传完毕
        existing = set()
        for f in chunk_dir.iterdir():
            if f.name.startswith("chunk_"):
                existing.add(int(f.name.split("_")[1]))#提取文件名中的数字，收集已上传的块号

        if len(existing) == total_chunks:
            return await cls._merge_chunks(db, chunk_dir, file_hash, file.filename, ext, save_dir, doc_id)#收集齐了合并成完整文件
        else:
            uploaded = sorted(existing)
            return {"uploaded": uploaded, "total": total_chunks, "status": "continue"}# 没齐，返回已收的块号，前端继续传

    @classmethod
    async def save_document_record(
        cls, db: AsyncSession, doc_id: str, file_name: str, file_size: int,
        file_path: str, ext: str, kb_id: str, user: CurrentUser,
    ) -> dict:
        """通用：保存文档记录到数据库"""
        doc = Document(
            doc_id=doc_id,
            file_name=file_name,
            file_type=ext.lstrip("."),
            file_size=file_size,
            file_path=file_path,
            file_ext=ext,
            kb_id=kb_id,
            chunk_status="pending",
            upload_time=datetime.now(),
            upload_by=user.user_name,
            uploader_id=user.user_id,
            dept_id=user.dept_id,
        )
        await DocumentDao.add(db, doc)
        #DocumentEntity.model_validate(doc) 把 SQLAlchemy （doc）对象转成 Pydantic 对象 Document(ORM) → DocumentEntity(schema)
        #.model_dump(by_alias=True) 把 Pydantic 对象转成字典 字段名用别名（小驼峰）输出
        #mode="json" 转成能 JSON 序列化的类型 ，例如 datetime 转成字符串
        #为什么要转换环：ORM 对象 doc 是 SQLAlchemy 的 Document 实例，它带着数据库的连接信息、内部状态，不能直接返回给前端（JSON 序列化会出错，还会泄漏内部信息）。所以要转成干净的 DocumentEntity，再 dump 成字典返回。by_alias=True 的意思是：输出时用别名（小驼峰）命名字段，比如 file_name → fileName，符合前端习惯。
        #models/document.py 中的class Document(Base):# 继承 SQLAlchemy 的 Base 用于读写数据库的  数据库层  框架是SQLAlchemy
        #schemas/document.py 中的class DocumentEntity(BaseModel):# 继承 BaseModel 用于序列化数据  接口层  框架是Pydantic
        return DocumentEntity.model_validate(doc).model_dump(by_alias=True, mode="json")

    """
    合并分块
    """
    @classmethod
    async def _merge_chunks(
        cls, db: AsyncSession, chunk_dir: Path, file_hash: str,
        file_name: str, ext: str, save_dir: Path, doc_id: str,
    ) -> dict:
        file_path = save_dir / f"{doc_id}{ext}"
        total_size = 0
        chunk_files = sorted(chunk_dir.iterdir(), key=lambda f: int(f.name.split("_")[1]))

        with open(file_path, "wb") as out:
            for cf in chunk_files:
                total_size += out.write(cf.read_bytes())

        # 清理分块目录
        shutil.rmtree(chunk_dir, ignore_errors=True)#rmtree — remove tree，递归删除整个目录树（目录 + 里面所有文件、子目录）

        return {"doc_id": doc_id, "file_name": file_name, "file_size": total_size, "file_path": str(file_path)}

    @classmethod
    async def get_doc_list_by_scope(
            cls, db: AsyncSession, scope: str, user: CurrentUser
    ) -> list[dict]:
        """按范围获取文档列表"""
        from app.dao.document_dao import DocumentDao
        items = await DocumentDao.get_by_scope(
            db, scope=scope, user_id=user.user_id, dept_id=user.dept_id, limit=50
        )
        return [
            DocumentEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]

    @classmethod
    async def get_doc_page_by_kb(
            cls, db: AsyncSession, kb_id: str, page_num: int, page_size: int, keyword: str | None = None
    ) -> Tuple[list[dict], int]:
        """获取知识库下的文档分页列表"""
        from app.dao.document_dao import DocumentDao
        items, total = await DocumentDao.get_page(db, page_num=page_num, page_size=page_size, keyword=keyword, kb_id=kb_id)
        rows = [
            DocumentEntity.model_validate(item).model_dump(by_alias=True, mode="json")
            for item in items
        ]
        return rows, total

    """将文档解析任务推入 Redis 队列，后台 worker 异步执行。"""
    @staticmethod
    async def enqueue_parse_task(doc_id: str, user: CurrentUser) -> dict:
        from app.services.task_worker import QUEUE_KEY

        task = {
            "doc_id": doc_id,
            "user_id": user.user_id,
            "user_name": user.user_name,
            "dept_id": user.dept_id,
        }
        redis = await RedisClient.get_client()
        # QUEUE_KEY列表下添加任务
        await redis.rpush(QUEUE_KEY, json.dumps(task))
        return {"status": "accepted", "doc_id": doc_id}

