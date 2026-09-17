import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.core.database import get_db
from app.core.get_redis import RedisClient
from app.core.permission import RequirePermission
from app.dao.document_dao import DocumentDao
from app.dao.knowledge_base_dao import KnowledgeBaseDao

from app.services.document_service import DocumentService
from app.schemas.document import DocumentEntity
from app.utils.auth_util import AuthUtil, CurrentUser
from app.utils.response_util import ResponseUtil


class ParseRequest(BaseModel):
    doc_id: str

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


router = APIRouter(prefix="/doc", tags=["文档"])

"""
分块上传
"""
@router.post("/upload")
async def upload_file(
        #文件上传（multipart/form-data）这种请求，跟普通 JSON 不一样，数据是分字段传的。FastAPI 用两个函数声明参数来源：
        #File(...):这个参数来自文件，接收上传的文件二进制
        #Form(...)：这个参数来自普通表单字段
        #上传文件时，文件用 File()，其他附带字段用 Form()。如果你用普通 JSON 的 Body() 或者直接声明参数，会报错——因为文件上传的 Content-Type 是 multipart/form-data，不是 application/json。
        #括号里的...什么意思：，FastAPI 用它来表示 "这个参数是必填的，没有默认值"。
        
        file: UploadFile = File(...),#必填的，必须传文件
        kbId: str = Form(...),  # 文件上传只能用Form()
        db: AsyncSession = Depends(get_db),
        user: CurrentUser = Depends(RequirePermission("ai:doc:add")),
        chunkNumber: int | None = Form(None),  # 当前块号 可传可不传，不传就是None
        totalChunks: int | None = Form(None),  # 总块数
        fileHash: str | None = Form(None),  # 文件md5
):
    result = await DocumentService.upload_file(
        db, file, kbId, user, chunkNumber, totalChunks, fileHash,
    )
    return ResponseUtil.success(data=result)

"""
文档解析：推入 Redis 队列后台执行，不阻塞接口
"""
@router.post("/parse")
async def parse_document(
        body: ParseRequest,
        user: CurrentUser = Depends(RequirePermission("ai:doc:parse")),
):
    # 异步解析文档
    await DocumentService.enqueue_parse_task(body.doc_id, user)


    return ResponseUtil.success(data={"status": "accepted", "doc_id": body.doc_id})


"""
文档列表（分页）
"""
@router.get("/list")
async def get_doc_list(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:doc:list")),
    kb_id: str = "",
    page_num: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
):
    rows, total = await DocumentService.get_doc_page_by_kb(db, kb_id, page_num, page_size, keyword)
    return ResponseUtil.paginate(rows=rows, total=total, page_num=page_num, page_size=page_size)


"""
文档列表（按范围：personal / public）
"""
@router.get("/scope")
async def get_doc_by_scope(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:doc:list")),
    scope: str = "personal",
):
    rows = await DocumentService.get_doc_list_by_scope(db, scope, user)
    return ResponseUtil.success(data=rows)


"""
删除文档
"""
@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(RequirePermission("ai:doc:delete")),
):
    doc = await DocumentDao.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if str(doc.uploader_id) != str(user.user_id):
        raise HTTPException(status_code=403, detail="只能删除自己的文档")

    # 删除物理文件
    if doc.file_path:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink(missing_ok=True)

    await DocumentDao.delete(db, doc_id)
    return ResponseUtil.success()


"""
文件预览/下载 — 支持 ?token=xxx 查询参数（用于 <a> 标签新标签页打开）
"""
@router.get("/view/{doc_id}")
async def view_document(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 手动解析 token：优先请求头，其次查询参数
    token_str = ""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token_str = auth[7:]
    else:
        token_str = request.query_params.get("token", "")
    if not token_str:
        raise HTTPException(status_code=401, detail="未登录或token无效")
    try:
        payload = jwt.decode(token_str, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="token已过期或无效")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="token无效")

    doc = await DocumentDao.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    kb = await KnowledgeBaseDao.get_by_id(db, doc.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if str(doc.uploader_id) != str(user_id) and kb.public_flag != "1":
        raise HTTPException(status_code=403, detail="无权访问该文档")

    file_path = Path(doc.file_path) if doc.file_path else None
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    media_type = "application/pdf" if doc.file_ext == ".pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    disposition = "inline" if doc.file_ext == ".pdf" else "attachment"
    encoded_name = quote(doc.file_name)

    def iter_file():
        with open(str(file_path), "rb") as f:
            yield from f

    return StreamingResponse(
        iter_file(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{encoded_name}"; filename*=UTF-8\'\'{encoded_name}',
            "Content-Length": str(file_path.stat().st_size),
        },
    )
