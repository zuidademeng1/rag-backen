from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.utils.response_util import ResponseUtil


class ServiceException(Exception):
    """业务自定义异常"""

    def __init__(self, msg: str = "业务异常", code: int = 400):
        self.msg = msg
        self.code = code
        super().__init__(self.msg)


async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
    """业务异常处理"""
    return JSONResponse(
        status_code=exc.code,
        content=ResponseUtil.error(msg=exc.msg, code=exc.code).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseUtil.error(msg=exc.detail, code=exc.status_code).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求参数校验异常处理"""
    errors = exc.errors()
    messages = [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in errors]
    return JSONResponse(
        status_code=422,
        content=ResponseUtil.error(msg="; ".join(messages), code=422).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局未捕获异常处理"""
    return JSONResponse(
        status_code=500,
        content=ResponseUtil.error(msg="服务器内部错误", code=500).model_dump(),
    )
