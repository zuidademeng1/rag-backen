"""
Optional mapping of local absolute media paths to public URLs (HTTPS, CDN, S3, etc.).

Implements the environment-variable contract described in docs and README:
when ingestion runs on a server but retrieval/UI runs elsewhere, stored paths
must remain valid locally while a parallel public URL can be shown to clients.

NOTE: ``attach_public_media_urls`` is currently invoked from the MinerU
parser path only. Other parsers (e.g. Docling) will not yield
``*_public_url`` fields until this helper is wired into their content_list
post-processing too.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# content_list fields that hold filesystem paths to raster or figure assets
MEDIA_PATH_FIELDS: tuple[str, ...] = (
    "img_path",#普通图片路径
    "table_img_path",#表格图片路径
    "equation_img_path",#公式图片路径
)

# Track which misconfiguration shape we have already warned about so we don't
# spam the log once per content_list item. Reset whenever the env state goes
# back to either "fully unset" or "fully set".
_MISCONFIG_WARNED: set[str] = set()


def _resolve_strip_prefix(strip_prefix: str) -> Path | None:
    """功能： 把传入的前缀字符串转成标准化的绝对路径对象（Path）。"""
    try:
        return Path(strip_prefix).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def public_url_for_local_path(
    local_abs: str,
    *,
    base_url: str,
    strip_prefix: str,
) -> str | None:
    """
    Build ``https://.../relative/path`` from a local absolute path by stripping
    a known filesystem root and appending the remainder to ``base_url``.
    """
    """
    功能： 把本地路径转成公网 URL，核心逻辑是"剥离本地根目录前缀 + 拼上公网域名"。
    本地路径:  /data/uploads/img/123.png
    strip_prefix: /data/uploads          ← 要剥掉的前缀
    base_url:  https://cdn.example.com   ← 公网地址
    → 剥离后相对路径: img/123.png
    → 拼上 base_url: https://cdn.example.com/img/123.png
    """
    if not local_abs or not base_url or not strip_prefix:
        return None
    root = _resolve_strip_prefix(strip_prefix)
    if root is None:
        return None
    try:
        abs_path = Path(local_abs).resolve()
        rel = abs_path.relative_to(root)
    except (ValueError, OSError, RuntimeError):
        return None
    return f"{base_url.rstrip('/')}/{rel.as_posix()}"


"""
为文档中的媒体文件（图片等）生成可公开访问的 URL
"""
def attach_public_media_urls(item: dict) -> None:

    base = os.environ.get("RAGANYTHING_PUBLIC_ASSET_BASE_URL", "").strip() # 公网域名
    strip = os.environ.get("RAGANYTHING_PUBLIC_ASSET_STRIP_PREFIX", "").strip()# 本地前缀

    if not base and not strip:
        _MISCONFIG_WARNED.clear()
        return
    if base and not strip:
        if "base_only" not in _MISCONFIG_WARNED:
            logger.warning(
                "RAGANYTHING_PUBLIC_ASSET_BASE_URL is set but "
                "RAGANYTHING_PUBLIC_ASSET_STRIP_PREFIX is not; "
                "skipping public URL attachment."
            )
            _MISCONFIG_WARNED.add("base_only")
        return
    if strip and not base:
        if "strip_only" not in _MISCONFIG_WARNED:
            logger.warning(
                "RAGANYTHING_PUBLIC_ASSET_STRIP_PREFIX is set but "
                "RAGANYTHING_PUBLIC_ASSET_BASE_URL is not; "
                "skipping public URL attachment."
            )
            _MISCONFIG_WARNED.add("strip_only")
        return
    _MISCONFIG_WARNED.clear()

    if not isinstance(item, dict):
        return

    for field in MEDIA_PATH_FIELDS:# 遍历三个媒体字段
        raw = item.get(field)
        if not raw or not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue
        if s.startswith(("http://", "https://", "s3://")): # 已经是公网URL就跳过
            continue
        url = public_url_for_local_path(s, base_url=base, strip_prefix=strip)# 本地路径 → 公网URL
        if url:
            item[f"{field}_public_url"] = url # 加上 xxx_public_url 字段
#它不覆盖原字段，而是新增一个带 _public_url 后缀的字段。比如 img_path 对应新增 img_path_public_url。原本地路径保留（服务器自己用），公网 URL 给前端展示。