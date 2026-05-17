from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.db import create_db_and_tables, get_async_session, Post, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from app.schemas import PostCreate, PostReturn,UserRead, UserCreate, UserUpdate
from sqlalchemy import select
import shutil
import os
import uuid
from app.user import auth_backend, current_active_user, fastapi_users

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

# 执行fastapi的时候执行数据库创建
test = FastAPI(lifespan=lifespan)
# 登录/登出路由
test.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
# 注册路由
test.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
# 重置密码路由
test.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
 # 邮箱验证路由
test.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
# 用户管理路由（GET/PATCH /me）
test.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

@test.delete('/posts/{post_id}')
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    try: 
        post_uuid = uuid.UUID(post_id)
        post = await session.execute(select(Post).where(Post.id == post_uuid))
        # 这行代码用于从查询结果中获取第一个对象
        post = post.scalars().first();

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")

        await session.delete(post)
        await session.commit()

        return { "status": "success", "message": "Post deleted successfully" }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@test.post('/upload')
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    original_filename = file.filename or "upload"
    file_ext = os.path.splitext(original_filename)[1]
    stored_file_name = f"{uuid.uuid4().hex}{file_ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, stored_file_name)

    try:
        with open(file_path, "wb") as upload_file:
            shutil.copyfileobj(file.file, upload_file)
    
    except Exception as e:
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()
        
        

    post = Post(
        user_id=user.id,
        caption=caption,
        url=file_path,
        file_name=stored_file_name,
        file_type=file.content_type or file_ext.lstrip(".") or "unknown"
    )

    session.add(post)
    await session.commit()       # 提交到数据库，数据库生成 id
    await session.refresh(post)  # 从数据库重新读取，更新 post 对象的属性

    return post


@test.get('/feed')
async def get_feed(session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    # result.all() 返回：
    # [(<Post object 1>,), (<Post object 2>,), (<Post object 3>,)]
    # print(result.all())
    posts = [row[0] for row in result.all()]

    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}

    post_data = []

    for post in posts:
        post_data.append({
            "id": str(post.id),
            "caption": post.caption,
            "user_id": str(post.user_id),
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),
            "is_owner": post.user_id == user.id,
            "email": user_dict.get(post.user_id, "Unknown")
        })
    
    return { "posts": post_data }


# text_post = {
#     1: { "title": "new post", "content": "this is a new post" },
#     2: { "title": "new post2", "content": "this is a new post2" },
#     3: { "title": "new post3", "content": "this is a new post3" },
#     4: { "title": "new post4", "content": "this is a new post4" },

# }

# users = [
#     {'name': '张三', 'age': 20},
#     {'name': '李四', 'age': 25},
#     {'name': '王五', 'age': 30}
# ]

# @test.get('/posts')
# def get_all_post(limit: int = None):
#    if limit:
#        return list(text_post.values())[:limit]
#    return text_post

# @test.get('/posts/{id}')
# def get_post(id: int):
#     if id not in text_post:
#         raise HTTPException(status_code=404, detail="Post not found")

#     return text_post.get(id)

# @test.post('/posts')
# def create_post(post: PostCreate) -> PostReturn:
#     return post

# @test.get('/')
# def root():
#     res =  {'name': '张三', 'age': 20} not in users
#     return text_post.values()
