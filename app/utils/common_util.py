from uuid import uuid4


def generate_fast_id() -> str:
    """生成32位UUID主键（去掉横线）"""
    return uuid4().hex


