from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.db import create_db_and_tables, get_async_session, Post
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from app.schemas import PostCreate, PostReturn
from sqlalchemy import select
import shutil
import os
import uuid
import tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

# 执行fastapi的时候执行数据库创建
test = FastAPI(lifespan=lifespan)


@test.post('/upload')
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None;

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()
        
        

    post = Post(caption=caption, url='dummy url',
                file_name="post.png", file_type="png")

    session.add(post)
    await session.commit()       # 提交到数据库，数据库生成 id
    await session.refresh(post)  # 从数据库重新读取，更新 post 对象的属性

    return post


@test.get('/feed')
async def get_feed(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    # result.all() 返回：
    # [(<Post object 1>,), (<Post object 2>,), (<Post object 3>,)]
    print(result.all())
    posts = [row[0] for row in result.all()]
    

    post_data = []

    for post in posts:
        post_data.append({
            "id": str(post.id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),
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
