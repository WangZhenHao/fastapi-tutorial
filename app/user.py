import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from app.db import User, get_user_db

SECRET = "sdfsffasfdsfdsaf"  # 用于加密 JWT token 的密钥（生产环境需使用环境变量）

# ========== 用户管理器 ==========
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    用户管理器 - 处理用户相关的业务逻辑
    - UUIDIDMixin: 使用 UUID 作为用户 ID 类型
    - BaseUserManager: 提供用户管理基础功能（注册、登录、重置密码等）
    """
    
    # 重置密码 token 的加密密钥
    reset_password_token_secret = SECRET
    # 邮箱验证 token 的加密密钥
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """
        用户注册成功后的回调函数
        用途：发送欢迎邮件、记录日志、创建默认配置等
        """
        print(f"User {user.id} has registered.")  # 实际应用中应发送邮件或记录到日志系统

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """
        用户忘记密码请求后的回调函数
        用途：发送包含重置密码链接的邮件
        token: 重置密码的临时凭证，需要包含在邮件链接中
        """
        print(f"User {user.id} has forgot their password. Reset token: {token}")

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """
    获取用户管理器实例的依赖函数
    - 依赖 get_user_db 获取数据库会话
    - yield 使得 FastAPI 可以自动管理资源生命周期
    """
    yield UserManager(user_db)


# ========== 认证配置 ==========
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
"""
Bearer 传输方式 - 定义客户端如何发送 token
- tokenUrl: 客户端获取 token 的登录端点 URL
- 客户端在请求头中携带: Authorization: Bearer <token>
"""

def get_jwt_strategy() -> JWTStrategy:
    """
    创建 JWT 策略的工厂函数
    JWT (JSON Web Token) 是一种无状态的认证方式
    - secret: 用于签名 JWT 的密钥
    - lifetime_seconds: token 有效期（3600秒 = 1小时）
    """
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",                    # 认证后端的唯一标识名称
    transport=bearer_transport,    # token 传输方式（如何接收/发送 token）
    get_strategy=get_jwt_strategy, # token 生成/验证策略（如何创建/解析 JWT）
)
"""
认证后端 - 整合传输方式和策略，定义完整的认证流程
"""


# ========== FastAPI Users 主实例 ==========
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,      # 用户管理器工厂函数
    [auth_backend],        # 支持的认证后端列表（支持多后端）
)
"""
FastAPI Users 主实例 - 提供所有用户相关功能
会自动生成以下路由：
- /auth/jwt/login      POST    - 登录
- /auth/jwt/logout     POST    - 登出
- /auth/register       POST    - 注册
- /auth/forgot-password POST   - 忘记密码
- /auth/reset-password POST    - 重置密码
- /auth/verify         POST    - 验证邮箱
- /auth/me             GET/PATCH - 获取/更新当前用户信息
"""

# ========== 依赖项 ==========
current_active_user = fastapi_users.current_user(active=True)
"""
当前活跃用户依赖项
- active=True: 要求用户已验证邮箱且账号激活
- 用于需要登录才能访问的接口
- 如果未登录或账号未激活，自动返回 401 未授权错误
"""