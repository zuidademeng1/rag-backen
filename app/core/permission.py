from fastapi import Depends, HTTPException

from app.utils.auth_util import AuthUtil, CurrentUser


class RequirePermission:
    """权限校验依赖：要求当前用户拥有指定权限标识"""

    def __init__(self, perm: str):
        self.perm = perm

    async def __call__(self, user: CurrentUser = Depends(AuthUtil.get_current_user)) -> CurrentUser:
        if not user.is_admin and self.perm not in user.permissions:
            raise HTTPException(status_code=403, detail=f"无权限: {self.perm}")
        return user


class RequireRole:
    """角色校验依赖：要求当前用户拥有指定角色标识"""

    def __init__(self, role: str):
        self.role = role

    async def __call__(self, user: CurrentUser = Depends(AuthUtil.get_current_user)) -> CurrentUser:
        if not user.is_admin and self.role not in user.roles:
            raise HTTPException(status_code=403, detail=f"需要角色: {self.role}")
        return user
