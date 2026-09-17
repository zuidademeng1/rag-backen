from pymilvus import MilvusClient as MilvusGrpcClient

from app.config.config import settings


class MilvusClient:
    _client: MilvusGrpcClient | None = None

    @classmethod
    def _build_connection_args(cls) -> dict:
        if settings.milvus_uri:
            return {
                "uri": settings.milvus_uri,
                "token": settings.milvus_token,
                "timeout": settings.milvus_timeout,
            }
        return {
            "uri": f"http://{settings.milvus_host}:{settings.milvus_port}",
            "timeout": settings.milvus_timeout,
        }

    @classmethod
    async def connect(cls) -> None:
        """连接Milvus向量数据库

        支持本地连接（host+port）和云服务连接（uri+token）

        Raises:
            ConnectionError: 连接失败时抛出
        """
        if cls._client is not None:
            return

        try:
            args = cls._build_connection_args()
            cls._client = MilvusGrpcClient(**args)
            cls._client.get_server_version()
        except Exception as e:
            cls._client = None
            raise ConnectionError(f"Milvus连接失败: {e}")

    @classmethod
    async def close(cls) -> None:
        """断开Milvus连接"""
        if cls._client is not None:
            cls._client.close()
            cls._client = None

    @classmethod
    def get_client(cls) -> MilvusGrpcClient:
        if cls._client is None:
            raise ConnectionError("Milvus未连接，请先调用 connect()")
        return cls._client

    @classmethod
    async def test_connection(cls) -> bool:
        """测试Milvus连接是否正常

        Returns:
            连接成功返回True，失败返回False
        """
        try:
            await cls.connect()
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import asyncio

    async def main():
        print("Milvus 连接成功" if await MilvusClient.test_connection() else "Milvus 连接失败")
        await MilvusClient.close()

    asyncio.run(main())