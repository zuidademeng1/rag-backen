import os
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 把.env文件加载到环境变量中   
load_dotenv()


class AppSettings(BaseSettings):
    app_name: str = '智慧办公系统'
    app_host: str = '0.0.0.0'
    app_port: int = 9090
    app_reload: bool = True
    app_version: str = '1.0.0'
    app_root_path: str = '/dev-api'


class JwtSettings(BaseSettings):
    jwt_secret_key: str = 'b01c66dc2c58dc6a0aabfe23edc56be36226de378bf87f72c0c795dda1qaz2ws'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 1440


class DataBaseSettings(BaseSettings):
    db_type: Literal['mysql', 'postgresql'] = 'postgresql'
    db_host: str = '127.0.0.1'
    db_port: int = 5432
    db_username: str = 'postgres'
    db_password: str = '123456'
    db_database: str = 'ruoyi-ai'
    db_echo: bool = True
    db_max_overflow: int = 10
    db_pool_size: int = 10
    db_pool_recycle: int = 3600
    db_pool_timeout: int = 30
    db_slow_query: float = 0.2  # 慢SQL阈值（秒），超过则打印警告日志


class RedisSettings(BaseSettings):
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_password: str = '123456'
    redis_database: int = 3

# Milvus配置
class MilvusSettings(BaseSettings):
    milvus_host: str = '127.0.0.1'
    milvus_port: int = 19530
    milvus_uri: str | None = None
    milvus_token: str | None = None
    milvus_collection: str = 'ai_embeddings'
    milvus_dimension: int = 1024
    milvus_index_type: str = 'AUTOINDEX'
    milvus_metric_type: str = 'COSINE'
    milvus_timeout: int = 30


# 上传配置
class UploadSettings(BaseSettings):
    upload_dir: str = "uploads"
    chunk_dir: str = "uploads/chunks"
    max_file_size: int = 524288000  # 500MB
    allowed_extensions: list[str] = ['.doc', '.docx', '.pdf']


# RAG配置
class RagSettings(BaseSettings):
    embedding_url: str = 'http://127.0.0.1:9003'


class LlmSettings(BaseSettings):
    llm_base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    llm_api_key: str = ''
    llm_model: str = 'qwen3-max'


class Settings(AppSettings, JwtSettings, DataBaseSettings, RedisSettings, UploadSettings, MilvusSettings, RagSettings, LlmSettings):
    log_level: str = 'INFO'
    log_dir: str = 'logs'


settings = Settings()
